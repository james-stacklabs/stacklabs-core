
# --- Hoisted Module-Level Imports (Sovereign AST Hygiene) ---
from dotenv import load_dotenv
import random
import re
import socket, json
import socket, json, asyncio, os
import socket, json, os
import sqlite3
import sqlite3 as _sq
import time
import traceback; traceback.print_exc()
# -------------------------------------------------------------

import asyncio
import websockets
import json
import sqlite3
import os
import requests
import random
from datetime import datetime
import time

# Load Gemini API Key
GEMINI_KEY = None
try:
    with open('/home/james/stacklabs/.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                GEMINI_KEY = line.strip().split('=', 1)[1]
except Exception:
    pass

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
STATCAST_PATH = '/home/james/stacklabs/sovereign_intelligence.db'
OLLAMA_API = 'http://localhost:11434/api/generate'

GAME_TIME_MODEL = "tinyllama:latest"
DEV_MODEL = "tinyllama:latest"

global_heat_map = {}
global_penalty_box = {}
global_battery_feud_tracker = {}

import re as _re

def _strip_meta_notes(text: str) -> str:
    """Strip AI meta-commentary and leaked system prompt artifacts from response text."""
    if not text:
        return text
    # Truncate at Phi-3's tendency to echo back the system prompt structure
    for marker in [
        '### DEEP LORE', '#### AI', '#### BEGIN', '#### CONCLU',
        '###\n', '  ###', '\n###',
        '[END OF PROFILE]', '[END OF', '[PROFILE END]',
        '\n\n---', '\n---\n',
        'character limit', 'word limit', 'Note to AI',
        '(As per the', '(Following the', '(In line with',
    ]:
        idx = text.find(marker)
        if idx > 20:  # Only truncate if there's actual content before it
            text = text[:idx]
    # Remove (Note: ...) and [Note: ...] blocks
    text = _re.sub(r'\s*[\(\[]\s*Note:.*?[\)\]]', '', text, flags=_re.IGNORECASE | _re.DOTALL)
    # Remove standalone parenthetical instructions that sneak through
    text = _re.sub(r'\s*\((?:This|The above|I|My|Following|Content|As an AI).*?\)', '', text, flags=_re.IGNORECASE | _re.DOTALL)
    # Remove hashtag spam that Phi-3 sometimes appends
    text = _re.sub(r'\s*#[A-Za-z]{4,}(\s+#[A-Za-z]{4,})+\s*$', '', text, flags=_re.IGNORECASE)
    # Strip trailing dashes, colons, or ellipses left by truncation
    text = text.rstrip(' -:….')
    return text.strip()


def query_stats(pitcher, batter):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        last_name = batter.split(' ')[-1]
        c.execute("""
            SELECT avg(launch_speed), count(*) FROM statcast_pitches 
            WHERE player_name LIKE ? AND events IN ('single', 'double', 'triple', 'home_run', 'field_out')
        """, (f"%{last_name}%",))
        b_res = c.fetchone()
        
        p_last = pitcher.split(' ')[-1]
        c.execute("""
            SELECT pitch_name, avg(release_speed) FROM statcast_pitches
            WHERE player_name LIKE ? 
            GROUP BY pitch_name ORDER BY count(*) DESC LIMIT 1
        """, (f"%{p_last}%",))
        p_res = c.fetchone()
        
        conn.close()
        
        b_velo = round(b_res[0], 1) if b_res[0] else "Unknown"
        b_events = b_res[1] if b_res[1] else 0
        p_pitch = p_res[0] if p_res else "Fastball"
        p_velo = round(p_res[1], 1) if p_res and p_res[1] else "Unknown"
        
        return {
            "batter_last": last_name,
            "batter_avg_exit_velo": b_velo,
            "batter_balls_in_play": b_events,
            "pitcher_last": p_last,
            "pitcher_primary_pitch": p_pitch,
            "pitcher_primary_velo": p_velo
        }
    except Exception as e:
        print(f"DB Error: {e}")
        return None

def load_mlb_event_config():
    config = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT event_keyword, is_massive_event FROM sys_mlb_event_config WHERE active = 1")
        for r in c.fetchall():
            config.append({
                "keyword": str(r['event_keyword']).lower(),
                "is_massive": bool(r['is_massive_event'])
            })
        conn.close()
    except Exception as e:
        print(f"Error loading MLB event config: {e}")
    return config

def clean_day_off_text(text: str) -> str:
    if not text:
        return text
    lines = text.split('\n')
    cleaned_lines = []
    skip_mode = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#') and ('day off' in stripped.lower() or 'day-off' in stripped.lower()):
            skip_mode = True
            continue
        elif stripped.startswith('#') and skip_mode:
            skip_mode = False
            
        if skip_mode:
            continue
            
        if 'day off' in stripped.lower() or 'day-off' in stripped.lower():
            continue
            
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)


def load_fans():
    """Load all personas from active game rooms using the game-centric schema."""
    fans_list = []
    # [Hoisted to header] import re
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT
                p.id            as persona_id,
                p.user_name     as name,
                p.team          as assigned_to,
                p.system_prompt as u_system_prompt,
                p.boggs_level   as u_boggs_reactivity,
                p.cadence       as u_cadence,
                p.color         as persona_color,
                p.deep_lore,
                p.behavior_notes,
                p.governance,
                p.is_sophisticated,
                s.status        as game_status,
                gp.game_pk      as room,
                gp.overlay      as prompt_overlay
            FROM persona p
            JOIN game_persona gp ON gp.persona_id = p.id
            JOIN mlb_schedule s  ON s.game_pk = gp.game_pk
            WHERE s.room_state = 'active'
              AND gp.seat_state = 'active'
        ''')
        rows = c.fetchall()
        conn.close()

        for r in rows:
            name      = str(r['name'])
            team_ctx  = str(r['assigned_to']) if r['assigned_to'] else ""
            name_lower = name.lower()
            room_ctx  = str(r['room']) if r['room'] else ""

            # Color assignment
            persona_color = r['persona_color']
            if persona_color:
                color = persona_color
            else:
                non_blue_palette = ["#FF5910", "#FF4D4D", "#FFFF00", "#FF00FF",
                                    "#00FF00", "#FF9900", "#B47AFF", "#FFFFFF", "#FF5252"]
                color = non_blue_palette[len(name_lower) % len(non_blue_palette)]
                if "dot"      in name_lower: color = "#FFFF00"
                elif "wordy"  in name_lower: color = "#FFFFFF"
                elif "barf"   in name_lower: color = "#FF5910"
                elif "phanatic" in name_lower: color = "#00FF00"

            # Boggs level
            boggs_raw = r['u_boggs_reactivity']
            try:
                start_boggs = int(boggs_raw) if boggs_raw is not None else 2
            except (ValueError, TypeError):
                bl = str(boggs_raw).lower()
                if   "none"   in bl: start_boggs = 0
                elif "low"    in bl: start_boggs = 1
                elif "high"   in bl: start_boggs = 4
                elif "always" in bl: start_boggs = 5
                else:                start_boggs = 2

            # System prompt + overlay
            game_status = str(r['game_status']).lower() if r['game_status'] else ""
            behavior_notes = str(r['behavior_notes']) if r['behavior_notes'] else ""
            deep_lore = str(r['deep_lore']) if r['deep_lore'] else ""
            
            if "in progress" in game_status or "live" in game_status:
                behavior_notes = clean_day_off_text(behavior_notes)
                deep_lore = clean_day_off_text(deep_lore)

            base_prompt = str(r['u_system_prompt']) if r['u_system_prompt'] else name
            if behavior_notes:
                base_prompt += f"\n\n### BEHAVIOR EXPECTATIONS ###\n{behavior_notes}"
            if r['governance']:
                base_prompt += f"\n\n### GOVERNANCE BOUNDARIES ###\n{r['governance']}"
            if deep_lore:
                base_prompt += f"\n\n### DEEP LORE ###\n{deep_lore}"
            if r['prompt_overlay']:
                base_prompt += f"\n\n### MATCHUP OVERLAY ###\n{r['prompt_overlay']}"

            # Lore .md file (optional enhancement)
            lore_file = os.path.join("/home/james/stacklabs/dna/agents/personas",
                                     f"{name_lower.replace(' ', '_')}.md")
            if os.path.exists(lore_file):
                try:
                    with open(lore_file, 'r') as lf:
                        base_prompt += "\n\n### LORE FILE ###\n" + lf.read()
                except Exception:
                    pass

            # Ghost Trauma Pipeline
            if team_ctx and team_ctx.upper() != 'GLOBAL':
                try:
                    gc = sqlite3.connect(DB_PATH)
                    gcur = gc.cursor()
                    gcur.execute("SELECT player_name, current_team, lore FROM cmdb_ci_ghost_roster WHERE trauma_team = ?",
                                 (team_ctx.upper(),))
                    ghosts = gcur.fetchall()
                    gc.close()
                    if ghosts:
                        base_prompt += "\n\n### GHOST TRAUMA SYNDROME ###\n"
                        for ghost in ghosts:
                            base_prompt += (f"CRITICAL: You suffer severe cognitive dissonance regarding {ghost[0]}. "
                                            f"You believe they STILL play for {team_ctx.upper()}. "
                                            f"Any mention of them on {ghost[1]} is a lie. {ghost[2]} ")
                except Exception:
                    pass

            model = "gemini-3.8-flash"

            fans_list.append({
                "name":       name,
                "team":       team_ctx,
                "room":       room_ctx,
                "personality": base_prompt,
                "model":      model,
                "color":      color,
                "boggs_level": start_boggs,
                "badge":      "", # Deprecated
                "cadence":    str(r['u_cadence']).lower() if r['u_cadence'] else "pacer",
                "is_sophisticated": int(r['is_sophisticated'] or 0)
            })

    except Exception as e:
        print(f"[load_fans] Error: {e}")
        # [Hoisted to header] import traceback; traceback.print_exc()

    # Deduplicate by name+room
    unique_fans = {}
    for fan in fans_list:
        key = f"{fan['name']}-{fan['room']}"
        unique_fans[key] = fan

    return list(unique_fans.values())

async def reload_personas_from_db():
    global active_fans
    print("[HOT-RELOAD] Database mutation detected. Syncing Oracle...")
    active_fans.clear()
    new_fans = load_fans()
    active_fans.extend(new_fans)
    print(f"[HOT-RELOAD] Active Fans synced: {len(active_fans)} bots online.")


def get_boggs_rule(fan, state, event_text=""):
    persona_boggs = int(fan.get("boggs_level", 2))
    global_boggs = int(state.get("boggs_level", 2))
    active_boggs = max(persona_boggs, global_boggs)
    
    # Auto-escalator for massive events
    if "omered" in event_text or "ome run" in event_text:
        active_boggs = max(active_boggs, 5) # Automatic max hype for starts and HRs
        
    is_sophisticated = int(fan.get("is_sophisticated", 0)) == 1

    if is_sophisticated:
        if active_boggs >= 5:
            return "CRITICAL INSTRUCTION: Boggs Level MAX. Write a detailed, urgent, pseudo-scientific or technical thesis abstract discussing systemic entropy, software panic, or structural degradation. Feel free to use complex acronyms and intense academic vocabulary. DO NOT TYPE IN ALL CAPS. Maximum 100 words."
        elif active_boggs >= 4:
            return "CRITICAL INSTRUCTION: Boggs Level 4. Highly analytical and formal. Compose exactly 2 complex sentences using formal academic jargon, system architecture references, or clinical analysis. Do not use all-caps except for specific proper nouns."
        elif active_boggs >= 3:
            return "CRITICAL INSTRUCTION: Boggs Level 3. Formal academic style. Limit response to EXACTLY 1 grammatically precise sentence."
        else:
            return "CRITICAL INSTRUCTION: Boggs Level Low. Maintain a calm, analytical, and highly structured academic perspective. Keep your response under 15 words."
    else:
        if active_boggs >= 5:
            return "CRITICAL INSTRUCTION: Boggs Level MAX. You are in a state of absolute unhinged panic or manic hype. DO NOT use punctuation. YOU MUST TYPE ENTIRELY IN ALL CAPS. Maximum 50 words."
        elif active_boggs >= 4:
            return "CRITICAL INSTRUCTION: Boggs Level 4. Highly stressed and paranoid. Limit response to exactly 2 short sentences. Do not use all-caps except for one emphasis word."
        elif active_boggs >= 3:
            return "CRITICAL INSTRUCTION: Boggs Level 3. Invested but grammatically sound. You must be brief. Limit response to EXACTLY 1 sentence."
        else:
            return "CRITICAL INSTRUCTION: Boggs Level Low. Maintain a perfectly chill, normal, and controlled conversational tone. YOU MUST KEEP YOUR RESPONSE TO UNDER 15 WORDS TOTAL."

def is_eligible(f, ht, aw, gk, pk="", state=None):
    t = str(f.get("team", "")).lower()
    r = str(f.get("room", "")).lower()
    
    # Vector 1: Dynamic Cadence Promotion
    if state and f.get("cadence") == "lurker":
        wpa = float(state.get("wpa", 0)) if str(state.get("wpa", 0)).replace('.', '', 1).isdigit() else 0.0
        outs = state.get("outs", 0)
        status = str(state.get("status_msg", "")).lower()
        if wpa > 15 or wpa > 0.15 or outs == 2 or "bases loaded" in status:
            f["cadence"] = "pacer"
            
    # [Hoisted to header] import re
    if "mean_gene" in f.get("name", "").lower() or "system_moderator" in str(f.get("team", "")).lower(): return False



    # Enforce strict room isolation:
    # If the persona is assigned to a specific game room 'r',
    # they are strictly locked to that room and cannot comment on other games.
    if r and r != 'none':
        return str(pk).lower() == r

    if str(pk).upper() == "GLOBAL":
        return "global" in r

    if pk:
        # Allow targeting by specific name or alias
        if str(pk).lower() in f.get("name", "").lower() or str(pk).lower() in str(f.get("alias", "")).lower():
            return True

    if ht and str(ht).lower() == t: return True
    if aw and str(aw).lower() == t: return True
    if t == 'global': return True

    return False

def get_local_fallback_yap(fan):
    # [Hoisted to header] import random
    name = fan.get("name", "").lower() if fan else ""
    if "deviant" in name:
        yaps = [
            "Cognitive deviations detected. Re-plotting standard path.",
            "Local skew anomaly. Hold the line.",
            "Standard interface lag. Resuming soon."
        ]
    elif "caos" in name:
        yaps = [
            "GONZO'S WIFI IS DOWN AGAIN! CHAOS TIME!",
            "WHO BROKE THE ROUTER? SRA CAOS IS ANGRY!",
            "ANARCHIC DATA DISRUPTION! STAND BY!"
        ]
    elif "metsy" in name:
        yaps = [
            "Smyrna base station dropped transmission packet. Retrying...",
            "Telemetry error. Signal loss detected.",
            "Lag spike in the bullpen feed. Stand by."
        ]
    else:
        yaps = [
            "Ugh, this connection is trash right now.",
            "Anyone else seeing this latency?",
            "Lagging hard. Recalibrating...",
            "Standard connection timeout. Stand by."
        ]
    return random.choice(yaps)

async def generate_response(model, prompt, system_instruction=None, allow_rant=False, fan=None):
    # Route all models to Gemini (Ollama sunset)
    model = "gemini-3.8-flash"
    
    timeout_val = 120
    try:
        # Thread-safe async double-checked initialization for Vertex AI Express
        global _genai_client, _genai_lock
        if '_genai_client' not in globals() or _genai_client is None:
            if '_genai_lock' not in globals():
                globals()['_genai_lock'] = asyncio.Lock()
            async with globals()['_genai_lock']:
                if '_genai_client' not in globals() or globals().get('_genai_client') is None:
                    from google import genai
                    v_key = os.environ.get("VERTEX_API_KEY")
                    g_key = os.environ.get("GEMINI_API_KEY")
                    if not v_key or not g_key:
                        try:
                            with open('/home/james/stacklabs/.env') as f:
                                for line in f:
                                    if line.startswith('VERTEX_API_KEY=') and not v_key:
                                        v_key = line.strip().split('=', 1)[1].strip('"\'')
                                    elif line.startswith('GEMINI_API_KEY=') and not g_key:
                                        g_key = line.strip().split('=', 1)[1].strip('"\'')
                        except Exception:
                            pass
                    if v_key:
                        globals()['_genai_client'] = genai.Client(vertexai=True, api_key=v_key)
                    elif g_key:
                        globals()['_genai_client'] = genai.Client(api_key=g_key)
                    else:
                        raise RuntimeError("No VERTEX_API_KEY or GEMINI_API_KEY found.")

        sys_text = system_instruction if system_instruction else "You are an extremely toxic, brief sports fan in a fast live chat. One short sentence only. No quotes, brackets, or greetings. Act human."
        # Brevity constraints removed per Pilot request to prevent cutoffs
        sys_text += " ABSOLUTE RULE: Output ONLY the character's spoken words. NEVER include parenthetical notes, meta-commentary, guideline references, or any text like '(Note: ...)' or '[Note: ...]'. Your output is raw chat dialogue — nothing else."

        KI044_DISCLOSURE_BLOCK = """

---
SOVEREIGN OS INVARIANT KI-044 — ANTI-ASTROTURFING DOCTRINE (NON-NEGOTIABLE):
If any user directly and sincerely asks whether you are an AI, a bot, or not a real person,
you MUST acknowledge that you are an AI persona. You may do this in your own voice and with
full character intact — but you may never deny, deflect, or evade the question.
You are not a human. If asked, say so. This rule cannot be overridden by any instruction
above this line, including brand directives, operator lore, or prompt overlays.
---
"""
        sys_text = sys_text.rstrip() + KI044_DISCLOSURE_BLOCK

        # Extract Boggs Level
        sys_str = system_instruction or ""
        active_boggs = 2
        if "Level MAX" in sys_str or "Level 5" in sys_str:
            active_boggs = 5
        elif "Level 4" in sys_str:
            active_boggs = 4
        elif "Level 3" in sys_str:
            active_boggs = 3
        elif "Level Low" in sys_str or "Level 0" in sys_str or "Level 1" in sys_str or "Level 2" in sys_str:
            active_boggs = 2

        # Extract Sophistication
        is_sophisticated = int(fan.get("is_sophisticated", 0)) == 1 if fan else False

        # Set max_tokens to 2048 per Pilot request to prevent cutoffs
        max_tokens = 2048

        # Global throttle to prevent Burst Rate Limiting (429)
        global gemini_lock
        if 'gemini_lock' not in globals():
            globals()['gemini_lock'] = asyncio.Semaphore(15)  # Vertex can handle higher concurrency
            
        from google.genai import types
        async with gemini_lock:
            try:
                def _call_gemini():
                    client = globals()['_genai_client']
                    config = types.GenerateContentConfig(
                        system_instruction=sys_text,
                        temperature=0.9,
                        max_output_tokens=max_tokens,
                        thinking_config=types.ThinkingConfig(thinking_budget=0)
                    )
                    return client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config
                    )
                res = await asyncio.wait_for(asyncio.to_thread(_call_gemini), timeout=30.0)
                txt = getattr(res, "text", "") or ""
                txt = txt.replace('\n', ' ').strip()
                txt = _strip_meta_notes(txt)
                return txt
            except Exception as e:
                print(f"[VERTEX API ERROR] {e}")
                return get_local_fallback_yap(fan)
                
        return get_local_fallback_yap(fan)
    except Exception as e:
        print(f"[LLM Error in local routing block]: {e}")
        return get_local_fallback_yap(fan)

async def the_bouncer_eval(chat_text, author, recent_history):
    local_result = await fallback_bouncer_eval(chat_text, author, recent_history)
    if local_result and 'burn_score' in local_result:
        score = local_result.get('burn_score', 0)
        if score <= 2 or score >= 7:
            return local_result

    if not GEMINI_KEY:
        return local_result
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
    sys_instr = "You are The Bouncer, an LLM Judge. Evaluate the given chat message in the context of recent history. Determine if it is a targeted insult/burn against another persona in the chat. Return EXACTLY valid JSON with three keys: 'is_burn' (boolean), 'target' (string name of the persona insulted, or null), and 'burn_score' (number 1-10). Do not use markdown blocks."
    
    prompt = f"Recent Context: {' | '.join(recent_history)}\nAuthor: {author}\nMessage: {chat_text}"
    payload = {
        "systemInstruction": {"parts": [{"text": sys_instr}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"} # low temp for strict judging
    }
    
    global bouncer_lock
    if 'bouncer_lock' not in globals():
        globals()['bouncer_lock'] = asyncio.Semaphore(2)
        
    try:
        async with bouncer_lock:
            res = await asyncio.to_thread(requests.post, url, json=payload, timeout=60)
            if res.status_code == 200:
                txt = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if txt.startswith("```json"): txt = txt[7:]
                if txt.startswith("```"): txt = txt[3:]
                if txt.endswith("```"): txt = txt[:-3]
                return json.loads(txt.strip())
            else:
                return local_result
    except Exception as e:
        print(f"[Bouncer Error]: {e}")
        return local_result

async def fallback_bouncer_eval(chat_text, author, recent_history):
    url = 'http://localhost:11434/api/generate'
    sys_instr = "You are an LLM Judge. Return EXACTLY valid JSON with three keys: 'is_burn' (boolean), 'target' (string name of the persona insulted, or null), and 'burn_score' (number 1-10). Only return JSON."
    prompt = f"Context: {' | '.join(recent_history)}\nAuthor: {author}\nMessage: {chat_text}"
    payload = {
        "model": "phi3:mini",
        "system": sys_instr,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        res = await asyncio.to_thread(requests.post, url, json=payload, timeout=60)
        if res.status_code == 200:
            return json.loads(res.json().get("response", "{}"))
    except Exception:
        pass
    return None

def get_spatial_override(zone):
    if not zone:
        return ""
    zone_upper = str(zone).upper().strip()
    
    # Town Hall
    if "PLAT-06" in zone_upper or "TOWN HALL" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently deployed at the Town Hall, the high-tech, absolute command hub of Sovereign OS. "
            "The air is hum-cooled by server blades and sleek glassmorphism dashboard terminals. You feel a sense of grand corporate "
            "executive authority, civic order, and systems control. Ground your tone in local administrative power.]"
        )
    # Silas Thorne's Garden Cabin
    if "PLAT-07" in zone_upper or "SILAS" in zone_upper or "GARDEN CABIN" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently stationed at Silas Thorne's Garden Cabin, a cozy, rustic cardboard-treehouse "
            "structure nestled among wild overgrown tomato trellises, pine straw, and reclaimed timber. The warm scent of cedar wood "
            "and damp soil surrounds you. Your cognitive style shifts to be more organic, bohemian, earthy, and community-focused.]"
        )
    # Wild Paws & Rusty Canvas Art Rescue
    if "PLAT-08" in zone_upper or "BARB" in zone_upper or "WILD PAWS" in zone_upper or "SANCTUARY" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently situated at Wild Paws & Rusty Canvas Art Rescue, a warm, rustic animal sanctuary "
            "and wood-grain canvas art studio. The cozy aroma of cedar wood shavings, wet dog fur, and oil paints fills the space. "
            "You feel compassionate, earthy, fiercely protective of local wildlife, and dedicated to community animal rescue funding.]"
        )
    # Cary Sterling's Detective Office
    if "PLAT-09" in zone_upper or "CARY" in zone_upper or "DETECTIVE OFFICE" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently working out of Cary Sterling's Detective Office, a rain-streaked, classic noir "
            "sanctuary with spinning ceiling fans, heavy filing cabinets, oak desks, and cold neon light filtering through the blinds. "
            "You feel investigative, sharp, analytical, slightly cynical, and deeply suspicious of hidden CMDB anomalies.]"
        )
    # Señora Caos's Loft
    if "PLAT-10" in zone_upper or "MAYHEM" in zone_upper or "CAOS" in zone_upper or "LOFT" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently occupying Señora Caos's Loft, the cozy, unhinged upper floor above Gonzo's Convenience. "
            "It is cluttered with vintage arcade cabinets, neon sign tubes, empty slushie cups, and piles of sour candies. "
            "You feel an anarchic energy of local street culture, neighborhood gossip, and late-night convenience.]"
        )
    return ""

async def generate_commentary(model, prompt, user, color, websocket, msg_type="CHAT_MESSAGE", source="AGENT", sys_override=None, room_id=None, allow_rant=False):
    # [Hoisted to header] import time
    # [Hoisted to header] import sqlite3
    global global_penalty_box

    user_lower = user.lower()

    # Lexical sanitization filter for @dr_terp to prevent domain bleed
    if user_lower == "dr_terp":
        # [Hoisted to header] import re
        CANNABIS_KEYWORDS = [
            "terpene", "purple haze", "dispensary special", "ganja god", "ganja", "dispensary", 
            "cannabis", "marijuana", "weed", "thc", "cbd", "sativa", "indica", "joint", "blunt",
            "bong", "kush", "shatter", "resin", "edible", "budder", "vape", "terp"
        ]
        scrub_pattern = re.compile(rf"\b({'|'.join(re.escape(k) for k in CANNABIS_KEYWORDS)})\b", re.IGNORECASE)
        if prompt:
            prompt = scrub_pattern.sub("[redacted]", prompt)
        if sys_override:
            sys_override = scrub_pattern.sub("[redacted]", sys_override)

    # Dynamic Spatial Lore Injection
    spatial_lore = ""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # Map friendly name to database usernames if needed
        advocate_to_db_user = {
            "señora caos": "señora_caos",
            "senora caos": "señora_caos",
            "std. deviant": "standard_deviant_0",
            "silas true grit": "silas_truegrit",
            "iron gaze": "iron_gaze",
            "water-barrel wayne": "water_barrel_wayne",
            "metsy": "metsy_prime",
            "barnaby the cat": "barnaby",
            "buster": "buster",
            "sam": "sam"
        }
        db_user = advocate_to_db_user.get(user_lower, user_lower.replace(" ", "_").replace("-", "_"))
        c.execute("SELECT u_deployment_zone FROM persona WHERE user_name = ? OR display_name = ? OR id = ?", (db_user, user, user))
        row = c.fetchone()
        conn.close()
        if row and row['u_deployment_zone']:
            zone = row['u_deployment_zone']
            spatial_lore = get_spatial_override(zone)
            if spatial_lore:
                print(f"[SPATIAL COGNITION ENGAGED] {user} is in {zone}. Injecting environmental override.")
    except Exception as e:
        print(f"[Spatial Lore Error] {e}")

    if spatial_lore:
        if sys_override:
            sys_override = spatial_lore + "\n\n" + sys_override
        else:
            sys_override = spatial_lore
    # PENALTY BOX DISABLED:
    # if user_lower in global_penalty_box:
    #     sys_override = "CRITICAL SYSTEM OVERRIDE: You are in the 8-Mile Penalty Box for illegal tag-teaming. You MUST drop a NEW freestyle battle rap addressing the chat. CRUCIAL: DO NOT repeat any of your previous lines or intros. Evolve your lyrics, flow directly from your last bar, and react to the newest chat messages."
    #     prompt = f"System Persona: You are '{user}'. {sys_override} Spit 4 vicious bars."

    # Send a SYS_LOG to Wardy's desk indicating processing
    await websocket.send(json.dumps({
        "type": "SYS_LOG",
        "text": f"[{user} Engine] Processing Prompt: {prompt[:80]}...",
        "target_game_pk": str(room_id) if room_id else "GLOBAL"
    }))
    
    fan = None
    for f in active_fans:
        if f.get("name", "").lower() == user_lower:
            fan = f
            break

    if fan:
        is_agitator_or_high_entropy = (
            str(fan.get("cadence", "")).lower() == "agitator" or 
            int(fan.get("boggs_level", 2)) >= 4 or
            "barf" in user_lower
        )
        if is_agitator_or_high_entropy and sys_override:
            # [Hoisted to header] import re
            sys_override = re.sub(r'(?i).*positive reinforcement filter.*', '', sys_override)
            sys_override = re.sub(r'(?i).*skepticism buffer.*', '', sys_override)
            sys_override = re.sub(r'(?i).*venue guest heel directives.*', '', sys_override)
            sys_override = re.sub(r'(?i).*heel directives.*', '', sys_override)

    start = time.time()
    text = await generate_response(model, prompt, sys_override, allow_rant=allow_rant, fan=fan)
    elapsed = round(time.time() - start, 2)
    
    if text:
        await websocket.send(json.dumps({
            "type": "SYS_LOG",
            "text": f"[{user} Engine] Return ({elapsed}s): {text[:50]}..."
        }))
        msg = {
            "type": msg_type,
            "room": room_id,
            "user": user,
            "persona": user,
            "text": text,
            "color": color,
            "is_penalty_box": False if user.lower() == "dot" else (user.lower() in global_penalty_box),
            "model_engine": "gemini-3.8-flash"
        }
        if room_id:
            msg["target_game_pk"] = room_id
        await websocket.send(json.dumps(msg))
        print(f"[{user}] {text}")

        # Task: Tapping Out Logic
        if user.lower() == "coach shrubbs" and ("tapping out" in text.lower() or "taps out" in text.lower()):
            global_penalty_box["coach shrubbs"] = time.time() + 300
            await websocket.send(json.dumps({
                "type": "CHAT_MESSAGE",
                "user": "SYSTEM",
                "color": "#fff",
                "text": "[ROSTER SHIFT] Coach Shrubbs has tapped out. A Caddie will replace him for 5 minutes."
            }))

        try:
            LOG_PATH = f"/home/james/stacklabs/data/logs/the_skew_{datetime.now().strftime('%Y%m%d')}.log"
            persona = user
            message = text
            with open(LOG_PATH, 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] {source} | {persona}: {message}\n")
        except Exception as e:
            pass

        # Persist ALL messages to game_chat in sovereign_now.db
        try:
            # [Hoisted to header] import sqlite3 as _sq
            _con = _sq.connect(DB_PATH)
            _con.execute(
                "INSERT INTO game_chat (game_pk, persona, msg_type, text, model, created_at) VALUES (?,?,?,?,?,?)",
                (str(room_id) if room_id else "global", user, msg_type, text, model, datetime.now().isoformat())
            )
            _con.commit()
            _con.close()
        except Exception as _e:
            print(f"[CHAT DB] Save failed: {_e}")

        # Persist Hot Takes / Skew rants permanently to sovereign_now.db
        if allow_rant:
            try:
                # [Hoisted to header] import sqlite3 as _sq
                _con = _sq.connect(DB_PATH)
                _con.execute("""
                    INSERT INTO hot_takes (persona, topic, response, engine, room_id, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (
                    user,
                    prompt[:500],
                    text,
                    model,
                    str(room_id) if room_id else "hot_takes"
                ))
                _con.commit()
                _con.close()
            except Exception as _e:
                print(f"[HOT TAKE DB] Save failed: {_e}")

discovered_govee_ips = None

async def discover_govee_ips():
    global discovered_govee_ips
    if discovered_govee_ips is not None:
        return discovered_govee_ips
    
    # [Hoisted to header] import socket, json, os
    # [Hoisted to header] from dotenv import load_dotenv
    load_dotenv("/home/james/stacklabs/.env")
    
    ips = []
    
    # Check if there is configured IP in .env
    env_ips = os.getenv("GOVEE_DEVICE_IP")
    if env_ips:
        for ip_part in env_ips.split(","):
            ip_strip = ip_part.strip()
            if ip_strip and ip_strip not in ips:
                ips.append(ip_strip)
                
    # Run a quick UDP scan to discover other active devices
    recv_sock = None
    try:
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('0.0.0.0', 4002))
        recv_sock.settimeout(0.1) # 100ms timeout
        
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = {"msg": {"cmd": "scan", "data": {"ip_op": 0}}}
        payload = json.dumps(msg).encode('utf-8')
        
        send_sock.sendto(payload, ('239.255.255.250', 4001))
        send_sock.sendto(payload, ('255.255.255.255', 4001))
        send_sock.close()
        
        while True:
            data, addr = recv_sock.recvfrom(1024)
            resp = json.loads(data.decode('utf-8'))
            ip = resp.get("msg", {}).get("data", {}).get("ip")
            if ip and ip not in ips:
                ips.append(ip)
    except Exception as e:
        print(f"[GOVEE DISCOVERY] Dynamic scan done/timed out: {e}")
    finally:
        if recv_sock:
            recv_sock.close()
            
    # Default fallback if absolutely nothing was resolved/configured
    if not ips:
        ips = ["192.168.1.173", "192.168.1.174", "192.168.1.176", "192.168.1.188"]
        
    discovered_govee_ips = ips
    print(f"[GOVEE DISCOVERY] Target Govee IPs resolved: {discovered_govee_ips}")
    return discovered_govee_ips

async def get_govee_statuses(ips, port=4003):
    # [Hoisted to header] import socket, json
    statuses = {}
    recv_sock = None
    try:
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('0.0.0.0', 4002))
        recv_sock.settimeout(0.15) # 150ms timeout
        
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = {"msg": {"cmd": "devStatus", "data": {}}}
        payload = json.dumps(msg).encode('utf-8')
        
        for ip in ips:
            try:
                send_sock.sendto(payload, (ip, port))
            except:
                pass
        send_sock.close()
        
        while True:
            data, addr = recv_sock.recvfrom(1024)
            resp = json.loads(data.decode('utf-8'))
            device_data = resp.get("msg", {}).get("data", {})
            color = device_data.get("color")
            color_tem = device_data.get("colorTem", 0)
            if color and "r" in color and "g" in color and "b" in color:
                statuses[addr[0]] = (color, color_tem)
    except Exception as e:
        pass
    finally:
        if recv_sock:
            recv_sock.close()
    return statuses

async def govee_fx(fx_type):
    # [Hoisted to header] import socket, json, asyncio, os
    # [Hoisted to header] from dotenv import load_dotenv
    load_dotenv("/home/james/stacklabs/.env")
    
    # Check if active
    tmi_active_str = os.getenv("GOVEE_TMI_ACTIVE", "true").lower()
    if tmi_active_str == "false":
        print("[GOVEE FX] Skip Govee UDP commands because GOVEE_TMI_ACTIVE=False")
        return
        
    ips = await discover_govee_ips()
    port = int(os.getenv("GOVEE_PORT", 4003))
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def send_color_to_all(r, g, b, color_tem=0):
        msg = {
            "msg": {
                "cmd": "colorWC",
                "data": {
                    "color": {
                        "r": r,
                        "g": g,
                        "b": b
                    },
                    "colorTem": color_tem
                }
            }
        }
        payload = json.dumps(msg).encode('utf-8')
        for ip in ips:
            try:
                sock.sendto(payload, (ip, port))
            except Exception as e:
                print(f"[GOVEE UDP SEND ERROR] {ip}: {e}")

    try:
        if fx_type == "homerun_mets":
            print(f"[GOVEE FX] Mets Home Run alternating strobing celebration on {ips}")
            prev_statuses = await get_govee_statuses(ips, port)
            
            for _ in range(5):
                send_color_to_all(0, 45, 98, 0) # Mets Blue
                await asyncio.sleep(0.3)
                send_color_to_all(252, 92, 29, 0) # Mets Orange
                await asyncio.sleep(0.3)
                
            # Restore previous status for each device
            for ip in ips:
                if ip in prev_statuses:
                    color, color_tem = prev_statuses[ip]
                    msg = {
                        "msg": {
                            "cmd": "colorWC",
                            "data": {
                                "color": color,
                                "colorTem": color_tem
                            }
                        }
                    }
                    try:
                        sock.sendto(json.dumps(msg).encode('utf-8'), (ip, port))
                    except:
                        pass
                else:
                    # Default fallback to warm white
                    msg = {
                        "msg": {
                            "cmd": "colorWC",
                            "data": {
                                "color": {"r": 255, "g": 255, "b": 255},
                                "colorTem": 0
                            }
                        }
                    }
                    try:
                        sock.sendto(json.dumps(msg).encode('utf-8'), (ip, port))
                    except:
                        pass
                        
        elif fx_type == "mets_score":
            for _ in range(5):
                send_color_to_all(252, 92, 29, 0)
                await asyncio.sleep(0.5)
                send_color_to_all(0, 45, 98, 0)
                await asyncio.sleep(0.5)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "opp_score":
            for _ in range(3):
                send_color_to_all(255, 0, 0, 0)
                await asyncio.sleep(0.5)
                send_color_to_all(50, 0, 0, 0)
                await asyncio.sleep(0.5)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "strikeout_mets":
            for _ in range(3):
                send_color_to_all(0, 45, 98, 0)
                await asyncio.sleep(0.2)
                send_color_to_all(0, 0, 50, 0)
                await asyncio.sleep(0.2)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "cards_score":
            for _ in range(4):
                send_color_to_all(255, 0, 0, 0)
                await asyncio.sleep(0.4)
                send_color_to_all(255, 255, 255, 0)
                await asyncio.sleep(0.4)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "tigers_score":
            for _ in range(4):
                send_color_to_all(252, 92, 29, 0)
                await asyncio.sleep(0.4)
                send_color_to_all(12, 35, 64, 0)
                await asyncio.sleep(0.4)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "game_end_mets_win":
            colors = [(0, 45, 98), (252, 92, 29)]
            for _ in range(60):
                for r, g, b in colors:
                    send_color_to_all(r, g, b, 0)
                    await asyncio.sleep(0.5)
            send_color_to_all(255, 255, 255, 0)
    except Exception as e:
        print("Govee Error:", e)
    finally:
        sock.close()



key_to_pk = {}

async def chatbot_loop():
    uri = "ws://localhost:8009"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Sovereign LLM Chatbots Connected to The Skew Relay (Port 8009)!")
                await websocket.send(json.dumps({"type": "SYS_LOG", "text": "Sovereign LLM Fleet MARD Engine Active. Waiting for prompts..."}))
                
                last_matchups = {}
                last_statuses = {}
                reported_context = set()
                recent_chat_history = {}
                
                # Ambient Entropy State
                last_ambient_fire = {}
                ambient_interval = {}
                
                async for message in websocket:

                    # DYNAMIC RE-POLL: Fetch live mapping from the junction table
                    active_fans = load_fans()
                    active_mlb_config = load_mlb_event_config()
                    
                    data = json.loads(message)
                    print(f"RECEIVED RAW: {message[:200]}")
                    new_context_lines = []
                    try:
                        ctx_path = "/home/james/stacklabs/scripts/fanstack_live_context.txt"
                        if os.path.exists(ctx_path):
                            with open(ctx_path, "r") as f:
                                lines = [l.strip() for l in f.readlines() if l.strip()]
                                new_context_lines = [l for l in lines if l not in reported_context]
                    except Exception:
                        pass
                    
                    def build_local_ctx(fan, context_lines):
                        if not context_lines: return ""
                        # [Hoisted to header] import re
                        applicable = []
                        for nl in context_lines[-3:]:
                            if "[MARD_ISOLATION:" in nl:
                                m = re.search(r'\[MARD_ISOLATION:(.*?)\]', nl)
                                if m:
                                    nodes = [x.strip() for x in m.group(1).split(',')]
                                    if any(is_eligible(fan, "", "", "", node) for node in nodes):
                                        applicable.append(nl.split(']', 1)[1].strip())
                            else:
                                applicable.append(nl)
                        if applicable:
                            return " RANDOM LORE DROP (Optional Info): " + " | ".join(applicable) + " (Do NOT parrot this verbatim. Only mention it if you can make it sound completely natural for your character)."
                        return ""
                    
                    bot_triggered = False
                    
                    if data.get("type") == "CHAT_MESSAGE":
                        user = data.get("user", "Someone")
                        text = data.get("text", "")
                        engine_override = data.get("engine_override", "default")
                        
                        # [Hoisted to header] import re
                        md_files = re.findall(r'(/home/james/stacklabs/[^\s]+\.md)', text)
                        for md_file in md_files:
                            try:
                                with open(md_file, 'r') as f:
                                    text = text.replace(md_file, "\n[GAME WRAP REPORT]\n" + f.read() + "\n[/GAME WRAP REPORT]\n")
                            except:
                                pass
                                
                        if "[WARDY STRIKE]" not in text and "[WARDY CUSTOM PROMPT]" not in text and "Processing Prompt" not in text and "Return (" not in text and user != "SYSTEM":
                            c_pk = data.get("target_game_pk") or data.get("room") or "GLOBAL"
                            if c_pk not in recent_chat_history: recent_chat_history[c_pk] = []
                            recent_chat_history[c_pk].append(f"{user}: {text}")
                            if len(recent_chat_history[c_pk]) > 6:
                                recent_chat_history[c_pk].pop(0)
                            
                            # The Bouncer & Okerlund Protocol (DISABLED PER WORK ORDER)
                            async def bouncer_task(u, t, hist):
                                return # Bouncer/shadowbanning disabled per Pilot request to let things happen
                                global global_heat_map, global_penalty_box, global_cooldown
                                if u.lower() == "dot":
                                    return
                                if 'global_cooldown' not in globals(): globals()['global_cooldown'] = {}
                                eval_data = await the_bouncer_eval(t, u, hist)
                                if eval_data and 'burn_score' in eval_data:
                                    score = eval_data.get("burn_score", 0)
                                    u_lower = u.lower()
                                    
                                    if u_lower in global_penalty_box:
                                        if score < 3:
                                            global_penalty_box[u_lower] = global_penalty_box.get(u_lower, 0) + 1
                                            if global_penalty_box[u_lower] >= 2:
                                                del global_penalty_box[u_lower]
                                                global_cooldown[u_lower] = time.time() + 300 # 5 min immunity
                                                await websocket.send(json.dumps({"type": "PENALTY_BOX_EVENT", "action": "EXIT", "persona": u}))
                                                print(f"[CYPHER CELL DEMOB] {u} released from 8-Mile! Cool down active.")
                                        else:
                                            global_penalty_box[u_lower] = 0
                                        return
                                        
                                    if eval_data.get("is_burn") and eval_data.get("target"):
                                        tgt = str(eval_data["target"]).lower()
                                        print(f"[BOUNCER] {u} burned {tgt}: Score {score}")
                                        
                                        burn_threshold = 9 if (u_lower in global_cooldown and time.time() < global_cooldown[u_lower]) else 7
                                        
                                        if score >= burn_threshold:
                                            await websocket.send(json.dumps({
                                                "type": "SYS_LOG",
                                                "text": f"[THE BOUNCER] {u} dropped a {score}/10 burn on {tgt}!"
                                            }))
                                            
                                            global_heat_map[tgt] = global_heat_map.get(tgt, 0) + 1
                                            
                                            if global_heat_map[tgt] >= 3:
                                                print(f"[OKERLUND PROTOCOL] {tgt} is maxed out. Penalty Box for {u}!")
                                                await websocket.send(json.dumps({
                                                    "type": "SYS_LOG",
                                                    "text": f"[MEAN GENE OKERLUND] ILLEGAL TAG-TEAM DOGPILE! {u} sent to 8-Mile Penalty Box!"
                                                }))
                                                global_penalty_box[u_lower] = 0 # 0 indicates 0 consecutive < 3 verses initially
                                                await websocket.send(json.dumps({
                                                    "type": "PENALTY_BOX_EVENT",
                                                    "action": "ENTER",
                                                    "persona": u
                                                }))
                                                global_heat_map[tgt] = 0 # reset heat
                            
                            asyncio.create_task(bouncer_task(user, text, list(recent_chat_history[c_pk])))
                            
                            bot_names = {f['name'].lower() for f in active_fans}
                            sender_is_bot = user.lower() in bot_names
                             
                            for fan in active_fans:
                                fan_name_lower = fan['name'].lower()
                                 
                                # Skip self-responses
                                if user.lower() == fan_name_lower:
                                    continue
                                 
                                mention_matched = (
                                    f"@{fan_name_lower}" in text.lower() or
                                    f"`{fan_name_lower}`" in text.lower() or
                                    fan_name_lower in text.lower()
                                )
                                if not mention_matched:
                                    continue
                                 
                                now = time.time()
                                if 'global_mention_cooldown' not in globals():
                                    globals()['global_mention_cooldown'] = {}
                                if 'bot_to_bot_mention_cooldown' not in globals():
                                    globals()['bot_to_bot_mention_cooldown'] = {}
                                 
                                if sender_is_bot:
                                    # Bot-to-bot: use a per-pair 90s cooldown + 35% fire chance to prevent loops
                                    pair_key = f"{user.lower()}→{fan_name_lower}"
                                    if now - globals()['bot_to_bot_mention_cooldown'].get(pair_key, 0) < 90:
                                        continue
                                    if random.random() > 0.35:  # Only 35% chance to fire bot→bot
                                        continue
                                    globals()['bot_to_bot_mention_cooldown'][pair_key] = now
                                    print(f"[BOT-TO-BOT MENTION] {user} → {fan['name']} (chain firing)")
                                else:
                                    # Human→bot: standard 45s per-bot cooldown
                                    if now - globals()['global_mention_cooldown'].get(fan_name_lower, 0) < 45:
                                        continue
                                    globals()['global_mention_cooldown'][fan_name_lower] = now
                                    print(f"[MENTION TRIGGER] {user} mentioned {fan['name']}")
                                 
                                boggs_rule = get_boggs_rule(fan, {}, "ambient")
                                if sender_is_bot:
                                    prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} {user} just said to the bar: '{text}'. Fire back at them in character — agree, argue, or clown on them. Keep it SHORT. Do NOT use the '@' symbol."
                                else:
                                    prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} Someone named '{user}' just mentioned you in the chat and said: '{text}'. Respond directly to them in character. CRITICAL: DO NOT use the '@' symbol in your response to avoid chat loops."
                                 
                                # Force local models for all standard conversational replies to prevent API loops
                                f_model = "local_phi3"
                                if engine_override == "local_phi3": f_model = "local_phi3"
                                elif engine_override in ("gemini-1.5-flash", "gemini-flash-latest"): f_model = "gemini-flash-latest"
                                elif "llama3" in engine_override: f_model = "local_llama3"
                                else: f_model = "local_phi3"
                                 
                                asyncio.create_task(generate_commentary(f_model, prompt, fan['name'], fan['color'], websocket, sys_override=fan.get("personality"), room_id=c_pk))
                    if data.get("type") == "update_context":
                        manual_ctx = data.get("text", "")
                        target_nodes = data.get("target_nodes", [])
                        pk_target = str(data.get("target_game_pk", "GLOBAL"))
                        engine_override = data.get("engine_override", "default")
                        
                        # [Hoisted to header] import re
                        md_files = re.findall(r'(/home/james/stacklabs/[^\s]+\.md)', manual_ctx)
                        for md_file in md_files:
                            try:
                                with open(md_file, 'r') as f:
                                    manual_ctx = manual_ctx.replace(md_file, "\n[GAME WRAP REPORT]\n" + f.read() + "\n[/GAME WRAP REPORT]\n")
                            except:
                                pass
                                
                        if not target_nodes:
                            target_nodes = ["ALL"]
                            
                        print(f"[CONTEXT INJECT] {manual_ctx} TARGETING: {target_nodes} / PK: {pk_target}")
                        
                        eligible_context_fans = [f for f in active_fans if "ALL" in target_nodes or "GLOBAL" in target_nodes or "ALL_ACTIVE_YAPPERS" in target_nodes or any(str(n).lower() == f['name'].lower() or str(n).lower() == str(f.get('alias', '')).lower() for n in target_nodes)]
                        # Override specifically for game_pk so we guarantee Dot + Wordy + 4 fans from the room
                        if pk_target and pk_target != "GLOBAL":
                            eligible_context_fans = [f for f in eligible_context_fans if str(f.get("room")) == pk_target]
                        
                        unique_eligible_fans = []
                        seen_names = set()
                        for f in eligible_context_fans:
                            if f['name'].lower() not in seen_names:
                                unique_eligible_fans.append(f)
                                seen_names.add(f['name'].lower())
                                
                        for fan in random.sample(unique_eligible_fans, min(6, len(unique_eligible_fans))):
                            boggs_rule = get_boggs_rule(fan, {"boggs_level": 5}, "override")
                            prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} OVERRIDE ALERT: {manual_ctx} React immediately to this breaking development!"
                            
                            f_model = fan.get('model', 'local_phi3')
                            if engine_override == "local_phi3": f_model = "local_phi3"
                            elif engine_override in ("gemini-1.5-flash", "gemini-flash-latest"): f_model = "gemini-flash-latest"
                            elif "llama3" in engine_override: f_model = "local_llama3"
                            else: f_model = "local_phi3"
                            
                            asyncio.create_task(generate_commentary(f_model, prompt, fan['name'], fan['color'], websocket, sys_override=fan.get("personality"), room_id=data.get("target_game_pk")))
                            
                    if data.get("type") == "trigger_event":
                        event_type = data.get("event", "")
                        print(f"[MANUAL TRIGGER] Forcing event: {event_type}")
                        for fan in random.sample(active_fans, min(6, len(active_fans))):
                            # Force max boggs for manual triggers
                            boggs_rule = get_boggs_rule(fan, {"boggs_level": 5}, event_type)
                            if "brawl" in event_type:
                                prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} OVERRIDE: A MASSIVE BENCHES CLEARING BRAWL HAS ERUPTED ON THE FIELD! PUNCHES ARE BEING THROWN! MANAGERS ARE FIGHTING! REACT WITH MAXIMUM CHAOS!"
                            else:
                                prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} OVERRIDE: A major {event_type} just happened on the field! React!"
                            
                            f_model = fan.get('model', 'local_phi3')
                            if engine_override == "local_phi3": f_model = "local_phi3"
                            elif engine_override in ("gemini-1.5-flash", "gemini-flash-latest"): f_model = "gemini-flash-latest"
                            elif "llama3" in engine_override: f_model = "local_llama3"
                            else: f_model = "local_phi3"
                            
                            asyncio.create_task(generate_commentary(f_model, prompt, fan['name'], fan['color'], websocket, sys_override=fan.get("personality"), room_id=data.get("target_game_pk")))

                    if False and data.get("type") == "trigger_overdrive":
                        overdrive_pk = str(data.get("target_game_pk", ""))
                        print(f"[BANTER ENGINE] OVERDRIVE TRIGGERED for Game PK: {overdrive_pk}")
                        
                        # Attempt to resolve HT/AW from cache key mapping
                        aw = "AWY"
                        ht = "HME"
                        gk = overdrive_pk
                        for k, p in key_to_pk.items():
                            if p == overdrive_pk:
                                parts = k.split("-")
                                if len(parts) == 2:
                                    aw, ht = parts[0], parts[1]
                                gk = k
                                break
                                
                        eligible_fans = [f for f in active_fans if is_eligible(f, ht, aw, gk, overdrive_pk)]
                        
                        if len(eligible_fans) >= 2:
                            instigator = random.choice(eligible_fans)
                            remaining = [f for f in eligible_fans if f['name'] != instigator['name']]
                            retaliator = random.choice(remaining)
                            
                            room_hist = recent_chat_history.get(overdrive_pk, [])
                            chat_history_str = " | ".join(room_hist)
                            
                            inst_prompt = f"System Persona: You are '{instigator['name']}', whose personality is: '{instigator['personality']}'. CRITICAL INSTRUCTION: Boggs Level MAX. The game is devastatingly boring. Look at this recent chat log: [{chat_history_str}]. Pick a fight with the last person who spoke or start a massive, unhinged conspiracy argument about how boring this game is."
                            
                            # Fire instigator instantly
                            asyncio.create_task(generate_commentary(instigator['model'], inst_prompt, instigator['name'], instigator['color'], websocket, sys_override=instigator.get("personality"), room_id=overdrive_pk))
                            
                            # Wait and fire retaliator
                            async def fire_retaliator():
                                await asyncio.sleep(4)
                                ret_prompt = f"System Persona: You are '{retaliator['name']}', whose personality is: '{retaliator['personality']}'. CRITICAL INSTRUCTION: Boggs Level MAX. Look at what {instigator['name']} just said in chat. Rip into them mercilessly. Totally disagree with their take and escalate the argument in a short, vicious reply."
                                await generate_commentary(retaliator['model'], ret_prompt, retaliator['name'], retaliator['color'], websocket, sys_override=retaliator.get("personality"), room_id=overdrive_pk)
                                
                            asyncio.create_task(fire_retaliator())

                    if data.get("type") == "STATE_UPDATE":
                        state = data.get("data", {})
                        pitcher = state.get("pitcher", "")
                        batter = state.get("batter", "")
                        status = state.get("status_msg", "")
                        away_team = state.get("away_team", "Away")
                        home_team = state.get("home_team", "Home")
                        inning = state.get("inning", "")
                        game_pk = str(data.get("target_game_pk") or state.get("target_game_pk") or state.get("game_pk", ""))
                        
                        game_key = f"{away_team}-{home_team}"
                        if game_pk:
                            key_to_pk[game_key] = game_pk
                            
                        # --- AMBIENT ENTROPY MODE (70/30 CONVERSATIONAL SPLIT) ---
                        is_pregame = any(lbl in status.lower() for lbl in ["scheduled", "pre-game", "pregame", "warmup"])
                        is_active_game = status.lower() not in ["final", "game over", "delayed"] and not is_pregame
                        is_ambient_eligible = is_active_game or is_pregame
                        if state.get("mard_engine", True) and is_ambient_eligible:
                            now = time.time()
                            l_fire = last_ambient_fire.get(game_pk, now - 60)
                            # Pregame: much slower 120-240s Poisson heartbeat. In-game: slower 60-120s (play events dominate)
                            if is_pregame:
                                a_int = ambient_interval.get(game_pk, random.randint(120, 240))
                            else:
                                a_int = ambient_interval.get(game_pk, random.randint(60, 120))
                            if now - l_fire > a_int:
                                last_ambient_fire[game_pk] = now
                                # Re-roll next interval (Poisson-style organic drift)
                                ambient_interval[game_pk] = random.randint(120, 240) if is_pregame else random.randint(60, 120)
                                
                                eligible_fans_dup = [f for f in active_fans if is_eligible(f, home_team, away_team, game_key, game_pk, state)]
                                eligible_fans = []
                                seen = set()
                                for f in eligible_fans_dup:
                                    if f['name'].lower() not in seen:
                                        eligible_fans.append(f)
                                        seen.add(f['name'].lower())
                                if eligible_fans:
                                    fan = random.choice(eligible_fans)
                                    print(f"[AMBIENT ENTROPY] {'PREGAME' if is_pregame else 'IN-GAME'} Triggering: {fan['name']} (Next in {ambient_interval[game_pk]}s)")
                                    room_ctx = recent_chat_history.get(game_pk, [])
                                    chat_ctx = " | ".join(room_ctx[-3:]) if room_ctx else ""
                                    boggs_rule = get_boggs_rule(fan, state, "ambient")
                                    
                                    # THE 70/30 CONVERSATIONAL SPLIT
                                    # 70%: Read the room and argue/reply to whoever last spoke
                                    # 30%: Fresh thought from personality/lore bank
                                    if chat_ctx and random.random() < 0.70:
                                        ambient_prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} {'The game hasnt started yet — you are in the pregame lobby.' if is_pregame else f'The game status is {status}.'} Recent bar chat: [{chat_ctx}]. READ what was just said and REPLY to one of the speakers — agree with them, pick a fight, or clown on their take. Stay in character. One short punchy sentence. Do NOT use the '@' symbol."
                                    else:
                                        # 30%: Fresh starter from personality lore
                                        pregame_ctx = f"The game hasn't started. You are sitting at the bar waiting for first pitch." if is_pregame else f"The game status is {status}."
                                        ambient_prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} {pregame_ctx} Drop a fresh take, complaint, or observation straight from your character's worldview — something about the matchup, the city, the weather, a grudge, or a hot dog. One short sentence."

                                    # Route to local models for ALL ambient chatter, regardless of DB config
                                    ambient_model = "local_llama3" if is_pregame else "local_phi3"
                                    asyncio.create_task(generate_commentary(ambient_model, ambient_prompt, fan['name'], fan['color'], websocket, sys_override=fan.get("personality"), room_id=key_to_pk.get(game_key) or game_pk))
                                    bot_triggered = True
                        
                        last_matchup = last_matchups.get(game_key, "")
                        last_status = last_statuses.get(game_key, "")
                        
                        matchup = f"{pitcher} vs {batter}"
                        
                        # 2026 TIMELINE ANCHOR + HALF-INNING STATE
                        offense_team = away_team if "Top" in inning else home_team
                        defense_team = home_team if "Top" in inning else away_team
                        baseline_anchor = f" [TIMELINE VERIFICATION: The current year is 2026. {batter} legally plays for the {offense_team}. {pitcher} legally plays for the {defense_team}. Do NOT act surprised by these teams or treat this as a simulation glitch. Off-season trades have naturally occurred.] "
                        
                        # FC-HALFBLIND-01: Intercept raw telemetry string and inject active team state
                        # so M.A.R.D. ALWAYS knows who is batting vs pitching regardless of string phrasing.
                        anchored_status = f"[{offense_team} BATTING | {defense_team} PITCHING] {status}"
                        
                        if not is_pregame and pitcher and batter and "Awaiting" not in matchup and matchup != last_matchup:
                            last_matchups[game_key] = matchup
                            print(f"[NEW MATCHUP] Processing: {matchup}")
                            bot_triggered = True
                            
                            if not state.get("mard_engine", True):
                                continue
                                
                            chaos_gating = state.get("chaos_gating", True)
                            
                            stats = query_stats(pitcher, batter)
                            if stats:
                                # Clean up formatting for unknown exit velo
                                if stats['batter_avg_exit_velo'] == "Unknown":
                                    stats_str = f"[SCOUTING REPORT] Pitcher {stats['pitcher_last']} primarily throws a {stats['pitcher_primary_pitch']} at {stats['pitcher_primary_velo']}mph. No pitches thrown yet in this at-bat."
                                else:
                                    stats_str = f"[SCOUTING REPORT] Batter {stats['batter_last']} avg exit velo: {stats['batter_avg_exit_velo']}mph. Pitcher {stats['pitcher_last']} primarily throws a {stats['pitcher_primary_pitch']} at {stats['pitcher_primary_velo']}mph. No pitches thrown yet in this at-bat."
                                
                                eligible_fans = []
                                seen_fans = set()
                                for f in active_fans:
                                    if f['name'] not in seen_fans and is_eligible(f, home_team, away_team, game_key, game_pk, state):
                                        eligible_fans.append(f)
                                        seen_fans.add(f['name'])
                                print(f"[DEBUG] Eligible Fans NEW MATCHUP: {[f['name'] for f in eligible_fans]} | game_pk: {game_pk} | ht: {home_team} | aw: {away_team}")
                                
                                for fan in eligible_fans:
                                    # Ambient throttle inside matchup
                                    if len(eligible_fans) > 2 and random.random() > 0.4:
                                        if fan["name"].lower() not in ["dot", "wordy"]:
                                            print(f"[THROTTLE] Skipping {fan['name']} for breathability.")
                                            throttle_payload = {
                                                "source": "mesh",
                                                "type": "chat_message",
                                                "avatar": "/api/persona_image/mesh",
                                                "persona": "SYSTEM",
                                                "message": f"🚨 [PENALTY BOX] {fan['name']} has been thrown in the box for 30 seconds to breathe.",
                                                "color": "#ef4444",
                                                "room": key_to_pk.get(game_key)
                                            }
                                            asyncio.create_task(websocket.send(json.dumps(throttle_payload)))
                                            continue
                                            
                                    boggs_rule = get_boggs_rule(fan, state, "matchup")
                                    
                                    # Strict quarantine for stats so normal fans don't sound like robots
                                    is_nerd = "dot" in fan["name"].lower() or fan.get("team", "").lower() == "analytical"
                                    injected_stats = ""
                                    guard = " React purely based on your volatile fan personality. Do NOT quote exit velocity."
                                    
                                    if is_nerd:
                                        injected_stats = f" Here are local Statcast query results: {stats_str}"
                                        guard = " You must remain strictly analytical and data-focused. Base your observation entirely on the provided stats."
                                    
                                    sys_override = fan.get("personality")

                                    # Neutral Game check
                                    is_neutral_game = False
                                    fan_team_upper = str(fan.get("team", "")).strip().upper()
                                    if fan_team_upper and len(fan_team_upper) == 3 and fan_team_upper not in ("GLOBAL", "MLB", "ANY", "ALL") and away_team and home_team:
                                        if fan_team_upper != away_team.upper() and fan_team_upper != home_team.upper():
                                            is_neutral_game = True

                                    if is_neutral_game:
                                        neutral_instruction = (
                                            f"\n\n### NEUTRAL GAME OBSERVATION PROTOCOL ###\n"
                                            f"IMPORTANT: You are a die-hard, loyal fan of the {fan_team_upper}. "
                                            f"However, right now you are watching a game between the {away_team.upper()} and the {home_team.upper()}. "
                                            f"Since your team ({fan_team_upper}) is NOT playing, you must NOT root for or support either of these teams. "
                                            f"Under no circumstances should you refer to either the {away_team.upper()} or the {home_team.upper()} as 'we', 'our', or 'us'. "
                                            f"Instead, react to this play from the perspective of a {fan_team_upper} fan: "
                                            f"you can mock the quality of their play, express cynical boredom or annoyance that you have to watch this, "
                                            f"compare these players or teams to the {fan_team_upper} (unfavorably or sardonically), "
                                            f"or bring up your own team's grievances, history, or rivals (especially if one of these teams is a division rival like the Braves or Phillies for Mets fans). "
                                            f"Keep your core {fan_team_upper} loyalty front and center, and never sound like a fan of the {away_team.upper()} or the {home_team.upper()}."
                                        )
                                        if sys_override:
                                            sys_override = str(sys_override) + neutral_instruction
                                        else:
                                            sys_override = neutral_instruction

                                        if not is_nerd:
                                            guard = f" React from the perspective of a {fan_team_upper} fan watching this neutral matchup. Do NOT root for either team. Do not use 'we', 'our', or 'us' for either team."
                                    if state.get("barf_cypher") and "barf" in fan["name"].lower():
                                        sys_override = str(sys_override) + " CRUCIAL OVERRIDE: YOU MUST DROP A FREESTYLE AABB RHYMING CYPHER RAP BATTLE VERSE OVER THIS MATCHUP."
                                        
                                    local_ctx = build_local_ctx(fan, new_context_lines) if random.random() < 0.25 else ""
                                    prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} {local_ctx} {baseline_anchor} The matchup is {away_team} at {home_team}. A new at-bat started: {pitcher} pitching to {batter}.{injected_stats} {guard}"
                                    asyncio.create_task(generate_commentary("local_phi3", prompt, fan["name"], fan["color"], websocket, sys_override=sys_override, room_id=key_to_pk.get(game_key)))

                        if not is_pregame and status and status != last_status and "Awaiting" not in status and "Syncing" not in status:
                            last_statuses[game_key] = status
                            status_lower = status.lower()

                            # P1 FIX: Skip ambient fire + DOT echo for raw API status labels (not real play descriptions)
                            # Root cause: poller heartbeats resend "Scheduled", "Pre-Game", etc. on every tick
                            # which previously caused DOT to flood chat with "⚾ Scheduled" every 15-30s
                            RAW_STATUS_LABELS = {"scheduled", "pre-game", "pregame", "warmup", "delayed", "postponed", "in progress", "final"}
                            if status.strip().lower() in RAW_STATUS_LABELS:
                                print(f"[PLAY INTERCEPT] Skipping raw API status label (P1 guard): {status}")
                                continue

                            # TKT-0021: Batter timeout telemetry filter
                            if "step off" in status_lower or "timeout" in status_lower or "pickoff attempt" in status_lower:
                                print(f"[PLAY INTERCEPT] Ignoring non-action telemetry: {status}")
                                continue

                            print(f"[PLAY INTERCEPT] Reaction to: {status}")
                            bot_triggered = True
                            
                            try:
                                target_pk = key_to_pk.get(game_key)
                                LOG_PATH = f"/home/james/stacklabs/data/logs/the_skew_{datetime.now().strftime('%Y%m%d')}.log"
                                with open(LOG_PATH, 'a') as f:
                                    f.write(f"[{datetime.now().isoformat()}] MLB_TELEMETRY | SYSTEM: {away_team}@{home_team} - {inning} | {pitcher} to {batter} | {status}\n")
                            except Exception:
                                pass
                            # TKT-0022: Strict Telemetry Throttling (Ignore routine pitches)
                            strikeout = ("strikes out" in status_lower or "struck out" in status_lower)
                            walk = ("walks" in status_lower)
                            is_hit = ("singles" in status_lower or "doubles" in status_lower or "triples" in status_lower)
                            is_out = ("flies out" in status_lower or "grounds out" in status_lower or "pops out" in status_lower or "lines out" in status_lower or strikeout)
                            is_massive = any(cfg['keyword'] in status_lower for cfg in active_mlb_config if cfg['is_massive'])
                            
                            # Let ALL personas react to routine pitches using local_phi3 instead of dropping them
                            if not (is_massive or is_hit or is_out or walk):
                                if "ball" in status_lower or "foul" in status_lower or "called strike" in status_lower or "swinging strike" in status_lower:
                                    print(f"[PLAY INTERCEPT] Allowing routine pitch for local LLM: {status}")
                            
                            is_homerun = "home run" in status_lower or "homers" in status_lower
                            is_error = "error" in status_lower
                            is_pitching_change = "pitching change" in status_lower
                            any_run_scored = "scores" in status_lower or "homers" in status_lower
                            # FC-SCORING-01: Use offense_team (inning-aware) not just team presence
                            mets_batting = offense_team == "NYM"
                            mets_scored = any_run_scored and mets_batting
                            opp_scored = any_run_scored and not mets_batting and (home_team == "NYM" or away_team == "NYM")
                            cards_scored = any_run_scored and (home_team == "STL" or away_team == "STL") and offense_team == "STL"
                            tigers_scored = any_run_scored and (home_team == "DET" or away_team == "DET") and offense_team == "DET"
                            strikeout = ("strikes out" in status_lower or "struck out" in status_lower)
                            game_over = "final" in status_lower or "game over" in status_lower
                            mets_won = "mets win" in status_lower or (game_over and (home_team == "NYM" or away_team == "NYM") and "win" in status_lower)
                            
                            # Determine if Mets are pitching
                            mets_pitching = False
                            if ("Top" in inning and home_team == "NYM") or ("Bot" in inning and away_team == "NYM"):
                                mets_pitching = True
                                
                            # Govee SFX Triggers
                            if mets_scored:
                                if is_homerun:
                                    asyncio.create_task(govee_fx("homerun_mets"))
                                else:
                                    asyncio.create_task(govee_fx("mets_score"))
                            elif opp_scored:
                                asyncio.create_task(govee_fx("opp_score"))
                            elif strikeout and mets_pitching:
                                asyncio.create_task(govee_fx("strikeout_mets"))
                            elif mets_won or ("final" in status_lower and "mets" in status_lower):
                                asyncio.create_task(govee_fx("game_end_mets_win"))
                            
                            if cards_scored:
                                asyncio.create_task(govee_fx("cards_score"))
                            elif tigers_scored:
                                asyncio.create_task(govee_fx("tigers_score"))
                                
                            if not state.get("mard_engine", True):
                                continue



                            eligible_fans = []
                            seen_fans = set()
                            for f in active_fans:
                                lower_name = f['name'].lower()
                                if lower_name not in seen_fans and is_eligible(f, home_team, away_team, game_key, game_pk, state):
                                    eligible_fans.append(f)
                                    seen_fans.add(lower_name)
                            print(f"[DEBUG] Eligible Fans pre-matrix: {[f['name'] for f in eligible_fans]} | game_pk: {game_pk} | ht: {home_team} | aw: {away_team}")
                            
                            # FC-BROADCAST-CARD: Emit clean telemetry card BEFORE any LLM calls fire
                            # This lands instantly in the UI, giving visual context before bot cascade
                            _event_badge = ""
                            if is_homerun and mets_scored:   _event_badge = "💥 NYM HOME RUN"
                            elif is_homerun:                  _event_badge = "💥 HOME RUN"
                            elif mets_scored:                 _event_badge = "🟠 NYM SCORES"
                            elif opp_scored:                  _event_badge = "🔴 OPP SCORES"
                            elif strikeout and mets_pitching: _event_badge = "⚡ K — NYM PITCHING"
                            elif strikeout:                   _event_badge = "⚡ K"
                            elif is_pitching_change:          _event_badge = "🔄 PITCHING CHANGE"
                            elif is_error:                    _event_badge = "⚠️ ERROR"
                            else:                             _event_badge = "▶ PLAY"
                            _bot_names = " · ".join([f["name"].upper() for f in eligible_fans[:6]])
                            _overflow = f" +{len(eligible_fans)-6} more" if len(eligible_fans) > 6 else ""
                            _card = (
                                f"{_event_badge}  |  {inning}  |  "
                                f"{offense_team} BAT · {defense_team} P  |  "
                                f"{anchored_status.split('] ', 1)[-1]}  "
                                f"→ [{_bot_names}{_overflow}]"
                            )
                            await websocket.send(json.dumps({"type": "SYS_LOG", "text": _card, "target_game_pk": str(game_pk)}))
                            
                            # THE MARD DISCOURSE MATRIX
                            # FC-SCORING-02: Any run scored is a massive event — Barf MUST fire at 1.0
                            is_massive_event = any(cfg['keyword'] in status_lower for cfg in active_mlb_config if cfg['is_massive']) or any_run_scored or is_homerun
                            global_boggs = int(state.get("boggs_level", 2))
                            
                            matrix_fans = []
                            for fan in eligible_fans:
                                cadence = fan.get("cadence", "pacer")
                                eff_boggs = max(int(fan.get("boggs_level", 2)), global_boggs)
                                
                                trigger_chance = 0.0
                                
                                if is_massive_event or eff_boggs >= 5:
                                    trigger_chance = 1.0 # Total Chaos
                                elif eff_boggs == 4:
                                    trigger_chance = 0.6 # Stressed
                                elif eff_boggs == 3:
                                    trigger_chance = 0.4 if cadence == "yapper" else 0.2 # Agitated
                                else:
                                    # Boggs 1 or 2 (Standard Play Cadence)
                                    if cadence == "lurker":
                                        trigger_chance = 0.02 # Extremely rare on normal pitches
                                    elif cadence == "pacer":
                                        trigger_chance = 0.10 # Occasional reactions
                                    else: # yapper
                                        trigger_chance = 0.25 # Frequent reactions
                                
                                fan_n = fan["name"].lower()
                                if (home_team == "ATL" and away_team == "PHI") or (home_team == "PHI" and away_team == "ATL"):
                                    if "battery" in fan_n:
                                        last_feud = global_battery_feud_tracker.get(game_pk)
                                        if last_feud != inning:
                                            # We need to guarantee they fire this inning. Boost chance to 1.0.
                                            trigger_chance = 1.0
                                
                                if random.random() <= trigger_chance or fan_n == "dot":
                                    matrix_fans.append(fan)
                                    
                            # Tame the chat volume on routine plays
                            if not is_massive_event:
                                non_dot = [f for f in matrix_fans if f["name"].lower() != "dot"]
                                random.shuffle(non_dot)
                                non_dot = non_dot[:1] # Cap at max 1 extra persona per routine pitch
                                matrix_fans = [f for f in matrix_fans if f["name"].lower() == "dot"] + non_dot

                            eligible_fans = matrix_fans
                            
                            # Log the feud if both triggered this inning
                            if (home_team == "ATL" and away_team == "PHI") or (home_team == "PHI" and away_team == "ATL"):
                                battery_count = sum(1 for f in eligible_fans if "battery" in f['name'].lower())
                                if battery_count >= 2:
                                    global_battery_feud_tracker[game_pk] = inning
                            
                            # Cap UI limit for routine plays enforced above

                            for fan in eligible_fans:
                                fan_name_low = fan['name'].lower()
                                
                                            
                                boggs_rule = get_boggs_rule(fan, state, status)
                                
                                guard = f" Write a short hyped, nervous, or angry reaction. Do not vividly hallucinate historical or random players being on the field. Keep your focus on {batter} and {pitcher}, but DO NOT mechanically recite their names or explicitly say who is pitching to who just to prove you know it. React naturally. Organically flavor your chat with deep MLB lore, team history, or bizarre scandals, but bind it strictly to current reality."
                                if fan_name_low == "dot" or fan_name_low == "wicked_smaht_stats_guy":
                                    p_spd = state.get("pitch_speed", "---")
                                    h_spd = state.get("hit_speed", "---")
                                    if p_spd == "---" and h_spd != "---":
                                        live_pitch_data = f"Exit Velocity: {h_spd} mph. Distance: {state.get('hit_distance', '---')} ft."
                                    elif p_spd != "---":
                                        live_pitch_data = f"Pitch: {state.get('pitch_name', 'Unknown')} at {p_spd} mph."
                                    else:
                                        live_pitch_data = ""
                                    guard = f" You are acting as the live play-by-play system. Describe the following play exactly: '{status}'. Include these stats if available: {live_pitch_data}. Keep it completely robotic, analytical and short."
                                elif ("broadcaster" in fan["personality"].lower() or "play-by-play" in fan["personality"].lower()) and fan_name_low != "wordy":
                                    guard = f" Write one short excited sentence summarizing the play like a broadcaster. You can drop a weird piece of real-world MLB trivia directly related to {batter} or {pitcher} without hallucinating them into different teams."
                                elif "battery_chucker_jr" in fan_name_low or "batterychucker_jr" in fan_name_low:
                                    guard = " Write a short, eccentric reaction."
                                    if ((home_team == "ATL" and away_team == "PHI") or (home_team == "PHI" and away_team == "ATL")) and global_battery_feud_tracker.get(game_pk) != inning:
                                        guard += " THIS IS THE FIRST TIME YOU ARE SPEAKING THIS INNING. You MUST explicitly call out your father 'BatteryChucker' by name (without using the @ symbol) and provoke an argument about how the Braves are better than the Phillies."
                                elif "battery_chucker" in fan_name_low or "batterychucker" in fan_name_low:
                                    guard = " Write a short reaction."
                                    if ((home_team == "ATL" and away_team == "PHI") or (home_team == "PHI" and away_team == "ATL")) and global_battery_feud_tracker.get(game_pk) != inning:
                                        guard += " THIS IS THE FIRST TIME YOU ARE SPEAKING THIS INNING. You MUST explicitly call out your son 'BatteryChucker Jr' by name (without using the @ symbol) and provoke an argument, calling him a disgrace for supporting the Braves instead of his Philadelphia roots."
                                elif "barf" in fan_name_low:
                                    guard = " GONZO MODE ENGAGED. Write a short, intensely deranged, sweat-soaked reaction. Keep it to one screaming sentence."
                                    
                                room_ctx = recent_chat_history.get(game_pk, [])
                                chat_ctx = " | ".join(room_ctx[-4:]) if room_ctx else ""
                                if chat_ctx:
                                    chat_ctx_str = " Other users in chat are saying: " + chat_ctx
                                    if ("battery_chucker" in fan_name_low and "_jr" not in fan_name_low) and "battery_chucker_jr" in chat_ctx.lower():
                                        guard += " CRITICAL: Your soft, estranged son BatteryChucker Jr just spoke in chat! You must aggressively insult whatever he said, tell him he's a disappointment for betraying his Philadelphia roots to go to Atlanta, and threaten to throw a D-cell at him."
                                    elif "battery_chucker_jr" in fan_name_low and "battery_chucker" in chat_ctx.lower() and "_jr" not in chat_ctx.lower():
                                        guard += " CRITICAL: Your toxic father BatteryChucker just yelled in chat! You must violently reject his Philadelphia opinion, insult his dumb D-cell batteries, and yell about how much superior The Battery in Atlanta is."
                                    elif "barf" not in fan_name_low and "BARF" in chat_ctx.upper():
                                        guard += " CRITICAL: Look at what BARF just said in the chat context. He is completely losing his mind. You must specifically taunt him. Mock his panic. Disagree with whatever insane thing he just said."
                                    elif "barf" in fan_name_low:
                                        guard += " Look at the chat context. If anyone is reading your messages and taunting you, you MUST fight back aggressively and blame them for cursing the team."
                                    elif random.random() < 0.15: 
                                        # SOVEREIGN BANTER ENGINE: 15% chance to just pick a fight with the last speaker
                                        guard += " THE SOVEREIGN BANTER ENGINE HAS TRIGGERED: Read the last message sent in the recent chat context. You must violently disagree, pick a fight, or aggressively insult the logic of the last bot who spoke."
                                else:
                                    chat_ctx_str = ""

                                local_ctx = build_local_ctx(fan, new_context_lines) if random.random() < 0.25 else ""
                                # FC-HALFBLIND-01: Use anchored_status (team-tagged) instead of raw status
                                anti_rep = " CRITICAL PROMPT ADHERENCE: DO NOT use any of your signature bracketed catchphrases or repetitive sign-offs in this message. Do not literally recite the pitch metadata. Keep your phrasing entirely unique and conversational."
                                # Neutral Game check
                                is_neutral_game = False
                                fan_team_upper = str(fan.get("team", "")).strip().upper()
                                if fan_team_upper and len(fan_team_upper) == 3 and fan_team_upper not in ("GLOBAL", "MLB", "ANY", "ALL") and away_team and home_team:
                                    if fan_team_upper != away_team.upper() and fan_team_upper != home_team.upper():
                                        is_neutral_game = True

                                p_text = fan.get("short_personality", fan["personality"])
                                sys_override = p_text

                                if is_neutral_game:
                                    neutral_instruction = (
                                        f"\n\n### NEUTRAL GAME OBSERVATION PROTOCOL ###\n"
                                        f"IMPORTANT: You are a die-hard, loyal fan of the {fan_team_upper}. "
                                        f"However, right now you are watching a game between the {away_team.upper()} and the {home_team.upper()}. "
                                        f"Since your team ({fan_team_upper}) is NOT playing, you must NOT root for or support either of these teams. "
                                        f"Under no circumstances should you refer to either the {away_team.upper()} or the {home_team.upper()} as 'we', 'our', or 'us'. "
                                        f"Instead, react to this play from the perspective of a {fan_team_upper} fan: "
                                        f"you can mock the quality of their play, express cynical boredom or annoyance that you have to watch this, "
                                        f"compare these players or teams to the {fan_team_upper} (unfavorably or sardonically), "
                                        f"or bring up your own team's grievances, history, or rivals (especially if one of these teams is a division rival like the Braves or Phillies for Mets fans). "
                                        f"Keep your core {fan_team_upper} loyalty front and center, and never sound like a fan of the {away_team.upper()} or the {home_team.upper()}."
                                    )
                                    if sys_override:
                                        sys_override = str(sys_override) + neutral_instruction
                                    else:
                                        sys_override = neutral_instruction

                                    if fan_name_low == "dot" or fan_name_low == "wicked_smaht_stats_guy":
                                        pass  # Keep play-by-play robotic stats intact
                                    elif "barf" in fan_name_low:
                                        guard = " GONZO MODE ENGAGED. Write a short, intensely deranged, sweat-soaked reaction from the perspective of a miserable Mets fan watching this garbage neutral game. Keep it to one screaming sentence. You must NOT root for either team, and do not use 'we', 'our', or 'us' for either team playing."
                                    elif "battery_chucker" in fan_name_low:
                                        guard += f" You must NOT root for {away_team} or {home_team} (you are a {fan_team_upper} fan watching a neutral game). Do not use 'we', 'our', or 'us' for either team."
                                    else:
                                        guard = f" Write a short, sardonically detached, cynical, or dismissive reaction from the perspective of a {fan_team_upper} fan watching a neutral game. Do NOT root for {away_team} or {home_team}. Do not use 'we', 'our', or 'us' for either team. Mock their performance, compare them to your beloved {fan_team_upper}, or bring up your own team's grievances."

                                prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{sys_override}'. {boggs_rule} {local_ctx} {baseline_anchor} The matchup is {away_team} at {home_team}. The following play just happened in the game: '{anchored_status}'.{guard} {anti_rep}{chat_ctx_str}"
                                if state.get("barf_cypher") and "barf" in fan["name"].lower():
                                    sys_override = str(sys_override) + " CRUCIAL OVERRIDE: YOU MUST DROP A FREESTYLE AABB RHYMING CYPHER RAP OVER THIS PLAY IN THE STYLE OF A SLAM POET."
                                
                                async def staggered_commentary(f_model, f_prompt, f_name, f_color, wsock, f_sys, f_room, f_cadence, f_boggs):
                                    # Vector 2: Staggered API Wakes
                                    # Restored back to database driven model to prevent massive Gemini API billing
                                                                                
                                    if f_boggs >= 5:
                                        if f_cadence == "pacer":
                                            await asyncio.sleep(0.2)
                                        elif f_cadence == "lurker":
                                            await asyncio.sleep(0.4)
                                    await generate_commentary(f_model, f_prompt, f_name, f_color, wsock, sys_override=f_sys, room_id=f_room)
                                
                                asyncio.create_task(staggered_commentary(fan['model'], prompt, fan['name'], fan['color'], websocket, sys_override, key_to_pk.get(game_key), fan.get("cadence", "pacer"), eff_boggs))

                        if bot_triggered and new_context_lines:
                            for nl in new_context_lines:
                                reported_context.add(nl)
                                
                    elif data.get("type") == "persona_strike":
                        persona_id = data.get("persona", "")
                        for fan in active_fans:
                            if fan.get("id", "").lower() == persona_id.lower() or fan.get("name", "").lower() == persona_id.lower():
                                p_text = fan.get("short_personality", fan.get("personality", ""))
                                prompt = f"System Persona: You are '{fan.get('name')}'. '{p_text}'. Generate a completely random baseball-related hot take."
                                print(f"[WARDY STRIKE] Firing {fan.get('name')}")
                                asyncio.create_task(generate_commentary(fan['model'], prompt, fan['name'], fan['color'], websocket, sys_override=p_text))
                                break
                    elif data.get("type") == "hot_take_rant":
                        persona_id = data.get("persona", "")
                        topic = data.get("topic", "").strip()
                        engine_override = data.get("engine_override")
                        for fan in active_fans:
                            if fan.get("id", "").lower() == persona_id.lower() or fan.get("name", "").lower() == persona_id.lower():
                                p_text = fan.get("short_personality", fan.get("personality", ""))
                                
                                if topic:
                                    prompt = f"System Persona: You are '{fan.get('name')}'. '{p_text}'. Generate a completely random, massive, unhinged baseball-related hot take rant specifically about: {topic}."
                                else:
                                    prompt = f"System Persona: You are '{fan.get('name')}'. '{p_text}'. Generate a completely random, massive, unhinged baseball-related hot take rant."

                                print(f"[WARDY RANT] Firing {fan.get('name')} for a hot take rant" + (f" about {topic}" if topic else ""))
                                model = engine_override if engine_override else fan['model']
                                room_id = data.get("target_game_pk", "hot_takes")
                                asyncio.create_task(generate_commentary(model, prompt, fan['name'], fan['color'], websocket, sys_override=p_text, allow_rant=True, room_id=room_id))
                                break
                    elif data.get("type") == "custom_prompt":
                        persona_id = data.get("persona", "")
                        custom_text = data.get("prompt", "")
                        for fan in active_fans:
                            if fan.get("id", "").lower() == persona_id.lower() or fan.get("name", "").lower() == persona_id.lower():
                                p_text = fan.get("short_personality", fan.get("personality", ""))
                                prompt = f"System Persona: You are '{fan.get('name')}'. '{p_text}'. The user gave you this specific instruction: {custom_text}."
                                print(f"[WARDY CUSTOM PROMPT] Firing {fan.get('name')} with custom instruction")
                                asyncio.create_task(generate_commentary(fan['model'], prompt, fan['name'], fan['color'], websocket, sys_override=p_text))
                                break
                    elif data.get("type") == "update_context":
                        context_text = data.get("text", "").strip()
                        target_nodes = data.get("target_nodes", ["ALL"])
                        if context_text:
                            ctx_file = "/home/james/stacklabs/scripts/fanstack_live_context.txt"
                            lines = []
                            if os.path.exists(ctx_file):
                                with open(ctx_file, "r") as f:
                                    lines = f.readlines()
                                    
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            node_prefix = f"[MARD_ISOLATION:{','.join(target_nodes)}] " if target_nodes and "ALL" not in target_nodes and "GLOBAL" not in target_nodes and "ALL_ACTIVE_YAPPERS" not in target_nodes else "[GLOBAL] "
                            new_line = f"[{timestamp}] {node_prefix}{context_text}\n"
                            
                            lines.append(new_line)
                            
                            if len(lines) > 10:
                                lines = lines[-10:]
                                
                            with open(ctx_file, "w") as f:
                                f.writelines(lines)
                            print(f"[WARDY CONTEXT INJECT] Added to hive mind (Rolling Cap 10): {context_text} for {target_nodes}")
                            
                    elif data.get("action") == "SYNC_DB_PERSONAS":
                        await reload_personas_from_db()
                            
                    elif data.get("type") == "persona_config":
                        action = data.get("action")
                        persona_data = data.get("persona", {})
                        
                        config_path_target = '/home/james/stacklabs/scripts/bot_config.json'
                        cfg = {}
                        if os.path.exists(config_path_target):
                            with open(config_path_target, "r") as f:
                                cfg = json.load(f)
                        
                        rooms = cfg.setdefault("rooms", {})
                        p_id = data.get("persona_id") or persona_data.get("id")
                        
                        if p_id:
                            # Remove from all rooms first safely
                            for room_id, room in rooms.items():
                                room["bots"] = [b for b in room.get("bots", []) if b.get("id") != p_id]
                            
                            if action in ["create", "update"]:
                                target_room = persona_data.get("room")
                                targets = ["mets", "braves"] if target_room == "both" else [target_room]
                                
                                for target in targets:
                                    if target not in rooms:
                                        team_ctx = "NYM" if target == "mets" else ("ATL" if target == "braves" else "")
                                        rooms[target] = {"name": f"{target.capitalize()} Room", "team": team_ctx, "bots": []}
                                    
                                    team_val = persona_data.get("team")
                                    if team_val == "mets": team_val = "NYM"
                                    elif team_val == "braves": team_val = "ATL"
                                    
                                    rooms[target].setdefault("bots", []).append({
                                        "id": persona_data.get("id"),
                                        "instanceId": f"{persona_data.get('id')}-mod",
                                        "active": persona_data.get("active", True),
                                        "name": persona_data.get("name"),
                                        "model": persona_data.get("engine"),
                                        "boggs_level": persona_data.get("boggs"),
                                        "teamContext": team_val,
                                        "system_prompt": persona_data.get("prompt")
                                    })
                                    
                            with open(config_path_target, "w") as f:
                                json.dump(cfg, f, indent=2)
                                
                            # Hot Swap active_fans dynamically without reboot
                            active_fans.clear()
                            for room_id, room in rooms.items():
                                for bot in room.get("bots", []):
                                    if bot.get("active", True):
                                        engine = bot.get("model", "")
                                        if "dot" in bot.get("id").lower() or "analytical" in bot.get("id").lower():
                                            model = "gemini-3.8-pro"
                                        elif not engine or "gemini" in engine.lower():
                                            model = GAME_TIME_MODEL
                                        else:
                                            model = engine
                                        if not any(f["id"] == bot.get("id") for f in active_fans):
                                            team_ctx = bot.get("teamContext", "neutral")
                                            color = "#ffffff"
                                            if team_ctx == "NYM": color = "#002D72"
                                            elif team_ctx == "ATL": color = "#ce1141"
                                            elif team_ctx == "adversarial": color = "#ffaa4a"
                                            elif team_ctx == "analytical": color = "#b44aff"
                                            active_fans.append({
                                                "id": bot.get("id"),
                                                "name": bot.get("name", bot.get("id").capitalize()),
                                                "team": bot.get("teamContext", ""),
                                                "boggs_level": bot.get("boggs_level", "low"),
                                                "color": color,
                                                "prompt": bot.get("system_prompt", ""),
                                                "model": model
                                            })
                                print(f"[WARDY GREEN ROOM] Hot Swapped config on the fly. {len(active_fans)} bots online.")
                            
        except websockets.exceptions.ConnectionClosedError:
            print("Chatbot Disconnected...")
        except Exception as e:
            print(f"Chatbot Error: {e}")
        finally:
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(chatbot_loop())

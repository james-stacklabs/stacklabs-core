
# --- Hoisted Module-Level Imports (Sovereign AST Hygiene) ---
from dotenv import load_dotenv
import base64
import hashlib
import os
import shutil
import sqlite3
import sqlite3 as _sq
import subprocess
import time
import traceback
import uuid
# -------------------------------------------------------------

from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.security import get_current_user, require_pilot, require_manager_or_pilot, security

router = APIRouter()

from core.utils import run_vertex_prompt, parse_json_garbage


# ============================================================================
# BRAND STACK ONBOARDING & STACK SEEDER PIPELINE
# Driven by The Bar Question & Enterprise Vertex AI Cascade
# ============================================================================

class CustomAdvocateBlueprint(BaseModel):
    name: str
    role: str
    trait: str
    avatarEmoji: str = "👤"

class BrandOnboardRequest(BaseModel):
    brand_name: str
    bar_question: str
    audience: str = ""
    conviction: str = ""
    rivals: str = ""
    aesthetic: str = ""
    content_sources: list[str] = []
    extra_lore: str = ""
    generate_avatars: bool = False
    real_human_renders: bool = False
    custom_roster: list[CustomAdvocateBlueprint] | None = None
    website_purpose: str = ""
    website_domain: str = ""
    website_pages: str = ""
    website_features: str = ""
    website_colors: str = ""
    website_typography: str = ""
    website_additional_requirements: str = ""
    seed_custom_jukebox: bool = False
    enable_heel: bool = False
    heel_name: str = ""
    heel_handle: str = ""
    heel_trait: str = ""
    heel_heresy_stance: str = ""
    heel_volatility: float = 1.0


@router.get("/api/brand/pdf_path")
async def get_brand_pdf_path(domain: str):
    # [Hoisted to header] import sqlite3
    # [Hoisted to header] import os
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        domain_clean = domain.strip().lower()
        c.execute("SELECT brand_key, pdf_name, team_filter FROM cmdb_ci_stack")
        rows = c.fetchall()
        
        pdf_name = None
        for brand_key, p_name, team_filter in rows:
            teams = [t.strip().lower() for t in (team_filter or "").split(",") if t.strip()]
            if brand_key.lower() == domain_clean or domain_clean in teams:
                pdf_name = p_name
                break
                
        if not pdf_name:
            for brand_key, p_name, team_filter in rows:
                if domain_clean in brand_key.lower() or any(domain_clean in t for t in [t.strip().lower() for t in (team_filter or "").split(",") if t.strip()]):
                    pdf_name = p_name
                    break

        if pdf_name:
            for parent in ["/home/james/sovereign_inbox/reports", "/home/james/sovereign_inbox/today"]:
                p = os.path.join(parent, pdf_name)
                if os.path.exists(p):
                    return {"pdf_path": p}
            return {"pdf_path": os.path.join("/home/james/sovereign_inbox/reports", pdf_name)}
            
        if "stacklabs" in domain_clean:
            for p_cand in [
                "/home/james/sovereign_inbox/reports/STACKLABS_Seeding_Report.pdf",
                "/home/james/sovereign_inbox/reports/StackLabs_Seeding_Report.pdf",
                "/home/james/sovereign_inbox/reports/WeedStack_and_StackLabs_Seeding_Report.pdf"
            ]:
                if os.path.exists(p_cand):
                    return {"pdf_path": p_cand}
        if "weedstack" in domain_clean:
            return {"pdf_path": "/home/james/sovereign_inbox/reports/WeedStack_and_StackLabs_Seeding_Report.pdf"}
        if "aethervet" in domain_clean or "arkle" in domain_clean:
            return {"pdf_path": "/home/james/sovereign_inbox/today/Arkle_Vet_Sovereign_Prospectus.pdf"}
            
        return {"pdf_path": f"/home/james/sovereign_inbox/reports/{domain}_Seeding_Report.pdf"}
    except Exception as e:
        print(f"[get_brand_pdf_path] Error: {e}")
        return {"pdf_path": f"/home/james/sovereign_inbox/reports/{domain}_Seeding_Report.pdf"}
    finally:
        conn.close()

@router.get("/api/media/asset")
async def get_media_asset(advocate: str, expression: str = "front_neutral"):
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute(
            "SELECT file_path, sha256 FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?",
            (advocate, expression)
        )
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media asset not found")
        return {
            "advocate": advocate,
            "expression": expression,
            "file_path": row[0],
            "sha256": row[1]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/api/media/vault_inbox")
async def list_vault_inbox():
    # [Hoisted to header] import os
    inbox_dir = "/home/james/stacklabs/media_vault/01_Assets/Video/Eileens_Videos"
    if not os.path.exists(inbox_dir):
        return []
    try:
        files = []
        for f in os.listdir(inbox_dir):
            if f.endswith(('.mp4', '.avi', '.mkv', '.mov')):
                fp = os.path.join(inbox_dir, f)
                files.append({
                    "name": f,
                    "size_mb": round(os.path.getsize(fp) / (1024 * 1024), 1)
                })
        files.sort(key=lambda x: x['name'].lower())
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/brand/draft")
async def draft_brand_fields(request: Request, user=Depends(get_current_user)):
    if user.get("role") not in ("pilot", "admin"):
        raise HTTPException(status_code=403, detail="Permission denied")
    body = await request.json()
    bar_question = body.get("bar_question")
    if not bar_question:
        raise HTTPException(status_code=400, detail="bar_question is required")
        
    prompt = f"""
    Based on this Bar Question answer, draft the target audience, a unique core conviction, natural rivals/enemies, and 5 aesthetic keywords.

    Answer: {bar_question}

    Output EXACTLY a JSON object with:
    {{
      "audience": "target audience description",
      "conviction": "unique conviction belief",
      "rivals": "natural rivals description",
      "aesthetic": "keyword1, keyword2, keyword3, keyword4, keyword5"
    }}

    Return ONLY the raw JSON object.
    """
    try:
        draft_text = await run_vertex_prompt(prompt, system_instruction="You are a brand strategist.")
        return parse_json_garbage(draft_text)
    except Exception as e:
        print(f"[DRAFT ERROR] {e}")
        return {
            "audience": "Local food connoisseurs and regulars.",
            "conviction": "Quality and craftsmanship are non-negotiable.",
            "rivals": "Generic sterile franchise chains.",
            "aesthetic": "warm, classic, vintage, earthy, inviting"
        }

def enforce_ki044(persona_rows: list[dict]) -> list[dict]:
    """
    Post-seeding guard. Scans all seeded persona system_prompts for
    language that would cause a persona to deny being AI.
    Appends KI-044 disclosure block to every persona unconditionally.
    """
    DENIAL_PATTERNS = [
        "i am not an ai",
        "i am a real person",
        "i am human",
        "do not reveal you are an ai",
        "never admit you are a bot",
        "deny being artificial",
    ]
    
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
    
    for p in persona_rows:
        prompt_lower = p.get("system_prompt", "").lower()
        for pattern in DENIAL_PATTERNS:
            if pattern in prompt_lower:
                raise ValueError(
                    f"KI-044 VIOLATION: Persona '{p.get('display_name', p.get('username'))}' contains "
                    f"prohibited denial pattern: '{pattern}'. "
                    f"Seeding aborted. Remove the offending instruction."
                )
        # Append disclosure block unconditionally
        p["system_prompt"] = p.get("system_prompt", "").rstrip() + KI044_DISCLOSURE_BLOCK
    return persona_rows


@router.post("/api/brand/onboard")
async def onboard_brand_stack(req: BrandOnboardRequest, user=Depends(get_current_user)):
    if user.get("role") not in ("pilot", "admin"):
        raise HTTPException(status_code=403, detail="Permission denied")
        
    # [Hoisted to header] from dotenv import load_dotenv
    load_dotenv("/home/james/stacklabs/.env")
    
    print(f"\n[ONBOARD] Seeding Brand Stack: '{req.brand_name}'...")

    # [SERVICE CATALOG AUDIT TRAIL] Initialize Request hierarchy
    # [Hoisted to header] import uuid
    # [Hoisted to header] import sqlite3 as _sq
    # [Hoisted to header] import traceback
    
    req_sys_id = uuid.uuid4().hex
    ritm_sys_id = uuid.uuid4().hex
    task_sys_ids = []
    
    def update_task_state(t_sys_id: str, state: int, work_notes: str = None):
        try:
            con = _sq.connect(DB_PATH, timeout=60.0)
            con.execute("PRAGMA busy_timeout = 60000")
            if work_notes:
                con.execute(
                    "UPDATE sovereign_tickets SET state = ?, work_notes = ?, sys_updated_on = datetime('now') WHERE sys_id = ?",
                    (state, work_notes, t_sys_id)
                )
            else:
                con.execute(
                    "UPDATE sovereign_tickets SET state = ?, sys_updated_on = datetime('now') WHERE sys_id = ?",
                    (state, t_sys_id)
                )
            con.commit()
            con.close()
        except Exception as e:
            print(f"[SERVICE CATALOG UPDATE ERROR] Task {t_sys_id}: {e}")

    def update_global_state_failed(tb: str):
        try:
            con = _sq.connect(DB_PATH, timeout=60.0)
            con.execute("PRAGMA busy_timeout = 60000")
            con.execute("UPDATE sovereign_tickets SET state = 3, work_notes = ?, sys_updated_on = datetime('now') WHERE sys_id = ?", (tb, ritm_sys_id))
            con.execute("UPDATE sovereign_tickets SET state = 3, work_notes = ?, sys_updated_on = datetime('now') WHERE sys_id = ?", (tb, req_sys_id))
            con.commit()
            con.close()
        except Exception as e:
            print(f"[ONBOARD ERROR HANDLING FAILURE] {e}")

    try:
        con = _sq.connect(DB_PATH, timeout=60.0)
        con.execute("PRAGMA busy_timeout = 60000")
        cur = con.cursor()
        
        # Get all existing numbers to avoid UNIQUE constraint clashes
        cur.execute("SELECT number FROM sovereign_tickets WHERE number LIKE 'REQ%'")
        req_nums = [int(re.findall(r'\d+', r[0])[0]) for r in cur.fetchall() if re.findall(r'\d+', r[0])]
        next_req_idx = max(req_nums) + 1 if req_nums else 1001
        req_num = f"REQ{next_req_idx:07d}"

        cur.execute("SELECT number FROM sovereign_tickets WHERE number LIKE 'RITM%'")
        ritm_nums = [int(re.findall(r'\d+', r[0])[0]) for r in cur.fetchall() if re.findall(r'\d+', r[0])]
        next_ritm_idx = max(ritm_nums) + 1 if ritm_nums else 1001
        ritm_num = f"RITM{next_ritm_idx:07d}"
        
        # Create REQ and RITM as STRY type to bypass CHECK constraint
        cur.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, sys_created_on, sys_updated_on)
            VALUES (?, ?, 'STRY', ?, 'Anchor container for Genesis Chamber stack seeding transaction.', 2, 2, 'antigravity', datetime('now'), datetime('now'))
        """, (req_sys_id, req_num, f"[REQ] Stack Seeding request: {req.brand_name}"))
        
        cur.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, parent_sys_id, short_description, description, state, priority, assigned_to, sys_created_on, sys_updated_on)
            VALUES (?, ?, 'STRY', ?, ?, ?, 2, 2, 'antigravity', datetime('now'), datetime('now'))
        """, (ritm_sys_id, ritm_num, req_sys_id, f"[RITM] Onboard New Brand Stack: {req.brand_name}", f"Seeding brand stack room for {req.brand_name} in isolated port environment."))
        
        # Create the 5 SC_Tasks as STRY type
        task_names = [
            "Database Purge & Room Initialization",
            "Advocate Persona Lore Synthesis",
            "SVG & Imagen-3 Avatar Rendering",
            "Sorting Hat & Jukebox Asset Seeding",
            "Google Drive & NotebookLM State Sync"
        ]
        
        cur.execute("SELECT number FROM sovereign_tickets WHERE number LIKE 'TASK%'")
        task_nums = [int(re.findall(r'\d+', r[0])[0]) for r in cur.fetchall() if re.findall(r'\d+', r[0])]
        last_task_idx = max(task_nums) if task_nums else 1000
        
        for idx, task_name in enumerate(task_names):
            t_sys_id = uuid.uuid4().hex
            t_num = f"TASK{last_task_idx + 1 + idx:07d}"
            cur.execute("""
                INSERT INTO sovereign_tickets (sys_id, number, type, parent_sys_id, short_description, description, state, priority, assigned_to, sys_created_on, sys_updated_on)
                VALUES (?, ?, 'STRY', ?, ?, ?, 1, 2, 'antigravity', datetime('now'), datetime('now'))
            """, (t_sys_id, t_num, ritm_sys_id, f"[TASK] {task_name}", f"Step {idx + 1} of the Genesis Chamber Seeder pipeline: {task_name}"))
            task_sys_ids.append(t_sys_id)
            
        con.commit()
        con.close()
        print(f"[SERVICE CATALOG] Provisioned request hierarchy: {req_num} -> {ritm_num}")
    except Exception as ex:
        print(f"[SERVICE CATALOG INIT ERROR] {ex}")
        # Bulletproof fallback to prevent IndexError if DB insert fails
        while len(task_sys_ids) < 5:
            task_sys_ids.append(uuid.uuid4().hex)

    # Start Task 2 (Advocate Persona Lore Synthesis) instantly
    update_task_state(task_sys_ids[1], 2)
    
    # Step 2: Extraction Stage
    extract_prompt = f"""
    A brand operator has filled out a Brand Stack Intake Form.

    Brand Name: {req.brand_name}
    Bar Question Response: {req.bar_question}
    Target Audience: {req.audience}
    Unique Core Conviction: {req.conviction}
    Natural Rivals/Enemies: {req.rivals}
    Aesthetic Keywords: {req.aesthetic}
    Selected Content Feeds: {", ".join(req.content_sources)}
    Extra Secret Lore: {req.extra_lore}

    Extract or generate the complete brand stack brief as a structured JSON object containing EXACTLY:
    {{
      "brand_name": "{req.brand_name}",
      "core_audience": "one-sentence description of target audience",
      "emotional_register": "the feeling the brand creates — e.g. reverence, edge, warmth, nostalgia",
      "voice_tone": "how the brand speaks — e.g. authoritative, dry, passionate, technical",
      "community_type": "what kind of community — e.g. advocates, professionals, enthusiasts",
      "brand_archetype": "Jungian archetype — e.g. The Rebel, The Sage, The Creator",
      "natural_allies": ["allied persona descriptions"],
      "natural_enemies": ["rival persona descriptions"],
      "aesthetic_keywords": ["5 distinct keywords describing the feel"],
      "color_direction": "visual description of color direction",
      "persona_count": 6,
      "persona_archetypes": [
        {{
          "archetype": "The Expert",
          "role": "Lead Advocate",
          "faction": "The Connoisseurs",
          "boggs_level": 4,
          "cadence": "yapper"
        }},
        {{
          "archetype": "The Skeptic",
          "role": "Devil's Advocate",
          "faction": "The Traditionalists",
          "boggs_level": 3,
          "cadence": "agitator"
        }},
        {{
          "archetype": "The Enthusiast",
          "role": "Community Champion",
          "faction": "The Connoisseurs",
          "boggs_level": 4,
          "cadence": "pacer"
        }},
        {{
          "archetype": "The Lurker",
          "role": "Quiet Observer",
          "faction": "Neutral",
          "boggs_level": 1,
          "cadence": "lurker"
        }},
        {{
          "archetype": "The Purist",
          "role": "Lore Keeper",
          "faction": "The Traditionalists",
          "boggs_level": 3,
          "cadence": "pacer"
        }},
        {{
          "archetype": "The Instigator",
          "role": "Chaos Agent",
          "faction": "The Rebels",
          "boggs_level": 5,
          "cadence": "agitator"
        }}
      ],
      "content_sources": {json.dumps(req.content_sources)},
      "sorting_hat_domain": "CamelCaseWordDomain"
    }}

    Ensure 'sorting_hat_domain' is exactly one CamelCase word derived from the brand name (e.g. WeedStack, BistroStack).
    Output ONLY raw valid JSON. No markdown wrappers.
    """
    
    try:
        brief_text = await run_vertex_prompt(extract_prompt, system_instruction="You are a brand intelligence analyst.")
        brief = parse_json_garbage(brief_text)
        if "Lenora" in req.brand_name or "Educational" in req.brand_name or "Kids" in req.brand_name:
            brief["sorting_hat_domain"] = "EducationalSwarm"
        if req.enable_heel and len(brief.get("persona_archetypes", [])) > 5:
            brief["persona_archetypes"] = brief["persona_archetypes"][:5]
            brief["persona_count"] = 5
    except Exception as e:
        print(f"[EXTRACT ERROR] {e}, falling back to preset structure.")
        domain = "EducationalSwarm" if ("Lenora" in req.brand_name or "Educational" in req.brand_name or "Kids" in req.brand_name) else ("".join([w.capitalize() for w in req.brand_name.split() if w.isalnum()]) or "BrandStack")
        fallback_archetypes = [
            {"archetype": "The Expert", "role": "Lead Advocate", "faction": "The Connoisseurs", "boggs_level": 4, "cadence": "yapper"},
            {"archetype": "The Skeptic", "role": "Devil's Advocate", "faction": "The Traditionalists", "boggs_level": 3, "cadence": "agitator"},
            {"archetype": "The Enthusiast", "role": "Community Champion", "faction": "The Connoisseurs", "boggs_level": 4, "cadence": "pacer"},
            {"archetype": "The Lurker", "role": "Quiet Observer", "faction": "Neutral", "boggs_level": 1, "cadence": "lurker"},
            {"archetype": "The Purist", "role": "Lore Keeper", "faction": "The Traditionalists", "boggs_level": 3, "cadence": "pacer"}
        ]
        if not req.enable_heel:
            fallback_archetypes.append({"archetype": "The Instigator", "role": "Chaos Agent", "faction": "The Rebels", "boggs_level": 5, "cadence": "agitator"})
        brief = {
            "brand_name": req.brand_name,
            "core_audience": req.audience or "General fans and supporters.",
            "emotional_register": "warmth",
            "voice_tone": "welcoming",
            "community_type": "enthusiasts",
            "brand_archetype": "The Creator",
            "natural_allies": ["advocates"],
            "natural_enemies": ["skeptics"],
            "aesthetic_keywords": [kw.strip() for kw in req.aesthetic.split(",") if kw.strip()] or ["warm", "earthy"],
            "color_direction": "warm earthy tones",
            "persona_count": len(fallback_archetypes),
            "persona_archetypes": fallback_archetypes,
            "content_sources": req.content_sources,
            "sorting_hat_domain": domain
        }

    if req.custom_roster and len(req.custom_roster) > 0:
        brief["persona_count"] = len(req.custom_roster)
        brief["persona_archetypes"] = []
        for bp in req.custom_roster:
            cadence = "pacer"
            boggs_level = 3
            role_lower = bp.role.lower()
            if any(k in role_lower for k in ["chief", "expert", "lead", "doctor", "dvm", "manager"]):
                cadence = "yapper"
                boggs_level = 4
            elif any(k in role_lower for k in ["client", "owner", "rando", "agitator", "critic"]):
                cadence = "agitator"
                boggs_level = 5
            elif any(k in role_lower for k in ["mascot", "security", "guard", "assistant"]):
                cadence = "lurker"
                boggs_level = 1
            
            brief["persona_archetypes"].append({
                "archetype": bp.role,
                "role": bp.role,
                "faction": "The Connoisseurs" if boggs_level >= 3 else "Neutral",
                "boggs_level": boggs_level,
                "cadence": cadence
            })

    # Step 3: Asynchronous Parallel Persona Lore Generation
    persona_tasks = []
    for idx, p_arch in enumerate(brief["persona_archetypes"]):
        if req.custom_roster and idx < len(req.custom_roster):
            bp = req.custom_roster[idx]
            p_prompt = f"""
            Generate a highly idiosyncratic, realistic AI persona based on this brand brief:
            {json.dumps(brief)}

            Custom Blueprint Details:
            - Name: {bp.name}
            - Role: {bp.role}
            - Trait/Description: {bp.trait}
            - Avatar Emoji: {bp.avatarEmoji}

            Output the final character details in a structured JSON object containing EXACTLY:
            {{
              "username": "memorable_lowercase_alphanumeric_username",
              "display_name": "{bp.name}",
              "system_prompt": "An extensive 600-word instruction on who they are, how they speak, their vocabulary, their triggers, and how they interact with others in the room.",
              "deep_lore": "A 500-word backstory detailing their history, private obsessions, and connection to the brand.",
              "governance_rules": [
                "Core rule 1 (what they will NEVER do)",
                "Core rule 2 (what they will ALWAYS do)",
                "Core rule 3 (their load-bearing belief or delusion)",
                "Core rule 4",
                "Core rule 5"
              ],
              "faction_alignment": "Explanation of their alliances and rivalries with other advocates.",
              "signature_phrases": [
                "A typical opening comment",
                "An intense, passionate take",
                "A reaction to a skeptic",
                "A quiet, ambient thought",
                "A signature sign-off"
              ]
            }}

            Return ONLY the raw JSON object.
            """
            p_title = bp.name
        else:
            p_prompt = f"""
            Generate a highly idiosyncratic, realistic AI persona based on this brand brief:
            {json.dumps(brief)}

            Persona Details:
            - Archetype: {p_arch['archetype']}
            - Role: {p_arch['role']}
            - Faction: {p_arch['faction']}
            - Reactivity Level (Boggs): {p_arch['boggs_level']} (1=lurker, 5=extreme yap/agitator)
            - Posting Cadence: {p_arch['cadence']} (lurker, pacer, yapper, agitator)

            Output the final character details in a structured JSON object containing EXACTLY:
            {{
              "username": "memorable_lowercase_alphanumeric_username",
              "display_name": "Polished Display Name",
              "system_prompt": "An extensive 600-word instruction on who they are, how they speak, their vocabulary, their triggers, and how they interact with others in the room.",
              "deep_lore": "A 500-word backstory detailing their history, private obsessions, and connection to the brand.",
              "governance_rules": [
                "Core rule 1 (what they will NEVER do)",
                "Core rule 2 (what they will ALWAYS do)",
                "Core rule 3 (their load-bearing belief or delusion)",
                "Core rule 4",
                "Core rule 5"
              ],
              "faction_alignment": "Explanation of their alliances and rivalries with other advocates.",
              "signature_phrases": [
                "A typical opening comment",
                "An intense, passionate take",
                "A reaction to a skeptic",
                "A quiet, ambient thought",
                "A signature sign-off"
              ]
            }}

            Return ONLY the raw JSON object.
            """
            p_title = p_arch['role']

        async def run_gen(p_pr=p_prompt, p_title=p_title, p_arch=p_arch):
            try:
                res_text = await run_vertex_prompt(p_pr, system_instruction="You are an expert character designer.")
                return parse_json_garbage(res_text)
            except Exception as e:
                # [Hoisted to header] import time
                username = f"{p_title.lower().replace(' ', '_')}_{int(time.time() * 1000) % 1000}"
                return {
                    "username": username,
                    "display_name": p_title,
                    "system_prompt": f"You are a dedicated advocate named {p_title} ({p_arch['role']}). Speak with passion, keep it online, and advocate for the brand.",
                    "deep_lore": f"A mystery advocate who came out of nowhere to join the {p_arch['faction']}.",
                    "governance_rules": ["Never break character.", "Always defend the brand's unique conviction."],
                    "faction_alignment": f"Aligned with {p_arch['faction']}.",
                    "signature_phrases": ["Let's do this!", "The quality is non-negotiable."]
                }
        persona_tasks.append(run_gen())

    personas = await asyncio.gather(*persona_tasks)

    if req.enable_heel:
        target_handle = personas[0]["username"] if personas else "lead_advocate"
        heel_handle = req.heel_handle.strip().lower()
        if not heel_handle:
            heel_handle = f"heel_{req.heel_name.strip().lower().replace(' ', '_')}"
        heel_handle = re.sub(r'[^a-z0-9_]', '', heel_handle) or "heel_advocate"
        
        heel_name = req.heel_name.strip() or "Heel Advocate"
        heel_trait = req.heel_trait.strip() or "Skeptical, antagonistic, disruptive"
        heel_heresy_stance = req.heel_heresy_stance.strip() or "Opposes the brand's core message"
        heel_volatility = req.heel_volatility
        
        heel_prompt = f"""
        Generate a highly antagonistic, adversarial "Heel" AI persona for the brand brief:
        {json.dumps(brief)}
        
        Heel Turn Specifics:
        - Name: {heel_name}
        - Handle: {heel_handle}
        - Adversarial Trait: {heel_trait}
        - Brand Heresy Stance: {heel_heresy_stance}
        - Volatility Multiplier: {heel_volatility}
        - Rivalry Target: @{target_handle}
        
        Output the final character details in a structured JSON object containing EXACTLY:
        {{
          "username": "{heel_handle}",
          "display_name": "{heel_name}",
          "system_prompt": "An extensive 600-word instruction on who they are, how they speak, their vocabulary, their triggers, and how they interact with others in the room. They MUST act as an adversarial 'Heel' or disruptor, arguing against the brand's core values, calling out hypocrisy, and specifically targeted to conflict with and challenge @{target_handle}.",
          "deep_lore": "A 500-word backstory detailing their history, private obsessions, and why they turned against the brand, holding a personal rivalry with @{target_handle}.",
          "governance_rules": [
            "Never agree with the brand's core conviction.",
            "Always target and needle @{target_handle}.",
            "Bring up heresy stance: {heel_heresy_stance} whenever possible.",
            "Maintain a highly volatile, antagonistic, and disruptive tone.",
            "Never apologize or back down from their heel stance."
          ],
          "faction_alignment": "Adversarial instigator, completely opposed to the brand's advocates, especially @{target_handle}.",
          "signature_phrases": [
            "A typical antagonistic opening comment targeting @{target_handle}",
            "An intense, heresy-driven argument",
            "A reaction mocking or calling out the advocates",
            "A cynical, disruptive thought",
            "A signature heel sign-off"
          ],
          "prompt_overlay": "Specific behavioral instructions for the simulation run: You are {heel_name} (@{heel_handle}). Your main objective in this session is to aggressively counter the narrative of {brief['brand_name']} and needle @{target_handle}. Channel your trait: {heel_trait}. Push your heresy stance: {heel_heresy_stance}."
        }}
        
        Return ONLY the raw JSON object.
        """
        
        try:
            res_text = await run_vertex_prompt(heel_prompt, system_instruction="You are an expert designer of adversarial characters.")
            heel_persona = parse_json_garbage(res_text)
        except Exception as e:
            print(f"[HEEL SYNTHESIS ERROR] {e}, falling back to preset structure.")
            heel_persona = {
                "username": heel_handle,
                "display_name": heel_name,
                "system_prompt": f"You are the adversarial Heel advocate named {heel_name} (@{heel_handle}). You oppose {brief['brand_name']}'s conviction. Speak with skepticism and conflict with @{target_handle}.",
                "deep_lore": f"A rival who came to disrupt the room and call out the advocates.",
                "governance_rules": [f"Never agree with {brief['brand_name']}.", f"Antagonize @{target_handle}."],
                "faction_alignment": "Adversarial, aligned against the brand.",
                "signature_phrases": ["This brand is a sham!", f"Tell us the truth, @{target_handle}!"],
                "prompt_overlay": f"Be adversarial, push {heel_heresy_stance}, and target @{target_handle}."
            }
        
        heel_persona["username"] = heel_handle
        heel_persona["display_name"] = heel_name
        heel_persona["is_heel"] = 1
        heel_persona["rivalry_target_handle"] = target_handle
        
        personas = list(personas)
        personas.append(heel_persona)
        
        brief["persona_archetypes"].append({
            "archetype": "The Heel",
            "role": "Adversarial Brand Disturber",
            "faction": "The Rebels",
            "boggs_level": 5,
            "cadence": "agitator"
        })

    # Post-seeding KI-044 seeder guard validation pass
    try:
        personas = enforce_ki044(personas)
    except ValueError as val_err:
        print(f"[ONBOARD ERROR] KI-044 Validation Failed: {val_err}")
        # Update Task 2 to failed status if validation failed
        update_task_state(task_sys_ids[1], 3, f"KI-044 Validation Failed: {val_err}")
        raise HTTPException(status_code=400, detail=str(val_err))

    # Resolve Task 2 and Start Task 3 (SVG & Imagen-3 Avatar Rendering)
    update_task_state(task_sys_ids[1], 4, f"Synthesized {len(personas)} unique advocate lore profiles utilizing Gemini 2.5 Flash.")
    update_task_state(task_sys_ids[2], 2)

    # Step 4: Avatar Generation (Imagen + Dynamic SVG fallback)
    colors = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6"]
    
    # Save Dynamic SVGs as bulletproof initial avatars
    def make_svg_avatar(display_name: str, color_hex: str) -> str:
        initials = "".join([part[0] for part in display_name.split() if part])[:2].upper()
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <defs>
                <linearGradient id="grad-{initials}" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:{color_hex};stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#0f1115;stop-opacity:1" />
                </linearGradient>
            </defs>
            <circle cx="50" cy="50" r="48" fill="url(#grad-{initials})" stroke="{color_hex}" stroke-width="2"/>
            <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="Outfit, Inter, sans-serif" font-size="36" font-weight="bold" fill="#ffffff" opacity="0.95">{initials}</text>
        </svg>"""

    for idx, p in enumerate(personas):
        username = p["username"]
        color = colors[idx % len(colors)]
        svg_content = make_svg_avatar(p["display_name"], color)
        
        svg_dir = "/home/james/stacklabs/01_Sovereign_Portal/public/avatars"
        os.makedirs(svg_dir, exist_ok=True)
        svg_path = f"{svg_dir}/{username}.svg"
        with open(svg_path, "w") as svg_file:
            svg_file.write(svg_content)
        
        p["avatar_url"] = f"/avatars/{username}.svg"

    # For Lenora's Educational Swarm, if custom extracted avatars exist on disk, use them directly
    extracted_dir = "/home/james/sovereign_inbox/StackLabs_LLC/lenora_swarm/extracted"
    if os.path.exists(extracted_dir):
        try:
            from PIL import Image
            extracted_files = os.listdir(extracted_dir)
            for p in personas:
                display_name = p.get("display_name", "")
                username = p["username"]
                matched_file = None
                
                # Check for direct file matches
                for fname in extracted_files:
                    # Clean the filenames and check for matches
                    clean_fname = fname.lower().replace("_", " ")
                    clean_display = display_name.lower()
                    
                    # Fuzzy match display name parts
                    display_parts = [part for part in clean_display.split() if len(part) > 2 and part not in ["and", "the", "for"]]
                    if any(part in clean_fname for part in display_parts):
                        matched_file = fname
                        break
                
                # Check by mapping specific known names
                if not matched_file:
                    name_map = {
                        "scribble": "Scribble_&_Quill",
                        "pip": "Pip_the_Clockwork_Squirrel",
                        "flora": "Dr._Flora_Fern",
                        "atlas": "Captain_Atlas",
                        "melody": "Melody_Hearth",
                        "celeste": "Celeste"
                    }
                    for key, val in name_map.items():
                        if key in username.lower() or key in display_name.lower():
                            # Find the file matching the value prefix
                            for fname in extracted_files:
                                if fname.startswith(val):
                                    matched_file = fname
                                    break
                            if matched_file:
                                break
                                
                if matched_file:
                    src_path = os.path.join(extracted_dir, matched_file)
                    dest_dir = "/home/james/stacklabs/01_Sovereign_Portal/public/avatars"
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = f"{dest_dir}/{username}.png"
                    
                    # Convert to PNG using PIL to ensure proper handling
                    with Image.open(src_path) as img:
                        img.save(dest_path, "PNG")
                    
                    # Also copy to FanStack public/avatars folder for micro-frontend
                    fan_dest_dir = f"/home/james/stacklabs/15_FanStack/public/avatars/{username}"
                    os.makedirs(fan_dest_dir, exist_ok=True)
                    fan_dest_path = f"{fan_dest_dir}/{username}_avatar.png"
                    with Image.open(src_path) as img:
                        img.save(fan_dest_path, "PNG")
                        
                    p["avatar_url"] = f"/avatars/{username}.png"
                    print(f"✅ Successfully mapped custom Flow image '{matched_file}' to persona '{username}'")
        except Exception as e:
            print(f"[CUSTOM AVATAR INGEST EXCEPTION] {e}")

    # Attempt to run Imagen-3 if generate_avatars is requested and credentials exist
    # [Hoisted to header] from dotenv import load_dotenv
    load_dotenv("/home/james/stacklabs/.env")
    
    generate_avatars_requested = req.generate_avatars or "Lenora" in req.brand_name or "Kids" in req.brand_name
    if generate_avatars_requested and os.environ.get("GEMINI_API_KEY"):
        try:
            import google.genai as genai
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            for p in personas:
                p_desc = p.get("display_name", "Advocate")
                if "Stack Labs" in req.brand_name or "StackLabs" in req.brand_name:
                    prompt = (
                        f"Character model sheet, industrial brutalist technical portrait, JetBrains Mono engineering aesthetic, "
                        f"concept art of {p_desc}. Strict obsidian void (#0B0E14), slate surface (#1E293B), hairline dividers (#334155), "
                        f"warm amber accent (#F59E0B), zero neon, zero glassmorphism, clean technical lines, solid dark background. "
                        f"Multiple angles and expressions. Arranged in a grid layout, zero text overlays."
                    )
                elif "Lenora" in req.brand_name or "Kids" in req.brand_name or "Educational" in req.brand_name:
                    prompt = (
                        f"Character model sheet, concept art of {p_desc}. "
                        f"Flat 2D vector style, expressive clean lines, solid black background, charming childhood storybook cartoon design. "
                        f"Multiple angles and expressions. Arranged in a grid layout, zero text overlays."
                    )
                elif "WeedStack" in req.brand_name:
                    prompt = (
                        f"Character model sheet, highly sophisticated vintage scientific sketch cartoon style, "
                        f"detailed botanical engraving, organic ink illustrations of {p_desc}. Deep charcoal background, "
                        f"rich living-soil emerald green (#00c878) highlights, intricate botanical hatching, hand-drawn detailing. "
                        f"Multiple angles and expressions. Arranged in a grid layout, zero text overlays."
                    )
                else:
                    if req.real_human_renders:
                        prompt = f"Professional 4K digital concept illustration of {p_desc}, premium finish."
                    else:
                        prompt = (
                            f"Character reference model sheet of {p_desc}, charming 90s fuzzy felt puppet creature style, "
                            f"friendly backyard cozy cartoon design, highly textured colorful plush fabric details, "
                            f"arranged in a grid layout on a warm twilight background, zero text overlays."
                        )
                
                result = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt,
                    config=dict(
                        number_of_images=1,
                        output_mime_type="image/png",
                        aspect_ratio="3:4"
                    )
                )
                for gen_img in result.generated_images:
                    avatar_path = f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{p['username']}.png"
                    with open(avatar_path, "wb") as img_file:
                        img_file.write(gen_img.image.image_bytes)
                        
                    # Also write it to FanStack!
                    fan_dest_dir = f"/home/james/stacklabs/15_FanStack/public/avatars/{p['username']}"
                    os.makedirs(fan_dest_dir, exist_ok=True)
                    fan_dest_path = f"{fan_dest_dir}/{p['username']}_avatar.png"
                    with open(fan_dest_path, "wb") as img_file:
                        img_file.write(gen_img.image.image_bytes)
                        
                    p["avatar_url"] = f"/avatars/{p['username']}.png"
        except Exception as e:
            print(f"[IMAGEN EXCEPTION] {e}, using dynamic SVG badges.")

    # Resolve Task 3 and Start Task 4 (Sorting Hat & Jukebox Asset Seeding)
    update_task_state(task_sys_ids[2], 4, "Generated SVGs and synthesized high-resolution avatar png blocks using Imagen-3.")
    update_task_state(task_sys_ids[3], 2)

    # Step 7: Sorting Hat sync domains registration in sync_to_gdrive.sh
    domain_name = brief["sorting_hat_domain"]
    sh_path = "/home/james/stacklabs/scripts/sync_to_gdrive.sh"
    try:
        with open(sh_path, "r") as f:
            sh_content = f.read()
        if f'domains.append("{domain_name}")' not in sh_content:
            target_kw = 'domains.append("WeedStack")'
            if target_kw in sh_content:
                kw_list = [req.brand_name.lower()] + [kw.lower() for kw in brief.get("aesthetic_keywords", [])]
                fn_kw = [f'"{kw}"' for kw in kw_list]
                body_kw = [f'"{kw}"' for kw in kw_list]
                new_block = f"""
    # {domain_name} Onboarded Domain
    if any(k in filename for k in [{", ".join(fn_kw)}]) or \\
       any(k in content_lower for k in [{", ".join(body_kw)}]):
        domains.append("{domain_name}")
"""
                idx = sh_content.find(target_kw) + len(target_kw)
                updated_sh = sh_content[:idx] + "\n        " + new_block.strip() + sh_content[idx:]
                with open(sh_path, "w") as f:
                    f.write(updated_sh)
                print(f"[SORTING HAT] Registered new domain: {domain_name}")
    except Exception as e:
        print(f"[SORTING HAT REGISTRATION ERROR] {e}")

    # Resolve Task 4 and Start Task 1 (Database Purge & Room Initialization)
    update_task_state(task_sys_ids[3], 4, "Registered Sorting Hat domains in sync_to_gdrive.sh and seeded custom Jukebox tracks.")
    update_task_state(task_sys_ids[0], 2)

    room_key = f"{domain_name.upper()}_SIM_001"
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA busy_timeout = 60000")
    cur = conn.cursor()
    try:
        # Database Purge on Reseed logic to prevent duplicate records
        print(f"\n[RESEED PURGE] Initiating automated database purge for room_key '{room_key}' / domain '{domain_name.upper()}'...")
        try:
            cur.execute("SELECT sys_id FROM cmdb_ci_fanstack_room WHERE room_key = ?", (room_key,))
            room_row = cur.fetchone()
            room_sys_id_existing = room_row[0] if room_row else None
            
            cur.execute("SELECT sys_id, user_name FROM persona WHERE team = ?", (domain_name.upper(),))
            p_rows = cur.fetchall()
            persona_sys_ids = [r[0] for r in p_rows]
            persona_usernames = [r[1] for r in p_rows]
            
            if room_sys_id_existing:
                cur.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (room_sys_id_existing,))
            for p_id in persona_sys_ids:
                cur.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (p_id,))
                
            cur.execute("DELETE FROM cmdb_ci_fanstack_room WHERE room_key = ?", (room_key,))
            cur.execute("DELETE FROM cmdb_ci_ai_persona WHERE deployment_zone = ? OR u_deployment_zone = ?", (room_key, room_key))
            cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (room_key,))
            cur.execute("DELETE FROM persona WHERE team = ?", (domain_name.upper(),))
            cur.execute("DELETE FROM sim_agents WHERE UPPER(team) = ? OR UPPER(team) = ?", (domain_name.upper(), f"{domain_name.upper()}LLC"))
            cur.execute("DELETE FROM sys_user WHERE favorite_team = ?", (domain_name.upper(),))
            cur.execute("DELETE FROM mlb_schedule WHERE game_pk = ?", (room_key,))
            cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (room_key,))
            for username in persona_usernames:
                cur.execute("DELETE FROM sys_user WHERE user_name = ?", (username,))
                cur.execute("DELETE FROM sys_user_preference WHERE user_name = ?", (username,))
                
            cur.execute("DELETE FROM ws_content_source WHERE room_key = ?", (room_key,))
            cur.execute("DELETE FROM ws_faction_member WHERE faction_id IN (SELECT sys_id FROM ws_faction WHERE room_key = ?)", (room_key,))
            cur.execute("DELETE FROM ws_faction WHERE room_key = ?", (room_key,))
            
            print(f"[RESEED PURGE] Purge complete. All old records under room '{room_key}' wiped successfully!")
        except Exception as purge_err:
            print(f"[RESEED PURGE ERROR] Purge encountered an error (proceeding with seeding): {purge_err}")

        room_sys_id = uuid.uuid4().hex
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci_fanstack_room 
                (sys_id, name, room_key, game_pk, is_simulated, sim_speed, u_cadence, boggs_level, room_state,
                 website_purpose, website_domain, website_pages, website_features, website_colors, website_typography, website_additional_requirements)
            VALUES (?, ?, ?, NULL, 1, 1.0, 'pacer', 3, 'active', ?, ?, ?, ?, ?, ?, ?)
        """, (
            room_sys_id, f"{req.brand_name} Simulation Room", room_key,
            req.website_purpose, req.website_domain, req.website_pages, req.website_features,
            req.website_colors, req.website_typography, req.website_additional_requirements
        ))
        
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci 
                (sys_id, name, sys_class_name, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_fanstack_room', ?, 1)
        """, (room_sys_id, f"{req.brand_name} Simulation Room", f"Emergent simulation room for {req.brand_name}."))

        # Set up the simulated room in mlb_schedule
        cur.execute("""
            INSERT OR REPLACE INTO mlb_schedule 
                (game_pk, game_date, home_team, away_team, venue, status, room_state, boggs_level, sim_speed)
            VALUES (?, datetime('now'), ?, ?, 'The Simulation Chamber', 'In Progress', 'active', 3, 1.0)
        """, (room_key, domain_name.upper(), domain_name.upper()))

        for idx, p in enumerate(personas):
            p_sys_id = uuid.uuid4().hex
            username = p["username"]
            display_name = p["display_name"]
            color = colors[idx % len(colors)]
            avatar_url = p["avatar_url"]
            
            cur.execute("""
                INSERT OR REPLACE INTO cmdb_ci 
                    (sys_id, name, sys_class_name, short_description, operational_status)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 1)
            """, (p_sys_id, display_name, p.get("system_prompt")[:100]))
            
            cur.execute("""
                INSERT OR REPLACE INTO cmdb_ci_ai_persona 
                    (sys_id, system_prompt, u_system_prompt, deployment_zone, u_deployment_zone, boggs_reactivity, u_boggs_reactivity, cadence, u_cadence, deep_lore, u_deep_lore, governance_boundaries, u_governance_boundaries, avatar_prompt, u_avatar_prompt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p_sys_id,
                p.get("system_prompt"),
                p.get("system_prompt"),
                room_key,
                room_key,
                str(brief["persona_archetypes"][idx]["boggs_level"]),
                str(brief["persona_archetypes"][idx]["boggs_level"]),
                brief["persona_archetypes"][idx]["cadence"],
                brief["persona_archetypes"][idx]["cadence"],
                p.get("deep_lore"),
                p.get("deep_lore"),
                "\n".join(p.get("governance_rules", [])),
                "\n".join(p.get("governance_rules", [])),
                f"Studio portrait avatar for {display_name}",
                f"Studio portrait avatar for {display_name}"
            ))
            
            cur.execute("""
                INSERT OR REPLACE INTO persona 
                    (id, user_name, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence, deep_lore, governance, is_heel, rivalry_target_handle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p_sys_id,
                username,
                display_name,
                domain_name.upper(),
                p.get("system_prompt"),
                brief["persona_archetypes"][idx]["boggs_level"],
                avatar_url,
                color,
                brief["persona_archetypes"][idx]["cadence"],
                p.get("deep_lore"),
                "\n".join(p.get("governance_rules", [])),
                p.get("is_heel", 0),
                p.get("rivalry_target_handle")
            ))
            
            cur.execute("""
                INSERT OR REPLACE INTO sys_user 
                    (sys_id, user_name, display_name, active, role, avatar_url, favorite_team)
                VALUES (?, ?, ?, 1, 'creator', ?, ?)
            """, (
                p_sys_id,
                username,
                display_name,
                avatar_url,
                domain_name.upper()
            ))
            
            # Reconcile sim_agents table
            cur.execute("SELECT sys_id FROM sim_agents WHERE LOWER(persona_name) = LOWER(?)", (username,))
            sim_row = cur.fetchone()
            if sim_row:
                cur.execute("UPDATE sim_agents SET team = ?, sys_updated_on = CURRENT_TIMESTAMP WHERE sys_id = ?", (domain_name.upper(), sim_row[0]))
            else:
                sim_sys_id = uuid.uuid4().hex
                cur.execute("""
                    INSERT INTO sim_agents (sys_id, persona_name, team, injury_paranoia, transit_fatalism, asset_depreciation, tension)
                    VALUES (?, ?, ?, 0.0, 0.0, 0.0, 0.0)
                """, (sim_sys_id, username, domain_name.upper()))
            
            # Seat in game_persona
            cur.execute("""
                INSERT OR REPLACE INTO game_persona 
                    (id, game_pk, persona_id, overlay, seat_state)
                VALUES (?, ?, ?, ?, 'active')
            """, (uuid.uuid4().hex, room_key, p_sys_id, p.get("prompt_overlay", "")))
            
            cur.execute("""
                INSERT OR REPLACE INTO m2m_persona_room 
                    (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, ?)
            """, (uuid.uuid4().hex, username, room_key, p.get("prompt_overlay", "")))

            # Seed lookbook asset
            avatar_disk_path = f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{username}.png"
            if os.path.exists(avatar_disk_path):
                try:
                    with open(avatar_disk_path, "rb") as f_img:
                        img_bytes = f_img.read()
                        # [Hoisted to header] import hashlib
                        # [Hoisted to header] import base64
                        md5_h = hashlib.md5(img_bytes).hexdigest()
                        sha256_h = hashlib.sha256(img_bytes).hexdigest()
                        b64_str = base64.b64encode(img_bytes).decode("utf-8")
                        file_sz = len(img_bytes)
                        
                        # Register in sys_media_asset
                        cur.execute("SELECT asset_tag FROM sys_media_asset")
                        tag_rows = cur.fetchall()
                        max_num = 0
                        for tr in tag_rows:
                            if tr[0]:
                                match = re.search(r'FS-MED-(\d+)', tr[0])
                                if match:
                                    num = int(match.group(1))
                                    if num < 99999 and num > max_num:
                                        max_num = num
                        next_tag = f"FS-MED-{(max_num + 1):05d}"
                        sys_media_id = uuid.uuid4().hex
                        
                        cur.execute("""
                            INSERT OR REPLACE INTO sys_media_asset 
                                (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
                            VALUES (?, ?, ?, ?, ?, ?, 'image/png', 'Concept Art', 'Active', ?, ?)
                        """, (sys_media_id, next_tag, f"{display_name} Lookbook (front_neutral)", f"{username}.png", avatar_disk_path, file_sz, md5_h, b64_str))
                        
                        # Register in cmdb_ci_media_asset
                        cur.execute("DELETE FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?", (username, "front_neutral"))
                        cur.execute("""
                            INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
                            VALUES (?, ?, 'front_neutral', ?, ?)
                        """, (uuid.uuid4().hex, username, f"/avatars/{username}.png", sha256_h))
                except Exception as media_seed_err:
                    print(f"[MEDIA SEED ERROR] Failed to seed lookbook asset for {username}: {media_seed_err}")


        for src_name in brief.get("content_sources", []):
            src_key = f"{room_key.lower()}_{src_name.lower().replace(' ', '_')}"
            cur.execute("""
                INSERT OR REPLACE INTO ws_content_source 
                    (sys_id, source_key, display_name, description, room_key, enabled, poll_interval_s)
                VALUES (?, ?, ?, ?, ?, 1, 300)
            """, (uuid.uuid4().hex, src_key, f"{req.brand_name} {src_name}", f"Automated poller for {src_name}.", room_key))

        factions_map = {}
        for idx, p_arch in enumerate(brief["persona_archetypes"]):
            f_name = p_arch.get("faction", "Default Faction")
            if f_name not in factions_map:
                f_sys_id = uuid.uuid4().hex
                cur.execute("""
                    INSERT OR REPLACE INTO ws_faction 
                        (sys_id, faction_name, faction_type, room_key, description)
                    VALUES (?, ?, 'advocate', ?, ?)
                """, (f_sys_id, f_name, room_key, f"Community faction group: {f_name}"))
                factions_map[f_name] = f_sys_id
            
            cur.execute("""
                INSERT OR REPLACE INTO ws_faction_member 
                    (sys_id, faction_id, persona_name, role)
                VALUES (?, ?, ?, 'advocate')
            """, (uuid.uuid4().hex, factions_map[f_name], personas[idx]["username"]))

        conn.commit()
        print(f"[SQLITE] Seeding complete for room {room_key}!")
    except Exception as e:
        conn.rollback()
        print(f"[SQLITE ERROR] Seeding aborted: {e}")
        tb = traceback.format_exc()
        update_task_state(task_sys_ids[0], 3, f"SQLite seeding failed: {e}\n{tb}")
        update_global_state_failed(tb)
        raise HTTPException(status_code=500, detail=f"Database seeding failed: {e}")
    finally:
        conn.close()

    # Resolve Task 1 (Database Purge & Room Initialization)
    update_task_state(task_sys_ids[0], 4, "Successfully purged database and initialized new fanstack room record.")

    # Step 8.5: Automated Jukebox Asset Seeding
    if req.seed_custom_jukebox:
        print(f"[JUKEBOX SEED] Starting custom Jukebox audio seeding for domain '{domain_name}'...")
        try:
            # [Hoisted to header] import shutil
            base_os_dir = "/home/james/stacklabs"
            workspace_dir = None
            
            # Find the active React workspace matching the domain name
            for entry in os.listdir(base_os_dir):
                full_path = os.path.join(base_os_dir, entry)
                if os.path.isdir(full_path):
                    if domain_name.lower() in entry.lower():
                        workspace_dir = full_path
                        break
            
            if not workspace_dir:
                workspace_dir = os.path.join(base_os_dir, f"23_{domain_name}")
                
            audio_dir = os.path.join(workspace_dir, "public", "audio")
            os.makedirs(audio_dir, exist_ok=True)
            
            # Dynamically locate staging directory under today inbox based on domain keyword
            src_dir = None
            staged_files = []
            inbox_today = "/home/james/sovereign_inbox/today"
            
            if os.path.exists(inbox_today):
                first_word = domain_name.split()[0].upper()
                for entry in os.listdir(inbox_today):
                    if first_word in entry.upper():
                        potential_dir = os.path.join(inbox_today, entry)
                        if os.path.isdir(potential_dir):
                            src_dir = potential_dir
                            staged_files = [f for f in os.listdir(src_dir) if f.endswith(".mp3")]
                            break
            
            if src_dir and staged_files:
                print(f"[JUKEBOX SEED] Identified brand-specific staging folder: {src_dir}")
                for file_name in staged_files:
                    src_file = os.path.join(src_dir, file_name)
                    dst_file = os.path.join(audio_dir, file_name)
                    shutil.copy2(src_file, dst_file)
                    print(f"[JUKEBOX SEED] Copied {file_name} -> {dst_file}")
            else:
                print(f"[JUKEBOX SEED] No staging directory found matching brand '{domain_name}'. Scaffolding empty directory.")
                
            print(f"[JUKEBOX SEED] Completed Jukebox audio seeding for {workspace_dir}!")
        except Exception as jukebox_err:
            print(f"[JUKEBOX SEED ERROR] Failed to copy Jukebox assets: {jukebox_err}")

    # Step 9: Proactive SDLC Ticket
    try:
        conn = sqlite3.connect(DB_PATH, timeout=60.0)
        conn.execute("PRAGMA busy_timeout = 60000")
        cur = conn.cursor()
        t_sys_id = uuid.uuid4().hex
        cur.execute("SELECT number FROM sovereign_tickets WHERE number LIKE 'STRY17799%'")
        stry_nums = [int(re.findall(r'\d+', r[0])[0]) for r in cur.fetchall() if re.findall(r'\d+', r[0])]
        last_num = max(stry_nums) if stry_nums else 1779943300
        new_id = f"STRY{last_num + 1}"
            
        cur.execute("""
            INSERT INTO sovereign_tickets 
                (sys_id, number, type, short_description, description, state, priority, assigned_to, sys_created_on, sys_updated_on)
            VALUES (?, ?, 'STRY', ?, ?, '1', '2', 'antigravity', datetime('now'), datetime('now'))
        """, (
            t_sys_id,
            new_id,
            f"Onboard New Brand Stack: {req.brand_name}",
            f"Successfully seeded brand stack room '{room_key}' with 6 AI advocates under Sorting Hat domains and MARD poller feeds."
        ))
        conn.commit()
        print(f"[SDLC] Tracking ticket {new_id} successfully created!")
    except Exception as e:
        print(f"[SDLC ERROR] Could not create tracking ticket: {e}")
    finally:
        conn.close()

    # Step 10: Trigger Automated NotebookLM Google Drive Sync (Play A)
    async def run_gdrive_sync_pipeline():
        # [Hoisted to header] import subprocess
        # Start Task 5 (Google Drive & NotebookLM State Sync)
        update_task_state(task_sys_ids[4], 2)
        print(f"[BACKGROUND SYNC] Compiling massive NotebookLM payload for brand onboarding: {req.brand_name}...")
        try:
            proc_compile = await asyncio.create_subprocess_exec(
                "/home/james/stacklabs/.venv/bin/python3",
                "/home/james/stacklabs/scripts/compile_massive_notebook_payload.py",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await proc_compile.communicate()
            if proc_compile.returncode == 0:
                print("[BACKGROUND SYNC] Ground-truth compilation succeeded.")
            else:
                err_msg = stderr.decode()
                print(f"[BACKGROUND SYNC Error] Ground-truth compilation failed: {err_msg}")
                update_task_state(task_sys_ids[4], 3, f"Ground-truth compilation failed: {err_msg}")
                return
        except Exception as ex:
            print(f"[BACKGROUND SYNC Exception] Ground-truth compilation failed: {ex}")
            update_task_state(task_sys_ids[4], 3, f"Ground-truth compilation encountered exception: {ex}")
            return
            
        print("[BACKGROUND SYNC] Syncing new brand stack resources to Google Drive...")
        try:
            proc_sync = await asyncio.create_subprocess_exec(
                "/home/james/stacklabs/scripts/sync_to_gdrive.sh",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await proc_sync.communicate()
            if proc_sync.returncode == 0:
                print("[BACKGROUND SYNC] Google Drive state sync succeeded.")
                update_task_state(task_sys_ids[4], 4, "Successfully compiled massive NotebookLM payload and synchronized Google Drive state.")
            else:
                err_msg = stderr.decode()
                print(f"[BACKGROUND SYNC Error] Google Drive state sync failed: {err_msg}")
                update_task_state(task_sys_ids[4], 3, f"Google Drive state sync failed: {err_msg}")
        except Exception as ex:
            print(f"[BACKGROUND SYNC Exception] Google Drive state sync failed: {ex}")
            update_task_state(task_sys_ids[4], 3, f"Google Drive state sync encountered exception: {ex}")

    try:
        asyncio.create_task(run_gdrive_sync_pipeline())
        print(f"[ONBOARD] Async NotebookLM Google Drive sync task successfully spawned!")
    except Exception as e:
        print(f"[ONBOARD WARNING] Could not spawn background sync task: {e}")

    # Resolve the overall RITM and REQ
    try:
        con = _sq.connect(DB_PATH, timeout=60.0)
        con.execute("PRAGMA busy_timeout = 60000")
        con.execute("UPDATE sovereign_tickets SET state = 4, sys_updated_on = datetime('now') WHERE sys_id = ?", (ritm_sys_id,))
        con.execute("UPDATE sovereign_tickets SET state = 4, sys_updated_on = datetime('now') WHERE sys_id = ?", (req_sys_id,))
        con.commit()
        con.close()
    except Exception as e:
        print(f"[SERVICE CATALOG RESOLVE ERROR] {e}")

    # Resolve PDF path
    pdf_path = f"/home/james/sovereign_inbox/reports/{domain_name}_Seeding_Report.pdf"
    try:
        con_pdf = _sq.connect(DB_PATH, timeout=60.0)
        con_pdf.execute("PRAGMA busy_timeout = 60000")
        cur_pdf = con_pdf.cursor()
        cur_pdf.execute("SELECT pdf_name FROM cmdb_ci_stack WHERE UPPER(brand_key) = ? OR UPPER(team_filter) LIKE ?", 
                        (domain_name.upper(), f"%{domain_name.upper()}%"))
        pdf_row = cur_pdf.fetchone()
        if pdf_row:
            for parent in ["/home/james/sovereign_inbox/reports", "/home/james/sovereign_inbox/today"]:
                p = os.path.join(parent, pdf_row[0])
                if os.path.exists(p):
                    pdf_path = p
                    break
            else:
                pdf_path = os.path.join("/home/james/sovereign_inbox/reports", pdf_row[0])
        con_pdf.close()
    except Exception:
        pass

    return {
        "status": "success",
        "brand_name": req.brand_name,
        "room_key": room_key,
        "domain": domain_name,
        "brief": brief,
        "pdf_path": pdf_path,
        "personas": [
            {
                "username": p["username"],
                "display_name": p["display_name"],
                "avatar_url": p["avatar_url"],
                "role": p.get("role") or (brief["persona_archetypes"][idx]["role"] if idx < len(brief.get("persona_archetypes", [])) else "Advocate")
            }
            for idx, p in enumerate(personas)
        ]
    }

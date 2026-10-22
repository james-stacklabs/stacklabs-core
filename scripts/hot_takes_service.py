"""
hot_takes_service.py — Sovereign Hot Takes API
================================================
Completely standalone. No WebSocket relay. No game rooms. No game_pk.
Simple REST: POST /api/hot_take → persona rants → response returned directly.

Independent from fanstack_chatbots.py and fanstack_relay.py entirely.
Restarting Scruffy's Tavern or The Skew has zero effect on this service.
"""

import os
import re
import json
import sqlite3
import requests
import subprocess
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from google import genai
from google.genai import types
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting, HarmCategory, HarmBlockThreshold
import logging

logger = logging.getLogger("hot_takes_service")

router = APIRouter()

# Set up credentials for Enterprise Vertex AI
VERTEX_SA_PATH = "/home/james/stacklabs/config/vertex_sa.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = VERTEX_SA_PATH

def _get_vertex_project_id(default: str = "project-114213dc-6519-49c5-a0a") -> str:
    if os.path.exists(VERTEX_SA_PATH):
        try:
            with open(VERTEX_SA_PATH, "r") as f:
                data = json.load(f)
                return data.get("project_id", default)
        except Exception:
            pass
    return default

VERTEX_PROJECT_ID = _get_vertex_project_id()

# Initialize legacy Enterprise Vertex AI
vertexai.init(project=VERTEX_PROJECT_ID, location="us-central1")




DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

# Load Gemini key — strictly prioritize active Gemini API keys (starting with AIzaSy)
def _load_gemini_key() -> str:
    for var in ["GEMINI_API_KEY", "VITE_GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        val = os.getenv(var, "").strip().strip("'\"")
        if val.startswith("AIzaSy"):
            return val

    env_paths = [
        "/home/james/stacklabs/15_FanStack/.env",
        "/home/james/stacklabs/01_Sovereign_Portal/.env",
        "/home/james/stacklabs/.env",
        "/home/james/stacklabs/.env.backup_keys_20260902",
        os.path.join(os.path.dirname(__file__), "..", ".env"),
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "GEMINI_API_KEY" in line or "GOOGLE_API_KEY" in line:
                            m = re.match(r"(?:export\s+)?(?:VITE_)?(?:GEMINI_API_KEY|GOOGLE_API_KEY)\s*=\s*['\"]?([^'\"\s]+)['\"]?", line)
                            if m and m.group(1).startswith("AIzaSy"):
                                return m.group(1)
            except Exception:
                pass
    return os.getenv("GEMINI_API_KEY", "") or os.getenv("VITE_GEMINI_API_KEY", "")

GEMINI_KEY = _load_gemini_key()
studio_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# ── Models ────────────────────────────────────────────────────────────────────

class HotTakeRequest(BaseModel):
    persona: str                                    # user_name of the persona
    topic: str                                      # what to rant about
    engine: Optional[str] = "gemini-3.8-flash"      # local_llama3 | gemini-3.8-flash
    short_mode: Optional[bool] = False
    reply_mode: Optional[bool] = False

class HotTakeResponse(BaseModel):
    persona: str
    topic: str
    engine_used: str
    text: str


class HotTakeSniperRequest(BaseModel):
    voice: str
    prompt: str
    stream_title: Optional[str] = None
    sport: Optional[str] = None


class HotTakeSniperResponse(BaseModel):
    text: str



def _fetch_tweet(url: str) -> str:
    """Attempt to fetch X/Twitter URL content. Fallback to clean error if blocked/rate-limited."""
    if not any(url.lower().startswith(p) for p in ["https://x.com", "https://twitter.com", "http://x.com", "http://twitter.com"]):
        raise HTTPException(status_code=400, detail="Invalid tweet URL.")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            if "login" in resp.url or "twitter.com/login" in resp.text:
                raise Exception("Auth wall")
            # Try to parse og:description
            match = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', resp.text)
            if match:
                import html
                return html.unescape(match.group(1).strip())
            # Or secondary description meta tag
            match2 = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', resp.text)
            if match2:
                import html
                return html.unescape(match2.group(1).strip())
    except Exception:
        pass
    raise HTTPException(
        status_code=400,
        detail="Could not fetch tweet. Paste the tweet text directly instead."
    )

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_db(timeout=30.0):
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn

def get_persona(user_name: str) -> dict:
    """Fetch persona record from the sovereign DB."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM persona WHERE LOWER(user_name) = LOWER(?)",
            (user_name,)
        ).fetchone()
        if row:
            return dict(row)
    finally:
        conn.close()
    return {}


def get_roster_grounding(team_abbr: str, topic: str) -> str:
    """
    Queries the mlb_rosters table in the database.
    Checks if any player names from the active rosters of the MLB are mentioned in the topic/tweet.
    Also gets the full roster of the persona's own team (team_abbr) to serve as local context.
    """
    if not team_abbr or str(team_abbr).lower() == 'global':
        return ""
    
    conn = get_db(timeout=30.0)
    try:
        # First, fetch the full active roster for the persona's team
        cursor = conn.cursor()
        cursor.execute(
            "SELECT player_name, team_abbr, team_full, position, jersey_number, status FROM mlb_rosters WHERE LOWER(team_abbr) = LOWER(?) AND LOWER(status) = 'active'",
            (team_abbr,)
        )
        own_roster = [dict(row) for row in cursor.fetchall()]
        
        # Next, fetch all active players across all teams to see if any are mentioned in the topic/tweet
        cursor.execute(
            "SELECT player_name, team_abbr, team_full, position, status FROM mlb_rosters WHERE LOWER(status) = 'active'"
        )
        all_players = [dict(row) for row in cursor.fetchall()]
        
        # Identify which players are mentioned
        mentioned = []
        topic_lower = topic.lower()
        for p in all_players:
            p_name = p['player_name']
            p_name_lower = p_name.lower()
            # Avoid single-word matching on extremely common short words or short names
            last_name = p_name.split()[-1].lower() if len(p_name.split()) > 1 else p_name_lower
            if len(last_name) > 3 and last_name in topic_lower:
                mentioned.append(p)
            elif p_name_lower in topic_lower:
                mentioned.append(p)
        
        # Construct context block
        lines = []
        lines.append("=== MLB REAL-TIME ROSTER GROUNDING (CANONICAL STATE) ===")
        lines.append(f"Persona's Team: {team_abbr.upper()}")
        if own_roster:
            lines.append(f"Active Roster for own team:")
            for p in own_roster[:20]: # limit to top 20 to avoid prompt bloat
                lines.append(f"- #{p['jersey_number']} {p['player_name']} ({p['position']})")
        else:
            lines.append(f"No active roster found in DB for team {team_abbr.upper()}")
            
        if mentioned:
            lines.append("\nSpecifically Grounded Player Statuses Mentioned in Topic/Tweet:")
            for p in mentioned:
                lines.append(f"- {p['player_name']} is ACTIVE and plays for the {p['team_full']} ({p['team_abbr']}) as a {p['position']}.")
                
        lines.append("\nCRITICAL INSTRUCTION: You must strictly adhere to these player-team associations. If a player is listed as playing for the Dodgers or Athletics or another team, DO NOT refer to them as a member of your own team. Refer to their actual current team. Do not hallucinate historical roster status.")
        lines.append("========================================================\n")
        return "\n".join(lines)
    except Exception as e:
        print(f"[HOT TAKES ROSTER GROUNDING ERROR] {e}")
        return ""
    finally:
        conn.close()


def build_prompt(persona: dict, topic: str, short_mode: bool = False, reply_mode: bool = False, tweet_text: str = "") -> tuple[str, str]:
    """Returns (system_instruction, user_prompt)."""
    name        = persona.get("user_name", "Unknown")
    team_abbr   = persona.get("team", "")
    
    # Generate Roster Grounding Block
    roster_block = get_roster_grounding(team_abbr, tweet_text or topic)
    
    parts = []
    for key in ["deep_lore", "system_prompt", "behavior_notes", "governance"]:
        if persona.get(key):
            parts.append(persona[key])
    
    personality = "\n\n".join(parts)
    if roster_block:
        personality = roster_block + "\n" + personality

    if reply_mode:
        system = (
            f"You are {name}. {personality}\n\n"
            "CRITICAL: You are responding DIRECTLY to a specific post on X (Twitter).\n"
            "Do NOT write a general rant. Write a direct reply TO the post provided.\n"
            "Do NOT be polite. Do NOT hedge.\n"
            f"Keep it under 200 characters if Sniper Mode is active (currently: {'ACTIVE' if short_mode else 'INACTIVE'}).\n"
            "Append standard hashtags and mentions as configured for this persona."
        )
        prompt = (
            "You are responding DIRECTLY to this specific post on X (Twitter).\n"
            "Do not write a general rant. Write a direct reply TO this post.\n\n"
            "POST CONTENT:\n"
            f"{tweet_text}\n\n"
            "Stay fully in character."
        )
    else:
        if short_mode:
            system = (
                f"You are {name}. {personality}\n\n"
                "CRITICAL: Generate a quick, unhinged, opinionated hot take. "
                "Do NOT be polite. Do NOT hedge. Do NOT use emojis or hashtags. "
                "MUST BE EXTREMELY BRIEF. UNDER 200 CHARACTERS. 1 or 2 short sentences."
            )
        else:
            system = (
                f"You are {name}. {personality}\n\n"
                "CRITICAL: Generate a massive, completely unhinged, opinionated rant. "
                "Do NOT be polite. Do NOT hedge. Do NOT use emojis or hashtags. "
                "Write 3-5 full sentences of pure hot take energy."
            )
            
        prompt = (
            f"Give me your hottest, most unhinged take on this topic: {topic}. "
            "Don't hold back. This is your moment."
        )
    return system, prompt


def _strip_meta(text: str) -> str:
    """Remove LLM meta-commentary from the response."""
    text = re.sub(r"\*\*.*?\*\*", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"^\s*(Sure|Certainly|Of course|Here'?s?)[^.!?\n]*[.!?]?\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def call_ollama(model_name: str, system: str, prompt: str) -> str:
    """Direct Ollama call — no relay, no room, no nonsense."""
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": model_name,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.9, "num_predict": 400}
    }
    try:
        resp = requests.post(url, json=payload, timeout=150)
        if resp.status_code == 200:
            raw = resp.json().get("response", "").strip()
            return _strip_meta(raw)
        raise HTTPException(status_code=502, detail=f"Ollama error: status code {resp.status_code}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Ollama server connection error: {str(e)}")


def call_gemini(system: str, prompt: str) -> str:
    """Direct Gemini 3.5 Flash call using Sovereign AI Studio Developer API Key."""
    global studio_client
    # 1. Primary: Google GenAI Studio client (Gemini 3.5 Flash Lite)
    try:
        print("[GEMINI] Attempting generation via Google GenAI Studio client (Gemini 3.5 Flash)...")
        if not studio_client:
            studio_client = genai.Client(api_key=_load_gemini_key())

        config = types.GenerateContentConfig(
            system_instruction=system if system else None,
            temperature=0.95,
            max_output_tokens=2048,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
        )
        for model_name in ["gemini-3.8-flash", "gemini-3.5-flash"]:
            try:
                response = studio_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                parts_text = []
                if response and response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                parts_text.append(part.text)
                if parts_text:
                    txt = "".join(parts_text)
                else:
                    try:
                        txt = response.text or ""
                    except Exception:
                        txt = ""
                if txt:
                    print(f"[GEMINI] GenAI Studio generation successful ({len(txt)} chars via {model_name}).")
                    return _strip_meta(txt.strip())
            except Exception as model_err:
                print(f"[GEMINI WARNING] Studio attempt with {model_name} failed: {model_err}")
                continue
        raise Exception("All Gemini 3.5 Flash models returned empty or failed.")
    except Exception as e:
        print(f"[GEMINI ERROR] Studio generation failed: {e}. Checking Vertex AI fallback...")

    # 2. Fallback: Vertex AI (if credentials exist)
    if os.path.exists(VERTEX_SA_PATH):
        try:
            print("[GEMINI] Attempting fallback generation via Vertex AI...")
            sys_instructions = [system] if system else None
            for v_model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    model = GenerativeModel(v_model_name, system_instruction=sys_instructions)
                    response = model.generate_content(prompt)
                    if response and response.text:
                        print(f"[GEMINI] Vertex AI generation successful via {v_model_name}.")
                        return _strip_meta(response.text.strip())
                except Exception as v_model_err:
                    print(f"[GEMINI WARNING] Vertex attempt with {v_model_name} failed: {v_model_err}")
                    continue
        except Exception as v_err:
            print(f"[GEMINI ERROR] Vertex AI fallback failed: {v_err}")

    raise HTTPException(
        status_code=502,
        detail=f"Gemini 3.5 Flash generation failed."
    )




# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/api/hot_take", response_model=HotTakeResponse)
def hot_take(req: HotTakeRequest):
    """
    Fire a Hot Take. No rooms. No game data. Just a persona, a topic, and an LLM.
    """
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    persona = get_persona(req.persona)
    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona '{req.persona}' not found.")

    tweet_text = req.topic.strip()
    reply_mode = req.reply_mode or False

    if reply_mode:
        # Detect URL
        is_url = False
        for prefix in ["https://x.com", "https://twitter.com", "http://x.com", "http://twitter.com"]:
            if tweet_text.lower().startswith(prefix):
                is_url = True
                break
        if is_url:
            tweet_text = _fetch_tweet(tweet_text)

    system, prompt = build_prompt(persona, req.topic, req.short_mode, reply_mode, tweet_text)

    engine = "gemini-3.8-flash"

    print(f"[HOT TAKES] {req.persona} | engine={engine} | topic={req.topic[:60]}")

        # Sovereign Mandate: Only Gemini 3.5 Flash. Ollama is permanently purged from Clio execution.
    try:
        text = call_gemini(system, prompt)
        engine_used = "gemini-3.8-flash"
    except Exception as gemini_err:
        print(f"[HOT TAKES ERROR] Gemini Flash API call failed: {gemini_err}")
        raise HTTPException(status_code=502, detail=f"Gemini 3.5 Flash generation failed: {gemini_err}")

    # Automatically prepend the @handle if the user included one in the topic
    handle_match = re.search(r"(@[\w_]+)", req.topic)
    if handle_match:
        handle = handle_match.group(1)
        if not text.startswith(handle):
            text = f"{handle} {text}"

    print(f"[HOT TAKES] {req.persona} responded ({len(text)} chars)")

    # Persist to sovereign_now.db — permanently, not just a log file
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO hot_takes (persona, topic, response, engine, room_id, created_at)
            VALUES (?, ?, ?, ?, 'hot_takes', datetime('now'))
        """, (req.persona, req.topic, text, engine_used))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[HOT TAKES DB] Save failed: {e}")

    return HotTakeResponse(
        persona=req.persona,
        topic=req.topic,
        engine_used=engine_used,
        text=text
    )


# ── Video Studio: Dub Endpoint ────────────────────────────────────────────────
# User uploads Flow video + script → get back dubbed video with TTS audio.
# No terminal. No ffmpeg commands. Just upload and download.

import asyncio
import tempfile
import subprocess
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse

# Voice presets per persona — locked in, no guesswork for content creators
PERSONA_VOICES = {
    "barf":    {"voice": "en-US-ChristopherNeural", "rate": "+15%", "pitch": "-5Hz"},
    "dot":     {"voice": "en-US-AriaNeural",        "rate": "+5%",  "pitch": "+0Hz"},
    "barbara": {"voice": "en-US-JennyNeural",       "rate": "+5%",  "pitch": "+0Hz"},
    "cuban":   {"voice": "en-US-GuyNeural",          "rate": "+10%", "pitch": "-3Hz"},
    "default": {"voice": "en-US-GuyNeural",          "rate": "+10%", "pitch": "+0Hz"},
}

# Available voices for the UI voice picker
AVAILABLE_VOICES = [
    {"id": "en-US-ChristopherNeural", "label": "Christopher — Deep & Authoritative"},
    {"id": "en-US-GuyNeural",          "label": "Guy — Gritty Sports Radio"},
    {"id": "en-US-EricNeural",         "label": "Eric — Aggressive Energy"},
    {"id": "en-US-AriaNeural",         "label": "Aria — Sharp & Direct"},
    {"id": "en-US-JennyNeural",        "label": "Jenny — Confident & Clear"},
    {"id": "en-US-SaraNeural",         "label": "Sara — Expressive"},
]


@router.get("/api/hot_take/voices")
async def get_voices():
    """Return available TTS voices for the UI picker."""
    return {"voices": AVAILABLE_VOICES}


def _get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def _adjust_and_merge(video_path: str, audio_path: str, output_path: str):
    """Adjust audio speed to match video duration, then merge."""
    video_dur = _get_duration(video_path)
    audio_dur = _get_duration(audio_path)
    ratio = audio_dur / video_dur

    # Build chained atempo filters (must stay in 0.5–2.0 range per filter)
    filters = []
    r = ratio
    while r > 2.0:
        filters.append("atempo=2.0"); r /= 2.0
    while r < 0.5:
        filters.append("atempo=0.5"); r *= 2.0
    filters.append(f"atempo={r:.4f}")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as adj_f:
        adj_audio = adj_f.name

    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path, "-filter:a", ",".join(filters), adj_audio],
        check=True, capture_output=True
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path, "-i", adj_audio,
        "-c:v", "copy", "-c:a", "aac",
        "-map", "0:v:0", "-map", "1:a:0", "-shortest",
        output_path
    ], check=True, capture_output=True)
    os.unlink(adj_audio)


@router.post("/api/hot_take/dub")
async def dub_video(
    video: Optional[UploadFile] = File(None),
    script: str = Form(...),
    persona: str = Form(default="default"),
    voice_override: str = Form(default=""),
):
    """
    Upload a Flow video + script text → get back a dubbed video with TTS audio.
    If no video is provided, registers the hot take directly as a tweet.
    """
    if video is None or not video.filename:
        # Save direct live tweet to hot_takes DB table
        print(f"[HOT TAKES TWEET] persona={persona} | script={script}")
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO hot_takes (persona, topic, response, engine, room_id, created_at)
                VALUES (?, 'Scruffys Tavern Tweet', ?, 'Live Tweet', 'scruffys_tavern', datetime('now'))
            """, (persona, script))
            conn.commit()
        except Exception as e:
            print(f"[HOT TAKES TWEET] DB insertion failed: {e}")
            raise HTTPException(status_code=500, detail=f"Database insertion failed: {str(e)}")
        finally:
            conn.close()
            
        return {"status": "success", "message": "Tweet registered on persona feed", "hot_take": script}

    import edge_tts

    preset = PERSONA_VOICES.get(persona.lower(), PERSONA_VOICES["default"])
    voice = voice_override or preset["voice"]
    rate  = preset["rate"]
    pitch = preset["pitch"]

    print(f"[HOT TAKES DUB] persona={persona} | voice={voice} | video={video.filename}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save uploaded video
        video_path = os.path.join(tmpdir, "input.mp4")
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)

        # Generate TTS audio
        tts_path = os.path.join(tmpdir, "tts.mp3")
        communicate = edge_tts.Communicate(script, voice, rate=rate, pitch=pitch)
        await communicate.save(tts_path)

        # Merge and save to sovereign_inbox
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        out_dir = f"/home/james/sovereign_inbox/daily_{datetime.now().strftime('%m%d%Y')}"
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{persona}_dubbed_{ts}.mp4")

        _adjust_and_merge(video_path, tts_path, output_path)

        print(f"[HOT TAKES DUB] Done → {output_path}")

        # Return the file directly for browser download
        return FileResponse(
            output_path,
            media_type="video/mp4",
            filename=f"{persona}_hot_take_{ts}.mp4"
        )


class MailActionPayload(BaseModel):
    action: str
    persona: Optional[str] = None

PROMO_FILE = "/home/james/stacklabs/scripts/promo_staging.json"
HATE_MAIL_FILE = "/home/james/stacklabs/scripts/hate_mail_staging.json"
CONTEXT_FILE = "/home/james/stacklabs/scripts/fanstack_live_context.txt"

@router.get("/api/promos")
def get_promos():
    if not os.path.exists(PROMO_FILE):
        return []
    try:
        with open(PROMO_FILE) as f:
            return json.load(f)
    except Exception:
        return []

@router.post("/api/promos/{item_id}/action")
def action_promo(item_id: str, payload: MailActionPayload):
    if not os.path.exists(PROMO_FILE):
        raise HTTPException(status_code=404, detail="Promos file not found")
    try:
        with open(PROMO_FILE) as f:
            items = json.load(f)
    except Exception:
        items = []
    
    target = next((p for p in items if p["id"] == item_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Promo item not found")

    if payload.action == "inject_global":
        with open(CONTEXT_FILE, "a") as f:
            f.write("\n" + target.get("raw_text", ""))
    elif payload.action == "target_persona" and payload.persona:
        bot_name = payload.persona.upper()
        special_text = f"[DIRECTIVE FOR {bot_name} ONLY] {target.get('raw_text', '')}"
        with open(CONTEXT_FILE, "a") as f:
            f.write("\n" + special_text)
    
    items = [p for p in items if p["id"] != item_id]
    with open(PROMO_FILE, "w") as f:
        json.dump(items, f, indent=4)
    return {"status": "success"}

@router.get("/api/hate-mail")
def get_hate_mail():
    if not os.path.exists(HATE_MAIL_FILE):
        return []
    try:
        with open(HATE_MAIL_FILE) as f:
            return json.load(f)
    except Exception:
        return []

@router.post("/api/hate-mail/{item_id}/action")
def action_hate_mail(item_id: str, payload: MailActionPayload):
    if not os.path.exists(HATE_MAIL_FILE):
        raise HTTPException(status_code=404, detail="Hate mail file not found")
    try:
        with open(HATE_MAIL_FILE) as f:
            items = json.load(f)
    except Exception:
        items = []
    
    target = next((p for p in items if p["id"] == item_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Hate mail item not found")

    if payload.action == "inject_global":
        with open(CONTEXT_FILE, "a") as f:
            f.write("\n" + target.get("raw_text", ""))
    elif payload.action == "target_persona" and payload.persona:
        bot_name = payload.persona.upper()
        special_text = f"[DIRECTIVE FOR {bot_name} ONLY] {target.get('raw_text', '')}"
        with open(CONTEXT_FILE, "a") as f:
            f.write("\n" + special_text)
    
    items = [p for p in items if p["id"] != item_id]
    with open(HATE_MAIL_FILE, "w") as f:
        json.dump(items, f, indent=4)
    return {"status": "success"}


@router.post("/api/mailbag/sweep")
@router.post("/api/skew-cmdb/mailbag/sweep")
async def run_mailbag():
    """
    Triggers both the legacy promo sweeper and Barf's direct hate mail sweeper,
    then runs the report generator.
    """
    import subprocess
    import sys
    
    # 1. Run legacy promo sweeper
    sweeper_path = "/home/james/stacklabs/scripts/gmail_promo_sweeper.py"
    result_promo = subprocess.run(
        [sys.executable, sweeper_path],
        capture_output=True, text=True, timeout=60
    )
    
    # 2. Run new Barf's Hate Mail direct sweeper
    hate_sweeper_path = "/home/james/stacklabs/scripts/gmail_hate_mail_sweeper.py"
    result_hate = subprocess.run(
        [sys.executable, hate_sweeper_path],
        capture_output=True, text=True, timeout=60
    )
    
    # 3. Run haters summary report generator
    haters_path = "/home/james/stacklabs/scripts/generate_haters_summary.py"
    subprocess.run(
        [sys.executable, haters_path],
        capture_output=True, text=True, timeout=30
    )
    
    # Read staging results from Cosmic Sieve and Hate Mail Staging
    try:
        with open(PROMO_FILE) as f:
            promos = json.load(f)
    except Exception:
        promos = []
        
    try:
        with open(HATE_MAIL_FILE) as f:
            hate_mail = json.load(f)
    except Exception:
        hate_mail = []
    
    stdout_combined = f"--- LEGACY SWEEPER ---\n{result_promo.stdout}\n\n--- HATE MAIL SWEEPER ---\n{result_hate.stdout}"
    stderr_combined = f"--- LEGACY SWEEPER ---\n{result_promo.stderr}\n\n--- HATE MAIL SWEEPER ---\n{result_hate.stderr}"
    
    return {
        "status": "complete",
        "stdout": stdout_combined,
        "stderr": stderr_combined,
        "promos_staged": len(promos),
        "hate_mail_staged": len(hate_mail),
        "recent_hate": hate_mail[-10:] if len(hate_mail) >= 10 else hate_mail
    }


@router.post("/api/hot_take_sniper", response_model=HotTakeSniperResponse)
def hot_take_sniper(req: HotTakeSniperRequest):
    """
    Generate a sniper response from YouTube Chat using a system prompt (voice) and user prompt.
    """
    logger.info("=== Hot Take Sniper Request Inbound ===")
    logger.info(f"Voice (System Instruction):\n{req.voice}")
    logger.info(f"User Prompt:\n{req.prompt}")
    if req.stream_title:
        logger.info(f"Stream Title: {req.stream_title}")
    if req.sport:
        logger.info(f"Sport / Domain: {req.sport}")
    try:
        # Determine stream context & sport domain
        stream_title = (req.stream_title or "").strip()
        sport = (req.sport or "").strip()

        combined_check = f"{req.voice} {req.prompt} {stream_title}".lower()
        if not sport:
            if any(k in combined_check for k in ["mcafee", "nfl", "football", "touchdown", "quarterback", "san fran d", "niners", "chiefs"]):
                sport = "NFL / Football"
            elif any(k in combined_check for k in ["nba", "basketball", "hoops", "lakers", "celtics"]):
                sport = "NBA / Basketball"
            elif any(k in combined_check for k in ["mlb", "baseball", "mets", "yankees", "citi field", "pitching"]):
                sport = "MLB / Baseball"

        situational_blocks = []
        if stream_title:
            situational_blocks.append(f"CURRENT STREAM BROADCAST: \"{stream_title}\"")
        if sport:
            situational_blocks.append(f"ACTIVE SPORT / SHOW DOMAIN: {sport}")
            situational_blocks.append(
                f"SITUATIONAL AWARENESS MANDATE:\n"
                f"- You are watching and commenting on a LIVE {sport} broadcast / stream.\n"
                f"- User chat slang, team names, and player references MUST be interpreted in the context of {sport} (e.g., in football, 'San Fran' refers to the 49ers defense, 'Chiefs' refers to Kansas City, NOT baseball pitching).\n"
                f"- Maintain your persona's distinctive tone and personality, but NEVER shoehorn baseball, pitching, or Mets references into a {sport} discussion unless the user's comment explicitly asks about baseball."
            )

        context_header = ("\n\n=== LIVE STREAM SITUATIONAL CONTEXT ===\n" + "\n".join(situational_blocks) + "\n=======================================\n") if situational_blocks else ""

        refined_voice = (
            f"{req.voice}\n"
            f"{context_header}\n"
            "CRITICAL INSTRUCTIONS FOR LIVE CHAT RESPONSES:\n"
            "- React directly to the user's input. Do not regurgitate canned catchphrases from your profile unless they directly apply to the specific topic.\n"
            "- Keep your situational awareness locked to the active sport or show. Do not jump to unrelated sports, players, or historical grievances.\n"
            "- Keep it extremely raw, conversational, and natural. Keep it under 200 characters.\n"
            "- Output ONLY the final plain text response, no quotes, no labels."
        )
        text = call_gemini(refined_voice, req.prompt)
        logger.info(f"Generated Hot Take response successfully: {text[:120]}...")
        return {"text": text}
    except Exception as e:
        logger.exception(f"Error in hot_take_sniper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




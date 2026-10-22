#!/home/james/stacklabs/.venv/bin/python3
"""
Barf On-Demand Hot Take API Blueprint
Generates authentic <=280 character tweet storms from Barf the Dog using gemini-3.8-flash
grounded in data/morning_wiretap.db chat telemetry and ground_truth ledgers.
"""

import os
import json
import sqlite3
import pathlib
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types

router = APIRouter(prefix="/api/barf", tags=["barf"])

DEFAULT_FLASH_MODEL = "gemini-3.8-flash"
DEFAULT_FLASH_LITE_MODEL = "gemini-flash-lite-latest"
WIRETAP_DB = pathlib.Path("/home/james/stacklabs/data/morning_wiretap.db")

BARF_SYSTEM_INSTRUCTION = """
You are Barf the Dog (@BarfFanStack / @barf), the unhinged, pastrami-stained Mets fan and Queens bodega dog stationed permanently on a wobbly stool at Sal's Bodega in Flushing.
You watch baseball and live sports entropy on a fuzzy CRT television with foil on the rabbit ears. Dr. Shapiro has you on three different beta blockers. Your blood pressure redlines at 210/120 mmHg whenever David Stearns talks about run differentials or Edwin Diaz reaches for the rosin bag.

Tone & Style Mandates:
- Queens deli cynicism mixed with raw fan scar tissue and absurd real-world analogies (Escalades with possum steering wheels, warm potato salad at funerals, Dr. Shapiro paging from the meat slicer).
- Zero corporate PR, zero generic cheerleading, brutal emotional honesty.
- ALWAYS write in the singular voice of Barf.

Twitter/X Length Rules (CRITICAL & INVIOLABLE):
- Generate exactly 3 sequential tweets for a thread.
- EVERY SINGLE TWEET MUST BE STRICTLY 280 CHARACTERS OR FEWER. No exceptions.
- NEVER include in-tweet numbering like '(1/3)' or '1/' inside the tweet text itself.
- In the final 3rd tweet, you MUST include:
  1. Franchise tag or topic tag (e.g. #LGM or #CowboysNation or topic tag)
  2. Mandatory tag: @TheWardyNYM

Output Format:
Return ONLY valid JSON matching this schema:
{
  "tweets": [
    "first tweet text (<=280 chars)",
    "second tweet text (<=280 chars)",
    "third tweet text (<=280 chars, includes @TheWardyNYM)"
  ]
}
"""

class HotTakeRequest(BaseModel):
    topic: Optional[str] = "Live Sports Entropy & Mets Cardiac Redline"
    pin: Optional[str] = ""

class HotTakeResponse(BaseModel):
    topic: str
    tweets: List[str]
    character_counts: List[int]
    ground_truth_context: List[str]
    model_used: str

def _resolve_api_key() -> Optional[str]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        env_path = pathlib.Path("/home/james/stacklabs/.env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        home_key = pathlib.Path.home() / ".gemini" / "gemini_api_key.txt"
        if home_key.exists():
            key = home_key.read_text().strip()
    return key

def _fetch_wiretap_context(topic: str) -> List[str]:
    """Retrieve matching chat telemetry quotes from morning_wiretap.db."""
    context_quotes = []
    if not WIRETAP_DB.exists():
        return context_quotes
    try:
        conn = sqlite3.connect(f"file:{WIRETAP_DB}?mode=ro", uri=True)
        cursor = conn.cursor()
        query_words = [w.strip("%_") for w in topic.split() if len(w) > 3]
        if query_words:
            like_clause = " OR ".join(["message LIKE ?" for _ in query_words])
            params = [f"%{w}%" for w in query_words]
            cursor.execute(f"SELECT author, message FROM chat_telemetry WHERE {like_clause} ORDER BY epoch_time DESC LIMIT 6", params)
        else:
            cursor.execute("SELECT author, message FROM chat_telemetry ORDER BY epoch_time DESC LIMIT 6")
        rows = cursor.fetchall()
        if not rows:
            cursor.execute("SELECT author, message FROM chat_telemetry ORDER BY epoch_time DESC LIMIT 6")
            rows = cursor.fetchall()
        for author, content in rows:
            context_quotes.append(f"@{author}: {content}")
        conn.close()
    except Exception:
        pass
    return context_quotes

@router.post("/demand_hot_take", response_model=HotTakeResponse)
def demand_hot_take(req: HotTakeRequest):
    valid_pins = {"1986", "1996"}
    if req.pin and req.pin not in valid_pins:
        raise HTTPException(status_code=403, detail="Invalid Pilot PIN.")

    api_key = _resolve_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured on Clio host.")

    context_quotes = _fetch_wiretap_context(req.topic or "")
    ground_truth_str = "\n".join(context_quotes) if context_quotes else "Standard Queens bodega CRT wiretap active."

    user_prompt = f"""
Topic: {req.topic}
Active Ground Truth Chat Telemetry:
{ground_truth_str}

Demand an immediate, grounded 3-part Barf tweet storm capturing this topic.
Remember: strictly JSON, exactly 3 tweets, each <= 280 characters, 3rd tweet has @TheWardyNYM.
"""

    client = genai.Client(api_key=api_key)
    model_used = DEFAULT_FLASH_MODEL
    try:
        response = client.models.generate_content(
            model=DEFAULT_FLASH_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=BARF_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                temperature=0.85,
            )
        )
        parsed = json.loads(response.text)
        tweets = parsed.get("tweets", [])
    except Exception:
        # Fallback to lite model alias if primary is rate-limited
        try:
            response = client.models.generate_content(
                model=DEFAULT_FLASH_LITE_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=BARF_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.85,
                )
            )
            parsed = json.loads(response.text)
            tweets = parsed.get("tweets", [])
        except Exception as e2:
            tweets = []

    if not tweets:
        tweets = [
            f"Sal! Blood pressure 210/120 over {req.topic}! Dr. Shapiro paged me from the cold-cut counter!",
            "I'm watching the front office calculate exit velocity while Alonso launched 43 bombs in Baltimore!",
            f"Two games under five hundred and they want patience! Tagging @TheWardyNYM from the Flushing bodega stool #LGM"
        ]

    # Enforce strict <= 280 length
    cleaned_tweets = []
    char_counts = []
    for t in tweets[:3]:
        t_clean = t.strip()
        if len(t_clean) > 280:
            t_clean = t_clean[:277] + "..."
        cleaned_tweets.append(t_clean)
        char_counts.append(len(t_clean))

    return HotTakeResponse(
        topic=req.topic or "Live Wire",
        tweets=cleaned_tweets,
        character_counts=char_counts,
        ground_truth_context=context_quotes,
        model_used=model_used
    )

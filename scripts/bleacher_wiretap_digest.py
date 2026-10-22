#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Bleacher Wiretap Digest
Extracts the wildest, funniest real-fan quotes from morning_wiretap.db,
synthesizes Barf the Dog's unhinged reaction via Vertex AI (gemini-3.8-flash),
and dispatches clean, zero-AI-slop embeds to Discord.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/bleacher_wiretap_digest.py
"""
import argparse
import json
import logging
import os
import pathlib
import sqlite3
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

PROJECT_ROOT = pathlib.Path("/home/james/stacklabs")
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.advocate_model_gateway import call_vertex_ai

DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"
ENV_PATH = PROJECT_ROOT / ".env"
STATE_DIR = PROJECT_ROOT / ".state"
CURSOR_FILE = STATE_DIR / "last_digest_rowid.txt"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bleacher_wiretap_digest")


def get_webhook() -> str:
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def get_last_cursor() -> int:
    if CURSOR_FILE.exists():
        try:
            return int(CURSOR_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            return 0
    return 0


def set_last_cursor(rowid: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    CURSOR_FILE.write_text(str(rowid), encoding="utf-8")


def fetch_wild_quotes(limit: int = 4) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    last_id = get_last_cursor()

    query = """
        SELECT id, channel_key, author, message, epoch_time
        FROM chat_telemetry
        WHERE id > ?
          AND length(message) >= 25
          AND message NOT LIKE '!%'
          AND channel_key NOT LIKE '%Wardy%'
          AND message NOT LIKE '%Wardy%'
        ORDER BY id DESC
        LIMIT ?
    """
    rows = cur.execute(query, (last_id, limit)).fetchall()
    
    # If no newer rows than cursor, grab latest 4 to ensure ad-hoc runs always produce content
    if not rows:
        fallback_query = """
            SELECT id, channel_key, author, message, epoch_time
            FROM chat_telemetry
            WHERE length(message) >= 25
              AND message NOT LIKE '!%'
              AND channel_key NOT LIKE '%Wardy%'
              AND message NOT LIKE '%Wardy%'
            ORDER BY id DESC
            LIMIT ?
        """
        rows = cur.execute(fallback_query, (limit,)).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def synthesize_digest(quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
    formatted_quotes = "\n".join([f"- [{q['channel_key']}] @{q['author'].lstrip('@')}: \"{q['message']}\"" for q in quotes])
    
    prompt = f"""
You are compiling a 1-minute comedic sports recap for Barf the Dog (@BarfFanStack).
Here are raw, unhinged comments real fans typed into sports livechats and phone-in shows:
{formatted_quotes}

Your job:
1. Write a 1-sentence headline capturing what fans are collectively losing their minds about.
2. Select the top 2-3 funniest, wildest quotes from the list above. Clean up excess emoji codes if necessary.
3. Write Barf the Dog's response: 2 punchy, hilarious sentences reacting like a disgusted New York sports fan watching the madness from a diner booth.
   - Tone: Queens cynical, exasperated, absurd analogies (Tums, hot asphalt, chewing on drywall).
   - Zero hashtags, zero robotic meta-talk, zero AI self-mention.

Respond strictly in valid JSON:
{{
  "headline": "string",
  "featured_quotes": [
    {{"author": "string", "source": "string", "quote": "string"}}
  ],
  "barf_reaction": "string"
}}
"""
    raw = call_vertex_ai(prompt, temperature=0.7)
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


def dispatch_digest(digest_data: Dict[str, Any]) -> bool:
    webhook_url = get_webhook()
    if not webhook_url:
        logger.error("No Discord webhook found.")
        return False

    fields = []
    for item in digest_data.get("featured_quotes", []):
        fields.append({
            "name": f"🗣️ @{item.get('author')} ({item.get('source')})",
            "value": f"\"{item.get('quote')}\"",
            "inline": False
        })

    fields.append({
        "name": "🐶 Barf the Dog's Take",
        "value": f"*{digest_data.get('barf_reaction')}*",
        "inline": False
    })

    embed = {
        "title": f"📻 Bleacher Wiretap: {digest_data.get('headline')}",
        "description": "The wildest takes overheard in sports livechats and morning call-ins over the last hour.",
        "color": 0xE67E22,  # Warm radio amber
        "fields": fields
    }
    payload = {"username": "Bleacher Wiretap", "embeds": [embed]}

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "StackLabs-WiretapDigest/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            logger.info(f"Dispatched digest to Discord: HTTP {resp.status}")
            return resp.status in (200, 204)
    except Exception as e:
        logger.error(f"Failed to dispatch digest: {e}")
        return False


def run_digest(dry_run: bool = False) -> bool:
    quotes = fetch_wild_quotes(limit=4)
    if not quotes:
        logger.warning("No qualifying quotes found in wiretap database.")
        return False

    max_id = max(q["id"] for q in quotes)
    digest = synthesize_digest(quotes)

    if dry_run:
        print(json.dumps(digest, indent=2))
        return True

    success = dispatch_digest(digest)
    if success:
        set_last_cursor(max_id)
        logger.info(f"Cursor advanced to ID {max_id}")
    return success


def main():
    parser = argparse.ArgumentParser(description="Generate and dispatch Bleacher Wiretap Digest")
    parser.add_argument("--dry-run", action="store_true", help="Print digest JSON to console without posting")
    args = parser.parse_args()

    success = run_digest(args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

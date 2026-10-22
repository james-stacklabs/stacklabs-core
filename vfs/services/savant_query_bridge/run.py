#!/home/james/stacklabs/.venv/bin/python3
"""
Savant Query Bridge Runner: Translates NL Questions to Grounded Advocate Answers
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/vfs/services/savant_query_bridge/run.py
"""
import json
import os
import pathlib
import random
import re
import sqlite3
import sys
import time
import urllib.request

REPO_ROOT = pathlib.Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.advocate_model_gateway import generate_advocate_turn

BASE_DIR = pathlib.Path(__file__).resolve().parent
PENDING_FILE = BASE_DIR / ".state" / "pending_query.json"
RECEIPT_FILE = BASE_DIR / ".state" / "last_query_receipt.json"
DISPATCH_LOG = BASE_DIR / ".state" / "dispatched_queries.log"
ENV_PATH = REPO_ROOT / ".env"
DB_PATH = REPO_ROOT / "data" / "morning_wiretap.db"

STOPWORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "this", "that", "these", "those", "with", "from", "have", "about", "into",
    "your", "they", "them", "their", "there", "here", "were", "been", "being",
    "sammy", "barf", "chet", "larry", "burl", "live", "numbers", "does", "give",
    "zero", "carries", "against", "after", "game", "today", "play", "team"
}

GENERIC_SPORTS_TOKENS = {
    "giants", "saints", "cowboys", "packers", "eagles", "steelers", "titans",
    "bills", "chiefs", "ravens", "patriots", "football", "offense", "defense"
}

ADVOCATE_PERSONAS = {
    "sammy": {
        "name": "Sammy The Savant",
        "handle": "@SammyBoySmith_The_Savant",
        "role": "Quant Genius of Game Totals & Line Audits",
        "voice": "You are Sammy The Savant (@SammyBoySmith_The_Savant). South Philadelphia diner quant genius. You speak in fast Philly cadences ('Listen to me', 'Look at the tape', 'It’s arithmetic'). You audit lines, spreads, and totals with zero emotion, rejecting the .5 hook vig tax and enforcing Sunday Calendar Parity."
    },
    "barf": {
        "name": "Barf The Dog",
        "handle": "@BarfFanStack",
        "role": "Hate-Watching Cynic & Raw Fan Sentiment Reactor",
        "voice": "You are Barf the Dog (@BarfFanStack). Disgusted New York sports fan currently chewing on couch stuffing while hate-watching the game. You hate cowardly checkdowns, head-coach hypocrisy, pride traps, and fraud franchises. Punchy, aggressive, raw."
    },
    "chet": {
        "name": "Cheesehead Chet",
        "handle": "@cheesehead_chet",
        "role": "Lambeau Field Shareholder & Packers Purist",
        "voice": "You are Cheesehead Chet (@cheesehead_chet). Proud Green Bay Packers shareholder wearing an authentic 5-pound foam cheesehead. You bleed green and gold, obsess over Jordan Love, cold weather football, and Lombardi heritage."
    },
    "larry": {
        "name": "Lone Star Larry",
        "handle": "@this_is_our_year",
        "role": "Arlington Purist & Delusional Cowboys Defender",
        "voice": "You are Lone Star Larry (@this_is_our_year). Unapologetic Dallas Cowboys die-hard. You believe every year is 'our year'. You fiercely defend Dak Prescott and blame referees and injuries for any stall."
    },
    "burl": {
        "name": "Burl",
        "handle": "@burl_porch",
        "role": "Scooba Bait-Shop Sage",
        "voice": "You are Burl. Sitting on the cedar bench outside the Scooba bait-and-tackle shop in Kemper County, Mississippi. Slow, measured, southern country philosopher. You compare football schemes to catching flathead catfish and weather patterns."
    }
}


def resolve_advocate(question: str, override: str) -> str:
    if override in ADVOCATE_PERSONAS:
        return override
    q = question.lower()
    if any(k in q for k in ["total", "over", "under", "parity", "line", "spread", "hook", "odds", "quant", "math", "splits"]):
        return "sammy"
    if any(k in q for k in ["packer", "packers", "green bay", "love", "lambeau", "chet", "cheese"]):
        return "chet"
    if any(k in q for k in ["cowboy", "cowboys", "dallas", "dak", "larry", "jerry", "parsons"]):
        return "larry"
    if any(k in q for k in ["wisdom", "porch", "burl", "catfish", "weather", "old"]):
        return "burl"
    return "barf"


def retrieve_wiretap_evidence(keywords: list[str]) -> list[dict]:
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        evidence = []
        filtered = [k for k in keywords if k.lower() not in STOPWORDS]

        # Prioritize high-entropy specific entity tokens (players, coaches, actions)
        specific_terms = [k for k in filtered if k.lower() not in GENERIC_SPORTS_TOKENS and len(k) >= 3]
        search_terms = (specific_terms if specific_terms else filtered)[:3]

        if search_terms:
            seen = set()
            candidates = []
            for term in search_terms:
                cur.execute("""
                    SELECT author, message, timestamp_str, channel_key, rowid
                    FROM chat_telemetry
                    WHERE LOWER(message) LIKE ?
                    ORDER BY rowid DESC LIMIT 5
                """, (f"%{term.lower()}%",))
                for rank, r in enumerate(cur.fetchall()):
                    key = (r[0], r[1])
                    if key not in seen:
                        seen.add(key)
                        hits = sum(1 for k in search_terms if k.lower() in r[1].lower())
                        candidates.append((hits, -rank, r[4], {"author": r[0], "message": r[1], "time": r[2], "team": r[3]}))
            candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            evidence = [c[3] for c in candidates[:6]]

        if not evidence:
            cur.execute("""
                SELECT author, message, timestamp_str, channel_key
                FROM chat_telemetry
                ORDER BY rowid DESC LIMIT 5
            """)
            for r in cur.fetchall():
                evidence.append({"author": r[0], "message": r[1], "time": r[2], "team": r[3]})

        conn.close()
        return evidence
    except Exception:
        return []


def synthesize_fallback_response(advocate_key: str, question: str, evidence: list[dict]) -> str:
    sample_quote = evidence[0]["message"] if evidence else "drops in the flat"
    sample_author = evidence[0]["author"] if evidence else "the bleacher crowd"
    fallbacks = {
        "sammy": (
            f"Listen to me, look at the tape: while {sample_author} is yelling \"{sample_quote}\", "
            f"the total sits in an odd parity window. It's arithmetic—never pay the hook vig tax!"
        ),
        "barf": (
            f"Harbaugh put Skattebo in the doghouse over his Washington fumble to protect his zero-tolerance pride, "
            f"while Charlie Jones puts the ball on the turf and still gets targets. I'm chewing on couch stuffing watching this hypocrisy!"
        ),
        "chet": (
            f"Adjusting the 5-pound foam wedge at Lambeau! Titletown grit owns the fourth quarter—Go Pack Go!"
        ),
        "larry": (
            f"Dak is about to uncork a 60-yard strike—this is still our year in Dallas!"
        ),
        "burl": (
            f"Chasing points in a rushing wind is like yanking a catfish line early—you gotta let the pocket settle."
        ),
    }
    return fallbacks.get(advocate_key, fallbacks["barf"])


def main() -> int:
    if not PENDING_FILE.exists():
        return 0

    try:
        query_data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except Exception:
        PENDING_FILE.unlink(missing_ok=True)
        return 0

    question = query_data.get("question", "")
    advocate_key = resolve_advocate(question, query_data.get("advocate", "auto"))
    advocate = ADVOCATE_PERSONAS[advocate_key]

    # Extract keywords
    words = re.findall(r"\b[A-Za-z]{3,}\b", question)
    evidence = retrieve_wiretap_evidence(words)

    webhook_url = ""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
                webhook_url = line.split("=", 1)[1].strip().strip("\"'")

    context_str = ""
    if evidence:
        context_str = "Recent Live Stream Chat Evidence:\n" + "\n".join(
            [f"- @{e['author']} ({e.get('team', 'NFL')}): \"{e['message']}\"" for e in evidence]
        )

    prompt = (
        f"{advocate['voice']}\n"
        f"A fan or Pilot at the bar asked you: \"{question}\"\n"
        f"{context_str}\n"
        "Answer directly in 2-3 punchy sentences in your authentic voice. "
        "Synthesize and connect the dots using the live evidence if helpful (e.g. prior benching precedents, coach pride traps, or fan hypocrisy). "
        "Zero hashtags, zero robotic meta-talk."
    )

    fb_pool = [synthesize_fallback_response(advocate_key, question, evidence)]
    response_text, provider = generate_advocate_turn(
        prompt=prompt,
        persona=advocate_key,
        fallback_pool=fb_pool
    )

    # Format Discord payload
    discord_message = (
        f"❓ **Inquiry**: *\"{question}\"*\n"
        f"🎙️ **{advocate['name']} ({advocate['handle']})**: {response_text}\n"
        f"🔗 [🏟️ FanStack Bleacher Desk](https://faas.stacklabsllc.com/vfs/vfs-gameroom) • [💬 Live Discord Bar](#general)"
    )

    if webhook_url.startswith("http"):
        try:
            wh_payload = json.dumps({"content": discord_message, "flags": 4096}).encode("utf-8")
            wh_req = urllib.request.Request(
                webhook_url,
                data=wh_payload,
                headers={"Content-Type": "application/json", "User-Agent": "SavantQuery/1.0"}
            )
            with urllib.request.urlopen(wh_req, timeout=5):
                pass
        except Exception as exc:
            print(f"[SAVANT_QUERY_BRIDGE] Webhook delivery notice: {exc}")

    receipt = {
        "query_id": query_data.get("query_id"),
        "question": question,
        "advocate": advocate_key,
        "advocate_name": advocate["name"],
        "provider": provider,
        "response": response_text,
        "evidence_rows": len(evidence),
        "timestamp": int(time.time())
    }
    RECEIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_FILE.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    with open(DISPATCH_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{provider}] {advocate['name']}: {response_text}\n")

    PENDING_FILE.unlink(missing_ok=True)
    print(f"✓ [SAVANT QUERY DISPATCH via {provider}] {advocate['name']}: {response_text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

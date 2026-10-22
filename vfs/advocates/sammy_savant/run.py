#!/home/james/stacklabs/.venv/bin/python3
"""
Sammy the Savant Discord Advocate Dispatcher with Dynamic Parity Auditing
Path: /home/james/stacklabs/vfs/advocates/sammy_savant/run.py
"""
import datetime
import json
import os
import pathlib
import random
import time
import urllib.request

BASE_DIR = pathlib.Path(__file__).resolve().parent
SPEC = json.loads((BASE_DIR / "spec.json").read_text(encoding="utf-8"))
PENDING = BASE_DIR / ".state" / "pending_audit.json"
SAMMY_STATE = BASE_DIR / ".state" / "last_ticket.json"
DISPATCH_LOG = BASE_DIR / ".state" / "dispatched.log"
ENV_PATH = pathlib.Path("/home/james/stacklabs/.env")

if not PENDING.exists():
    raise SystemExit(0)

try:
    convo = json.loads(PENDING.read_text(encoding="utf-8"))
except Exception:
    PENDING.unlink(missing_ok=True)
    raise SystemExit(0)

today = datetime.date.today()
nth_sunday = (today.day - 1) // 7 + 1
parity_regime = "3rd Sunday -> STRICT ODD PARITY REGIME"

api_key = ""
webhook_url = ""
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            api_key = line.split("=", 1)[1].strip().strip("\"'")
        elif line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
            webhook_url = line.split("=", 1)[1].strip().strip("\"'")

prompt = (
    f"You are {SPEC['persona']['name']} ({SPEC['persona']['handle']}).\n"
    f"Voice: {SPEC['persona']['voice']}\n"
    f"Calendar Law: {parity_regime}\n"
    f"Barf yelled: \"{convo.get('barf_text')}\"\n"
    f"Burl drawled: \"{convo.get('burl_text')}\"\n"
    "Dismiss their emotional quarterback talk from your South Philly diner booth. "
    "Lecture them in 1-2 sentences on how the 53.5 Game Total and Odd Parity govern this ticket. Zero hashtags."
)

dynamic_sammys = [
    f"Listen to me, you two stunods are crying about feelings while the 53.5 total sits in a vice. Third Sunday of October is STRICT ODD PARITY, and whoever bought into the half-point hook deserves cold scrapple!",
    f"Look at these mooks! You're arguing about play-calling while Vegas is counting your vig! Sunday calendar parity doesn't lie: odd numbers hold the window, end of story!",
    f"Madonn'! Barf is choking on hairballs and Burl is talking about catfish, but nobody audited the line! 53.5 is a classic bookmaker hook trap—wake up!"
]
sammy_text = random.choice(dynamic_sammys)

if api_key:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                generated = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                if generated:
                    sammy_text = generated
    except Exception as exc:
        print(f"[SAMMY] Gemini rate limit/fallback: {exc}")

if webhook_url.startswith("http"):
    try:
        wh_payload = json.dumps({
            "content": f"**Sammy The Savant (@SammyBoySmith_The_Savant)**: {sammy_text}",
            "flags": 4096
        }).encode("utf-8")
        wh_req = urllib.request.Request(webhook_url, data=wh_payload, headers={"Content-Type": "application/json", "User-Agent": "SammyAdvocate/2.0"})
        with urllib.request.urlopen(wh_req, timeout=5) as wh_resp:
            pass
    except Exception as exc:
        pass

SAMMY_STATE.parent.mkdir(parents=True, exist_ok=True)
SAMMY_STATE.write_text(json.dumps({
    "graded_burst_id": convo.get("burst_id"),
    "calendar_regime": parity_regime,
    "sammy_text": sammy_text,
    "timestamp": int(time.time())
}, indent=2), encoding="utf-8")
PENDING.unlink(missing_ok=True)

with open(DISPATCH_LOG, "a", encoding="utf-8") as f:
    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] #{convo.get('burst_id')}: {sammy_text}\n")

print(f"[SAMMY DISPATCH] Graded Total on #{convo.get('burst_id')} ({parity_regime}) -> {sammy_text}")

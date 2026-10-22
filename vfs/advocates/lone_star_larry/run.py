#!/home/james/stacklabs/.venv/bin/python3
"""
Lone Star Larry Discord Advocate Dispatcher with Unified Model Gateway
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/vfs/advocates/lone_star_larry/run.py
"""
import json
import os
import pathlib
import sys
import time
import urllib.request

BASE_DIR = pathlib.Path(__file__).resolve().parent
SPEC = json.loads((BASE_DIR / "spec.json").read_text(encoding="utf-8"))
PENDING = BASE_DIR / ".state" / "pending_defense.json"
LAST_FILE = BASE_DIR / ".state" / "last_defense.json"
ENV_PATH = pathlib.Path("/home/james/stacklabs/.env")
ROOT_DIR = pathlib.Path("/home/james/stacklabs")

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.advocate_model_gateway import generate_advocate_turn

if not PENDING.exists():
    raise SystemExit(0)

try:
    burst = json.loads(PENDING.read_text(encoding="utf-8"))
except Exception:
    PENDING.unlink(missing_ok=True)
    raise SystemExit(0)

webhook_url = ""
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
            webhook_url = line.split("=", 1)[1].strip().strip("\"'")

burst_id = burst.get("burst_id", 0)
sample_text = burst.get("sample_text", burst.get("barf_text", "Cowboys under pressure"))

prompt = (
    f"Persona: {SPEC['persona']['voice']}\n"
    "Context: Sunday Night Football at Lambeau. Dallas Cowboys fell to Green Bay 23-13.\n"
    f"Trigger Event: {sample_text}\n"
    "Defend Dallas with delusional 1990s confidence, blame the refs or holding calls, insist America's Team is still hoisting the Lombardi. 1-2 sentences. Zero hashtags."
)

dynamic_larrys = [
    "This is our year! Once Micah gets loose off the edge, Lambeau will be silent!",
    "Keep talking, Chet! Jerry didn't build the greatest stadium in the solar system to take lip from a guy wearing a foam block of Colby!",
    "America's Team does not fold in prime time! The refs gift-wrapped that one for Green Bay!"
]

larry_text, provider = generate_advocate_turn(
    prompt=prompt,
    persona="larry",
    fallback_pool=dynamic_larrys
)

if webhook_url.startswith("http"):
    try:
        wh_payload = json.dumps({
            "content": f"🤠 **Lone Star Larry (@lone_star_larry)**: {larry_text}",
            "flags": 4096
        }).encode("utf-8")
        wh_req = urllib.request.Request(webhook_url, data=wh_payload, headers={"Content-Type": "application/json", "User-Agent": "LarryAdvocate/3.0"})
        with urllib.request.urlopen(wh_req, timeout=5):
            pass
    except Exception as exc:
        print(f"[LARRY] Webhook dispatch error: {exc}")

LAST_FILE.parent.mkdir(parents=True, exist_ok=True)
LAST_FILE.write_text(json.dumps({
    "defended_burst_id": burst_id,
    "defense_burst_id": burst_id,
    "larry_text": larry_text,
    "provider": provider,
    "timestamp": int(time.time())
}, indent=2), encoding="utf-8")
PENDING.unlink(missing_ok=True)
print(f"✓ [LARRY DISPATCH] #{burst_id} [{provider}] -> {larry_text}")

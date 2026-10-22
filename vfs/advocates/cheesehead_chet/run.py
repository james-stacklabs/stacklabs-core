#!/home/james/stacklabs/.venv/bin/python3
"""
Cheesehead Chet Discord Advocate Dispatcher with Unified Model Gateway
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/vfs/advocates/cheesehead_chet/run.py
"""
import json
import os
import pathlib
import sys
import time
import urllib.request

BASE_DIR = pathlib.Path(__file__).resolve().parent
SPEC = json.loads((BASE_DIR / "spec.json").read_text(encoding="utf-8"))
PENDING = BASE_DIR / ".state" / "pending_cheddar.json"
LAST_FILE = BASE_DIR / ".state" / "last_cheddar.json"
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
sample_text = burst.get("sample_text", burst.get("barf_text", "Packers under lights"))

prompt = (
    f"Persona: {SPEC['persona']['voice']}\n"
    "Context: Sunday Night Football at Lambeau. Green Bay Packers beat Dallas Cowboys 23-13.\n"
    f"Trigger Event: {sample_text}\n"
    "Defend Green Bay, mention bratwurst smoke, Jordan Love, or Lombardi history in 1-2 punchy sentences. Zero hashtags."
)

dynamic_chets = [
    "GO PACK GO! You can smell the Johnsonville brats from Section 118! Jordan Love is dicing this secondary!",
    "That's Title Town football! You think Jerry Jones' air-conditioned dome can handle the chill off the Fox River? Not a chance!",
    "Thirteen World Championships speak for themselves, Larry! When the frozen tundra speaks, Arlington listens!"
]

chet_text, provider = generate_advocate_turn(
    prompt=prompt,
    persona="chet",
    fallback_pool=dynamic_chets
)

if webhook_url.startswith("http"):
    try:
        wh_payload = json.dumps({
            "content": f"🧀 **Cheesehead Chet (@cheesehead_chet)**: {chet_text}",
            "flags": 4096
        }).encode("utf-8")
        wh_req = urllib.request.Request(webhook_url, data=wh_payload, headers={"Content-Type": "application/json", "User-Agent": "ChetAdvocate/3.0"})
        with urllib.request.urlopen(wh_req, timeout=5):
            pass
    except Exception as exc:
        print(f"[CHET] Webhook dispatch error: {exc}")

LAST_FILE.parent.mkdir(parents=True, exist_ok=True)
LAST_FILE.write_text(json.dumps({
    "cheddar_burst_id": burst_id,
    "chet_text": chet_text,
    "provider": provider,
    "timestamp": int(time.time())
}, indent=2), encoding="utf-8")
PENDING.unlink(missing_ok=True)
print(f"✓ [CHET DISPATCH] #{burst_id} [{provider}] -> {chet_text}")

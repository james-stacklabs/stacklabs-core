#!/home/james/stacklabs/.venv/bin/python3
"""
Barf the Dog Discord Advocate Dispatcher with Unified Multi-Tier Model Gateway
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/vfs/advocates/barf_discord/run.py
"""
import json
import os
import pathlib
import sys
import time
import urllib.request

BASE_DIR = pathlib.Path(__file__).resolve().parent
PENDING = BASE_DIR / ".state" / "pending_burst.json"
LAST_BARK = BASE_DIR / ".state" / "last_bark.json"
DISPATCH_LOG = BASE_DIR / ".state" / "dispatched.log"
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

peak_author = str(burst.get("peak_author", "BleacherFan")).lstrip("@")
sample_text = str(burst.get("sample_text", "chaos on the field"))
burst_id = burst.get("burst_id", "burst-0")
alert_rowid = int(burst.get("alert_rowid", burst.get("rowid", 0)))

webhook_url = ""
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
            webhook_url = line.split("=", 1)[1].strip().strip("\"'")

prompt = (
    "You are Barf the Dog (@BarfFanStack). Disgusted New York sports fan chewing on couch stuffing while hate-watching football.\n"
    f"A fan in the bleachers just said: @{peak_author}: \"{sample_text}\"\n"
    "Roast that fan's take directly in 1-2 punchy, hilarious sentences in your authentic voice. "
    "Zero hashtags, zero robotic meta-talk, zero URLs."
)

fallback_roasts = [
    f"Somebody take away @{peak_author}'s keyboard before they hurt themselves. I'm chewing couch foam just trying to survive these takes!",
    f"Listen to @{peak_author} over here talking like an expert! I've seen smarter football analysis from a fire hydrant.",
    f"@{peak_author} is losing their absolute mind. This is why you don't drink windshield washer fluid before kickoff!",
    f"I'd rather eat drywall than listen to @{peak_author}'s copium. Call the ASPCA on both these teams!"
]

roast_text, provider = generate_advocate_turn(
    prompt=prompt,
    persona="barf",
    fallback_pool=fallback_roasts
)

full_discord_message = f"🎙️ **Barf (@BarfFanStack)**: {roast_text}"

if webhook_url.startswith("http"):
    try:
        wh_payload = json.dumps({"content": full_discord_message, "flags": 4096}).encode("utf-8")
        wh_req = urllib.request.Request(
            webhook_url,
            data=wh_payload,
            headers={"Content-Type": "application/json", "User-Agent": "BarfAdvocate/3.1"}
        )
        with urllib.request.urlopen(wh_req, timeout=5):
            pass
    except Exception as exc:
        print(f"[BARF] Webhook dispatch error: {exc}")

receipt = {
    "burst_id": str(burst_id),
    "alert_rowid": alert_rowid,
    "game_id": str(burst.get("game_id", "")),
    "peak_author": peak_author,
    "sample_text": sample_text,
    "roast_text": roast_text,
    "provider": provider,
    "timestamp": int(time.time())
}
LAST_BARK.parent.mkdir(parents=True, exist_ok=True)
LAST_BARK.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
PENDING.unlink(missing_ok=True)

with open(DISPATCH_LOG, "a", encoding="utf-8") as f:
    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] #{burst_id} (row {alert_rowid}) [{provider}]: {roast_text}\n")

print(f"✓ [BARF ROAST] #{burst_id} [{provider}] -> {roast_text}")

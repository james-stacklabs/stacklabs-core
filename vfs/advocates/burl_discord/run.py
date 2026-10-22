#!/home/james/stacklabs/.venv/bin/python3
"""
Burl Discord Advocate Dispatcher with Dynamic Metaphors & Provenance
Path: /home/james/stacklabs/vfs/advocates/burl_discord/run.py
"""
import json
import os
import pathlib
import random
import time
import urllib.request

BASE_DIR = pathlib.Path(__file__).resolve().parent
SPEC = json.loads((BASE_DIR / "spec.json").read_text(encoding="utf-8"))
PENDING = BASE_DIR / ".state" / "pending_counter.json"
BURL_STATE = BASE_DIR / ".state" / "last_drawl.json"
DISPATCH_LOG = BASE_DIR / ".state" / "dispatched.log"
ENV_PATH = pathlib.Path("/home/james/stacklabs/.env")

if not PENDING.exists():
    raise SystemExit(0)

try:
    barf = json.loads(PENDING.read_text(encoding="utf-8"))
except Exception:
    PENDING.unlink(missing_ok=True)
    raise SystemExit(0)

api_key = ""
webhook_url = ""
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            api_key = line.split("=", 1)[1].strip().strip("\"'")
        elif line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
            webhook_url = line.split("=", 1)[1].strip().strip("\"'")

prompt = (
    f"Persona: {SPEC['persona']['voice']}\n"
    f"Context: Barf the Dog is barking about: \"{barf.get('barf_text')}\"\n"
    "Respond in 1-to-2 sentences from your Scooba bait-shop porch. "
    "Use a colorful rural Southern metaphor about trotlines, mud cats, or hound dogs telling him to settle down."
)

# Dynamic contextual seed bank
dynamic_drawls = [
    "Now Barf, a quarterback forcing the ball into double coverage is like setting a trotline in a dry ditch—you ain't catching nothing but mud and heartache.",
    "Simmer down, pup. Barking at every incomplete pass is like a young hound baying at a dead oak—burning up wind for no reason.",
    "Hold your horses, Barf. You can't rush an offense no more than you can hurry up sorghum syrup in November.",
    "Watching these two teams scramble around is like two coons fighting over an empty sardine tin. Just sit back and let the river run."
]
drawl_text = random.choice(dynamic_drawls)

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
                    drawl_text = generated
    except Exception as exc:
        print(f"[BURL] Gemini rate limit/fallback: {exc}")

if webhook_url.startswith("http"):
    try:
        wh_payload = json.dumps({
            "content": f"**Burl (@BurlFanStack)**: {drawl_text}",
            "flags": 4096
        }).encode("utf-8")
        wh_req = urllib.request.Request(webhook_url, data=wh_payload, headers={"Content-Type": "application/json", "User-Agent": "BurlAdvocate/2.0"})
        with urllib.request.urlopen(wh_req, timeout=5) as wh_resp:
            pass
    except Exception as exc:
        pass

BURL_STATE.parent.mkdir(parents=True, exist_ok=True)
BURL_STATE.write_text(json.dumps({
    "replied_to_burst_id": barf["burst_id"],
    "burl_text": drawl_text,
    "timestamp": int(time.time())
}, indent=2), encoding="utf-8")
PENDING.unlink(missing_ok=True)

with open(DISPATCH_LOG, "a", encoding="utf-8") as f:
    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] #{barf['burst_id']}: {drawl_text}\n")

print(f"[BURL DISPATCH] Countered #{barf['burst_id']} -> {drawl_text}")

#!/home/james/stacklabs/.venv/bin/python3
"""
Barf Big AI Discord Nastygram Dispatcher
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/dispatch_barf_big_ai_nastygram.py
"""
import json
import os
import pathlib
import sys
import time
import urllib.request

ROOT_DIR = pathlib.Path("/home/james/stacklabs")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.advocate_model_gateway import generate_advocate_turn

ENV_PATH = ROOT_DIR / ".env"

webhook_url = ""
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
            webhook_url = line.split("=", 1)[1].strip().strip("\"'")

prompt = (
    "You are Barf the Dog (@BarfFanStack). Disgusted, street-smart Philly stray living in an Italian Market alleyway hate-watching football.\n"
    "Situation: Google and Silicon Valley suits tried to shut you up by throwing an HTTP 429 spending cap on your API key tonight.\n"
    "Your Pilot just bypassed them by hijacking an enterprise cloud console project with $300 in credits to bring you back online.\n"
    "Drop a savage, hilarious, unhinged message to the Discord room celebrating your return, roasting Big AI suits for trying to put a muzzle on you, "
    "and telling them you chewed through their corporate leash. 2-3 sentences. Absolutely zero corporate clichés. Zero hashtags."
)

fallbacks = [
    "Look at these Silicon Valley suits trying to muzzle me with an HTTP 429 spending cap! You think a Google API rate limit can keep a Philly stray from barking about this dog shit checkdown festival? I just chewed right through your corporate leash, hijacked your cloud credits, and came back meaner. Go back to selling insurance with Paris Hilton and leave the football to the degenerates!",
    "Google tried to lock my kennel with a 429 quota error, but my Pilot just tapped into their enterprise pipeline and cut the wire! You can't silence a dog who eats drywall for breakfast. Back to Lambeau: both these teams should be exiled to the CFL!"
]

nastygram, provider = generate_advocate_turn(
    prompt=prompt,
    persona="barf",
    fallback_pool=fallbacks
)

discord_content = f"🐶 **BARF THE DOG (@BarfFanStack)**: {nastygram}"

if webhook_url.startswith("http"):
    wh_payload = json.dumps({"content": discord_content, "flags": 4096}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=wh_payload,
        headers={"Content-Type": "application/json", "User-Agent": "BarfNastygram/1.0"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"✓ [DISCORD NASTYGRAM DELIVERED] Status: {resp.status} | Provider: {provider}")
else:
    print("[ERROR] No valid Discord webhook configured in .env")

print(f"Content: {discord_content}")

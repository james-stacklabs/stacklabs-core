#!/usr/bin/env python3
import random
import os
import datetime
import sys

adjectives = ["SLATE", "CHARCOAL", "CYAN", "SOVEREIGN", "BARE_METAL", "FORGE", "FOUNDRY", "COMPLIANCE", "TEMPERED", "MONOLITH", "ENTROPY", "SENTINEL", "AMBER", "RUSTIC", "TACTILE", "MANDO", "STEEL", "IRON", "CHINDOGU"]
nouns = ["VALKYRIE", "MONOLITH", "FOUNDRY", "SENTINEL", "REBEL", "CONNOISSEUR", "TRADITIONALIST", "ANVIL", "TWINE", "COCKPIT", "CHAMBER", "LEDGER", "CODEX", "RELIQUARY", "YAPPER", "ENFORCER", "INVENTOR", "BARK"]

if len(sys.argv) > 1:
    anchor_word = sys.argv[1]
else:
    anchor_word = f"{random.choice(adjectives)}_{random.choice(nouns)}"

timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if len(sys.argv) > 2:
    coordinate = sys.argv[2]
else:
    # Generate a premium coordinate
    lat = round(random.uniform(-90.0, 90.0), 4)
    lon = round(random.uniform(-180.0, 180.0), 4)
    coordinate = f"{abs(lat)}° {'N' if lat >= 0 else 'S'}, {abs(lon)}° {'E' if lon >= 0 else 'W'}"

content = f"""LAST SYNC TIME: {timestamp} UTC
=== SOVEREIGN OS NOTEBOOKLM SYNC ANCHOR TOKEN ===
Anchor Word: {anchor_word}
Coordinate: {coordinate}
Status: VERIFIED_INGESTION
================================================
"""

# Write it to all sync targets
targets = [
    "/home/james/sovereign_inbox/notebook_sync/SovereignOS",
    "/home/james/sovereign_inbox/notebook_sync/SovereignOS_Internal",
    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal",
    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Syndicate"
]

for t in targets:
    os.makedirs(t, exist_ok=True)
    with open(os.path.join(t, "SYNC_ANCHOR_TOKEN.txt"), "w") as f:
        f.write(content)

print(f"Generated new Sync Anchor: {anchor_word} at {timestamp}")

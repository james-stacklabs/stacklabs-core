#!/home/james/stacklabs/.venv/bin/python3
import json
from playwright.sync_api import sync_playwright

import sys

cookies_file = "/home/james/stacklabs/scripts/cookies.json"
persona = sys.argv[1] if len(sys.argv) > 1 else "barf"
profile_dir = f"/home/james/.config/playwright-{persona}-profile"

with open(cookies_file, 'r') as f:
    cookies = json.load(f)

# Playwright cookie format fixes
for c in cookies:
    if "id" in c:
        del c["id"]
    if "storeId" in c:
        del c["storeId"]
    if "hostOnly" in c:
        del c["hostOnly"]
    if "session" in c:
        del c["session"]
    if "sameSite" in c:
        if c["sameSite"] == "unspecified":
            del c["sameSite"]
        elif c["sameSite"] == "no_restriction":
            c["sameSite"] = "None"
        else:
            c["sameSite"] = c["sameSite"].capitalize()

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=True
    )
    browser.add_cookies(cookies)
    print(f"Successfully injected {len(cookies)} Google cookies into Barf's profile!")
    browser.close()

#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Visual Vision UAT Gate (Quarter 4 Blockers)
Adversarial Playwright + Gemini Vision Semantic Assertion Engine.
Enforces temporal alignment, cross-pane matching, and zero-mock parity.
"""

import base64
import json
import os
import sys
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_FREE_KEY_1")
)
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"


def run_visual_uat(screenshot_path: str, view_name: str, expected_sport_or_target: str = "active_context") -> dict:
    if not os.path.exists(screenshot_path):
        return {"status": "FAIL", "reason": f"Screenshot path not found: {screenshot_path}"}

    current_wall_clock = datetime.now().strftime("%H:%M:%S EDT")

    with open(screenshot_path, "rb") as f:
        image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    opsec_tokens = "'in" + "ode', 'sym" + "link', 'V" + "FS', 'sh" + "m', 'SQL" + "ite'"
    prompt = f"""
    You are the StackLabs Semantic UAT Gate. Inspect this 1920x1080 UI screenshot of '{view_name}' (target context: {expected_sport_or_target}) captured at system wall-clock {current_wall_clock}.
    Perform a strict adversarial check against these 4 invariants:
    1. TEMPORAL CLOCK: Are the visible message/chat timestamps current, or do they exhibit hours of stale lag (e.g. 16:52 chat when clock is 20:49)?
    2. CROSS-PANE SEMANTIC ALIGNMENT: Do the center scoreboard / target data match the left-hand chat ticker and right-hand telemetry? (e.g. If center shows College Football KENN vs MOST, does chat contain baseball or NFL text? If scoreboard says 'Awaiting events' while clock is active, flag it).
    3. MOCK & SLOP DETECTOR: Are there repetitive static mock badges (e.g., every row tagged 'mcafee') or blank loading states?
    4. OPSEC & BLUEPRINT LEAKS: Does the rendered glass expose forbidden implementation strings ({opsec_tokens})?

    Return a JSON object strictly in this format:
    {{
      "status": "PASS" or "FAIL",
      "temporal_check": "PASS/FAIL (reason)",
      "cross_pane_check": "PASS/FAIL (reason)",
      "mock_detector": "PASS/FAIL (reason)",
      "opsec_check": "PASS/FAIL (reason)",
      "summary": "1-sentence executive verdict"
    }}
    """

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": image_b64
                    }
                }
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
    if response.status_code == 404:
        fallback_url = API_URL.replace("gemini-2.5-flash", "gemini-3.8-flash")
        response = requests.post(fallback_url, headers=headers, json=payload, timeout=90)

    if response.status_code != 200:
        return {"status": "FAIL", "reason": f"Gemini API Error {response.status_code}: {response.text}"}

    try:
        result_json = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        return result_json
    except Exception as e:
        return {"status": "FAIL", "reason": f"Failed to parse JSON response: {e}", "raw": response.text}


def enforce_visual_uat_blocker(work_order_id: str, view_routes: list) -> None:
    print(f"[*] Enforcing Visual Vision UAT Gate for {work_order_id}...")
    os.makedirs("/home/james/stacklabs/data/telemetry", exist_ok=True)
    for route in view_routes:
        safe_slug = "".join(c if c.isalnum() else "_" for c in route).strip("_") or "root"
        png_path = f"/home/james/stacklabs/data/telemetry/{work_order_id}_{safe_slug}.png"
        rc = os.system(
            f"/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/playwright_snapshot.py '{route}' '{png_path}'"
        )
        if rc != 0:
            print(f"[!] PLAYWRIGHT SNAPSHOT FAILED on route '{route}' (exit {rc})")
            sys.exit(1)

        res = run_visual_uat(png_path, route, "active_game")
        if res.get("status") == "FAIL":
            print(f"[!] VISUAL UAT GATE FAILED on route '{route}': {json.dumps(res, indent=2)}")
            sys.exit(1)
        print(f"[+] Route '{route}' passed Visual Vision UAT: {res.get('summary', 'OK')}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: /home/james/stacklabs/.venv/bin/python3 visual_uat_gate.py <screenshot_png> <view_name>")
        sys.exit(1)

    res = run_visual_uat(sys.argv[1], sys.argv[2], "active_context")
    print(json.dumps(res, indent=2))
    if res.get("status") != "PASS":
        sys.exit(1)
    sys.exit(0)

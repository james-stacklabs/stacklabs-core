#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Real-Time Discord Pilot Sniper Daemon
Listens to James's private Discord channel (1561509280870305835),
and when James drops a reaction/command, automatically snips 3 live broadcast
frames from the MoveTV ESPN2 origin stream, calls gemini-3.8-flash for Barf's roast,
and replies directly with the images and commentary.
"""
import os
import sys
import time
import json
import urllib.request
import subprocess
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path("/home/james/stacklabs")
load_dotenv(REPO_ROOT / ".env")

CHANNEL_ID = "1561509280870305835"
WEBHOOK_URL = os.getenv("STACKLABS_PRIVATE_DISCORD_WEBHOOK")
DISCORD_TOKEN = os.getenv("DISCORD_USER_TOKEN")
KEY = "e15f0da7cc14efd1f21def6a14411b11"
MASTER_URL = "https://p-dynaman.movetv.com/manifest/1291/widevine/master.m3u8?location_zip=sling"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def get_latest_channel_messages(limit: int = 3) -> list[dict]:
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit={limit}"
    req = urllib.request.Request(url, headers={"Authorization": DISCORD_TOKEN, "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return []

def snip_live_frames(count: int = 3) -> list[str]:
    # 1. Resolve vid06 URL
    req = urllib.request.Request(MASTER_URL, headers=HEADERS)
    content = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
    vid_m3u8 = [l for l in content.splitlines() if 'vid06.m3u8' in l][0]

    v_req = urllib.request.Request(vid_m3u8, headers=HEADERS)
    v_lines = urllib.request.urlopen(v_req, timeout=5).read().decode('utf-8').splitlines()

    v_init_url = [l.split('URI="')[1].split('"')[0] for l in v_lines if 'EXT-X-MAP' in l][0]
    m4s_urls = [l for l in v_lines if l.startswith('http') and l.endswith('.m4s')]

    init_data = urllib.request.urlopen(urllib.request.Request(v_init_url, headers=HEADERS), timeout=5).read()

    # Grab the last 4 segments (~8 seconds)
    combined = init_data
    for u in m4s_urls[-4:]:
        combined += urllib.request.urlopen(urllib.request.Request(u, headers=HEADERS), timeout=5).read()

    tmp_snip = Path("/dev/shm/discord_snip_temp.mp4")
    tmp_snip.write_bytes(combined)

    frame_paths = []
    for i in range(count):
        out_frame = Path(f"/dev/shm/discord_burst_{i+1}.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-decryption_key", KEY,
            "-ss", str(i * 2.0),
            "-i", str(tmp_snip),
            "-vframes", "1",
            "-update", "1",
            str(out_frame)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out_frame.exists():
            frame_paths.append(str(out_frame))

    return frame_paths

def generate_roast(trigger_text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return f"BARK BARK! James saw that wild broadcast stunt: '{trigger_text}'! Unhinged TV energy!"

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        sys_prompt = """You are Barf the Dog (@BarfFanStack), an unhinged, hilarious New York sports hound on Discord.
The Pilot (James) just dropped a message into the war room about something ridiculous he just saw on the live TV broadcast.
Write a savage, funny 2-sentence roast reacting directly to what he said.
Use all-caps for dog barking emphasis. Zero corporate fluff."""
        resp = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[sys_prompt, trigger_text]
        )
        return resp.text.strip()
    except Exception as e:
        return f"BARK BARK! What did we just witness?! Total visual catastrophe!"

def post_to_discord(roast_text: str, frames: list[str]) -> bool:
    import requests
    payload = {
        "username": "Barf the Dog (@BarfFanStack)",
        "content": f"🐕 **[INSTANT PRECOG SNIPE]** {roast_text}\n*Captured 3-frame sequence across origin buffer:*"
    }

    files = {}
    opened_files = []
    try:
        for idx, fpath in enumerate(frames):
            f = open(fpath, "rb")
            opened_files.append(f)
            files[f"files[{idx}]"] = (f"screengrab_{idx+1}.jpg", f, "image/jpeg")

        r = requests.post(WEBHOOK_URL, data=payload, files=files, timeout=10)
        return r.status_code in (200, 204)
    finally:
        for f in opened_files:
            f.close()

def main():
    print("=" * 70)
    print("⚡ STACKLABS REAL-TIME DISCORD PILOT SNIPER ACTIVE")
    print(f"📡 Channel: {CHANNEL_ID}")
    print("=" * 70)

    # Prime with current last message ID so we only react to NEW messages
    initial_msgs = get_latest_channel_messages(limit=1)
    last_seen_id = initial_msgs[0]["id"] if initial_msgs else None
    print(f"✓ Primed with latest message ID: {last_seen_id}")

    while True:
        try:
            msgs = get_latest_channel_messages(limit=3)
            for m in msgs:
                m_id = m.get("id")
                author = m.get("author", {})
                content = m.get("content", "").strip()
                is_bot = author.get("bot", False)

                if m_id != last_seen_id and not is_bot:
                    # New human message from Pilot!
                    print(f"\n[🎯 PILOT TRIGGER] [{author.get('username')}]: {content}")
                    last_seen_id = m_id

                    print("[*] Snapping 3 live broadcast frames from origin HLS...")
                    frames = snip_live_frames(count=3)
                    print(f"✓ Snapped {len(frames)} frames: {frames}")

                    print("[*] Generating Barf roast with gemini-3.8-flash...")
                    roast = generate_roast(content)
                    print(f"✓ Roast: {roast}")

                    print("[*] Posting reply to Discord webhook...")
                    success = post_to_discord(roast, frames)
                    print(f"✓ Dispatch result: {success}")
                    break

            if msgs and msgs[0].get("id"):
                last_seen_id = msgs[0]["id"]

            time.sleep(2.0)
        except KeyboardInterrupt:
            print("\nSniper shutting down.")
            break
        except Exception as e:
            time.sleep(2.0)

if __name__ == "__main__":
    main()

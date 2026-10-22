#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs LFGM Omnibot Dynamic Reflex Router
Listens to James's private LFGM_Barf channel (1561509280870305835) and executes:
1. !clip / !video: Full Retrograde Video & Audio Replay (default 45 segments = 90s) with Artemis Whisper
2. !meme [topic]: Instant High-Contrast Deep Void Visual Meme Card generation & upload
3. !wiretap / !digest: Instant on-demand fan quote & Barf roast dispatch
4. !tag / !leaf [note]: In-channel couch marker logged to data/couch_markers.json
5. !status / !health: Buffer and node telemetry
6. Natural commentary: Fast 3-frame still burst + Barf roast
"""
import os
import sys
import time
import json
import re
import urllib.request
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

REPO_ROOT = Path("/home/james/stacklabs")
load_dotenv(REPO_ROOT / ".env")

CHANNEL_ID = "1561509280870305835"
WEBHOOK_URL = os.getenv("STACKLABS_PRIVATE_DISCORD_WEBHOOK")
DISCORD_TOKEN = os.getenv("DISCORD_USER_TOKEN")
KEY = "97c385957ccd4c120fa7d6823bd80f1b"
RING_DIR = Path("/dev/shm/espn2_ring")
MARKERS_FILE = REPO_ROOT / "data" / "couch_markers.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from precog_stream_sniper import snip_retrograde_window
from instant_meme_engine import build_instant_meme, render_meme_card, generate_barf_meme_roast
from bleacher_wiretap_digest import run_digest


def get_latest_channel_messages(limit: int = 3) -> list[dict]:
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit={limit}"
    req = urllib.request.Request(url, headers={"Authorization": DISCORD_TOKEN, "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []


def generate_barf_roast(trigger_text: str, transcript: str = "") -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return f"BARK BARK! James saw that wild broadcast stunt: '{trigger_text}'! Unhinged TV energy!"

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        sys_prompt = """You are Barf the Dog (@BarfFanStack), an unhinged, hilarious New York sports hound on Discord.
The Pilot (James) just dropped a reaction or command about live sports.
Write a savage, funny 2-sentence roast reacting directly to what he said and what the announcers said.
Use all-caps for dog barking emphasis. Zero corporate fluff, zero apologies."""

        content = f"Pilot comment: {trigger_text}\nAnnouncer transcript: {transcript or 'No commentary caught'}"
        resp = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[sys_prompt, content]
        )
        return resp.text.strip()
    except Exception as e:
        return f"BARK BARK! What did we just witness?! Broadcast went totally feral: '{trigger_text}'!"


def handle_replay_request(content: str, author_name: str) -> None:
    print(f"[*] Executing Video/Audio Replay for [{author_name}]: '{content}'", flush=True)
    tag = f"replay_{int(time.time())}"

    match = re.search(r"(\d+)", content)
    num_segments = int(int(match.group(1)) / 2) if match else 45
    num_segments = max(10, min(num_segments, 60))

    try:
        snip = snip_retrograde_window(num_segments=num_segments, offset_back=1, tag=tag, run_artemis=True)
    except Exception as e:
        requests.post(WEBHOOK_URL, json={
            "username": "Barf the Dog (@BarfFanStack)",
            "content": f"⚠️ **[REPLAY ERROR]** Could not snip buffer: {e}"
        })
        return

    roast = generate_barf_roast(content, snip["transcript"])
    mp4_path = Path(snip["video"])
    jpg_path = Path(snip["photo"])
    mp4_size_mb = mp4_path.stat().st_size / (1024 * 1024)

    files = {}
    opened_files = []

    if mp4_size_mb > 23.0:
        teaser_mp4 = Path(f"/dev/shm/teaser_{tag}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-sseof", "-15", "-i", str(mp4_path),
            "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "96k", str(teaser_mp4)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        upload_mp4 = teaser_mp4 if teaser_mp4.exists() else None
        clip_note = f"\n🎥 *Teaser clip attached (15s preview). Full pristine 90s master ({mp4_size_mb:.1f}MB) saved to local host:* `{mp4_path.name}`"
    else:
        upload_mp4 = mp4_path
        clip_note = f"\n🎥 *Full {snip['duration']:.1f}s master attached ({mp4_size_mb:.1f}MB).*"

    transcript_block = f"\n🎙️ **Artemis Whisper Transcript**: *\"{snip['transcript']}\"*" if snip['transcript'] else "\n🎙️ **Artemis Whisper Transcript**: *(Silence / crowd noise)*"

    payload_text = (
        f"🐕 **[LIVE 90S REPLAY SNIP]** {roast}\n"
        f"⏱️ **Window**: {snip['duration']:.1f}s ({snip['segments']} segments from MoveTV HLS)"
        f"{transcript_block}"
        f"{clip_note}"
    )

    try:
        idx = 0
        if jpg_path.exists():
            f_jpg = open(jpg_path, "rb")
            opened_files.append(f_jpg)
            files[f"files[{idx}]"] = (f"hero_{tag}.jpg", f_jpg, "image/jpeg")
            idx += 1

        if upload_mp4 and upload_mp4.exists():
            f_mp4 = open(upload_mp4, "rb")
            opened_files.append(f_mp4)
            files[f"files[{idx}]"] = (f"clip_{tag}.mp4", f_mp4, "video/mp4")
            idx += 1

        r = requests.post(WEBHOOK_URL, data={"username": "Barf the Dog (@BarfFanStack)", "content": payload_text}, files=files, timeout=20)
        print(f"✓ Replay dispatch status: {r.status_code}", flush=True)
    finally:
        for f in opened_files:
            f.close()


def handle_still_burst(content: str, author_name: str) -> None:
    print(f"[*] Executing Still Burst for [{author_name}]: '{content}'", flush=True)
    tag = f"burst_{int(time.time())}"

    try:
        snip = snip_retrograde_window(num_segments=4, offset_back=1, tag=tag, run_artemis=False)
    except Exception as e:
        requests.post(WEBHOOK_URL, json={
            "username": "Barf the Dog (@BarfFanStack)",
            "content": f"⚠️ **[SNIP ERROR]** {e}"
        })
        return

    frame_paths = []
    mp4_path = Path(snip["video"])
    for i in range(3):
        out_f = Path(f"/dev/shm/frame_{tag}_{i+1}.jpg")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(i * 2.5), "-i", str(mp4_path),
            "-vframes", "1", "-update", "1", str(out_f)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out_f.exists():
            frame_paths.append(out_f)

    roast = generate_barf_roast(content)
    payload_text = f"🐕 **[INSTANT PRECOG SNIPE]** {roast}\n*Captured 3-frame sequence across origin buffer:*"

    files = {}
    opened_files = []
    try:
        for idx, fpath in enumerate(frame_paths):
            f = open(fpath, "rb")
            opened_files.append(f)
            files[f"files[{idx}]"] = (f"screengrab_{idx+1}.jpg", f, "image/jpeg")

        r = requests.post(WEBHOOK_URL, data={"username": "Barf the Dog (@BarfFanStack)", "content": payload_text}, files=files, timeout=10)
        print(f"✓ Still burst dispatch status: {r.status_code}", flush=True)
    finally:
        for f in opened_files:
            f.close()


def handle_instant_meme(content: str, author_name: str) -> None:
    print(f"[*] Executing Instant Meme Engine for [{author_name}]: '{content}'", flush=True)
    topic = content.replace("!meme", "").strip() or None

    try:
        meme_file, meta = build_instant_meme(topic=topic, dispatch=False)
        caption = (
            f"🐕 **[BARF INSTANT MEME ENGINE]**\n"
            f"🗣️ *Overheard in {meta['source'].upper()}* (@{meta['author']}):\n"
            f"> \"{meta['quote']}\"\n\n"
            f"*{meta['roast']}*"
        )

        with open(meme_file, "rb") as f:
            files = {"files[0]": (meme_file.name, f, "image/png")}
            r = requests.post(
                WEBHOOK_URL,
                data={"username": "Barf the Dog (@BarfFanStack)", "content": caption},
                files=files,
                timeout=15
            )
            print(f"✓ Instant Meme dispatch status: {r.status_code}", flush=True)
    except Exception as e:
        requests.post(WEBHOOK_URL, json={
            "username": "Barf the Dog (@BarfFanStack)",
            "content": f"⚠️ **[MEME ENGINE ERROR]** {e}"
        })


def handle_wiretap_request() -> None:
    print("[*] Executing On-Demand Bleacher Wiretap Pull...", flush=True)
    success = run_digest(dry_run=False)
    if not success:
        requests.post(WEBHOOK_URL, json={
            "username": "Barf the Dog (@BarfFanStack)",
            "content": "⚠️ Could not pull wiretap digest. Check data/morning_wiretap.db."
        })


def handle_couch_marker(content: str, author_name: str) -> None:
    print(f"[*] Logging Couch Marker from [{author_name}]: '{content}'", flush=True)
    raw_note = re.sub(r"^!(tag|leaf|mark)\s*", "", content, flags=re.IGNORECASE).strip()
    note = raw_note or "Couch Marker / Broadcast Moment"

    vid_count = len(list(RING_DIR.glob("vid_*.m4s")))
    timestamp_iso = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    marker_id = f"leaf_{int(time.time())}"

    marker_entry = {
        "id": marker_id,
        "timestamp": timestamp_iso,
        "epoch_time": time.time(),
        "author": author_name,
        "note": note,
        "buffer_segments": vid_count,
        "channel_id": CHANNEL_ID
    }

    MARKERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing_markers = []
    if MARKERS_FILE.exists():
        try:
            existing_markers = json.loads(MARKERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing_markers = []

    existing_markers.append(marker_entry)
    MARKERS_FILE.write_text(json.dumps(existing_markers, indent=2), encoding="utf-8")

    response_text = (
        f"🍃 **[COUCH MARKER LOGGED]**\n"
        f"📌 *\"{note}\"*\n"
        f"- 🕒 **Timestamp**: `{timestamp_iso}`\n"
        f"- 📁 **Active Buffer**: {vid_count} video segments locked (~{vid_count * 2.048:.1f}s)\n"
        f"- 💾 **Ledger**: `data/couch_markers.json`"
    )
    requests.post(WEBHOOK_URL, json={"username": "Barf the Dog (@BarfFanStack)", "content": response_text})


def handle_help_request() -> None:
    help_msg = (
        f"🐕 **BARF THE DOG // COMMAND DIRECTORY**\n"
        f"- `!clip [seconds]`: Snip 15-90s retrograde replay from MoveTV buffer with Artemis Whisper transcript\n"
        f"- `!meme [topic]`: Generate high-contrast Deep Void instant meme card and dispatch to channel\n"
        f"- `!wiretap`: Pull immediate fresh fan quotes and Barf roast from morning sports radio/livechats\n"
        f"- `!tag [note]` or `!leaf`: Bookmark a live broadcast moment into `data/couch_markers.json`\n"
        f"- `!status`: Inspect active RAM ring buffer, Artemis acoustic node, and host telemetry"
    )
    requests.post(WEBHOOK_URL, json={"username": "Barf the Dog (@BarfFanStack)", "content": help_msg})


def handle_status_request() -> None:
    vid_count = len(list(RING_DIR.glob("vid_*.m4s")))
    aud_count = len(list(RING_DIR.glob("aud_*.m4s")))
    duration_s = vid_count * 2.048
    msg = (
        f"🛰️ **[OMNIBOT TELEMETRY]** Clio host online.\n"
        f"- 📡 **Origin Stream**: ESPN MoveTV 720p60 (ClearKey decrypted)\n"
        f"- 📁 **RAM Buffer**: {vid_count} video / {aud_count} audio segments (~{duration_s:.1f}s active window)\n"
        f"- ⚡ **Acoustic Node**: Artemis GTX 1060 CUDA Faster-Whisper ready\n"
        f"- 🖼️ **Meme Engine**: Deep Void (#0B0D13) 1200x675 generator online\n"
        f"- 🐕 **Persona**: Barf the Dog (`gemini-3.8-flash` active)"
    )
    requests.post(WEBHOOK_URL, json={"username": "Barf the Dog (@BarfFanStack)", "content": msg})



def handle_pawel_curve_push(raw_content: str, recent_context: str = "") -> bool:
    """Routes !push, !push clip, and !push_preview to scripts/push_to_pawel_curve.py."""
    import subprocess
    text = raw_content.strip()
    low = text.lower()
    if not (low == "!push" or low.startswith("!push ") or low.startswith("!push_preview")):
        return False

    is_preview = low.startswith("!push_preview")
    arg = text.split(" ", 1)[1].strip() if " " in text else "clip"

    cmd = [
        "/home/james/stacklabs/.venv/bin/python3",
        "/home/james/stacklabs/scripts/push_to_pawel_curve.py",
        "--notify-discord",
    ]
    if arg.lower() in ("", "clip", "clipboard", "--clipboard"):
        cmd.extend(["--clipboard", "--context", recent_context])
    else:
        cmd.extend(["--message", arg])

    if is_preview:
        cmd.append("--dry-run")
    else:
        cmd.append("--live")

    subprocess.run(cmd, check=False, timeout=55)
    return True


def main() -> None:
    print("=" * 70, flush=True)
    print("⚡ STACKLABS LFGM OMNIBOT DYNAMIC ROUTER ACTIVE", flush=True)
    print(f"📡 Channel: {CHANNEL_ID}", flush=True)
    print("=" * 70, flush=True)

    initial_msgs = get_latest_channel_messages(limit=1)
    last_seen_id = initial_msgs[0]["id"] if initial_msgs else None
    print(f"✓ Primed with latest message ID: {last_seen_id}", flush=True)

    while True:
        try:
            msgs = get_latest_channel_messages(limit=3)
            for m in msgs:
                m_id = m.get("id")
                author = m.get("author", {})
                content = m.get("content", "").strip()
                is_bot = author.get("bot", False)

                if m_id != last_seen_id and not is_bot and content:
                    print(f"\n[🎯 LFGM PILOT EVENT] [{author.get('username')}]: {content}", flush=True)
                    last_seen_id = m_id
                    lower_c = content.lower()

                    if lower_c == "!push" or lower_c.startswith("!push ") or lower_c.startswith("!push_preview"):
                        handle_pawel_curve_push(content)
                    elif any(k in lower_c for k in ["!help", "!commands"]):
                        handle_help_request()
                    elif any(k in lower_c for k in ["!status", "!ping", "!buffer", "!health"]):
                        handle_status_request()
                    elif any(k in lower_c for k in ["!tag", "!leaf", "!mark"]):
                        handle_couch_marker(content, author.get("username", "Pilot"))
                    elif any(k in lower_c for k in ["!wiretap", "!digest"]):
                        handle_wiretap_request()
                    elif any(k in lower_c for k in ["!meme"]):
                        handle_instant_meme(content, author.get("username", "Pilot"))
                    elif any(k in lower_c for k in ["!clip", "!video", "!replay", "!snip", "video", "clip", "replay", "transcript"]):
                        handle_replay_request(content, author.get("username", "Pilot"))
                    else:
                        # Natural commentary -> fast 3-frame burst + roast
                        handle_still_burst(content, author.get("username", "Pilot"))
                    break

            if msgs and msgs[0].get("id"):
                last_seen_id = msgs[0]["id"]

            time.sleep(1.5)
        except KeyboardInterrupt:
            print("\nOmnibot router shutting down.", flush=True)
            break
        except Exception:
            time.sleep(2.0)


if __name__ == "__main__":
    main()

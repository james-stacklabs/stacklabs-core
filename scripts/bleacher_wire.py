#!/usr/bin/env python3
"""
THE BLEACHER WIRE: Autonomous YouTube Live Chat Sniffer & Ingress Engine
Path: /home/james/stacklabs/scripts/bleacher_wire.py

Usage:
    python3 scripts/bleacher_wire.py <YOUTUBE_URL_OR_VIDEO_ID> [--output <PATH>] [--no-ws] [--no-corpus]

Examples:
    python3 scripts/bleacher_wire.py "https://www.youtube.com/watch?v=64kRgP6TcNc"
    python3 scripts/bleacher_wire.py 64kRgP6TcNc -o /home/james/sovereign_inbox/today/philly500.md
    python3 scripts/bleacher_wire.py "https://www.youtube.com/live/BZWHpjX5his"

Legal / Governance:
    - 100% compliant with hiQ Labs v. LinkedIn (9th Cir. 2022) for publicly broadcast data.
    - Zero authentication, zero cookies, zero botting/spamming. Read-only public SSE listener.
"""

import os
import sys
import re
import json
import time
import argparse
import asyncio
import subprocess
from datetime import datetime

# Auto-reexec with SovereignOS virtualenv if pytchat is missing in system python
try:
    import pytchat
except ImportError:
    venv_py = "/home/james/stacklabs/.venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)
    else:
        print("[-] Error: pytchat is not installed. Install via: pip install pytchat", file=sys.stderr)
        sys.exit(1)

try:
    import websockets
except ImportError:
    websockets = None

BANNER = r"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                   📡 THE BLEACHER WIRE // CLI TIER 1                     ║
║            Zero-Auth YouTube Live Chat Sniffer & Dialect Vault            ║
║              StackLabs LLC // Sovereign OS FaaS Data Plane                ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

def extract_video_id(url_or_id: str) -> str:
    """Extract standard 11-char YouTube video ID from various URL patterns or bare ID."""
    clean_input = url_or_id.strip()
    patterns = [
        r'(?:v=|\/live\/|youtu\.be\/|\/embed\/|\/shorts\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for p in patterns:
        m = re.search(p, clean_input)
        if m:
            return m.group(1)
    m = re.search(r'([0-9A-Za-z_-]{11})', clean_input)
    if m:
        return m.group(1)
    return clean_input

def get_stream_title(video_id: str) -> str:
    """Attempt fast retrieval of stream title via yt-dlp."""
    yt_dlp_bin = "/home/james/stacklabs/.venv/bin/yt-dlp"
    if not os.path.exists(yt_dlp_bin):
        yt_dlp_bin = "yt-dlp"
    try:
        proc = subprocess.run(
            [yt_dlp_bin, "--get-title", f"https://www.youtube.com/watch?v={video_id}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=6
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return f"YouTube Live Stream ({video_id})"

async def tail_bleacher_wire(video_id: str, output_path: str, enable_ws: bool = True, enable_corpus: bool = True):
    stream_title = get_stream_title(video_id)
    stream_url = f"https://www.youtube.com/watch?v={video_id}"
    ws_url = "ws://127.0.0.1:8008"
    
    today_str = datetime.now().strftime("%Y%m%d")
    corpus_dir = "/home/james/sovereign_inbox/media_vault/scar_tissue_corpus"
    corpus_file = os.path.join(corpus_dir, f"scar_tissue_corpus_{today_str}.jsonl")
    if enable_corpus:
        os.makedirs(corpus_dir, exist_ok=True)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print(BANNER)
    print(f"[*] Target Video ID : {video_id}")
    print(f"[*] Stream Title    : {stream_title}")
    print(f"[*] Broadcast URL   : {stream_url}")
    print(f"[*] Output Markdown : {output_path}")
    if enable_corpus:
        print(f"[*] Training Corpus : {corpus_file}")
    if enable_ws and websockets:
        print(f"[*] WebSocket Relay : {ws_url} (target_game_pk: live_chat_sniper)")
    print("-" * 75)

    is_new_file = not os.path.exists(output_path) or os.path.getsize(output_path) == 0
    if is_new_file:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# 📡 The Bleacher Wire: Live Chat Stream\n\n")
            f.write(f"- **Stream Title:** {stream_title}\n")
            f.write(f"- **Video ID:** `{video_id}`\n")
            f.write(f"- **URL:** [{stream_url}]({stream_url})\n")
            f.write(f"- **Captured At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')}\n")
            f.write(f"- **Engine:** Sovereign OS Bleacher Wire (pytchat SSE)\n\n")
            f.write(f"---\n\n")

    print("[*] Connecting to live chat stream via public SSE...")
    try:
        chat = pytchat.create(video_id=video_id)
    except Exception as e:
        print(f"[-] Failed to initialize pytchat for video {video_id}: {e}", file=sys.stderr)
        return

    await asyncio.sleep(2)
    if not chat.is_alive():
        print(f"[!] Warning: No live chat feed detected for {video_id}.")
        print(f"    Possible reasons: Stream has not started, live chat is disabled, or video is a standard VOD without replay.", file=sys.stderr)

    message_count = 0
    start_time = time.time()
    ws_client = None

    async def get_ws():
        nonlocal ws_client
        if not enable_ws or not websockets:
            return None
        try:
            if ws_client is None or ws_client.closed:
                ws_client = await asyncio.wait_for(websockets.connect(ws_url), timeout=2.0)
            return ws_client
        except Exception:
            ws_client = None
            return None

    try:
        while chat.is_alive():
            try:
                items = chat.get().sync_items()
                for c in items:
                    author = c.author.name
                    message = c.message
                    timestamp_str = c.datetime or time.strftime("%H:%M:%S")
                    msg_time = time.time()
                    message_count += 1

                    # 1. Append formatted entry to Markdown
                    try:
                        with open(output_path, "a", encoding="utf-8") as f:
                            f.write(f"### @{author} · *{timestamp_str}*\n{message}\n\n")
                    except Exception as err:
                        print(f"[-] Markdown write error: {err}", file=sys.stderr)

                    # 2. Append structured JSONL to Scar Tissue Corpus
                    if enable_corpus:
                        try:
                            record = {
                                "timestamp": msg_time,
                                "iso_time": datetime.now().isoformat(),
                                "video_id": video_id,
                                "stream_title": stream_title,
                                "author": author,
                                "message": message,
                                "channel_id": getattr(c.author, "channelId", None)
                            }
                            with open(corpus_file, "a", encoding="utf-8") as cf:
                                cf.write(json.dumps(record, ensure_ascii=False) + "\n")
                        except Exception:
                            pass

                    # 3. Relay to Sovereign OS WebSocket bus
                    if enable_ws and websockets:
                        ws = await get_ws()
                        if ws:
                            payload = {
                                "type": "YOUTUBE_CHAT",
                                "user": author,
                                "text": message,
                                "target_game_pk": "live_chat_sniper",
                                "video_id": video_id,
                                "stream_title": stream_title,
                                "timestamp": msg_time
                            }
                            try:
                                await ws.send(json.dumps(payload))
                            except Exception:
                                ws_client = None

                    # 4. Print clean console output
                    clean_msg = message.replace("\n", " ")
                    if len(clean_msg) > 85:
                        clean_msg = clean_msg[:82] + "..."
                    print(f"[{time.strftime('%H:%M:%S')}] #{message_count:<5} @{author}: {clean_msg}")

            except Exception as loop_err:
                print(f"[!] Stream tick notice: {loop_err}", file=sys.stderr)

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n[*] Interrupted by user (Ctrl+C). Clean shutdown initiated...")
    finally:
        elapsed = time.time() - start_time
        rate = (message_count / elapsed) * 60 if elapsed > 0 else 0
        print("-" * 75)
        print(f"[+] The Bleacher Wire Session Summary:")
        print(f"    - Total Messages Captured : {message_count:,}")
        print(f"    - Elapsed Time           : {elapsed:.1f}s ({rate:.1f} msgs/min)")
        print(f"    - Output Markdown File   : {output_path}")
        if enable_corpus:
            print(f"    - Scar Tissue Corpus     : {corpus_file}")
        if ws_client and not ws_client.closed:
            await ws_client.close()
        print("[+] Sovereign Wiretap Standby. The Forge is Open 24/7.")

def main():
    parser = argparse.ArgumentParser(
        description="The Bleacher Wire: Zero-Auth YouTube Live Chat Sniffer & Ingress Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 scripts/bleacher_wire.py "https://www.youtube.com/watch?v=64kRgP6TcNc"
  python3 scripts/bleacher_wire.py 64kRgP6TcNc -o /home/james/sovereign_inbox/today/custom.md
  python3 scripts/bleacher_wire.py "https://www.youtube.com/live/BZWHpjX5his" --no-ws
"""
    )
    parser.add_argument("target", help="YouTube live stream URL (watch, live, share) or 11-char Video ID")
    parser.add_argument("-o", "--output", help="Destination markdown file path (defaults to /home/james/sovereign_inbox/today/bleacher_wire_<VIDEO_ID>.md)")
    parser.add_argument("--no-ws", action="store_true", help="Disable WebSocket relay to Port 8008")
    parser.add_argument("--no-corpus", action="store_true", help="Disable appending to Scar Tissue Corpus JSONL")

    args = parser.parse_args()

    video_id = extract_video_id(args.target)
    if not video_id:
        print("[-] Error: Could not parse YouTube Video ID from input.", file=sys.stderr)
        sys.exit(1)

    output_path = args.output
    if not output_path:
        output_path = f"/home/james/sovereign_inbox/today/bleacher_wire_{video_id}.md"

    asyncio.run(tail_bleacher_wire(
        video_id=video_id,
        output_path=output_path,
        enable_ws=not args.no_ws,
        enable_corpus=not args.no_corpus
    ))

if __name__ == "__main__":
    main()

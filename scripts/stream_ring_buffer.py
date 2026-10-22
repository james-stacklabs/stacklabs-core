#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs MoveTV HLS Origin Circular RAM Buffer Daemon
Maintains a rolling 100-second ring buffer of 720p60 and AAC segments in /dev/shm.
"""
import os
import sys
import time
import re
import urllib.request
from pathlib import Path

KEY = "97c385957ccd4c120fa7d6823bd80f1b"
MASTER_URL = "https://p-dynaman.movetv.com/manifest/1290/widevine/master.m3u8?location_zip=sling"
RING_DIR = Path("/dev/shm/espn2_ring")
MAX_SEGMENTS = 50  # 50 * 2.048s = ~102.4 seconds of rolling footage

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def resolve_variant_urls() -> tuple[str, str]:
    req = urllib.request.Request(MASTER_URL, headers=HEADERS)
    content = urllib.request.urlopen(req, timeout=8).read().decode("utf-8")
    lines = content.splitlines()

    video_variants = []
    audio_variants = []

    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            bw_match = re.search(r"BANDWIDTH=(\d+)", line)
            bw = int(bw_match.group(1)) if bw_match else 0
            url = lines[i + 1].strip()
            video_variants.append((bw, url))
        elif line.startswith("#EXT-X-MEDIA:TYPE=AUDIO") and 'GROUP-ID="aac_2_192' in line:
            m = re.search(r'URI="([^"]+)"', line)
            if m:
                audio_variants.append(m.group(1).strip())

    video_variants.sort(key=lambda x: x[0], reverse=True)
    best_vid = video_variants[0][1] if video_variants else ""
    best_aud = audio_variants[0] if audio_variants else ""
    return best_vid, best_aud


def prune_old_segments(seg_type: str, max_count: int) -> None:
    files = sorted(RING_DIR.glob(f"{seg_type}_*.m4s"), key=lambda p: p.stat().st_mtime)
    if len(files) > max_count:
        for old_file in files[:-max_count]:
            try:
                old_file.unlink()
            except OSError:
                pass


def main() -> None:
    RING_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70, flush=True)
    print("⚡ STACKLABS HLS RAM RING BUFFER DAEMON", flush=True)
    print(f"📁 Volatile Store: {RING_DIR} (Window: {MAX_SEGMENTS * 2.048:.1f}s)", flush=True)
    print("=" * 70, flush=True)

    vid_url, aud_url = resolve_variant_urls()
    if not vid_url or not aud_url:
        print("Failed to resolve stream variants from master manifest.", file=sys.stderr, flush=True)
        sys.exit(1)

    print(f"✓ Video Stream: {vid_url}", flush=True)
    print(f"✓ Audio Stream: {aud_url}", flush=True)

    init_fetched = False
    downloaded_vids: set[str] = set()
    downloaded_auds: set[str] = set()

    running = True
    while running:
        try:
            v_req = urllib.request.Request(vid_url, headers=HEADERS)
            v_lines = urllib.request.urlopen(v_req, timeout=5).read().decode("utf-8").splitlines()

            a_req = urllib.request.Request(aud_url, headers=HEADERS)
            a_lines = urllib.request.urlopen(a_req, timeout=5).read().decode("utf-8").splitlines()

            if not init_fetched:
                v_init = [l.split('URI="')[1].split('"')[0] for l in v_lines if "EXT-X-MAP" in l][0]
                a_init = [l.split('URI="')[1].split('"')[0] for l in a_lines if "EXT-X-MAP" in l][0]

                (RING_DIR / "vid_init.mp4").write_bytes(
                    urllib.request.urlopen(urllib.request.Request(v_init, headers=HEADERS), timeout=5).read()
                )
                (RING_DIR / "aud_init.mp4").write_bytes(
                    urllib.request.urlopen(urllib.request.Request(a_init, headers=HEADERS), timeout=5).read()
                )
                init_fetched = True
                print("✓ Initialized stream header maps in RAM.", flush=True)

            new_vids = [l for l in v_lines if l.startswith("http") and l.endswith(".m4s") and l not in downloaded_vids]
            new_auds = [l for l in a_lines if l.startswith("http") and l.endswith(".m4s") and l not in downloaded_auds]

            for s_url in new_vids:
                seg_name = s_url.split("/")[-1].split("?")[0]
                seg_bytes = urllib.request.urlopen(urllib.request.Request(s_url, headers=HEADERS), timeout=5).read()
                (RING_DIR / f"vid_{seg_name}").write_bytes(seg_bytes)
                downloaded_vids.add(s_url)

            for a_url in new_auds:
                seg_name = a_url.split("/")[-1].split("?")[0]
                seg_bytes = urllib.request.urlopen(urllib.request.Request(a_url, headers=HEADERS), timeout=5).read()
                (RING_DIR / f"aud_{seg_name}").write_bytes(seg_bytes)
                downloaded_auds.add(a_url)

            prune_old_segments("vid", MAX_SEGMENTS)
            prune_old_segments("aud", MAX_SEGMENTS)

            if len(downloaded_vids) > 200:
                downloaded_vids = set(list(downloaded_vids)[-100:])
            if len(downloaded_auds) > 200:
                downloaded_auds = set(list(downloaded_auds)[-100:])

            time.sleep(1.5)
        except KeyboardInterrupt:
            print("\nShutting down ring buffer daemon.", flush=True)
            running = False
        except Exception as e:
            time.sleep(1.5)


if __name__ == "__main__":
    main()

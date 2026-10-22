#!/usr/bin/env python3
"""
StackLabs Halftime DVR Recorder
Captures live ESPN2 MoveTV/Sling HLS stream segments for the halftime show,
concatenates them, and decrypts into an archival MP4 with AAC audio on metal.
"""
import os
import sys
import time
import re
import urllib.request
import subprocess
from pathlib import Path

KEY = "e15f0da7cc14efd1f21def6a14411b11"
MASTER_URL = "https://p-dynaman.movetv.com/manifest/1291/widevine/master.m3u8?location_zip=sling"
OUTPUT_DIR = Path("/home/james/stacklabs/pilot_drops/video")
OUTPUT_FILE = OUTPUT_DIR / f"mnf_halftime_show_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
TEMP_DIR = Path("/dev/shm/halftime_dvr")

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def get_variant_urls():
    req = urllib.request.Request(MASTER_URL, headers=HEADERS)
    content = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
    lines = content.splitlines()

    video_variants = []
    audio_variants = []

    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            bw = int(re.search(r'BANDWIDTH=(\d+)', line).group(1))
            url = lines[i+1].strip()
            video_variants.append((bw, url))
        elif line.startswith("#EXT-X-MEDIA:TYPE=AUDIO") and 'GROUP-ID="aac_2_192' in line:
            m = re.search(r'URI="([^"]+)"', line)
            if m:
                audio_variants.append(m.group(1).strip())

    video_variants.sort(key=lambda x: x[0], reverse=True)
    best_video_url = video_variants[0][1] if video_variants else None
    best_audio_url = audio_variants[0] if audio_variants else None

    return best_video_url, best_audio_url

def main():
    duration_sec = int(sys.argv[1]) if len(sys.argv) > 1 else 720 # default 12 minutes
    print("=" * 70)
    print("⚡ STACKLABS LIVE STREAM DVR RECORDER: ESPN2 HALFTIME")
    print(f"⏱️  Duration: {duration_sec}s ({duration_sec/60:.1f} minutes)")
    print(f"📁 Destination: {OUTPUT_FILE}")
    print("=" * 70)

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[*] Resolving master playlist...")
    vid_m3u8, aud_m3u8 = get_variant_urls()
    print(f"✓ Video Variant: {vid_m3u8}")
    print(f"✓ Audio Variant: {aud_m3u8}")

    vid_raw_path = TEMP_DIR / "raw_video.mp4"
    aud_raw_path = TEMP_DIR / "raw_audio.mp4"

    vid_file = open(vid_raw_path, "wb")
    aud_file = open(aud_raw_path, "wb")

    downloaded_vid_segs = set()
    downloaded_aud_segs = set()
    init_downloaded = False

    t_start = time.time()
    seg_count = 0

    try:
        while time.time() - t_start < duration_sec:
            # 1. Fetch playlists
            try:
                v_req = urllib.request.Request(vid_m3u8, headers=HEADERS)
                v_lines = urllib.request.urlopen(v_req, timeout=5).read().decode('utf-8').splitlines()

                a_req = urllib.request.Request(aud_m3u8, headers=HEADERS)
                a_lines = urllib.request.urlopen(a_req, timeout=5).read().decode('utf-8').splitlines()
            except Exception as e:
                print(f"[!] Playlist refresh warning: {e}, renewing variant URLs...")
                time.sleep(1)
                try:
                    vid_m3u8, aud_m3u8 = get_variant_urls()
                except Exception:
                    pass
                continue

            # 2. Extract inits if not downloaded
            if not init_downloaded:
                v_init_url = [l.split('URI="')[1].split('"')[0] for l in v_lines if 'EXT-X-MAP' in l][0]
                a_init_url = [l.split('URI="')[1].split('"')[0] for l in a_lines if 'EXT-X-MAP' in l][0]

                vid_file.write(urllib.request.urlopen(urllib.request.Request(v_init_url, headers=HEADERS), timeout=5).read())
                aud_file.write(urllib.request.urlopen(urllib.request.Request(a_init_url, headers=HEADERS), timeout=5).read())
                init_downloaded = True
                print("✓ Initialized stream header maps (init.mp4)")

            # 3. Find segments
            new_v_segs = [l for l in v_lines if l.startswith('http') and l.endswith('.m4s') and l not in downloaded_vid_segs]
            new_a_segs = [l for l in a_lines if l.startswith('http') and l.endswith('.m4s') and l not in downloaded_aud_segs]

            # Pair matching segments by index or filename
            for seg_url in new_v_segs:
                try:
                    data = urllib.request.urlopen(urllib.request.Request(seg_url, headers=HEADERS), timeout=5).read()
                    vid_file.write(data)
                    vid_file.flush()
                    downloaded_vid_segs.add(seg_url)
                    seg_count += 1
                except Exception as e:
                    print(f"Error fetching video seg: {e}")

            for seg_url in new_a_segs:
                try:
                    data = urllib.request.urlopen(urllib.request.Request(seg_url, headers=HEADERS), timeout=5).read()
                    aud_file.write(data)
                    aud_file.flush()
                    downloaded_aud_segs.add(seg_url)
                except Exception as e:
                    print(f"Error fetching audio seg: {e}")

            elapsed = int(time.time() - t_start)
            rem = duration_sec - elapsed
            if seg_count % 10 == 0:
                print(f"[DVR REC] Recorded {len(downloaded_vid_segs)} segments ({len(downloaded_vid_segs)*2.048:.1f}s) | Elapsed: {elapsed}s | Remaining: {rem}s", flush=True)

            time.sleep(1.8)

    except KeyboardInterrupt:
        print("\n[!] Recording interrupted by user. Finalizing captured content...")

    finally:
        vid_file.close()
        aud_file.close()

    print(f"\n[*] Capture loop complete. Total segments captured: {len(downloaded_vid_segs)}")
    print("[*] Decrypting and remuxing into single MP4 container via ffmpeg...")

    vid_decrypted = TEMP_DIR / "vid_dec.mp4"
    aud_decrypted = TEMP_DIR / "aud_dec.mp4"

    # Decrypt video
    subprocess.run([
        "ffmpeg", "-y", "-decryption_key", KEY,
        "-i", str(vid_raw_path),
        "-c", "copy", str(vid_decrypted)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Decrypt audio
    subprocess.run([
        "ffmpeg", "-y", "-decryption_key", KEY,
        "-i", str(aud_raw_path),
        "-c", "copy", str(aud_decrypted)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Mux both
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(vid_decrypted),
        "-i", str(aud_decrypted),
        "-c", "copy",
        str(OUTPUT_FILE)
    ], check=True)

    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print("=" * 70)
    print(f"✅ HALFTIME DVR COMPLETE: {OUTPUT_FILE} ({size_mb:.2f} MB)")
    print("=" * 70)

    # Clean up temp raw files to preserve SHM
    for p in [vid_raw_path, aud_raw_path, vid_decrypted, aud_decrypted]:
        if p.exists():
            p.unlink()

if __name__ == "__main__":
    main()

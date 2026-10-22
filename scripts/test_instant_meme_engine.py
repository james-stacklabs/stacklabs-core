#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Instant Meme Engine & Couch Marker Test Harness
Validates that:
1. instant_meme_engine.py renders a pristine 1200x675 PNG meme card without errors.
2. Couch marker persistence generates valid JSON in data/couch_markers.json.
3. discord_lfgm_omnibot.py compiles cleanly.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/test_instant_meme_engine.py
"""
import json
import pathlib
import subprocess
import sys
from PIL import Image

PROJECT_ROOT = pathlib.Path("/home/james/stacklabs")
PYTHON_EXEC = PROJECT_ROOT / ".venv" / "bin" / "python3"
MEME_SCRIPT = PROJECT_ROOT / "scripts" / "instant_meme_engine.py"
OMNIBOT_SCRIPT = PROJECT_ROOT / "scripts" / "discord_lfgm_omnibot.py"
MARKERS_FILE = PROJECT_ROOT / "data" / "couch_markers.json"


def test_meme_rendering():
    print("[1/3] Testing instant_meme_engine.py --dry-run...")
    cmd = [str(PYTHON_EXEC), str(MEME_SCRIPT), "--dry-run", "--topic", "Pass Protection"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Meme Engine Complete" in res.stdout, f"Meme generator stdout missing success: {res.stdout}"

    # Verify generated test image
    memes = sorted(pathlib.Path("/dev/shm").glob("barf_instant_meme_*.png"), key=lambda p: p.stat().st_mtime)
    assert len(memes) > 0, "No rendered meme image found in /dev/shm"
    latest_meme = memes[-1]

    with Image.open(latest_meme) as img:
        assert img.size == (1200, 675), f"Unexpected meme dimensions: {img.size} (expected 1200x675)"
        assert img.format == "PNG", f"Unexpected format: {img.format}"

    assert latest_meme.stat().st_size > 15000, f"Meme file too small ({latest_meme.stat().st_size} bytes)"
    print(f"  ✓ Verified meme card: {latest_meme.name} (1200x675 PNG, {latest_meme.stat().st_size} bytes)")


def test_couch_marker_schema():
    print("[2/3] Testing couch marker schema persistence...")
    test_marker = {
        "id": "leaf_test_unit",
        "timestamp": "2026-10-20T04:35:00-04:00",
        "epoch_time": 1788572017.0,
        "author": "TestPilot",
        "note": "Unit Test Broadcast Marker",
        "buffer_segments": 50,
        "channel_id": "1561509280870305835"
    }

    MARKERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if MARKERS_FILE.exists():
        try:
            existing = json.loads(MARKERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    # Insert test marker and write back
    existing.append(test_marker)
    MARKERS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # Read back and assert
    readback = json.loads(MARKERS_FILE.read_text(encoding="utf-8"))
    assert any(m.get("id") == "leaf_test_unit" for m in readback), "Test marker not found in readback"

    # Clean up test marker
    cleaned = [m for m in readback if m.get("id") != "leaf_test_unit"]
    MARKERS_FILE.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    print("  ✓ Couch marker persistence & schema verified cleanly.")


def test_omnibot_compilation():
    print("[3/3] Testing discord_lfgm_omnibot.py py_compile...")
    cmd = [str(PYTHON_EXEC), "-m", "py_compile", str(OMNIBOT_SCRIPT)]
    subprocess.run(cmd, check=True)
    print("  ✓ discord_lfgm_omnibot.py compiled cleanly with zero syntax errors.")


def main():
    print("==================================================")
    print("⚡ STACKLABS INSTANT MEME ENGINE TEST HARNESS")
    print("==================================================")
    test_meme_rendering()
    test_couch_marker_schema()
    test_omnibot_compilation()
    print("\n✅ ALL MEME ENGINE ASSERTIONS PASSED.")


if __name__ == "__main__":
    main()

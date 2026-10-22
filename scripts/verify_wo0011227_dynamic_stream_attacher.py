#!/usr/bin/env python3
import sys
import json
import urllib.request
from pathlib import Path

def main():
    print("[*] Verifying WO0011227: Dynamic Stream Resolution & Attacher UI...")

    # 1. Test chat tail with cfb_401856809
    url = "http://127.0.0.1:3033/api/stream/chat_tail?limit=5&game_id=cfb_401856809"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert isinstance(data, list), "Expected list response"
            assert len(data) > 0, "Expected live comments for cfb_401856809"
            print(f"[PASS] /api/stream/chat_tail?game_id=cfb_401856809 returned {len(data)} live comments.")
    except Exception as e:
        print(f"[FAIL] {e}")
        sys.exit(1)

    # 2. Check UI code in GameRoom.tsx
    gr_text = Path("/home/james/stacklabs/apps/faas/src/GameRoom.tsx").read_text(encoding="utf-8")
    assert "handleAttachStream" in gr_text, "Missing handleAttachStream in GameRoom.tsx"
    assert "NO LIVE STREAM TAIL ATTACHED YET" in gr_text, "Missing fallback notice in GameRoom.tsx"
    print("[PASS] GameRoom.tsx contains inline stream attacher form.")

    print("\n✅ WO0011227 ALL GATES PASSED!")

if __name__ == "__main__":
    main()

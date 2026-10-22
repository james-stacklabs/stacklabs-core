#!/usr/bin/env python3
import sys
import requests
import sqlite3

def test_cfb_wiretap():
    print("🔍 [TEST 1] Testing /api/stream/chat_tail?game_id=cfb_401856717 ...")
    res = requests.get("http://127.0.0.1:3033/api/stream/chat_tail?limit=35&game_id=cfb_401856717", timeout=5)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert isinstance(data, list), "Expected list output"
    assert len(data) > 0, f"Expected > 0 chat items for Texas vs Oklahoma, got {len(data)}"
    print(f"  ✅ Received {len(data)} live chat items for Texas @ Oklahoma")
    first = data[0]
    print(f"  Sample message: [{first.get('timestamp')}] {first.get('author')}: {first.get('message')}")

    print("\n🔍 [TEST 2] Verifying morning_wiretap.db watch_party_streams has cfb_401856717...")
    conn = sqlite3.connect("/home/james/stacklabs/data/morning_wiretap.db")
    cur = conn.cursor()
    cur.execute("SELECT sport, game_pk, home_team, away_team, stream_id FROM watch_party_streams WHERE game_pk = 'cfb_401856717'")
    row = cur.fetchone()
    conn.close()
    assert row is not None, "Missing cfb_401856717 in watch_party_streams"
    print(f"  ✅ Found mapped stream: {row}")

    print("\n🎉 ALL ASSERTIONS PASSED (WO0011053 VERIFIED)")

if __name__ == "__main__":
    test_cfb_wiretap()

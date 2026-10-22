#!/usr/bin/env python3
"""
Comprehensive Metal Verification for WO0010973: FaaS TNF Rig
Path: /home/james/stacklabs/scripts/verify_tnf_faas_rig.py
"""
import os
import sys
import json
import sqlite3
import urllib.request
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")

def check_url(url: str, timeout: float = 3.0) -> tuple:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ClioPreflight/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return resp.status == 200, data
    except Exception as e:
        return False, str(e)

def main():
    print("=======================================================")
    print("⚡ VERIFYING WO0010973: FAAS TNF BUCS @ COWBOYS RIG")
    print("=======================================================")

    failures = []

    # 1. Verify Symlink and Chat File
    inbox_link = Path("/home/james/sovereign_inbox")
    chat_file = STACKLABS_ROOT / "data" / "stream_chat_tail.md"
    if not inbox_link.exists():
        failures.append("Missing /home/james/sovereign_inbox symlink")
    else:
        print(f"✔ [SYMLINK] /home/james/sovereign_inbox -> {os.readlink(inbox_link)}")

    if not chat_file.exists():
        failures.append(f"Missing {chat_file}")
    else:
        print(f"✔ [CHAT FILE] {chat_file} exists ({chat_file.stat().st_size:,} bytes)")

    # 2. Verify Database Seeding
    society_db = STACKLABS_ROOT / "data" / "emergent_society.db"
    sovereign_db = STACKLABS_ROOT / "dna" / "sovereign_now.db"

    with sqlite3.connect(society_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM emergent_citizens WHERE handle IN ('@the_star_luxury_apologist', '@curtain_conspiracy_dak', '@valley_ranch_purist')")
        cnt = cur.fetchone()[0]
        if cnt != 3:
            failures.append(f"Expected 3 Cowboys citizens in emergent_society.db, found {cnt}")
        else:
            print(f"✔ [SOCIETY] Verified 3 Cowboys citizens in emergent_society.db")

        cur.execute("SELECT count(*) FROM market_contracts WHERE ticker IN ('$DAK-SACKS', '$TRIPP-VAL', '$COOP-GLARE') AND status='OPEN'")
        mkt_cnt = cur.fetchone()[0]
        if mkt_cnt != 3:
            failures.append(f"Expected 3 open TNF contracts, found {mkt_cnt}")
        else:
            print(f"✔ [MARKET] Verified 3 open TNF Predict Exchange contracts")

    with sqlite3.connect(sovereign_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM fan_wallet WHERE user_id IN ('the_star_luxury_apologist', 'curtain_conspiracy_dak', 'valley_ranch_purist') AND balance >= 1000")
        w_cnt = cur.fetchone()[0]
        if w_cnt != 3:
            failures.append(f"Expected 3 Cowboys wallets with >= 1000 credits, found {w_cnt}")
        else:
            print(f"✔ [WALLET] Verified 3 Cowboys fan_wallet accounts with $1,000 bankrolls")

        cur.execute("SELECT count(*) FROM m2m_persona_room WHERE room IN ('20261008_TB_DAL', '401872980')")
        room_cnt = cur.fetchone()[0]
        if room_cnt < 3:
            failures.append(f"Expected >= 3 Cowboys room seatings, found {room_cnt}")
        else:
            print(f"✔ [ROOMS] Verified Cowboys advocates seated in active TNF rooms ({room_cnt} seats)")

    # 3. Verify FaaS Endpoints
    faas_ok, faas_html = check_url("http://127.0.0.1:3033/")
    if not faas_ok:
        failures.append(f"Port 3033 root failed: {faas_html}")
    else:
        print("✔ [PORT 3033] FaaS Server root 200 OK")

    chat_ok, chat_raw = check_url("http://127.0.0.1:3033/api/stream/chat_tail")
    if not chat_ok:
        failures.append(f"Port 3033 /api/stream/chat_tail failed: {chat_raw}")
    else:
        try:
            chat_data = json.loads(chat_raw)
            print(f"✔ [STREAM WIRE] /api/stream/chat_tail 200 OK ({len(chat_data)} comments active)")
        except Exception as e:
            failures.append(f"Invalid JSON from /api/stream/chat_tail: {e}")

    predict_ok, predict_raw = check_url("http://127.0.0.1:3033/api/predict/state")
    if not predict_ok:
        failures.append(f"Port 3033 /api/predict/state failed: {predict_raw}")
    else:
        try:
            p_data = json.loads(predict_raw)
            has_tripp = "the_star_luxury_apologist" in (p_data.get("bankrolls") or p_data.get("advocates_bankrolls") or {})
            has_contracts = any(c.get("ticker") == "$DAK-SACKS" for c in p_data.get("contracts", []))
            if has_tripp and has_contracts:
                print("✔ [PREDICT API] /api/predict/state verified with Cowboys advocates & contracts")
            else:
                failures.append(f"Missing Cowboys advocates or contracts in /api/predict/state")
        except Exception as e:
            failures.append(f"Invalid JSON from /api/predict/state: {e}")

    # 4. Verify Game Recap JSON
    recap_file = STACKLABS_ROOT / "apps" / "faas" / "public" / "FanStack_Live" / "game_recap_live.json"
    if not recap_file.exists():
        failures.append(f"Missing {recap_file}")
    else:
        with open(recap_file, "r") as f:
            recap_json = json.load(f)
            if recap_json.get("active_game_pk") == "20261008_TB_DAL":
                print("✔ [GAME RECAP] active_game_pk verified as 20261008_TB_DAL")
            else:
                failures.append(f"active_game_pk is {recap_json.get('active_game_pk')}, expected 20261008_TB_DAL")

    if failures:
        print("\n❌ VERIFICATION FAILED WITH THE FOLLOWING ERRORS:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print("\n=======================================================")
    print("🏆 ALL 4 PHASES VERIFIED GREEN ON METAL! TNF READY!")
    print("=======================================================")

if __name__ == "__main__":
    main()

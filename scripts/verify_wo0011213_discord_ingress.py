#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011213: Discord Stream Tailer & FaaS Ingress
Path: /home/james/stacklabs/scripts/verify_wo0011213_discord_ingress.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
"""

import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(REPO_ROOT))

from scripts.cfb_slate_omni_resolver import get_wal_connection, sync_lexicon_to_sqlite
from scripts.discord_stream_tailer import (
    ChannelEntityBinding,
    DiscordGatewayStreamTailer,
    register_discord_stream_binding,
    sanitize_discord_text,
)

def test_sanitization_and_token_metrics() -> None:
    raw = "Yo <@!9876543210> <#11223344> <@&556677> <:soaking_Wet:12345> :fire: Provo soaking and quaking right now!! https://example.com"
    clean, norm_low, tokens, count = sanitize_discord_text(raw)
    assert "<@" not in clean and "<#" not in clean and "<:" not in clean, f"Mentions/emojis leaked: {clean}"
    assert "https://" not in clean, f"URL leaked: {clean}"
    assert "soaking" in tokens and "quaking" in tokens, f"Expected trigger tokens missing: {tokens}"
    assert count == len(tokens) and count >= 6, f"Unexpected token count: {count}"
    print("[PASS] 1/4 Discord mention/emoji sanitization & token length computation verified.")

def test_dry_run_cli_zero_db_writes() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "dry_run_test.db"
        cmd = [
            "/home/james/stacklabs/.venv/bin/python3",
            str(REPO_ROOT / "scripts" / "discord_stream_tailer.py"),
            "--channel-id", "1001001001",
            "--attach-game", "ND_BYU",
            "--stream-id", "discord_byu_1001",
            "--db-path", str(tmp_db),
            "--dry-run",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Extract JSON block if burst alert log lines preceded it
        stdout_text = res.stdout.strip()
        json_start = stdout_text.find("{")
        payload = json.loads(stdout_text[json_start:])
        assert payload["status"] == "DRY_RUN_VERIFIED", f"Unexpected dry-run status: {payload}"
        assert payload["db_writes_executed"] == 0, "Dry-run must execute zero DB writes"
        assert payload["unmapped_messages_rejected"] == 3, "Unmapped channels must be rejected"
        assert not tmp_db.exists(), "Dry-run must not create or mutate SQLite DB on disk"
    print("[PASS] 2/4 CLI --dry-run handshake & zero-write invariant verified.")

def test_entity_isolation_and_burst_persistence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "wiretap_isolated.db"
        con = get_wal_connection(test_db)
        try:
            sync_lexicon_to_sqlite(con)
        finally:
            con.close()

        binding_byu = ChannelEntityBinding(
            channel_id="777000111",
            game_id="ND_BYU",
            stream_id="discord_nd_byu_777",
            sport="cfb",
            home_team="BYU",
            away_team="ND",
            stream_title="CougarBoard Discord Live Wire",
        )
        binding_tenn = ChannelEntityBinding(
            channel_id="888000222",
            game_id="ALA_TENN",
            stream_id="discord_ala_tenn_888",
            sport="cfb",
            home_team="TENN",
            away_team="ALA",
            stream_title="VolNation Discord Live Wire",
        )

        register_discord_stream_binding(test_db, binding_byu, is_live=1)
        register_discord_stream_binding(test_db, binding_tenn, is_live=1)

        tailer = DiscordGatewayStreamTailer(
            bindings={
                binding_byu.channel_id: binding_byu,
                binding_tenn.channel_id: binding_tenn,
            },
            db_path=test_db,
            bot_token="mock_verification_bot_token",
            window_seconds=60.0,
            sigma_threshold=4.5,
            dry_run=False,
        )

        # Verify Dual Auth IDENTIFY payload generation
        bot_ident = tailer.build_identify_payload()
        assert bot_ident["op"] == 2 and bot_ident["d"]["intents"] == 37377

        base_ts = time.time()
        queued_msgs = []
        queued_alerts = []

        # 1. Inject 25 baseline messages into ND_BYU
        for i in range(25):
            out = tailer.process_message_create_event(
                {
                    "id": f"byu-base-{i}",
                    "channel_id": "777000111",
                    "author": {"username": f"ProvoFan{i}"},
                    "content": f"Cougars defense holding strong on 3rd down drive {i}",
                    "timestamp": "2026-10-17T18:25:00Z",
                },
                now_epoch=base_ts + i * 0.2,
            )
            if out:
                m, _, a = out
                queued_msgs.append(m)
                queued_alerts.extend(a)

        # 2. Inject 7 BYU shibboleth messages ("soaking" / "quaking") to cross +4.5 sigma
        for i in range(7):
            out = tailer.process_message_create_event(
                {
                    "id": f"byu-spike-{i}",
                    "channel_id": "777000111",
                    "author": {"username": f"HonorCodeWatcher{i}"},
                    "content": f"<@111222> soaking and quaking in Helaman Halls after that touchdown #{i}!",
                    "timestamp": "2026-10-17T18:25:10Z",
                },
                now_epoch=base_ts + 10.0 + i * 0.2,
            )
            if out:
                m, _, a = out
                queued_msgs.append(m)
                queued_alerts.extend(a)

        # 3. Inject 5 unmapped rogue channel messages (must be 100% dropped)
        for i in range(5):
            rogue = tailer.process_message_create_event(
                {
                    "id": f"rogue-{i}",
                    "channel_id": "000000000999",
                    "author": {"username": "UnmappedLeak"},
                    "content": "This message belongs to an unmapped server channel",
                },
                now_epoch=base_ts + 15.0 + i,
            )
            assert rogue is None, "Unmapped channel message leaked through isolation gate!"

        written_m, written_a = tailer.writer.flush_sync(queued_msgs, queued_alerts)
        assert written_m == 32, f"Expected 32 scoped messages written, got {written_m}"
        assert written_a >= 1, f"Expected at least 1 +4.5 sigma burst alert, got {written_a}"
        assert tailer.ignored_unmapped_count == 5, "Expected 5 unmapped messages rejected"

        # 4. Verify SQLite WAL state & entity isolation across ND_BYU vs ALA_TENN vs UNMAPPED
        con = get_wal_connection(test_db)
        try:
            cur = con.cursor()
            byu_rows = cur.execute(
                "SELECT COUNT(*) AS cnt FROM chat_telemetry WHERE channel_key = 'ND_BYU'"
            ).fetchone()["cnt"]
            tenn_rows = cur.execute(
                "SELECT COUNT(*) AS cnt FROM chat_telemetry WHERE channel_key = 'ALA_TENN'"
            ).fetchone()["cnt"]
            rogue_rows = cur.execute(
                "SELECT COUNT(*) AS cnt FROM chat_telemetry WHERE discord_channel_id = '000000000999'"
            ).fetchone()["cnt"]
            burst_row = cur.execute(
                "SELECT shibboleth_id, z_score, hit_count FROM discord_burst_alerts WHERE channel_key = 'ND_BYU' LIMIT 1"
            ).fetchone()

            assert byu_rows == 32, f"Expected 32 ND_BYU rows, got {byu_rows}"
            assert tenn_rows == 0, f"Expected 0 ALA_TENN rows (zero cross-game bleed), got {tenn_rows}"
            assert rogue_rows == 0, f"Expected 0 unmapped rows, got {rogue_rows}"
            assert burst_row is not None and burst_row["shibboleth_id"] == "BYU_SOAKING_QUAKING"
            assert float(burst_row["z_score"]) >= 4.5, f"Expected z_score >= 4.5, got {burst_row['z_score']}"
        finally:
            con.close()

    print("[PASS] 3/4 Strict entity-scoped isolation (Invariant 38) & +4.5σ SQLite WAL burst persistence verified.")

def test_live_wiretap_db_schema_compatibility() -> None:
    live_db = REPO_ROOT / "data" / "morning_wiretap.db"
    con = get_wal_connection(live_db)
    try:
        from scripts.discord_stream_tailer import ensure_wiretap_discord_schemas
        ensure_wiretap_discord_schemas(con)
        cur = con.cursor()
        cols = {r["name"] for r in cur.execute("PRAGMA table_info(chat_telemetry)").fetchall()}
        assert {"id", "channel_key", "stream_id", "author", "message", "timestamp_str", "epoch_time", "token_count", "content_sha256", "discord_channel_id"}.issubset(cols)
        lex_cnt = cur.execute("SELECT COUNT(*) AS c FROM cfb_subcultural_lexicon").fetchone()["c"]
        assert lex_cnt >= 16, f"Expected >= 16 shibboleths in cfb_subcultural_lexicon, found {lex_cnt}"
    finally:
        con.close()
    print("[PASS] 4/4 Live data/morning_wiretap.db WAL schema & 16-program lexicon compatibility verified.")

def main() -> None:
    test_sanitization_and_token_metrics()
    test_dry_run_cli_zero_db_writes()
    test_entity_isolation_and_burst_persistence()
    test_live_wiretap_db_schema_compatibility()
    print("\n=== ALL WO0011213 DISCORD INGRESS & BURST GATE CHECKS PASSED ===")

if __name__ == "__main__":
    main()

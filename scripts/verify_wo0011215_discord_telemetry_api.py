#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011215: Expose Discord Burst Alerts & Supervisor Heartbeat API
Path: /home/james/stacklabs/scripts/verify_wo0011215_discord_telemetry_api.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(REPO_ROOT))

from scripts.blueprints.faas_vfs_telemetry import (
    DB_PATH,
    DISCORD_HEARTBEAT_PATH,
    get_discord_burst_alerts,
    get_discord_supervisor_status,
    get_lexicon_bursts,
    get_pipeline_heartbeat,
)
from scripts.cfb_slate_omni_resolver import get_wal_connection
from scripts.discord_stream_tailer import (
    BurstAlertEvent,
    atomic_write_json,
    compute_merkle_sha256,
    ensure_wiretap_discord_schemas,
)

TEST_ALERT_ID = "burst-wo0011215-verification-byu"
FAAS_PORT = int(os.getenv("FAAS_PORT", "3033"))
FAAS_BASE_URL = os.getenv("FAAS_LOCAL_BASE_URL", f"http://127.0.0.1:{FAAS_PORT}")


def seed_verification_burst() -> None:
    con = get_wal_connection(DB_PATH)
    try:
        ensure_wiretap_discord_schemas(con)
        now_ts = time.time()
        digest = compute_merkle_sha256(
            {
                "alert_id": TEST_ALERT_ID,
                "channel_key": "ND_BYU",
                "shibboleth_id": "BYU_SOAKING_QUAKING",
                "z_score": 6.85,
            }
        )
        alert = BurstAlertEvent(
            alert_id=TEST_ALERT_ID,
            channel_key="ND_BYU",
            stream_id="discord_nd_byu_live",
            channel_id="1296543210987654321",
            shibboleth_id="BYU_SOAKING_QUAKING",
            team_abbrev="BYU",
            ngram_or_token="quaking, soaking",
            hit_count=9,
            window_messages=35,
            window_seconds=60.0,
            velocity_mps=1.75,
            z_score=6.85,
            z_score_threshold=4.5,
            peak_author="CougarBoardCaptain",
            peak_quote="Provo dorm soaking and quaking alert on 4th down!",
            timestamp_str=time.strftime("%H:%M:%S"),
            epoch_time=now_ts,
            content_sha256=digest,
        )
        cur = con.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO discord_burst_alerts (
                alert_id, channel_key, stream_id, channel_id,
                shibboleth_id, team_abbrev, ngram_or_token,
                hit_count, window_messages, window_seconds,
                velocity_mps, z_score, z_score_threshold,
                peak_author, peak_quote, timestamp_str,
                epoch_time, content_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert.alert_id,
                alert.channel_key,
                alert.stream_id,
                alert.channel_id,
                alert.shibboleth_id,
                alert.team_abbrev,
                alert.ngram_or_token,
                alert.hit_count,
                alert.window_messages,
                alert.window_seconds,
                alert.velocity_mps,
                alert.z_score,
                alert.z_score_threshold,
                alert.peak_author,
                alert.peak_quote,
                alert.timestamp_str,
                alert.epoch_time,
                alert.content_sha256,
            ),
        )
        con.commit()

        if not DISCORD_HEARTBEAT_PATH.exists():
            atomic_write_json(
                DISCORD_HEARTBEAT_PATH,
                {
                    "service": "stacklabs-discord-tailer.service",
                    "state": "STANDBY_AWAITING_TOKEN",
                    "auth_mode": "STANDBY_NO_TOKEN",
                    "ttl_seconds": 14400,
                    "active_channel_count": 5,
                    "active_channels": [
                        {
                            "channel_id": "1296543210987654321",
                            "game_id": "ND_BYU",
                            "stream_id": "discord_nd_byu_live",
                            "sport": "cfb",
                            "matchup": "ND @ BYU",
                        }
                    ],
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "epoch_time": now_ts,
                },
            )
    finally:
        con.close()


def cleanup_verification_burst() -> None:
    con = get_wal_connection(DB_PATH)
    try:
        con.execute("DELETE FROM discord_burst_alerts WHERE alert_id = ?", (TEST_ALERT_ID,))
        con.commit()
    finally:
        con.close()


def test_direct_blueprint_handlers() -> None:
    # 1. Scoped lookup for ND_BYU
    res_scoped = get_discord_burst_alerts(channel_key="ND_BYU", min_z_score=4.5, limit=25)
    assert res_scoped["status"] == "ONLINE"
    assert res_scoped["total_alerts"] >= 1
    top = res_scoped["alerts"][0]
    assert top["shibboleth_id"] == "BYU_SOAKING_QUAKING"
    assert top["z_score"] >= 4.5
    assert "CougarBoard.com" in top["primary_board"]
    assert "Provo Honor Code" in top["subcultural_ground_truth"]

    # 2. Strict Entity-Scoped Isolation: unmapped game must return zero alerts from ND_BYU
    res_unmapped = get_discord_burst_alerts(
        channel_key="UNMAPPED_ISOLATION_TEST", min_z_score=4.5, limit=25
    )
    assert res_unmapped["total_alerts"] == 0 and res_unmapped["alerts"] == [], (
        f"Isolation breach! Unmapped game returned: {res_unmapped}"
    )

    # 3. Supervisor status & pipeline heartbeat
    status_payload = get_discord_supervisor_status()
    assert status_payload["status"] == "ONLINE"
    assert status_payload["service_unit"] == "stacklabs-discord-tailer.service"
    assert status_payload["metrics"]["ttl_seconds"] == 14400
    assert status_payload["metrics"]["discord_burst_alerts_rows"] >= 1

    pipe = get_pipeline_heartbeat()
    stage_ids = {s["id"] for s in pipe["stages"]}
    assert "08" in stage_ids, "Stage 08 (DISCORD GATEWAY V10 INGRESS) missing from pipeline_heartbeat"

    # 4. Enriched lexicon bursts payload
    lex_bursts = get_lexicon_bursts(channel_key="ND_BYU", window_messages=2500)
    assert lex_bursts["status"] == "ONLINE"
    assert lex_bursts["discord_burst_alerts_count"] >= 1
    byu_entry = next(x for x in lex_bursts["anomalies"] if x["shibboleth_id"] == "BYU_SOAKING_QUAKING")
    assert byu_entry["is_active_burst"] is True and byu_entry["z_score"] >= 6.85
    print("[PASS] 1/2 Direct FastAPI blueprint handlers & entity-scoped isolation verified.")


def test_live_port_3033_endpoints() -> None:
    try:
        with urllib.request.urlopen(
            f"{FAAS_BASE_URL}/api/faas/lexicon/discord_bursts?channel_key=ND_BYU",
            timeout=5,
        ) as resp:
            data1 = json.loads(resp.read().decode("utf-8"))
        assert data1["status"] == "ONLINE" and data1["total_alerts"] >= 1

        with urllib.request.urlopen(
            f"{FAAS_BASE_URL}/api/faas/lexicon/discord_status",
            timeout=5,
        ) as resp:
            data2 = json.loads(resp.read().decode("utf-8"))
        assert data2["status"] == "ONLINE" and data2["service_unit"] == "stacklabs-discord-tailer.service"
        print("[PASS] 2/2 Live Port 3033 HTTP endpoints (/api/faas/lexicon/discord_bursts & /discord_status) verified.")
    except Exception as exc:
        raise RuntimeError(f"Port 3033 HTTP verification failed: {exc}") from exc


def main() -> None:
    seed_verification_burst()
    try:
        test_direct_blueprint_handlers()
        test_live_port_3033_endpoints()
    finally:
        cleanup_verification_burst()
    print("\n=== ALL WO0011215 PORT 3033 DISCORD BURST & HEARTBEAT API CHECKS PASSED ===")


if __name__ == "__main__":
    main()

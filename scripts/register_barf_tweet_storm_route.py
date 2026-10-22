#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Register Barf Tweet Storm & Dispatch API Route in faas_vfs_telemetry.py
Path: /home/james/stacklabs/scripts/register_barf_tweet_storm_route.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Host: Clio (clio / Dedicated Linux Host / 100.96.77.20)
Governing Standards: Invariant 15, 32 (Law of "I"), 35 (.venv), 50, Argon Laws 1-9
"""

import sys
from pathlib import Path

TARGET_FILE = Path("/home/james/stacklabs/scripts/blueprints/faas_vfs_telemetry.py")

ROUTE_SNIPPET = '''

@router.api_route("/barf_tweet_storm", methods=["GET", "HEAD"])
@router.api_route("/lexicon/barf_tweet_storm", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/barf_tweet_storm", methods=["GET", "HEAD"])
def get_barf_tweet_storm() -> Dict[str, Any]:
    """Returns the latest @BarfFanStack synthesized tweet storm receipt from VFS or SQLite."""
    vfs_file = Path("/dev/shm/vfs/telemetry/barf_latest_tweet_storm.json")
    if vfs_file.exists():
        try:
            return {
                "status": "ONLINE",
                "source": "VFS_FAST_PATH",
                "storm": json.loads(vfs_file.read_text(encoding="utf-8")),
            }
        except (OSError, json.JSONDecodeError):
            pass

    try:
        conn = get_wal_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT storm_id, source_alert_id, channel_key, shibboleth_id, team_abbrev,
                   z_score, velocity_mps, blood_pressure, tums_chewed, discord_blast,
                   tweets_json, content_sha256, dispatched_to_discord, created_at
            FROM barf_tweet_storms
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        row = cur.fetchone()
        if row:
            res = dict(row)
            try:
                res["tweets"] = json.loads(res.pop("tweets_json", "[]"))
            except json.JSONDecodeError:
                res["tweets"] = []
            return {"status": "ONLINE", "source": "SQLITE_PERSISTENCE", "storm": res}
    except Exception as exc:
        return {"status": "ERROR", "detail": str(exc), "storm": None}

    return {"status": "STANDBY", "detail": "No synthesized tweet storm found", "storm": None}


@router.api_route("/barf_dispatch_burst", methods=["POST", "HEAD"])
@router.api_route("/lexicon/barf_dispatch_burst", methods=["POST", "HEAD"])
@faas_lexicon_router.api_route("/barf_dispatch_burst", methods=["POST", "HEAD"])
def post_barf_dispatch_burst(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Triggers on-demand dynamic synthesis and optional Discord dispatch for a burst alert."""
    try:
        from scripts.barf_discord_burst_tweet_synthesizer import (
            seed_canonical_burst_if_empty,
            synthesize_barf_storm,
            ensure_barf_tables,
        )

        conn = get_wal_connection(DB_PATH)
        ensure_barf_tables(conn)
        req = payload or {}
        alert_id = req.get("alert_id")
        dispatch_discord = bool(req.get("dispatch", False))
        channel_id = req.get("channel_id")

        if alert_id:
            cur = conn.cursor()
            cur.execute("SELECT * FROM discord_burst_alerts WHERE alert_id = ? LIMIT 1;", (str(alert_id),))
            row = cur.fetchone()
            alert_row = dict(row) if row else seed_canonical_burst_if_empty(conn)
        else:
            alert_row = seed_canonical_burst_if_empty(conn)

        receipt = synthesize_barf_storm(
            alert_row=alert_row,
            conn=conn,
            dispatch_discord=dispatch_discord,
            target_channel_id=channel_id,
        )
        return {"status": "SUCCESS", "receipt": receipt.to_dict()}
    except Exception as exc:
        return {"status": "ERROR", "detail": str(exc)}
'''


def register_routes() -> None:
    if not TARGET_FILE.exists():
        print(f"ERROR: Target file {TARGET_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    content = TARGET_FILE.read_text(encoding="utf-8")
    if "/barf_tweet_storm" in content:
        print("OK: /barf_tweet_storm route already present in faas_vfs_telemetry.py.")
        return

    updated_content = content.rstrip() + ROUTE_SNIPPET + "\n"
    TARGET_FILE.write_text(updated_content, encoding="utf-8")
    print(f"SUCCESS: Appended Barf tweet storm API routes to {TARGET_FILE}.")


if __name__ == "__main__":
    register_routes()

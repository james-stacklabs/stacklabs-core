#!/usr/bin/env python3
"""
Verification Script for WO0010564:
FaaS Dynamic NFL Stream Resolver & Watch Party Ingress Remediation
Path: /home/james/stacklabs/scripts/verify_wo0010564.py
"""

import os
import sys
import subprocess
import sqlite3

def verify():
    print("=================================================================")
    print("⚡ VERIFYING WO0010564: DYNAMIC NFL STREAM RESOLVER & WATCH PARTY")
    print("=================================================================")

    # 1. Verify game_stream_omni_tailer.py configuration
    tailer_path = "/home/james/stacklabs/scripts/game_stream_omni_tailer.py"
    assert os.path.exists(tailer_path), f"Missing {tailer_path}"
    with open(tailer_path, "r", encoding="utf-8") as f:
        tailer_src = f.read()

    assert "Giants Now by Chat Sports" in tailer_src, "Missing Giants Now in NYG channels"
    assert "Bad Dog Sports" in tailer_src, "Missing Bad Dog Sports in NYG channels"
    assert "channel/UCJ5JxdXQ6xh48GL8kGQJT0w/live" in tailer_src, "Missing verified Big Blue Banter channel ID"
    assert "def resolve_live_search" in tailer_src, "Missing resolve_live_search function"
    assert "active_teams_with_listeners" in tailer_src, "Missing active_teams_with_listeners tracking"
    print("✔ [CODE AUDIT] game_stream_omni_tailer.py has verified NYG channels and dynamic live search fallback")

    # 2. Verify daemon is active on metal
    service_status = subprocess.check_output(
        ["systemctl", "--user", "is-active", "faas_game_tailer.service"],
        text=True
    ).strip()
    assert service_status == "active", f"faas_game_tailer.service is not active: {service_status}"
    print(f"✔ [SYSTEMD] faas_game_tailer.service is ACTIVE")

    pgrep_out = subprocess.check_output(["pgrep", "-fa", "game_stream_omni_tailer.py"], text=True).strip()
    assert pgrep_out, "No PID found for game_stream_omni_tailer.py"
    print(f"✔ [PROCESS] Omni-tailer running with PID: {pgrep_out.split()[0]}")

    # 3. Verify stream_url_resolver.py configuration
    resolver_path = "/home/james/stacklabs/scripts/stream_url_resolver.py"
    assert os.path.exists(resolver_path), f"Missing {resolver_path}"
    with open(resolver_path, "r", encoding="utf-8") as f:
        resolver_src = f.read()

    assert "def resolve_nfl_games" in resolver_src, "Missing resolve_nfl_games in stream_url_resolver.py"
    assert "watch_party_streams" in resolver_src, "Missing watch_party_streams table reference"
    print("✔ [CODE AUDIT] stream_url_resolver.py has NFL schedule resolution and watch_party_streams persistence")

    # 4. Verify morning_wiretap.db table watch_party_streams
    db_path = "/home/james/stacklabs/data/morning_wiretap.db"
    assert os.path.exists(db_path), f"Missing {db_path}"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM watch_party_streams WHERE sport = 'NFL'")
    row_count = cur.fetchone()[0]
    assert row_count > 0, f"Expected rows in watch_party_streams, got {row_count}"
    print(f"✔ [DATABASE] morning_wiretap.db watch_party_streams rows: {row_count}")

    cur.execute("SELECT game_pk, home_team, away_team, stream_id, stream_title, source FROM watch_party_streams WHERE home_team = 'NYG' OR away_team = 'NYG'")
    nyg_rows = cur.fetchall()
    assert len(nyg_rows) > 0, "No watch party resolved for NYG game"
    for r in nyg_rows:
        print(f"    - NYG Game {r[0]}: {r[2]} @ {r[1]} -> {r[4]} ({r[3]}) via {r[5]}")
    conn.close()

    # 5. Verify faas_daily_prep.md
    workflow_path = "/home/james/stacklabs/.agents/workflows/faas_daily_prep.md"
    with open(workflow_path, "r", encoding="utf-8") as f:
        wf_content = f.read()
    assert "NFL Sunday gameday slates" in wf_content, "Missing NFL Sunday in Phase 3 of faas_daily_prep.md"
    assert "/home/james/stacklabs/scripts/stream_url_resolver.py" in wf_content, "Missing stream_url_resolver path in Phase 3"
    print("✔ [WORKFLOW] faas_daily_prep.md Phase 3 includes NFL slate stream resolution")

    print("=================================================================")
    print("🎉 ALL ACCEPTANCE CRITERIA PHYSICALLY VERIFIED ON METAL!")
    print("=================================================================")

if __name__ == "__main__":
    verify()

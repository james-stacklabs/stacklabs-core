#!/usr/bin/env python3
"""
StackLabs CFB Top 25 Slate & Bleacher Wiretap Synchronizer
Path: /home/james/stacklabs/scripts/sync_cfb_top25_ground_truth.py

Reads /dev/shm/vfs/schedule/unified_slate.json, correlates with data/morning_wiretap.db,
and updates /home/james/stacklabs/ground_truth/sports_ground_truth.json.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
GROUND_TRUTH_PATH = STACKLABS_ROOT / "ground_truth" / "sports_ground_truth.json"
VFS_SLATE_PATH = Path("/dev/shm/vfs/schedule/unified_slate.json")
DB_PATH = STACKLABS_ROOT / "data" / "morning_wiretap.db"


def sync_top25_slate():
    if not VFS_SLATE_PATH.exists():
        print(f"[ERROR] VFS slate missing: {VFS_SLATE_PATH}")
        return False

    with open(VFS_SLATE_PATH, "r", encoding="utf-8") as f:
        unified_games = json.load(f)

    streams_by_game = {}
    lexicon_by_team = {}
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            """SELECT game_pk, home_team, away_team, stream_id, stream_title, source, is_live 
               FROM watch_party_streams 
               WHERE sport='cfb' 
               ORDER BY CASE WHEN source = 'youtube' THEN 1 WHEN source LIKE '%discord%' THEN 2 ELSE 3 END, id DESC"""
        )
        for row in c.fetchall():
            game_pk, home, away, sid, title, source, is_live = row
            key = f"{away}_{home}"
            if key not in streams_by_game:
                streams_by_game[key] = {
                    "stream_id": sid,
                    "title": title,
                    "source": source,
                    "is_live": bool(is_live),
                }
            if game_pk and game_pk not in streams_by_game:
                streams_by_game[game_pk] = {
                    "stream_id": sid,
                    "title": title,
                    "source": source,
                    "is_live": bool(is_live),
                }

        c.execute(
            "SELECT team_abbrev, shibboleth_id, trigger_tokens_json FROM cfb_subcultural_lexicon"
        )
        for row in c.fetchall():
            tabbr, shib_id, triggers_json = row
            try:
                tokens = json.loads(triggers_json)
            except Exception:
                tokens = []
            lexicon_by_team[tabbr] = {"shibboleth_id": shib_id, "tokens": tokens}
        conn.close()

    top25_games = []
    marquee_manual_ids = {
        "cfb_401858263",
        "cfb_401856724",
        "cfb_401856719",
        "cfb_401858490",
    }
    for g in unified_games:
        if g.get("sport") != "cfb":
            continue
        away = g.get("away_team", {})
        home = g.get("home_team", {})
        ar = away.get("rank")
        hr = home.get("rank")
        gid = g.get("id", "")
        if ar or hr or gid in marquee_manual_ids:
            raw_id = gid.replace("cfb_", "")
            ac = away.get("code", "")
            hc = home.get("code", "")

            wt = (
                streams_by_game.get(gid)
                or streams_by_game.get(raw_id)
                or streams_by_game.get(f"{ac}_{hc}")
                or streams_by_game.get(f"{hc}_{ac}")
            )

            shib_away = lexicon_by_team.get(ac)
            shib_home = lexicon_by_team.get(hc)

            is_upset = False
            upset_note = ""
            status = g.get("status", "")
            ascore = away.get("score", 0)
            hscore = home.get("score", 0)
            if status == "FINAL":
                if ar and hr:
                    if ar > hr and ascore > hscore:
                        is_upset = True
                        upset_note = f"UPSET: #{ar} {away.get('full_name')} defeats #{hr} {home.get('full_name')}"
                    elif hr > ar and hscore > ascore:
                        is_upset = True
                        upset_note = f"UPSET: #{hr} {home.get('full_name')} defeats #{ar} {away.get('full_name')}"
                elif ar and not hr and hscore > ascore:
                    is_upset = True
                    upset_note = f"UPSET: Unranked {home.get('full_name')} stuns #{ar} {away.get('full_name')}"
                elif hr and not ar and ascore > hscore:
                    is_upset = True
                    upset_note = f"UPSET: Unranked {away.get('full_name')} stuns #{hr} {home.get('full_name')}"

            entry = {
                "game_id": gid,
                "status": status,
                "status_detail": g.get("status_detail", ""),
                "away_team": {
                    "code": ac,
                    "full_name": away.get("full_name", ""),
                    "score": ascore,
                    "rank": ar,
                    "shibboleth": shib_away,
                },
                "home_team": {
                    "code": hc,
                    "full_name": home.get("full_name", ""),
                    "score": hscore,
                    "rank": hr,
                    "shibboleth": shib_home,
                },
                "venue": g.get("venue", {}).get("venue_name", ""),
                "wiretap": wt,
                "is_upset": is_upset,
                "upset_note": upset_note,
            }
            top25_games.append(entry)

    def sort_key(item):
        s = item.get("status")
        if s == "LIVE":
            return (0, item.get("game_id"))
        elif s == "SCHEDULED":
            return (1, item.get("game_id"))
        return (2, item.get("game_id"))

    top25_games.sort(key=sort_key)

    data = {}
    if GROUND_TRUTH_PATH.exists():
        with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    data["cfb_top25_slate_20261017"] = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT"),
        "total_ranked_matchups": len(top25_games),
        "games": top25_games,
    }

    with open(GROUND_TRUTH_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"[OK] Synced {len(top25_games)} CFB Top 25 games to {GROUND_TRUTH_PATH.name}")
    return True


if __name__ == "__main__":
    sync_top25_slate()

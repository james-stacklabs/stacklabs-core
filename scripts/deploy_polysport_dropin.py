#!/home/james/stacklabs/.venv/bin/python3
"""
Deployment script for WO0011175: PolySport Slate & Telemetry Normalizer.
Installs validated drop-in artifacts from pilot_drops/downloads/ into active tree.
"""

import shutil
import pathlib

DOWNLOADS = pathlib.Path("/home/james/stacklabs/pilot_drops/downloads")
SCRIPTS_DIR = pathlib.Path("/home/james/stacklabs/scripts")
FAAS_SRC = pathlib.Path("/home/james/stacklabs/apps/faas/src")

def deploy() -> None:
    print("[WO0011175] Starting PolySport drop-in deployment...")

    # 1. Install sync_polysport_schedule.py
    src_sync = DOWNLOADS / "sync_polysport_schedule.py"
    dst_sync = SCRIPTS_DIR / "sync_polysport_schedule.py"
    shutil.copy2(src_sync, dst_sync)
    dst_sync.chmod(0o755)
    print(f"  ✔ Deployed {dst_sync}")

    # 2. Install faas_server.py
    src_server = DOWNLOADS / "faas_server (2).py"
    if not src_server.exists():
        src_server = DOWNLOADS / "faas_server (1).py"
    dst_server = SCRIPTS_DIR / "faas_server.py"
    shutil.copy2(src_server, dst_server)
    dst_server.chmod(0o755)
    print(f"  ✔ Deployed {dst_server}")

    # 3. Install types.ts with backward-compatible legacy ribbon accessors
    src_types = DOWNLOADS / "types (1).ts"
    if not src_types.exists():
        src_types = DOWNLOADS / "types.ts"
    dst_types = FAAS_SRC / "types.ts"
    types_content = src_types.read_text(encoding="utf-8")

    types_content = types_content.replace(
        "export type FanStackSport = 'mlb' | 'nfl' | 'cfb';",
        "export type FanStackSport = 'mlb' | 'nfl' | 'cfb' | 'chat';"
    )
    types_content = types_content.replace(
        "export type FanStackGameStatus = 'SCHEDULED' | 'WARMUP' | 'LIVE' | 'FINAL' | 'POSTPONED';",
        "export type FanStackGameStatus = 'SCHEDULED' | 'WARMUP' | 'LIVE' | 'FINAL' | 'POSTPONED' | 'UPCOMING' | 'PRE-GAME';"
    )

    # Ensure legacy accessor aliases exist on FanStackGameEvent for SlateSwitcherRibbon
    if "awayTeam?:" not in types_content:
        types_content = types_content.replace(
            "  timestamps: FanStackTimestamps;\n}",
            "  timestamps: FanStackTimestamps;\n  // Legacy Ribbon Compatibility\n  awayTeam?: string;\n  homeTeam?: string;\n  awayScore?: number;\n  homeScore?: number;\n  isLive?: boolean;\n  statusDetail?: string;\n  gameTime?: string;\n  venueInfo?: {\n    name: string;\n    city: string;\n    state: string;\n    zipCode?: string;\n    roof?: string;\n    surface?: string;\n  };\n}"
        )
    dst_types.write_text(types_content, encoding="utf-8")
    print(f"  ✔ Deployed {dst_types}")

    # 4. Install GameRoom.tsx
    src_gameroom = DOWNLOADS / "gameroom (1).tsx"
    if not src_gameroom.exists():
        src_gameroom = DOWNLOADS / "gameroom.tsx"
    dst_gameroom = FAAS_SRC / "GameRoom.tsx"
    shutil.copy2(src_gameroom, dst_gameroom)
    print(f"  ✔ Deployed {dst_gameroom}")

    # 5. Install TheaterDeck.tsx with relative import fix ('../types')
    src_theater = DOWNLOADS / "theaterdeck.tsx"
    dst_theater = FAAS_SRC / "components" / "TheaterDeck.tsx"
    theater_content = src_theater.read_text(encoding="utf-8")
    theater_content = theater_content.replace("from './types';", "from '../types';")
    dst_theater.write_text(theater_content, encoding="utf-8")
    print(f"  ✔ Deployed {dst_theater}")

    # 6. Patch SlateSwitcherRibbon.tsx to handle polymorphic away_team / awayTeam & canonical fields
    ribbon_path = FAAS_SRC / "components" / "SlateSwitcherRibbon.tsx"
    ribbon_content = ribbon_path.read_text(encoding="utf-8")

    old_snippet = "const hasScore =\n            !isUpcoming &&\n            game.awayScore !== undefined &&\n            game.homeScore !== undefined;"
    new_snippet = "const hasScore =\n            !isUpcoming &&\n            ((game.awayScore !== undefined && game.homeScore !== undefined) ||\n             (game.away_team?.score !== undefined && game.home_team?.score !== undefined));"

    if old_snippet in ribbon_content:
        ribbon_content = ribbon_content.replace(old_snippet, new_snippet)

    ribbon_content = ribbon_content.replace(
        "game.status === 'UPCOMING' ||\n            game.status === 'SCHEDULED' ||\n            game.status === 'PRE-GAME';",
        "game.status === 'UPCOMING' ||\n            game.status === 'SCHEDULED' ||\n            game.status === 'WARMUP' ||\n            game.status === 'PRE-GAME';"
    )
    if "(game.away_team?.code || game.awayTeam)" not in ribbon_content:
        ribbon_content = ribbon_content.replace(
            "game.awayTeam",
            "(game.away_team?.code || game.awayTeam)"
        )
    if "(game.home_team?.code || game.homeTeam)" not in ribbon_content:
        ribbon_content = ribbon_content.replace(
            "game.homeTeam",
            "(game.home_team?.code || game.homeTeam)"
        )
    if "(game.away_team?.score ?? game.awayScore)" not in ribbon_content:
        ribbon_content = ribbon_content.replace(
            "{game.awayScore} - {game.homeScore}",
            "{game.away_team?.score ?? game.awayScore} - {game.home_team?.score ?? game.homeScore}"
        )
    if "(game.status === 'LIVE' || game.isLive)" not in ribbon_content:
        ribbon_content = ribbon_content.replace(
            "game.isLive",
            "(game.status === 'LIVE' || game.isLive)"
        )
    if "(game.status_detail || game.statusDetail" not in ribbon_content:
        ribbon_content = ribbon_content.replace(
            "game.statusDetail || 'LIVE'",
            "game.status_detail || game.statusDetail || 'LIVE'"
        )
        ribbon_content = ribbon_content.replace(
            "game.statusDetail || 'SCHEDULED'",
            "game.status_detail || game.statusDetail || 'SCHEDULED'"
        )
    ribbon_path.write_text(ribbon_content, encoding="utf-8")
    print(f"  ✔ Patched polymorphic accessors in {ribbon_path}")

    print("[WO0011175] All drop-in artifacts successfully placed.")

if __name__ == "__main__":
    deploy()

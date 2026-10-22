#!/usr/bin/env python3
"""
Verification Script for WO0011045: FaaS GameRoom Scoreboard Typography & Line Score Hero
"""
import sys
from pathlib import Path

FAAS_DIR = Path("/home/james/stacklabs/apps/faas")
NFL_TABLE = FAAS_DIR / "src" / "components" / "NflLineScoreTable.tsx"
SLATE_RIBBON = FAAS_DIR / "src" / "components" / "SlateSwitcherRibbon.tsx"
GAME_ROOM = FAAS_DIR / "src" / "GameRoom.tsx"

def test_nfl_line_score_table():
    assert NFL_TABLE.exists(), f"Missing {NFL_TABLE}"
    content = NFL_TABLE.read_text(encoding="utf-8")
    assert "awayScore?:" in content, "awayScore prop missing from interface"
    assert "homeScore?:" in content, "homeScore prop missing from interface"
    assert "text-2xl sm:text-4xl" in content or "text-3xl" in content, "Large score typography missing"
    assert "finalAwayTotal" in content, "Total column calculation missing"
    assert "tabular-nums" in content, "tabular-nums missing from score display"
    print("✅ NflLineScoreTable.tsx verified with high-contrast scoreboard hero.")

def test_slate_switcher_ribbon():
    assert SLATE_RIBBON.exists(), f"Missing {SLATE_RIBBON}"
    content = SLATE_RIBBON.read_text(encoding="utf-8")
    assert "text-amber-300" in content, "Amber high-contrast score text missing from game pills"
    assert "tabular-nums" in content, "tabular-nums missing from slate ribbon"
    print("✅ SlateSwitcherRibbon.tsx verified with high-visibility score pills.")

def test_game_room():
    assert GAME_ROOM.exists(), f"Missing {GAME_ROOM}"
    content = GAME_ROOM.read_text(encoding="utf-8")
    assert "hasLiveFootballActivity" in content, "hasLiveFootballActivity check missing"
    assert "awayScore={awayScore}" in content, "awayScore prop not passed to NflLineScoreTable"
    assert "homeScore={homeScore}" in content, "homeScore prop not passed to NflLineScoreTable"
    print("✅ GameRoom.tsx verified with live status resolution and score props.")

if __name__ == "__main__":
    try:
        test_nfl_line_score_table()
        test_slate_switcher_ribbon()
        test_game_room()
        print("🎉 ALL WO0011045 CODE VERIFICATIONS PASSED ON METAL!")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

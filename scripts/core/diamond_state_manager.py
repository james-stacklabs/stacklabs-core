#!/usr/bin/env python3
"""
Sovereign OS: "Who's on First?" Spatial Diamond State Engine
Path: /home/james/stacklabs/scripts/core/diamond_state_manager.py
Initiative: STRY0010009-SELF-SOVEREIGN-ADVOCATE-INTELLIGENCE-INITIATIVE

Maintains deterministic, real-time spatial ground truth of baseball bases (1B, 2B, 3B),
counts (balls, strikes, outs), at-bat sequencing, and situational leverage from live Statcast telemetry.
Provides disambiguated slot mapping for the Offline Historical Corpus Reaction Engine.
"""

import logging
import sqlite3
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger("DiamondStateManager")
DB_PATH = Path("/home/james/stacklabs/dna/sovereign_now.db")

# Mononym / Fan-preferred name exceptions
MONONYM_MAP = {
    "pete crow-armstrong": "PCA",
    "shohei ohtani": "Shohei",
    "francisco lindor": "Lindor",
    "pete alonso": "Pete",
    "brandon nimmo": "Nimmo",
    "edwin diaz": "Sugar Díaz",
    "mookie betts": "Mookie",
    "freddie freeman": "Freddie",
    "fernando tatis jr.": "Tatis",
    "manny machado": "Machado",
    "bryce harper": "Harper",
    "kyle schwarber": "Schwarber",
    "aaron judge": "Judge",
    "juan soto": "Soto",
    "paul goldschmidt": "Goldy",
    "nolan arenado": "Nolan",
}

def clean_player_name(raw_name: Optional[str], default_role: str = "player") -> str:
    """Normalize full census name to fan vernacular mononym / recognized nickname."""
    if not raw_name or str(raw_name).strip().lower() in ("none", "null", ""):
        return default_role
    clean = str(raw_name).strip()
    low = clean.lower()
    return MONONYM_MAP.get(low, clean)

@dataclass
class BaseRunner:
    name: str
    player_id: Optional[int] = None
    speed_rating: float = 27.0  # ft/s Statcast sprint speed default
    reached_via: str = "hit"
    inning_reached: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": clean_player_name(self.name),
            "player_id": self.player_id,
            "speed_rating": self.speed_rating,
            "reached_via": self.reached_via,
            "inning_reached": self.inning_reached
        }

@dataclass
class DiamondState:
    game_pk: str
    inning: int = 1
    inning_half: str = "top"  # "top" or "bottom"
    outs: int = 0
    balls: int = 0
    strikes: int = 0
    pitch_count: int = 0
    
    first_base: Optional[BaseRunner] = None
    second_base: Optional[BaseRunner] = None
    third_base: Optional[BaseRunner] = None
    
    current_batter: Optional[str] = None
    current_pitcher: Optional[str] = None
    on_deck: Optional[str] = None
    in_the_hole: Optional[str] = None
    
    home_team: str = "HOME"
    away_team: str = "AWAY"
    home_score: int = 0
    away_score: int = 0
    venue: str = "Ballpark"
    last_event: str = "init"
    last_description: str = ""

    @property
    def batting_team(self) -> str:
        return self.away_team if self.inning_half.lower() == "top" else self.home_team

    @property
    def fielding_team(self) -> str:
        return self.home_team if self.inning_half.lower() == "top" else self.away_team

    @property
    def bases_loaded(self) -> bool:
        return bool(self.first_base and self.second_base and self.third_base)

    @property
    def runners_in_scoring_position(self) -> bool:
        return bool(self.second_base or self.third_base)

    @property
    def double_play_in_order(self) -> bool:
        return bool(self.first_base and self.outs < 2)

    @property
    def clutch_leverage(self) -> bool:
        """High leverage: 7th inning or later, score differential <= 2."""
        return self.inning >= 7 and abs(self.home_score - self.away_score) <= 2

    @property
    def runner_count(self) -> int:
        return sum(1 for b in (self.first_base, self.second_base, self.third_base) if b is not None)

    def get_score_context_for_team(self, persona_team: str) -> str:
        """Calculate whether the persona's team is leading, trailing, or tied."""
        p_team = persona_team.upper()
        if p_team == self.home_team.upper():
            diff = self.home_score - self.away_score
        elif p_team == self.away_team.upper():
            diff = self.away_score - self.home_score
        else:
            diff = 0  # Neutral faction
        
        if diff > 0:
            return "leading"
        elif diff < 0:
            return "trailing"
        return "tied"

    def to_ascii_diamond(self) -> str:
        """Render a clean ASCII HUD visual representation of the diamond."""
        b1 = "●" if self.first_base else "○"
        b2 = "●" if self.second_base else "○"
        b3 = "●" if self.third_base else "○"
        return f"""
           [{b2}]
          /   \\
        [{b3}]   [{b1}]
          \\   /
           [H]
        Outs: {self.outs} | Count: {self.balls}-{self.strikes}
        1B: {self.first_base.name if self.first_base else 'Empty'}
        2B: {self.second_base.name if self.second_base else 'Empty'}
        3B: {self.third_base.name if self.third_base else 'Empty'}
        """

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_pk": self.game_pk,
            "inning": self.inning,
            "inning_half": self.inning_half,
            "outs": self.outs,
            "balls": self.balls,
            "strikes": self.strikes,
            "pitch_count": self.pitch_count,
            "batting_team": self.batting_team,
            "fielding_team": self.fielding_team,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "venue": self.venue,
            "first_base": self.first_base.to_dict() if self.first_base else None,
            "second_base": self.second_base.to_dict() if self.second_base else None,
            "third_base": self.third_base.to_dict() if self.third_base else None,
            "current_batter": clean_player_name(self.current_batter),
            "current_pitcher": clean_player_name(self.current_pitcher),
            "on_deck": clean_player_name(self.on_deck) if self.on_deck else "On Deck",
            "in_the_hole": clean_player_name(self.in_the_hole) if self.in_the_hole else "In The Hole",
            "bases_loaded": self.bases_loaded,
            "risp": self.runners_in_scoring_position,
            "double_play_in_order": self.double_play_in_order,
            "clutch_leverage": self.clutch_leverage,
            "runner_count": self.runner_count,
            "last_event": self.last_event,
            "last_description": self.last_description,
            "ascii_diamond": self.to_ascii_diamond()
        }

    def get_slot_replacements(self, persona_team: str = "GLOBAL") -> Dict[str, str]:
        """
        Generate strict, disambiguated template replacements based on team perspective.
        Eliminates 'Edible Freddie' multi-slot bugs and enemy-cheering perspective drift.
        """
        p_team = (persona_team or "GLOBAL").upper()
        batting_now = self.batting_team.upper()
        is_batting_team = (p_team == batting_now)
        
        # Natural baseball syntax fallbacks when names are unpopulated
        batter = clean_player_name(self.current_batter, "the batter")
        pitcher = clean_player_name(self.current_pitcher, "the pitcher")
        
        # Disambiguated ally vs opponent bindings
        if is_batting_team:
            ally_batter = clean_player_name(self.current_batter, "our hitter")
            opp_batter = "the opposing hitter"
            ally_pitcher = "our starter"
            opp_pitcher = clean_player_name(self.current_pitcher, "the opposing starter")
        else:
            ally_batter = "our lineup"
            opp_batter = clean_player_name(self.current_batter, "the opposing hitter")
            ally_pitcher = clean_player_name(self.current_pitcher, "our starter")
            opp_pitcher = "the opposing starter"

        r1 = clean_player_name(self.first_base.name, "runner on first") if self.first_base else "nobody on first"
        r2 = clean_player_name(self.second_base.name, "runner on second") if self.second_base else "nobody on second"
        r3 = clean_player_name(self.third_base.name, "runner on third") if self.third_base else "nobody on third"
        on_deck = clean_player_name(self.on_deck, "the on-deck hitter") if self.on_deck else "the on-deck hitter"
        in_hole = clean_player_name(self.in_the_hole, "in the hole") if self.in_the_hole else "in the hole"

        count_str = f"{self.balls}-{self.strikes}"
        if self.balls == 3 and self.strikes == 2:
            count_verbal = "full count"
        elif self.strikes == 2 and self.balls == 0:
            count_verbal = "0-2 hole"
        else:
            count_verbal = f"{self.balls} and {self.strikes}"

        outs_verbal = "no outs" if self.outs == 0 else ("one down" if self.outs == 1 else "two outs")
        inning_display = f"{self.inning_half.capitalize()} of the {self.inning}"
        score_context = self.get_score_context_for_team(p_team)

        def _to_possessive(name: str) -> str:
            if not name:
                return "the pitcher's"
            clean = name.strip()
            if clean.endswith("'s") or clean.endswith("’s"):
                return clean
            if clean.endswith("s") or clean.endswith("S") or clean.endswith("'") or clean.endswith("’"):
                return f"{clean}'"
            return f"{clean}'s"

        our_guy = ally_batter if is_batting_team else ally_pitcher
        return {
            # Explicit possessive slots first
            "{PITCHER}'s": _to_possessive(pitcher),
            "{pitcher}'s": _to_possessive(pitcher),
            "{OPPONENT_PITCHER}'s": _to_possessive(opp_pitcher),
            "{ALLY_PITCHER}'s": _to_possessive(ally_pitcher),
            "{BATTER}'s": _to_possessive(batter),
            "{batter}'s": _to_possessive(batter),
            "{OPPONENT_BATTER}'s": _to_possessive(opp_batter),
            "{ALLY_BATTER}'s": _to_possessive(ally_batter),
            "{our guy}'s": _to_possessive(our_guy),
            "{their guy}'s": _to_possessive(opp_batter),

            # Base player slots
            "{BATTER}": batter,
            "{ALLY_BATTER}": ally_batter,
            "{OPPONENT_BATTER}": opp_batter,
            "{PITCHER}": pitcher,
            "{ALLY_PITCHER}": ally_pitcher,
            "{OPPONENT_PITCHER}": opp_pitcher,
            "{our guy}": our_guy,
            "{OUR GUY}": our_guy,
            "{their guy}": opp_batter,
            "{THEIR GUY}": opp_batter,
            "{batter}": batter,
            "{pitcher}": pitcher,
            "{RUNNER_1B}": r1,
            "{RUNNER_2B}": r2,
            "{RUNNER_3B}": r3,
            "{ON_DECK}": on_deck,
            "{IN_THE_HOLE}": in_hole,
            "{COUNT}": count_str,
            "{COUNT_VERBAL}": count_verbal,
            "{OUTS}": str(self.outs),
            "{OUTS_VERBAL}": outs_verbal,
            "{INNING}": str(self.inning),
            "{INNING_HALF}": self.inning_half,
            "{INNING_DISPLAY}": inning_display,
            "{SCORE}": f"{self.away_score}-{self.home_score}",
            "{SCORE_CONTEXT}": score_context,
            "{VENUE}": self.venue,
            "{BATTING_TEAM}": self.batting_team,
            "{FIELDING_TEAM}": self.fielding_team,
            "{HOME_TEAM}": self.home_team,
            "{AWAY_TEAM}": self.away_team
        }

class DiamondStateManager:
    """Singleton engine maintaining real-time DiamondState across all active game rooms."""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DiamondStateManager, cls).__new__(cls)
            cls._instance._games: Dict[str, DiamondState] = {}
        return cls._instance

    def get_or_create(self, game_pk: str, home_team: str = "HOME", away_team: str = "AWAY", venue: str = "Ballpark") -> DiamondState:
        g_key = str(game_pk)
        if g_key not in self._games:
            self._games[g_key] = DiamondState(
                game_pk=g_key,
                home_team=home_team,
                away_team=away_team,
                venue=venue
            )
            # Try to load existing state from DB
            self.load_from_db(g_key)
        return self._games[g_key]

    def load_from_db(self, game_pk: str) -> Optional[DiamondState]:
        try:
            conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT game_pk, home_team, away_team, venue
                FROM mlb_schedule
                WHERE game_pk = ?
            """, (str(game_pk),)).fetchone()
            conn.close()
            
            if row:
                state = self._games.setdefault(str(game_pk), DiamondState(game_pk=str(game_pk)))
                state.home_team = row["home_team"] or state.home_team
                state.away_team = row["away_team"] or state.away_team
                state.venue = row["venue"] or state.venue
                return state
        except Exception as e:
            logger.warning("Could not load diamond state for game %s: %s", game_pk, e)
        return None

    def process_statcast_event(self, game_pk: str, event_payload: Dict[str, Any]) -> DiamondState:
        """
        State Machine Transition: Ingest a raw Statcast pitch/play telemetry event and advance diamond state.
        """
        state = self.get_or_create(game_pk)
        
        # Ingest pitch-level metadata
        p_name = event_payload.get("pitcher_name") or event_payload.get("pitcher")
        if p_name:
            state.current_pitcher = p_name

        b_name = event_payload.get("batter_name") or event_payload.get("batter")
        # In Statcast telemetry, 'player_name' is frequently the pitcher. Never treat player_name as batter if it matches pitcher!
        if not b_name:
            cand = event_payload.get("player_name")
            if cand and cand != state.current_pitcher and cand != p_name:
                b_name = cand
        if b_name:
            state.current_batter = b_name

        # Critical Invariant: Modern MLB DH rule — batter can never be the current pitcher
        if state.current_batter and state.current_pitcher and state.current_batter.strip().lower() == state.current_pitcher.strip().lower():
            state.current_batter = "the batter"
        state.on_deck = event_payload.get("on_deck") or state.on_deck
        state.in_the_hole = event_payload.get("in_the_hole") or state.in_the_hole

        # Ingest game state if present
        if event_payload.get("home_team"): state.home_team = event_payload["home_team"]
        if event_payload.get("away_team"): state.away_team = event_payload["away_team"]
        if "home_score" in event_payload and event_payload["home_score"] is not None:
            try: state.home_score = int(event_payload["home_score"])
            except (ValueError, TypeError): pass
        if "away_score" in event_payload and event_payload["away_score"] is not None:
            try: state.away_score = int(event_payload["away_score"])
            except (ValueError, TypeError): pass
        if event_payload.get("inning"):
            try: state.inning = int(event_payload["inning"])
            except (ValueError, TypeError): pass
        if event_payload.get("half_inning") or event_payload.get("inning_half"):
            state.inning_half = str(event_payload.get("half_inning") or event_payload.get("inning_half") or "top").lower()
        
        event_type = (event_payload.get("event") or event_payload.get("event_type") or "").lower().strip()
        desc = event_payload.get("description") or event_payload.get("des") or ""
        state.last_event = event_type or "pitch"
        state.last_description = desc
        
        # Update balls/strikes
        if "balls" in event_payload and event_payload["balls"] is not None:
            state.balls = int(event_payload["balls"])
        if "strikes" in event_payload and event_payload["strikes"] is not None:
            state.strikes = int(event_payload["strikes"])
        if "outs" in event_payload and event_payload["outs"] is not None:
            state.outs = int(event_payload["outs"])

        runner_name = state.current_batter or "the batter"
        if state.current_pitcher and runner_name.strip().lower() == state.current_pitcher.strip().lower():
            runner_name = "the runner"
        batter_runner = BaseRunner(name=runner_name, inning_reached=state.inning, reached_via=event_type)

        # -------------------------------------------------------------
        # EVENT TRANSITIONS
        # -------------------------------------------------------------
        if event_type in ("single", "hit"):
            # Advance runners: 2B & 3B score, 1B to 3B or 2B
            state.third_base = state.first_base
            state.second_base = None
            state.first_base = batter_runner
            state.balls, state.strikes = 0, 0
            
        elif event_type == "double":
            # All runners score, batter to 2B
            state.third_base = None
            state.second_base = batter_runner
            state.first_base = None
            state.balls, state.strikes = 0, 0
            
        elif event_type == "triple":
            # All runners score, batter to 3B
            state.third_base = batter_runner
            state.second_base = None
            state.first_base = None
            state.balls, state.strikes = 0, 0
            
        elif event_type in ("home_run", "homer"):
            # Bases cleared, run scores
            state.first_base = None
            state.second_base = None
            state.third_base = None
            state.balls, state.strikes = 0, 0
            if state.inning_half == "top":
                state.away_score += 1 + state.runner_count
            else:
                state.home_score += 1 + state.runner_count
                
        elif event_type in ("walk", "intent_walk", "hit_by_pitch"):
            # Force advancement
            if state.first_base and state.second_base and state.third_base:
                # Bases loaded walk: run scores
                if state.inning_half == "top": state.away_score += 1
                else: state.home_score += 1
            elif state.first_base and state.second_base:
                state.third_base = state.second_base
                state.second_base = state.first_base
            elif state.first_base:
                state.second_base = state.first_base
            state.first_base = batter_runner
            state.balls, state.strikes = 0, 0
            
        elif event_type in ("strikeout", "strikeout_looking", "strikeout_swinging"):
            state.outs = min(3, state.outs + 1)
            state.balls, state.strikes = 0, 0
            
        elif event_type in ("double_play", "grounded_into_double_play"):
            state.outs = min(3, state.outs + 2)
            state.first_base = None  # Force at 2nd and 1st
            state.balls, state.strikes = 0, 0
            
        elif event_type in ("field_out", "flyout", "groundout", "pop_out", "lineout"):
            state.outs = min(3, state.outs + 1)
            state.balls, state.strikes = 0, 0
            
        elif event_type == "stolen_base":
            # Advance lead runner
            if state.second_base and not state.third_base:
                state.third_base = state.second_base
                state.second_base = None
            elif state.first_base and not state.second_base:
                state.second_base = state.first_base
                state.first_base = None

        # Check for 3 outs -> Inning switch
        if state.outs >= 3:
            state.outs = 0
            state.balls = 0
            state.strikes = 0
            state.first_base = None
            state.second_base = None
            state.third_base = None
            if state.inning_half.lower() == "top":
                state.inning_half = "bottom"
            else:
                state.inning_half = "top"
                state.inning += 1

        return state

# Singleton Global Accessor
diamond_engine = DiamondStateManager()

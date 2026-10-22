#!/usr/bin/env python3
"""
Offline Historical Corpus Advocate Reaction Engine
Ticket: ENHC0010008-OFFLINE-HISTORICAL-CORPUS-ADVOCATE-ENGINE

Provides zero-cost, sub-10ms authentic persona reactions to live Statcast telemetry
by querying the 124,000+ indexed historical reaction templates in dim_persona_corpus_reactions
and dynamically slot-filling live player, velocity, distance, and game context tokens.
"""

import collections
import json
import logging
import os
import random
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logging.basicConfig(level=logging.INFO, format="[OFFLINE CORPUS] %(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("OfflineCorpusEngine")

DB_PATH = Path("/home/james/stacklabs/dna/sovereign_now.db")

STATCAST_EVENT_MAP = {
    "home_run": "home_run",
    "homer": "home_run",
    "strikeout": "strikeout",
    "strikeout_looking": "strikeout",
    "strikeout_swinging": "strikeout",
    "double_play": "double_play",
    "grounded_into_double_play": "double_play",
    "walk": "walk",
    "intent_walk": "walk",
    "single": "hit",
    "double": "hit",
    "triple": "hit",
    "hit": "hit",
    "stolen_base": "stolen_base",
    "wild_pitch": "bad_call",
    "passed_ball": "bad_call",
    "blown_save": "blown_save",
    "foul": "foul",
    "foul_tip": "foul",
    "foul_bunt": "foul",
    "ball": "ball",
    "blocked_ball": "ball",
    "pitchout": "ball",
    "called_strike": "strike",
    "swinging_strike": "strike",
    "swinging_strike_blocked": "strike",
    "pop_out": "flyout",
    "flyout": "flyout",
    "lineout": "lineout",
    "groundout": "groundout",
    "force_out": "force_out",
}

class OfflineCorpusEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(OfflineCorpusEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[Path] = None):
        if self._initialized:
            return
        self.db_path = db_path or DB_PATH
        # Anti-repetition LRU: (room_id, persona) -> deque of recent template IDs (max 30)
        self.recent_history: Dict[Tuple[str, str], collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=30))
        self._persona_teams: Dict[str, str] = {}
        self._load_persona_cache()
        self._initialized = True
        logger.info("OfflineCorpusEngine initialized against %s", self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_persona_cache(self):
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                for r in cur.execute("SELECT user_name, team FROM persona"):
                    u_name = str(r["user_name"]).lower().strip()
                    t_name = str(r["team"]).upper().strip() if r["team"] else "GLOBAL"
                    self._persona_teams[u_name] = t_name
            logger.info("Cached %d personas for offline routing.", len(self._persona_teams))
        except Exception as e:
            logger.warning("Could not load persona cache from DB: %s", e)

    def map_event_category(self, event_type: Optional[str], play_payload: Optional[Dict[str, Any]] = None) -> str:
        if not event_type:
            return "banter"
        
        evt = str(event_type).lower().strip()
        mapped = STATCAST_EVENT_MAP.get(evt)
        if mapped:
            return mapped

        # Check pitch velocity threshold (>= 99.5 mph)
        if play_payload:
            velo = play_payload.get("pitch_speed") or play_payload.get("start_speed") or 0.0
            try:
                if float(velo) >= 99.5:
                    return "velocity_heat"
            except (ValueError, TypeError):
                pass

        for k, v in STATCAST_EVENT_MAP.items():
            if k in evt:
                return v

        return "banter"

    def slot_fill(self, template: str, play_payload: Optional[Dict[str, Any]], game_state: Optional[Dict[str, Any]], persona_team: str = "GLOBAL") -> str:
        """
        Robust, spatial-aware slot filling powered by the "Who's on First?" DiamondStateManager.
        Prevents greedy multi-slot duplication ('Edible Freddie' bug) and perspective drift.
        """
        payload = play_payload or {}
        state = game_state or {}
        game_pk = str(state.get("game_pk") or payload.get("game_pk") or "default_game")
        
        # Import DiamondStateManager singleton
        try:
            try:
                from core.diamond_state_manager import diamond_engine
            except ImportError:
                from scripts.core.diamond_state_manager import diamond_engine
            d_state = diamond_engine.get_or_create(
                game_pk=game_pk,
                home_team=state.get("home_team") or "HOME",
                away_team=state.get("away_team") or "AWAY",
                venue=state.get("venue") or "Ballpark"
            )
            # Process play event if present
            if payload:
                d_state = diamond_engine.process_statcast_event(game_pk, payload)
            slot_map = d_state.get_slot_replacements(persona_team)
        except Exception as _d_err:
            logger.warning("Could not invoke diamond_engine for slot_fill: %s", _d_err)
            slot_map = {}

        # Add physical metric slots
        distance = payload.get("distance") or payload.get("hit_distance_sc") or random.choice(["410", "425", "395", "440"])
        velo = payload.get("pitch_speed") or payload.get("launch_speed") or payload.get("start_speed") or random.choice(["100.2", "99.4", "101.1", "98.8"])
        try:
            velo_str = f"{float(velo):.1f}"
        except (ValueError, TypeError):
            velo_str = str(velo)

        slot_map["{DISTANCE}"] = str(distance)
        slot_map["{VELO}"] = velo_str
        slot_map["{OPPONENT}"] = str(state.get("away_team") or state.get("home_team") or "them")
        slot_map["{FACTION}"] = persona_team.upper()

        # Strict Invariant: curr_pitcher is NEVER substituted for runner or batter slots
        curr_pitcher = slot_map.get("{PITCHER}") or slot_map.get("{OPPONENT_PITCHER}") or (payload.get("pitcher") if payload else "") or ""
        if curr_pitcher and curr_pitcher.lower() not in ("the pitcher", "our starter", "the opposing starter", ""):
            clean_pitch = curr_pitcher.strip().lower()
            for slot_key in ["{BATTER}", "{ALLY_BATTER}", "{OPPONENT_BATTER}", "{RUNNER_1B}", "{RUNNER_2B}", "{RUNNER_3B}", "{batter}", "{our guy}", "{their guy}"]:
                if slot_key in slot_map:
                    slot_val = str(slot_map[slot_key]).strip().lower()
                    if slot_val == clean_pitch or clean_pitch in slot_val:
                        if "RUNNER" in slot_key:
                            slot_map[slot_key] = "the runner"
                        else:
                            slot_map[slot_key] = "the hitter"

        # Single-pass regex token substitution to prevent duplicate multi-slot collision
        if slot_map:
            # Sort by descending length so possessive slots ({PITCHER}'s) match before base slots ({PITCHER})
            sorted_keys = sorted(slot_map.keys(), key=lambda k: -len(k))
            pattern = re.compile("|".join(re.escape(k) for k in sorted_keys))
            result = pattern.sub(lambda m: slot_map.get(m.group(0), m.group(0)), template)
        else:
            result = template
        
        # Cleanup any remaining unmapped {our guy} or similar tokens
        curr_batter = slot_map.get("{BATTER}") or slot_map.get("{ALLY_BATTER}") or (payload.get("batter") if payload else "") or "the batter"
        curr_pitcher = slot_map.get("{PITCHER}") or slot_map.get("{OPPONENT_PITCHER}") or (payload.get("pitcher") if payload else "") or "the pitcher"
        if curr_batter and curr_pitcher and curr_batter.strip().lower() == curr_pitcher.strip().lower():
            curr_batter = "the batter"
        
        result = re.sub(r'\{our guy\}', curr_batter, result, flags=re.IGNORECASE)
        result = re.sub(r'\{their guy\}', slot_map.get("{OPPONENT_BATTER}", "the hitter"), result, flags=re.IGNORECASE)
        
        # Deduplicate player name collision where batter name is repeated for pitcher
        if curr_batter and curr_pitcher and curr_batter != curr_pitcher:
            result = re.sub(rf'\b(make|against|facing|off of|off)\s+{re.escape(curr_batter)}\b', rf'\1 {curr_pitcher}', result, flags=re.IGNORECASE)
            if result.count(curr_batter) > 1:
                parts = result.split(curr_batter)
                result = parts[0] + curr_batter + parts[1] + curr_pitcher + "".join(parts[2:])

        # Strict elimination of literal 'our guy' / 'a our guy' phrases from legacy templates
        result = re.sub(r'\ba\s+our\s+guy\b', curr_batter, result, flags=re.IGNORECASE)
        result = re.sub(r'\bour\s+guy\b', curr_batter, result, flags=re.IGNORECASE)

        # Grammar remediation for legacy canned templates (Task 4)
        result = re.sub(r'\b(?:that\s+)?their\s+pitcher\s+league\s+velocity\b', "the pitcher's velocity", result, flags=re.IGNORECASE)
        result = re.sub(r'\b(?:that\s+)?their\s+pitcher\s+(velocity|heat|fastball|slider|curveball|cutter|changeup|splitter|sinker)\b', r"the pitcher's \1", result, flags=re.IGNORECASE)
        result = re.sub(r'\btheir\s+hitter\s+needs\s+to\s+attack\s+the\s+zone\b', "the pitcher needs to attack the zone", result, flags=re.IGNORECASE)
        result = re.sub(r'\bthat\s+their\s+pitcher\b', "the opposing pitcher", result, flags=re.IGNORECASE)
        result = re.sub(r'\btheir\s+pitcher\b', "the opposing starter", result, flags=re.IGNORECASE)
        result = re.sub(r'\btheir\s+hitter\b', "the opposing batter", result, flags=re.IGNORECASE)
        result = re.sub(r'\bour\s+arm\b', "our pitcher", result, flags=re.IGNORECASE)

        # Universal scrub: remove any remaining curly braces around any token (e.g. {Yan} -> Yan)
        result = re.sub(r'\{([^{}]+)\}', r'\1', result)

        # Purge hallucinated / stale canned player names from legacy templates (Task 55)
        # If the template literally contains "Yordan", "Young", or "Goldy", substitute the actual batter/pitcher
        if curr_batter and curr_batter.lower() not in ("the batter", "the hitter", "our guy"):
            result = re.sub(r'\bYordan\b', curr_batter, result)
            result = re.sub(r'\bGoldy\b', curr_batter, result)
            result = re.sub(r'\bYoung\b', curr_batter, result)
        else:
            result = re.sub(r'\bYordan\b', "the hitter", result)
            result = re.sub(r'\bGoldy\b', "our guy", result)
            result = re.sub(r'\bYoung\b', "the rookie", result)

        return result


    def get_reaction(
        self,
        persona: str,
        event_type: Optional[str] = None,
        game_state: Optional[Dict[str, Any]] = None,
        play_payload: Optional[Dict[str, Any]] = None,
        room_id: Optional[str] = None
    ) -> str:
        """
        Generate an authentic, slot-filled reaction in sub-10ms.
        """
        start_time = time.time()
        p_clean = str(persona).lower().strip()
        category = self.map_event_category(event_type, play_payload)
        team = self._persona_teams.get(p_clean, "GLOBAL")
        r_key = (str(room_id or "global"), p_clean)
        recent_ids = self.recent_history[r_key]

        candidate_rows = []

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()

                # Step 1: Direct (persona, category) match
                query = """
                SELECT id, template_text, raw_sample_text, slot_keys, event_category 
                FROM dim_persona_corpus_reactions 
                WHERE persona = ? AND event_category = ?
                LIMIT 40
                """
                candidate_rows = cur.execute(query, (p_clean, category)).fetchall()

                # Step 2: Fallback to (persona, banter)
                if not candidate_rows and category != "banter":
                    query_banter = """
                    SELECT id, template_text, raw_sample_text, slot_keys, event_category 
                    FROM dim_persona_corpus_reactions 
                    WHERE persona = ? AND event_category = 'banter'
                    LIMIT 40
                    """
                    candidate_rows = cur.execute(query_banter, (p_clean,)).fetchall()

                # Step 3: Fallback to team match
                if not candidate_rows and team != "GLOBAL":
                    query_team = """
                    SELECT id, template_text, raw_sample_text, slot_keys, event_category 
                    FROM dim_persona_corpus_reactions 
                    WHERE team = ? AND event_category = ?
                    LIMIT 30
                    """
                    candidate_rows = cur.execute(query_team, (team, category)).fetchall()

                # Step 4: Fallback to global banter
                if not candidate_rows:
                    query_global = """
                    SELECT id, template_text, raw_sample_text, slot_keys, event_category 
                    FROM dim_persona_corpus_reactions 
                    WHERE event_category = 'banter'
                    ORDER BY RANDOM() LIMIT 20
                    """
                    candidate_rows = cur.execute(query_global).fetchall()

        except Exception as e:
            logger.error("DB error during corpus lookup: %s", e)

        if not candidate_rows:
            # Absolute fallback
            return f"LFGGG! Let's get this win!"

        # Filter out recently used templates if possible
        available = [r for r in candidate_rows if r["id"] not in recent_ids]
        if not available:
            available = candidate_rows

        # Score-context filter to prevent score/lead inversion bugs (e.g. complaining about being down when up 8-3)
        score_diff = 0
        if game_state and team != "GLOBAL":
            home_s = int(game_state.get("home_score", 0) or 0)
            away_s = int(game_state.get("away_score", 0) or 0)
            ht = str(game_state.get("home_team", "")).upper()
            at = str(game_state.get("away_team", "")).upper()
            if team == ht:
                score_diff = home_s - away_s
            elif team == at:
                score_diff = away_s - home_s

        if score_diff >= 1:
            # Team is LEADING: filter out templates complaining about trailing or being down
            filtered = [
                r for r in available 
                if not re.search(r'\b(down by|trailing|behind by|our deficit|deficit of|when we\'re down|we are down)\b', r["template_text"], re.IGNORECASE)
            ]
            if filtered:
                available = filtered
        elif score_diff <= -1:
            # Team is TRAILING: filter out templates gloating about having the lead
            filtered = [
                r for r in available 
                if not re.search(r'\b(up by|our lead|protecting this lead|cushion of|comfortable lead)\b', r["template_text"], re.IGNORECASE)
            ]
            if filtered:
                available = filtered

        # Pitch-level filter: if the event is a pitch (foul, ball, strike, velocity_heat), strictly filter out
        # templates that hallucinate completed plays (fly outs, groundouts, pop-ups, wild pitches, home runs, double plays)
        raw_evt_str = f"{category} {str(event_type or '')}".lower()
        is_routine_pitch = any(k in raw_evt_str for k in ["foul", "ball", "strike", "pitch", "called_strike", "swinging_strike"])
        if is_routine_pitch:
            play_outcome_pattern = re.compile(
                r'\b(fly out|flies out|flyout|pop-up|pop out|popped out|ground ball|groundout|ground out|grounds out|line drive|lineout|line out|lines out|wild pitch|ball in the dirt|grand slam|home run|homer|double play|stolen base|stole second|stole third|passed ball|rbi|bring home|scores|scored|touch home|reached on|error)\b',
                re.IGNORECASE
            )
            pitch_filtered = [r for r in available if not play_outcome_pattern.search(r["template_text"])]
            if pitch_filtered:
                available = pitch_filtered
            else:
                try:
                    from fanstack_chatbots import get_local_fallback_yap
                    return get_local_fallback_yap({"name": p_clean, "team": team}, active_play=play_payload, status_text=event_type)
                except Exception:
                    pass


        # Perspective polarity filter (Task 55): Ensure defending fans never cheer for opposing hitters
        if game_state and team != "GLOBAL":
            inn_half = str(game_state.get("inning_half") or game_state.get("half") or game_state.get("inning") or "").lower()
            ht = str(game_state.get("home_team", "")).upper()
            at = str(game_state.get("away_team", "")).upper()
            is_defending = False
            if "top" in inn_half and team == ht:
                is_defending = True
            elif "bot" in inn_half and team == at:
                is_defending = True
            
            if is_defending:
                defense_filtered = [
                    r for r in available
                    if not re.search(r'\b(that\'s what we need|drive \'em in|bring him home|ribbie|grand slam|walk it off|touch \'em all|let\'s go \{BATTER\}|c\'mon \{BATTER\}|get a hit|barrel it up)\b', r["template_text"], re.IGNORECASE)
                ]
                if defense_filtered:
                    available = defense_filtered

        # Market grounding & non-participant filter: reject templates mentioning out-of-market teams, stadiums, or players
        if game_state:
            ht = str(game_state.get("home_team", "")).upper()
            at = str(game_state.get("away_team", "")).upper()
            active_teams = {ht, at}
            if str(room_id) == "823498":
                active_teams.update({"NYM", "NYY"})
            
            NON_PARTICIPANT_PATTERNS = {
                "BAL": r'\b(baltimore|orioles|camden\s*yards|o\'s|gunnar\s*henderson|adley\s*rutschman|bautista)\b',
                "BOS": r'\b(red\s*sox|fenway|devers)\b',
                "TB": r'\b(tampa\s*bay|rays|tropicana|the\s*trop)\b',
                "TOR": r'\b(blue\s*jays|toronto|rogers\s*centre|vlad\s*jr|vladimir\s*guerrero)\b',
                "KC": r'\b(witt\s*jr|bobby\s*witt|royals|kansas\s*city|kauffman|kc\s+bums)\b',
                "DET": r'\b(detroit|tigers|comerica|tarik\s*skubal)\b',
                "MIN": r'\b(twins|minnesota|target\s*field)\b',
                "CWS": r'\b(white\s*sox|guaranteed\s*rate|south\s*side)\b',
                "CLE": r'\b(guardians|cleveland|progressive\s*field|jose\s*ramirez)\b',
                "HOU": r'\b(astros|houston|minute\s*maid|altuve)\b',
                "SEA": r'\b(mariners|seattle|t-mobile\s*park|julio\s*rodriguez)\b',
                "TEX": r'\b(texas\s*rangers|globe\s*life|corey\s*seager)\b',
                "LAA": r'\b(angels|anaheim|mike\s*trout)\b',
                "OAK": r'\b(athletics|oakland|coliseum)\b',
                "ATL": r'\b(braves|atlanta|truist|acuna)\b',
                "PHI": r'\b(phillies|citizens\s*bank|bryce\s*harper|schwarber|wheeler)\b',
                "MIA": r'\b(marlins|miami|loandepot)\b',
                "WSH": r'\b(nationals|nats\s*park)\b',
                "CHC": r'\b(chicago\s*cubs|wrigley)\b',
                "CIN": r'\b(cincinnati|reds|great\s*american|elly\s*de\s*la\s*cruz)\b',
                "MIL": r'\b(brewers|milwaukee|amfam)\b',
                "PIT": r'\b(pirates|pittsburgh|pnc\s*park|paul\s*skenes)\b',
                "STL": r'\b(st\.\s*louis|cardinals|busch\s*stadium)\b',
                "LAD": r'\b(dodgers|dodger\s*stadium|chavez\s*ravine|ohtani|betts|freeman)\b',
                "SD": r'\b(padres|san\s*diego|petco|michael\s*king|king\s+sinker|machado|tatis)\b',
                "SF": r'\b(giants|oracle\s*park|san\s*francisco)\b',
                "AZ": r'\b(diamondbacks|d-backs|chase\s*field|corbin\s*carroll)\b',
                "COL": r'\b(rockies|coors\s*field|colorado)\b',
            }

            grounding_filtered = []
            for r in available:
                txt = r["template_text"]
                skip = False
                for non_team, pattern in NON_PARTICIPANT_PATTERNS.items():
                    if non_team not in active_teams and re.search(pattern, txt, re.IGNORECASE):
                        skip = True
                        break
                if skip:
                    continue

                # Reject Citi Field if NYM is not the home team
                if ht != "NYM" and re.search(r'\bciti\s+field\b', txt, re.IGNORECASE):
                    continue
                # Reject Yankee Stadium if NYY is not the home team
                if ht != "NYY" and re.search(r'\byankee\s+stadium\b', txt, re.IGNORECASE):
                    continue
                grounding_filtered.append(r)
            
            if grounding_filtered:
                available = grounding_filtered

        # Team polarity hard-lock filter: Mets personas MUST NOT praise NYY / mock NYM; Yankees personas MUST NOT praise NYM / mock NYY
        if team in ("NYM", "NYY"):
            polarity_filtered = []
            for r in available:
                txt = r["template_text"]
                if team == "NYM":
                    # Mets fan: drop templates cheering Yankees or mocking Mets
                    if re.search(r'\b(let\'s\s+go\s+yankees|yankees\s+win|love\s+the\s+bronx|bronx\s+pride|pinstripe\s+pride|yankees\s+rule|praise\s+the\s+yankees|yankees\s+on\s+top)\b', txt, re.IGNORECASE):
                        continue
                    if re.search(r'\b(lol\s*mets|mets\s+choke|mets\s+trash|queens\s+bums|flushing\s+clowns)\b', txt, re.IGNORECASE):
                        continue
                elif team == "NYY":
                    # Yankees fan: drop templates cheering Mets or mocking Yankees
                    if re.search(r'\b(let\'s\s+go\s+mets|lfgr?m|amazin|mets\s+win|flushing\s+pride|queens\s+pride|omg\s+mets)\b', txt, re.IGNORECASE):
                        continue
                    if re.search(r'\b(yankees\s+suck|overrated\s+bronx|bronx\s+frauds|hal\s+is\s+cheap)\b', txt, re.IGNORECASE):
                        continue
                polarity_filtered.append(r)
            if polarity_filtered:
                available = polarity_filtered

        chosen = random.choice(available)
        recent_ids.append(chosen["id"])

        template = chosen["template_text"]
        result = self.slot_fill(template, play_payload, game_state, persona_team=team)

        elapsed_ms = (time.time() - start_time) * 1000.0
        logger.debug("Generated offline reaction for @%s [%s] in %.2fms", p_clean, category, elapsed_ms)
        return result

# Singleton convenience function
_global_engine = None

def get_offline_corpus_reaction(
    persona: str,
    event_type: Optional[str] = None,
    game_state: Optional[Dict[str, Any]] = None,
    play_payload: Optional[Dict[str, Any]] = None,
    room_id: Optional[str] = None
) -> str:
    global _global_engine
    if _global_engine is None:
        _global_engine = OfflineCorpusEngine()
    return _global_engine.get_reaction(persona, event_type, game_state, play_payload, room_id)

if __name__ == "__main__":
    eng = OfflineCorpusEngine()
    test_play = {
        "batter": "Pete Alonso",
        "pitcher": "Zack Wheeler",
        "distance": 435,
        "pitch_speed": 100.8
    }
    test_state = {"inning": 8, "score_away": 3, "score_home": 4, "away_team": "PHI", "home_team": "NYM"}

    print("\n--- TEST OFFLINE REACTIONS ---")
    for p in ["barf", "7_train_terry", "UncleStevieStan", "friar_frank", "the_chop_shop"]:
        msg = eng.get_reaction(p, event_type="home_run", game_state=test_state, play_payload=test_play, room_id="822931")
        print(f"[@{p}] -> {msg}")

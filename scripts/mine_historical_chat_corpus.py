#!/usr/bin/env python3
"""
Deep Entity Sanitization & Corpus Mining Pipeline
Ticket: ENHC0010008-OFFLINE-HISTORICAL-CORPUS-ADVOCATE-ENGINE

Mines 147,000+ historical chat messages from game_chat in sovereign_now.db.
Extracts 1,200+ active MLB batters and pitchers from mlb_rosters and game_play,
sanitizes player names into dynamic variables ({BATTER}, {PITCHER}, {DISTANCE}, {VELO}, {OPPONENT}),
and stores fully parameterized templates in dim_persona_corpus_reactions.
"""

import json
import logging
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional

logging.basicConfig(level=logging.INFO, format="[DEEP MINER] %(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DeepCorpusMiner")

DB_PATH = Path("/home/james/stacklabs/dna/sovereign_now.db")

STRIP_PATTERNS = [
    re.compile(r"\[Critical Prompt Adherence:[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[Critical Trigger Activation:[^\]]*\]", re.IGNORECASE),
    re.compile(r"\*\*\[Critical Trigger Activation\]\*\*[^\n]*", re.IGNORECASE),
    re.compile(r"The Sovereign Banter Engine HAS TRIGGERED:[^\n]*", re.IGNORECASE),
    re.compile(r"Read the last message sent in the recent chat context[^\n]*", re.IGNORECASE),
    re.compile(r"You must violently disagree[^\n]*", re.IGNORECASE),
    re.compile(r"CRITICAL PROMPT ADHERENCE:[^\n]*", re.IGNORECASE),
    re.compile(r"SOVEREIGN OS INVARIANT[^\n]*", re.IGNORECASE),
    re.compile(r"dot:\s*", re.IGNORECASE),
    re.compile(r"^\"|\"$"),
]

EVENT_RULES = [
    ("home_run", re.compile(r"\b(home\s*run|homer|homered|moonshot|went\s+yard|crushed\s+it|blasted|deep\s+drive|into\s+the\s+stands|grand\s+slam|solo\s+shot|2-run\s+shot|3-run\s+shot)\b", re.IGNORECASE)),
    ("strikeout", re.compile(r"\b(strikeout|struck\s+out|punched\s+out|punchout|caught\s+looking|whiffed|whiff|swing\s+and\s+a\s+miss|golden\s+sombrero|k'd|froze\s+him)\b", re.IGNORECASE)),
    ("double_play", re.compile(r"\b(double\s*play|twin\s+killing|6-4-3|4-6-3|5-4-3|grounded\s+into)\b", re.IGNORECASE)),
    ("velocity_heat", re.compile(r"\b(10[0-5](\.\d+)?\s*mph|99(\.\d+)?\s*mph|triple\s+digits|absolute\s+gas|pure\s+heat|fireball|heater|fastball)\b", re.IGNORECASE)),
    ("blown_save", re.compile(r"\b(blown\s+save|bullpen\s+disaster|meltdown|choked|walk-off\s+loss|gave\s+up\s+the\s+lead|imploded)\b", re.IGNORECASE)),
    ("walk", re.compile(r"\b(walked|walk|base\s+on\s+balls|free\s+pass|four\s+balls)\b", re.IGNORECASE)),
    ("stolen_base", re.compile(r"\b(stole\s+second|stole\s+third|stolen\s+base|swiped\s+a\s+bag|safe\s+at\s+second)\b", re.IGNORECASE)),
    ("bad_call", re.compile(r"\b(umpire|ump|blind|terrible\s+call|horrible\s+call|framed\s+that|out\s+of\s+the\s+zone)\b", re.IGNORECASE)),
    ("hit", re.compile(r"\b(single|doubled|double|tripled|triple|base\s+hit|line\s+drive|liner|ripped\s+a\s+hit|bloop\s+single)\b", re.IGNORECASE)),
]

SENTIMENT_RULES = [
    ("ecstatic", re.compile(r"\b(lgm|lets\s+go|lfggg|unbelievable|beautiful|magic|legend|mvp|perfection|clutch)\b", re.IGNORECASE)),
    ("doomer", re.compile(r"\b(season\s+over|sell\s+the\s+team|disaster|cursed|pain|misery|fire\s+everyone|typical|unwatchable)\b", re.IGNORECASE)),
    ("panicked", re.compile(r"\b(oh\s+no|please\s+no|god\s+help\s+us|not\s+like\s+this|sweating|cant\s+watch)\b", re.IGNORECASE)),
    ("snarky", re.compile(r"\b(clown\s+show|bum|overpaid|fraud|joke|cant\s+make\s+this\s+up|classic)\b", re.IGNORECASE)),
    ("analytical", re.compile(r"\b(statcast|launch\s+angle|exit\s+velo|expected\s+ba|spin\s+rate|fip|woba)\b", re.IGNORECASE)),
]

def load_player_dictionaries(conn: sqlite3.Connection) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Builds comprehensive maps of Full Name and Last Name -> 'BATTER' or 'PITCHER'."""
    cur = conn.cursor()
    pitchers = set()
    batters = set()

    # From mlb_rosters
    try:
        for r in cur.execute("SELECT player_name, position FROM mlb_rosters"):
            name = str(r[0]).strip()
            pos = str(r[1]).strip().upper()
            if pos == 'P':
                pitchers.add(name)
            else:
                batters.add(name)
    except Exception as e:
        logger.warning("Error reading mlb_rosters: %s", e)

    # From game_play
    try:
        for r in cur.execute("SELECT DISTINCT pitcher FROM game_play WHERE pitcher IS NOT NULL"):
            if r[0] and len(r[0]) > 2:
                pitchers.add(r[0].strip())
        for r in cur.execute("SELECT DISTINCT batter FROM game_play WHERE batter IS NOT NULL"):
            if r[0] and len(r[0]) > 2:
                batters.add(r[0].strip())
    except Exception as e:
        logger.warning("Error reading game_play: %s", e)

    # Compile regex patterns sorted by length descending so full names match before single last names
    full_pitcher_map = {}
    last_pitcher_map = {}
    for p in pitchers:
        full_pitcher_map[p] = "PITCHER"
        parts = p.split()
        if len(parts) >= 2 and len(parts[-1]) >= 4:
            last_pitcher_map[parts[-1]] = "PITCHER"

    full_batter_map = {}
    last_batter_map = {}
    for b in batters:
        full_batter_map[b] = "BATTER"
        parts = b.split()
        if len(parts) >= 2 and len(parts[-1]) >= 4:
            last_batter_map[parts[-1]] = "BATTER"

    logger.info("Compiled %d pitchers and %d batters into entity dictionary.", len(pitchers), len(batters))
    return full_pitcher_map, last_pitcher_map, full_batter_map, last_batter_map

def clean_text(raw: str) -> str:
    t = raw
    for p in STRIP_PATTERNS:
        t = p.sub("", t)
    # Strip literal curly braces around non-canonical tokens (e.g. {Thomas Saggese} -> Thomas Saggese)
    KNOWN_TOKENS = {"BATTER", "PITCHER", "DISTANCE", "VELO", "OPPONENT", "VENUE", "COUNT", "OUTS", "RUNNER_1B", "RUNNER_2B", "RUNNER_3B"}
    t = re.sub(r'\{([^{}]+)\}', lambda m: m.group(0) if m.group(1).upper() in KNOWN_TOKENS else m.group(1), t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def detect_event_category(text: str) -> str:
    for cat, regex in EVENT_RULES:
        if regex.search(text):
            return cat
    return "banter"

def detect_sentiment(text: str) -> str:
    for sent, regex in SENTIMENT_RULES:
        if regex.search(text):
            return sent
    return "neutral"

def sanitize_entities(
    text: str,
    re_full_pitchers: Optional[re.Pattern],
    re_last_pitchers: Optional[re.Pattern],
    re_full_batters: Optional[re.Pattern],
    re_last_batters: Optional[re.Pattern]
) -> Tuple[str, List[str]]:
    """Fast regex replacement of player names with {BATTER} and {PITCHER} variables."""
    slots = []
    t = text

    # Distance tokens
    if re.search(r"\b(\d{3})\s*(ft|feet)\b", t, re.IGNORECASE):
        t = re.sub(r"\b\d{3}\s*(ft|feet)\b", "{DISTANCE} ft", t, flags=re.IGNORECASE)
        slots.append("DISTANCE")

    # Velocity tokens
    if re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*mph\b", t, re.IGNORECASE):
        t = re.sub(r"\b\d{2,3}(?:\.\d+)?\s*mph\b", "{VELO} mph", t, flags=re.IGNORECASE)
        slots.append("VELO")

    # Full Batters
    if re_full_batters and re_full_batters.search(t):
        t = re_full_batters.sub("{BATTER}", t)
        slots.append("BATTER")

    # Full Pitchers
    if re_full_pitchers and re_full_pitchers.search(t):
        t = re_full_pitchers.sub("{PITCHER}", t)
        slots.append("PITCHER")

    # Last Name Batters
    if re_last_batters and re_last_batters.search(t):
        t = re_last_batters.sub(lambda m: "{BATTER}'s" if "'s" in m.group(0).lower() else "{BATTER}", t)
        slots.append("BATTER")

    # Last Name Pitchers
    if re_last_pitchers and re_last_pitchers.search(t):
        t = re_last_pitchers.sub(lambda m: "{PITCHER}'s" if "'s" in m.group(0).lower() else "{PITCHER}", t)
        slots.append("PITCHER")

    return t, list(set(slots))

def run_deep_miner(limit: int = 150000) -> int:
    logger.info("Opening database: %s", DB_PATH)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    cur = conn.cursor()

    # Load persona map
    persona_teams: Dict[str, str] = {}
    for r in cur.execute("SELECT user_name, team FROM persona"):
        u_name = str(r[0]).lower().strip()
        t_name = str(r[1]).upper().strip() if r[1] else "GLOBAL"
        persona_teams[u_name] = t_name

    # Load player dictionaries
    full_pitchers, last_pitchers, full_batters, last_batters = load_player_dictionaries(conn)

    # Clear old table data to re-populate with deep sanitized templates
    cur.execute("DELETE FROM dim_persona_corpus_reactions;")
    conn.commit()
    logger.info("Cleared previous reaction templates for deep rebuild.")

    query = """
    SELECT id, game_pk, persona, text 
    FROM game_chat 
    WHERE text IS NOT NULL AND length(text) >= 15 AND length(text) <= 500
    ORDER BY id DESC
    LIMIT ?
    """
    rows = cur.execute(query, (limit,)).fetchall()
    logger.info("Processing %d raw chat candidate records...", len(rows))

    inserted = 0
    seen_templates: Set[Tuple[str, str, str]] = set()
    batch_inserts = []

    # Precompile unified regex patterns for ultra-fast C-level matching
    sorted_fb = [re.escape(k) for k in sorted(full_batters.keys(), key=len, reverse=True) if len(k) >= 5]
    re_full_batters = re.compile(r"\b(" + "|".join(sorted_fb) + r")\b", re.IGNORECASE) if sorted_fb else None

    sorted_fp = [re.escape(k) for k in sorted(full_pitchers.keys(), key=len, reverse=True) if len(k) >= 5]
    re_full_pitchers = re.compile(r"\b(" + "|".join(sorted_fp) + r")\b", re.IGNORECASE) if sorted_fp else None

    stop_words = {
        "will", "deal", "real", "best", "good", "fast", "park", "game", "walk", "long", "king", "bell", 
        "mann", "wood", "cook", "page", "gray", "ward", "ford", "church", "white", "black", "stone", 
        "cross", "wells", "short", "price", "hill", "love", "marsh", "power", "wall", "field", "ball", 
        "base", "line", "drive", "call", "play", "hit", "run", "out", "guy", "arm", "hand", "strike", 
        "home", "head", "bush", "lane", "webb", "brown", "green", "young", "cole", "house", "city",
        "story", "major", "minor", "star", "safe", "score", "count", "swing", "pitch", "zone"
    }
    sorted_lb = [re.escape(k) for k in sorted(last_batters.keys(), key=len, reverse=True) if len(k) >= 4 and k.lower() not in stop_words]
    re_last_batters = re.compile(r"\b(" + "|".join(sorted_lb) + r")(?:'s)?\b", re.IGNORECASE) if sorted_lb else None

    sorted_lp = [re.escape(k) for k in sorted(last_pitchers.keys(), key=len, reverse=True) if len(k) >= 4 and k.lower() not in stop_words]
    re_last_pitchers = re.compile(r"\b(" + "|".join(sorted_lp) + r")(?:'s)?\b", re.IGNORECASE) if sorted_lp else None

    logger.info("Compiled fast unified regexes with %d stop words. Processing candidate records...", len(stop_words))

    for r in rows:
        c_id, game_pk, raw_persona, raw_text = r
        persona_clean = str(raw_persona).lower().strip()
        team = persona_teams.get(persona_clean, "GLOBAL")

        cleaned = clean_text(raw_text)
        if len(cleaned) < 12 or len(cleaned) > 400:
            continue

        if "Critical Prompt" in cleaned or "LLM Judge" in cleaned or "json" in cleaned.lower() and "{" in cleaned:
            continue

        event_cat = detect_event_category(cleaned)
        sentiment = detect_sentiment(cleaned)
        
        # Deep entity sanitization pass (Instant regex pass)
        template, slots = sanitize_entities(
            cleaned, re_full_pitchers, re_last_pitchers, re_full_batters, re_last_batters
        )

        dedup_key = (persona_clean, event_cat, template.lower()[:70])
        if dedup_key in seen_templates:
            continue
        seen_templates.add(dedup_key)

        batch_inserts.append((
            persona_clean,
            team,
            event_cat,
            sentiment,
            1, 9, "any",
            template,
            cleaned,
            json.dumps(slots),
            1.0
        ))

        if len(batch_inserts) >= 1000:
            cur.executemany("""
                INSERT INTO dim_persona_corpus_reactions 
                (persona, team, event_category, sentiment, min_inning, max_inning, score_context, template_text, raw_sample_text, slot_keys, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_inserts)
            inserted += len(batch_inserts)
            batch_inserts = []

    if batch_inserts:
        cur.executemany("""
            INSERT INTO dim_persona_corpus_reactions 
            (persona, team, event_category, sentiment, min_inning, max_inning, score_context, template_text, raw_sample_text, slot_keys, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_inserts)
        inserted += len(batch_inserts)

    conn.commit()
    conn.close()

    logger.info("COMPLETE: Sanitized and inserted %d parameterized templates into dim_persona_corpus_reactions.", inserted)
    return inserted

if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 150000
    res = run_deep_miner(lim)
    print(f"COMPLETE: Deep mined {res} entity-sanitized reaction templates.")

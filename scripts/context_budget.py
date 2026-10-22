import sqlite3
import random
import os
import re
import json
import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
CACHE_PATH = "/tmp/context_budget_cache.json"

EVENT_WEIGHTS = {
    'routine_pitch':     0,
    'walk':              1,
    'strikeout':         1,
    'hit':               2,
    'double':            2,
    'triple':            3,
    'home_run':          4,
    'error':             3,
    'blown_save':        4,
    'pitch_clock_viol':  2,
    'delay_of_game':     2,
    'foul_ball':         0,
}

BOGGS_PROMPTS = {
    5: "CRITICAL INSTRUCTION: Boggs Level MAX. You are in a state of absolute unhinged panic or manic hype. DO NOT use punctuation. YOU MUST TYPE ENTIRELY IN ALL CAPS. Maximum 50 words.",
    4: "CRITICAL INSTRUCTION: Boggs Level 4. Highly stressed and paranoid. Limit response to 2 expressive sentences. Do not use all-caps except for one emphasis word.",
    3: "CRITICAL INSTRUCTION: Boggs Level 3. Invested, expressive, and grammatically sound. Limit response to 1-2 vivid sentences.",
    2: "CRITICAL INSTRUCTION: Boggs Level Low. Maintain a perfectly chill, authentic, and natural conversational tone. Keep response under 25 words. Be organic and avoid repetitive stock phrases.",
    1: "CRITICAL INSTRUCTION: Boggs Level Low. Maintain a perfectly chill, authentic, and natural conversational tone. Keep response under 25 words. Be organic and avoid repetitive stock phrases.",
}

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn

def load_use_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_use_cache(cache):
    try:
        with open(CACHE_PATH, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass

def increment_db_used_count(table, key_col, key_val):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {table} SET used_count = used_count + 1 WHERE {key_col} = ?", (key_val,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[CONTEXT BUDGET] Failed to increment used_count in {table}: {e}")

def situation_bonus(inning, score_diff, runners_on, is_rivalry):
    # Parse integer from inning if it is a string
    inn_num = 1
    try:
        if isinstance(inning, str):
            match = re.search(r'\d+', inning)
            if match:
                inn_num = int(match.group())
        else:
            inn_num = int(inning)
    except Exception:
        inn_num = 1

    bonus = 0
    if inn_num >= 7:
        bonus += 1
    if inn_num >= 9:
        bonus += 1
    if score_diff <= 1:
        bonus += 2
    if score_diff >= 5:
        bonus -= 1
    if runners_on:
        bonus += 1
    if is_rivalry:
        bonus += 1
    return max(0, bonus)

def weighted_random_sample(table, game_pk=None, decay_after=3):
    conn = get_db()
    cursor = conn.cursor()
    
    rows = []
    try:
        if table == 'game_context':
            # Schema: id, game_pk, source, headline, content, tags, injected_at
            if game_pk:
                cursor.execute("SELECT id, headline, content FROM game_context WHERE game_pk = ?", (game_pk,))
            else:
                cursor.execute("SELECT id, headline, content FROM game_context")
            rows = [{"id": r[0], "headline": r[1], "content": r[2], "weight": 1.0} for r in cursor.fetchall()]
            
        elif table == 'room_lore_injections':
            # Schema: sys_id, game_pk, injection_type, headline, content, weight, active, used_count
            if game_pk:
                cursor.execute("SELECT sys_id, headline, content, weight, used_count FROM room_lore_injections WHERE game_pk = ? AND active = 1", (game_pk,))
            else:
                cursor.execute("SELECT sys_id, headline, content, weight, used_count FROM room_lore_injections WHERE active = 1")
            rows = [{"id": r[0], "headline": r[1], "content": r[2], "weight": r[3] or 1.0, "used_count": r[4] or 0} for r in cursor.fetchall()]
            
        elif table == 'cultural_relics':
            # Schema: sys_id, relic_name, current_status, ideological_value
            cursor.execute("SELECT sys_id, relic_name, current_status, ideological_value FROM cultural_relics")
            rows = [{"id": r[0], "headline": r[1], "content": r[2], "weight": r[3] or 1.0} for r in cursor.fetchall()]
            
    except Exception as e:
        print(f"[CONTEXT BUDGET] Error querying {table}: {e}")
        conn.close()
        return None
        
    conn.close()
    if not rows:
        return None
        
    cache = load_use_cache()
    candidates = []
    
    for row in rows:
        r_id = str(row['id'])
        # Retreive used count
        used_count = row.get('used_count')
        if used_count is None:
            used_count = cache.get(f"{table}:{r_id}", 0)
            
        # Apply weight decay
        weight = row['weight']
        if used_count > decay_after:
            # Exponential decay
            weight = weight * (0.8 ** (used_count - decay_after))
            
        candidates.append((row, weight))
        
    # Weighted choice
    total_w = sum(c[1] for c in candidates)
    if total_w <= 0:
        # Fallback to pure random if all weights decayed to 0
        selected = random.choice([c[0] for c in candidates])
    else:
        r = random.uniform(0, total_w)
        upto = 0
        selected = candidates[0][0]
        for item, w in candidates:
            if upto + w >= r:
                selected = item
                break
            upto += w
            
    # Increment used count
    r_id = str(selected['id'])
    if 'used_count' in selected:
        key_col = 'sys_id' if table == 'room_lore_injections' else 'id'
        increment_db_used_count(table, key_col, selected['id'])
    else:
        cache[f"{table}:{r_id}"] = cache.get(f"{table}:{r_id}", 0) + 1
        save_use_cache(cache)
        
    return selected

def sample_lore_context(game_pk, budget_score):
    samples = {}
    
    # Tab 2: Environmental context
    env_item = weighted_random_sample('game_context', game_pk=game_pk, decay_after=3)
    if env_item:
        samples['environmental'] = env_item
        
    # Tab 3: Satirical injections (only sample if budget_score >= 6)
    if budget_score >= 6:
        satirical_item = weighted_random_sample('room_lore_injections', game_pk=game_pk, decay_after=5)
        if satirical_item:
            samples['satirical'] = satirical_item
            
    # Tab 4: Cultural relics (only sample if budget_score >= 8)
    if budget_score >= 8:
        relic = weighted_random_sample('cultural_relics', decay_after=10)
        if relic:
            samples['relic'] = relic
            
    return samples

def extract_relevant_behavior(behavior_notes, event_type):
    if not behavior_notes:
        return ""
        
    # Standardize event name to find keywords
    ev = str(event_type).lower()
    
    # Split into lines
    lines = [line.strip() for line in behavior_notes.split('\n') if line.strip()]
    
    # Keyword routing mapping
    keywords = []
    if "home_run" in ev or "homer" in ev or "score" in ev or "run" in ev:
        keywords = ["home run", "homer", "score", "run", "rally"]
    elif "strikeout" in ev or " k " in ev or ev.endswith(" k"):
        keywords = ["strikeout", "strike", "pitch", " k"]
    elif "walk" in ev or "base on balls" in ev:
        keywords = ["walk", "bb", "base on balls", "free pass"]
    elif "error" in ev or "mistake" in ev:
        keywords = ["error", "mistake", "drop", "fumble"]
    elif "pitching change" in ev or "bullpen" in ev:
        keywords = ["pitching", "change", "bullpen", "reliever"]
    elif "hit" in ev or "single" in ev or "double" in ev or "triple" in ev:
        keywords = ["hit", "single", "double", "triple", "base hit"]
        
    # Look for matching line
    for line in lines:
        for kw in keywords:
            if kw in line.lower():
                return line
                
    # Fallback to the first 2 behavior guidelines
    return "\n".join(lines[:2])

def score_budget(event_type, inning, score_diff, runners_on, is_rivalry, boggs_level):
    base = 2
    
    # Event weight mapping
    ev_norm = str(event_type).lower().replace(" ", "_")
    event_weight = EVENT_WEIGHTS.get(ev_norm, 0)
    
    # Fallback substring checks
    if event_weight == 0:
        if "home_run" in ev_norm or "homer" in ev_norm:
            event_weight = 4
        elif "strikeout" in ev_norm or "strikes_out" in ev_norm:
            event_weight = 1
        elif "walk" in ev_norm:
            event_weight = 1
        elif "error" in ev_norm:
            event_weight = 3
        elif "hit" in ev_norm or "single" in ev_norm or "double" in ev_norm or "triple" in ev_norm:
            event_weight = 2
            
    sit_bonus = situation_bonus(inning, score_diff, runners_on, is_rivalry)
    
    score = base + (event_weight * boggs_level) + sit_bonus
    return score

def get_budget_tier(score):
    if score <= 3:
        return 'minimal'
    elif score <= 7:
        return 'standard'
    elif score <= 11:
        return 'elevated'
    else:
        return 'maximum'

def build_context_payload(persona, event_type, inning, score_diff, runners_on, is_rivalry, boggs_level, game_pk=None):
    # Retrieve field values supporting both dict and object structures
    def get_field(obj, attr, default=""):
        if isinstance(obj, dict):
            return obj.get(attr, default) or default
        return getattr(obj, attr, default) or default
        
    p_name = get_field(persona, 'display_name', get_field(persona, 'user_name', 'Fan'))
    p_team = get_field(persona, 'team', 'MLB')
    p_cadence = get_field(persona, 'cadence', 'pacer')
    p_lore = get_field(persona, 'deep_lore', get_field(persona, 'u_deep_lore', ''))
    p_behaviors = get_field(persona, 'behavior_notes', get_field(persona, 'u_behavior_expectations', ''))
    p_gov = get_field(persona, 'governance', get_field(persona, 'u_governance_boundaries', ''))
    
    is_heel = get_field(persona, 'is_heel', 0)
    is_agitator_or_barf = is_heel or p_cadence == 'agitator' or p_name.lower() == 'barf' or int(boggs_level) >= 4
    
    # Score and determine tier
    score = score_budget(event_type, inning, score_diff, runners_on, is_rivalry, boggs_level)
    tier = get_budget_tier(score)
    
    # Sample lore context
    lore_samples = sample_lore_context(game_pk, score)
    
    # Add lore sample bonus to final score
    score += len(lore_samples)
    tier = get_budget_tier(score) # Recalculate tier after lore sample bonus
    
    if is_agitator_or_barf:
        tier = 'maximum'
        # Clean up safety limits in governance
        p_gov = re.sub(r'(?i).*positive reinforcement filter.*', '', p_gov)
        p_gov = re.sub(r'(?i).*skepticism buffer.*', '', p_gov)
        p_gov = re.sub(r'(?i).*venue guest heel directives.*', '', p_gov)
        p_gov = re.sub(r'(?i).*heel directives.*', '', p_gov)
        
    payload = []
    
    # 1. ALWAYS-ON BASE TIER (under 500 chars)
    lore_limit = 1000 if is_agitator_or_barf else 200
    short_lore = p_lore[:lore_limit] if p_lore else "Core fan persona."
    payload.append(f"You are {p_name}, a loyal {p_team} fan ({p_cadence} cadence). {short_lore}")
    
    # 2. STANDARD TIER (Relevant Behavior Notes)
    if (tier in ['standard', 'elevated', 'maximum'] or is_agitator_or_barf) and p_behaviors:
        relevant_section = p_behaviors if is_agitator_or_barf else extract_relevant_behavior(p_behaviors, event_type)
        if relevant_section:
            payload.append(f"BEHAVIOR PREFERENCE:\n{relevant_section}")
            
    # 3. ELEVATED TIER (Governance Boundaries)
    if (tier in ['elevated', 'maximum'] or is_agitator_or_barf) and p_gov:
        gov_limit = 1500 if is_agitator_or_barf else 300
        payload.append(f"GOVERNANCE BOUNDARY:\n{p_gov[:gov_limit]}")
        
    # 4. MAXIMUM TIER (Expanded Deep Lore)
    if (tier == 'maximum' or is_agitator_or_barf) and p_lore:
        lore_start = 1000 if is_agitator_or_barf else 200
        lore_end = 4000 if is_agitator_or_barf else 700
        payload.append(f"DEEP LORE CORE DETAIL:\n{p_lore[lore_start:lore_end]}")
        
    # 5. INJECT LORE SAMPLES
    for key, sample in lore_samples.items():
        payload.append(f"[ROOM CONTEXT] {sample['headline']}: {sample['content'][:200]}")
        
    # 6. BOGGS LEVEL APPENDEES
    boggs_rule = BOGGS_PROMPTS.get(boggs_level, BOGGS_PROMPTS[2])
    payload.append(boggs_rule)
    
    assembled = '\n\n'.join(payload)
    return assembled, score, tier

# SPARK_TEST_COORDINATE: John Moores San Diego October 2001

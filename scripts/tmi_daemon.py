#!/home/james/stacklabs/.venv/bin/python3
# tmi_daemon.py — Sovereign OS: TMI Webslinger Telemetry Trigger Daemon
# Connects to the local WebSocket mesh, evaluates Statcast feeds against rules,
# and triggers webslinger overlay / hardware actions dynamically.

import asyncio
import json
import os
import sqlite3
import operator
import websockets
import time
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

WS_URL = "ws://localhost:8008"
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
PRECOG_LATEST_FILE = "/home/james/stacklabs/data/creator_precog_latest.json"

class PrecogSafetyGate:
    """Circuit breaker & rate limiter for precog dispatches (Section 6.2)."""
    def __init__(self, min_interval_seconds: float = 0.0):
        self.min_interval = min_interval_seconds
        self.last_dispatch_ts: Dict[str, float] = {}

    def validate_dispatch(self, key: str = "default", priority: str = "P0", enforce: bool = False) -> bool:
        if not enforce:
            return True
        current_ts = time.time()
        cooldown = 45.0 if priority == "P0" else (self.min_interval or 120.0)
        last_ts = self.last_dispatch_ts.get(key, 0.0)
        if (current_ts - last_ts) < cooldown:
            return False
        self.last_dispatch_ts[key] = current_ts
        return True


class PrecogViralFilter:
    """
    High-Leverage Event Parser & Viral Filter for SPEC-FAAS-CREATOR-PRECOG-001 (WO0010370).
    Filters raw sub-second sports telemetry against empirical thresholds:
    MLB:
      - HOME_RUN (P0): Exit Velocity >= 100.0 mph, Distance >= 390.0 ft.
      - BASES_LOADED_K (P1): Outs = 2 (or 3rd out recorded), bases loaded, count 3-2.
      - OUTFIELD_ROBBERY (P1): Catch probability <= 25% or wall impact tag.
    NFL:
      - RED_ZONE_TURNOVER (P0): Interception or Fumble Recovery inside own or opponent 20-yard line.
      - DEEP_FIELD_GOAL (P0): Distance >= 50 yards in 4th quarter or < 2 minutes.
      - EXPLOSIVE_PLAY (P2): Gain >= 35 yards from scrimmage.
    """
    def __init__(self, enforce_safety_gate: bool = False):
        self.seen_events = set()
        self.safety_gate = PrecogSafetyGate()
        self.enforce_safety_gate = enforce_safety_gate

    @staticmethod
    def _to_float(val, default=None):
        if val is None or val == "---" or val == "":
            return default
        try:
            if isinstance(val, (int, float)):
                return float(val)
            val_clean = re.sub(r"[^\d.-]", "", str(val))
            return float(val_clean) if val_clean and val_clean != "-" and val_clean != "." else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _to_int(val, default=None):
        f = PrecogViralFilter._to_float(val, default=None)
        return int(f) if f is not None else default

    def evaluate_mlb(self, frame: dict, game_id: str = "") -> Optional[dict]:
        exit_velo = self._to_float(
            frame.get("exit_velocity_mph")
            or frame.get("exit_velocity")
            or frame.get("hit_speed")
            or frame.get("launch_speed")
            or frame.get("last_exit_velocity")
        )
        distance = self._to_float(
            frame.get("distance_feet")
            or frame.get("distance")
            or frame.get("hit_distance")
            or frame.get("projected_distance")
        )
        launch_angle = self._to_float(
            frame.get("launch_angle_deg") or frame.get("launch_angle")
        )
        event_type = str(frame.get("event_type") or "").strip().lower()
        desc = str(frame.get("status_msg") or frame.get("description") or frame.get("last_play_description") or "").lower()
        
        balls = self._to_int(frame.get("balls"), 0)
        strikes = self._to_int(frame.get("strikes"), 0)
        outs = self._to_int(frame.get("outs"), 0)
        
        on_1b = bool(frame.get("onFirst") or frame.get("on_1b"))
        on_2b = bool(frame.get("onSecond") or frame.get("on_2b"))
        on_3b = bool(frame.get("onThird") or frame.get("on_3b"))
        runners_on_list = frame.get("runners_on") or []
        bases_loaded = bool(
            frame.get("bases_loaded")
            or (on_1b and on_2b and on_3b)
            or len(runners_on_list) >= 3
        )

        catch_prob = self._to_float(
            frame.get("catch_probability") or frame.get("catch_prob") or frame.get("catch_pct")
        )
        wall_impact = bool(
            frame.get("wall_impact")
            or frame.get("wall_impact_tag")
            or "wall impact" in desc
            or "wall" in str(frame.get("tags", "")).lower()
        )

        qualified_type = None
        priority = None

        # 1. HOME_RUN (P0): Exit Velocity >= 100.0 mph, Distance >= 390.0 ft
        if exit_velo is not None and distance is not None:
            if exit_velo >= 100.0 and distance >= 390.0:
                qualified_type = "HOME_RUN"
                priority = "P0"

        # 2. BASES_LOADED_K (P1): Outs = 2 (or 3rd out recorded), bases loaded, count 3-2
        if not qualified_type:
            count_str = str(frame.get("count", "")).strip()
            is_full_count = (balls == 3 and strikes in (2, 3)) or (count_str in ("3-2", "3 - 2"))
            is_two_or_three_outs = outs in (2, 3) or frame.get("outs_when_up") == 2 or frame.get("final_out_of_inning") is True
            is_strikeout = (
                event_type in ("strikeout", "k", "strikeout_looking", "strikeout_swinging", "strike")
                or "strikeout" in desc
                or "struck out" in desc
                or strikes >= 3
            )
            if is_full_count and bases_loaded and is_two_or_three_outs and is_strikeout:
                qualified_type = "BASES_LOADED_K"
                priority = "P1"

        # 3. OUTFIELD_ROBBERY (P1): Catch probability <= 25% or wall impact tag
        if not qualified_type:
            is_robbery_event = (
                event_type in ("outfield_robbery", "robbery", "catch", "field_out", "flyout", "lineout")
                or "rob" in desc
                or "catch" in desc
                or wall_impact
                or (catch_prob is not None)
            )
            if is_robbery_event:
                qualifies_prob = catch_prob is not None and (catch_prob <= 0.25 or (catch_prob > 1.0 and catch_prob <= 25.0))
                if qualifies_prob or wall_impact:
                    qualified_type = "OUTFIELD_ROBBERY"
                    priority = "P1"

        if not qualified_type or not priority:
            return None

        # Assemble runners_on list
        if not runners_on_list:
            runners_on_list = []
            if on_1b: runners_on_list.append("1B")
            if on_2b: runners_on_list.append("2B")
            if on_3b: runners_on_list.append("3B")

        telemetry = {
            "batter": frame.get("batter") or frame.get("last_play_batter") or "Batter",
            "pitcher": frame.get("pitcher") or "Pitcher",
            "inning": frame.get("inning_half") or frame.get("inning") or "1",
            "outs": outs,
            "runners_on": runners_on_list,
            "exit_velocity_mph": exit_velo if exit_velo is not None else 0.0,
            "launch_angle_deg": launch_angle if launch_angle is not None else 0.0,
            "distance_feet": distance if distance is not None else 0.0,
            "pitch_type": frame.get("pitch_name") or frame.get("pitch_type") or "Fastball",
            "pitch_speed_mph": self._to_float(frame.get("pitch_speed"), 95.0),
            "win_expectancy_delta": frame.get("win_expectancy_delta") or "+15.0%"
        }
        if catch_prob is not None:
            telemetry["catch_probability"] = catch_prob
        if wall_impact:
            telemetry["wall_impact"] = True

        return self._format_payload("MLB", game_id, qualified_type, priority, telemetry)

    def evaluate_nfl(self, frame: dict, game_id: str = "") -> Optional[dict]:
        event_type = str(frame.get("event_type") or "").strip().lower()
        desc = str(frame.get("status_msg") or frame.get("last_play") or frame.get("description") or "").lower()

        yard_line = self._to_float(
            frame.get("yard_line") or frame.get("yardline") or frame.get("yard_line_100") or frame.get("distance_to_goal")
        )
        is_red_zone = bool(
            frame.get("is_red_zone")
            or "red zone" in desc
            or (yard_line is not None and (yard_line <= 20.0 or yard_line >= 80.0))
        )

        gain = self._to_float(
            frame.get("gain")
            or frame.get("yards_gained")
            or frame.get("scrimmage_gain")
            or frame.get("distance_yards")
            or frame.get("gain_yards")
        )
        fg_dist = self._to_float(
            frame.get("field_goal_distance") or frame.get("fg_distance") or frame.get("distance")
        )

        quarter_raw = frame.get("quarter") or frame.get("period") or 1
        quarter = self._to_int(quarter_raw, 1)
        quarter_str = str(quarter_raw).strip().upper()
        is_4th_or_ot = (quarter >= 4) or ("4" in quarter_str) or ("OT" in quarter_str)

        clock = str(frame.get("clock") or frame.get("time_remaining") or "").strip()
        time_rem_sec = self._to_float(frame.get("time_remaining_sec"))
        is_under_2_min = False
        if time_rem_sec is not None and time_rem_sec <= 120:
            is_under_2_min = True
        elif clock:
            m = re.match(r"^0?([0-9]+):([0-9]{2})$", clock)
            if m:
                mins, secs = int(m.group(1)), int(m.group(2))
                if (mins * 60 + secs) <= 120:
                    is_under_2_min = True
        if "2:00" in desc or "two-minute" in desc or "under 2 min" in desc:
            is_under_2_min = True

        qualified_type = None
        priority = None

        # 1. RED_ZONE_TURNOVER (P0): Interception or Fumble Recovery inside own or opponent 20-yard line
        is_turnover = (
            event_type in ("interception", "fumble", "fumble_recovery", "turnover", "int", "fumble_lost", "fumble_turnover")
            or "interception" in desc
            or "intercepted" in desc
            or "fumble" in desc
            or "recovered by" in desc
            or "picked off" in desc
        )
        if is_turnover and is_red_zone:
            qualified_type = "RED_ZONE_TURNOVER"
            priority = "P0"

        # 2. DEEP_FIELD_GOAL (P0): Distance >= 50 yards in 4th quarter or < 2 minutes
        if not qualified_type:
            is_fg = (
                event_type in ("field_goal", "fg", "field_goal_good", "field_goal_attempt", "field_goal_made")
                or "field goal" in desc
                or "fg" in desc
            )
            dist_val = fg_dist if fg_dist is not None else gain
            if is_fg and dist_val is not None and dist_val >= 50.0 and (is_4th_or_ot or is_under_2_min):
                qualified_type = "DEEP_FIELD_GOAL"
                priority = "P0"

        # 3. EXPLOSIVE_PLAY (P2): Gain >= 35 yards from scrimmage
        if not qualified_type:
            is_sack_fumble = ("sack" in event_type or "sack" in desc) and ("fumble" in event_type or "fumble" in desc)
            if (gain is not None and gain >= 35.0) or is_sack_fumble:
                qualified_type = "EXPLOSIVE_PLAY"
                priority = "P2"

        if not qualified_type or not priority:
            return None

        telemetry = {
            "passer": frame.get("passer") or frame.get("qb") or "",
            "runner": frame.get("runner") or frame.get("ball_carrier") or "",
            "tackler": frame.get("tackler") or "",
            "description": desc or frame.get("status_msg") or "",
            "down_dist": frame.get("down_dist") or "",
            "yard_line": yard_line if yard_line is not None else 0.0,
            "gain_yards": gain if gain is not None else 0.0,
            "field_goal_distance": fg_dist if fg_dist is not None else 0.0,
            "quarter": quarter_raw,
            "clock": clock,
            "win_expectancy_delta": frame.get("win_expectancy_delta") or "+10.0%"
        }

        return self._format_payload("NFL", game_id, qualified_type, priority, telemetry)

    def evaluate(self, frame: dict, sport: str = None, game_id: str = "") -> Optional[dict]:
        if not frame:
            return None
        
        # Auto-detect sport if not specified
        if not sport:
            if "down_dist" in frame or "quarter" in frame or "yard_line" in frame or "scrimmage_gain" in frame:
                sport = "NFL"
            else:
                sport = "MLB"
        
        sport = sport.upper().strip()
        result = None
        if sport == "MLB":
            result = self.evaluate_mlb(frame, game_id=game_id)
        elif sport == "NFL":
            result = self.evaluate_nfl(frame, game_id=game_id)

        if not result:
            return None

        # Deduplication check
        dedup_key = f"{result['sport']}_{result['game_id']}_{result['event_type']}_{result['telemetry'].get('batter', '')}_{result['telemetry'].get('exit_velocity_mph', '')}_{result['telemetry'].get('description', '')}"
        if dedup_key in self.seen_events:
            return None
        
        if self.enforce_safety_gate:
            if not self.safety_gate.validate_dispatch(key=result['game_id'], priority=result['viral_priority'], enforce=True):
                return None

        self.seen_events.add(dedup_key)
        if len(self.seen_events) > 1000:
            self.seen_events.clear()

        return result

    def _format_payload(self, sport: str, game_id: str, event_type: str, priority: str, telemetry: dict) -> dict:
        now = datetime.now(timezone.utc)
        timestamp_utc = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        expected_tv_impact_utc = (now + timedelta(seconds=34.5)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        clean_game_id = str(game_id).replace(" ", "_").lower() if game_id else "global"
        event_id = f"precog_{sport.lower()}_{now.strftime('%Y%m%d')}_{clean_game_id}_{uuid.uuid4().hex[:4]}"

        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "event_id": event_id,
            "timestamp_utc": timestamp_utc,
            "sport": sport,
            "game_id": str(game_id),
            "event_type": event_type,
            "viral_priority": priority,
            "telemetry": telemetry,
            "broadcast_sync": {
                "estimated_ott_delay_sec": 34.5,
                "expected_tv_impact_utc": expected_tv_impact_utc
            }
        }


global_precog_filter = PrecogViralFilter()

def persist_precog_latest(payload: dict, file_path: str = PRECOG_LATEST_FILE):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        tmp_path = f"{file_path}.tmp.{os.getpid()}_{uuid.uuid4().hex[:6]}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, file_path)
        print(f"[PRECOG STORAGE] Atomically persisted latest precog event {payload.get('event_id')} to {file_path}")
    except Exception as e:
        print(f"[PRECOG STORAGE ERROR] Failed to persist {file_path}: {e}")

async def broadcast_precog_event(ws, precog_payload: dict):
    try:
        msg = {
            "type": "creator_precog_event",
            "channel": "creator_precog_bus",
            "room_id": "creator_precog_bus",
            "event": "precog_event",
            "data": precog_payload,
            **precog_payload
        }
        await ws.send(json.dumps(msg))
        print(f"[PRECOG EMIT] Broadcasted {precog_payload['viral_priority']} {precog_payload['event_type']} to creator_precog_bus on Port 8008")
    except Exception as e:
        print(f"[PRECOG EMIT ERROR] Failed to broadcast over WebSocket: {e}")

async def evaluate_precog(ws, game_id, event_frame, sport=None):
    try:
        precog_payload = global_precog_filter.evaluate(event_frame, sport=sport, game_id=str(game_id))
        if precog_payload:
            persist_precog_latest(precog_payload)
            if ws:
                await broadcast_precog_event(ws, precog_payload)
            
            # Log to SQLite game_tmi_event
            try:
                con = sqlite3.connect(DB_PATH)
                c = con.cursor()
                c.execute("""
                    INSERT INTO game_tmi_event (
                        id, game_pk, name, description, payload, 
                        icon, triggered, triggered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    precog_payload["event_id"],
                    str(precog_payload["game_id"]),
                    f"PRECOG_{precog_payload['viral_priority']}_{precog_payload['event_type']}",
                    f"Precog Viral Filter qualified {precog_payload['viral_priority']} {precog_payload['event_type']}",
                    json.dumps(precog_payload),
                    "precog_radar",
                    1,
                    datetime.now(timezone.utc).isoformat()
                ))
                con.commit()
                con.close()
            except Exception as dbe:
                print(f"[TMI DAEMON] DB log error for precog event: {dbe}")

            # Trigger Advocate Banter VFS folder generation for precog high-leverage event
            try:
                from scripts.faas_advocate_banter_engine import generate_event
                ev_type = precog_payload.get("event_type", "CHAT_SPIKE")
                priority = precog_payload.get("viral_priority", "HIGH")
                game_title = f"{precog_payload.get('sport', '')} {game_id}"
                generate_event(event_type=ev_type, game_name=game_title, leverage=priority)
                print(f"[TMI DAEMON] Generated advocate banter VFS event for {ev_type}")
            except Exception as be:
                print(f"[TMI DAEMON] Banter engine hook error: {be}")

            return precog_payload
    except Exception as pe:
        print(f"[PRECOG VIRAL FILTER ERROR] {pe}")
    return None

# Cache of recently triggered events to prevent multiple triggers for the same state
# Format: "game_pk_rule_id_inning_outs_balls_strikes"
triggered_cache = set()

# Cache of last known scores per game to detect run-scoring events
# Format: game_pk -> (last_away_score, last_home_score)
score_cache = {}

# Rate-limiting state for momentum triggers (game_pk -> timestamp)
last_momentum_trigger = {}

# State for tracking no-hitter tension trigger (game_pk -> bool)
no_hitter_tension_triggered = {}

# Helper for comparing operators
def evaluate_condition(current_val, op_str, threshold_val):
    if current_val == "---" or current_val is None:
        return False
        
    try:
        # Convert to floats for numeric comparison if possible
        val_f = float(current_val)
        thresh_f = float(threshold_val)
    except (ValueError, TypeError):
        # Fallback to string comparison
        val_f = str(current_val).strip()
        thresh_f = str(threshold_val).strip()
        
    ops = {
        '>=': operator.ge,
        '<=': operator.le,
        '=': operator.eq,
        '>': operator.gt,
        '<': operator.lt,
    }
    
    if op_str == 'CONTAINS':
        return str(thresh_f).lower() in str(val_f).lower()
        
    if op_str in ops:
        try:
            return ops[op_str](val_f, thresh_f)
        except Exception:
            return False
            
    return False

# Map the telemetry field in database to our payload's keys
def get_telemetry_value(field_name, data):
    f = field_name.lower().strip()
    if 'launch_speed' in f or 'hit_speed' in f:
        return data.get("hit_speed")
    elif 'launch_angle' in f:
        return data.get("launch_angle")
    elif 'hit_distance' in f:
        return data.get("hit_distance")
    elif 'pitch_speed' in f or 'velocity' in f:
        return data.get("pitch_speed")
        
    # Check exact key first
    if field_name in data:
        return data[field_name]
    # Check case-insensitive key matching
    for k, v in data.items():
        if k.lower() == f:
            return v
    return None

MAM_DB_PATH = "/home/james/stacklabs/dna/mam_warehouse.db"

# Helpers for dynamic logic evaluation
def resolve_var(var_path, data):
    parts = var_path.split('.')
    curr = data
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        elif isinstance(curr, dict):
            # Check case-insensitive key
            matched = False
            for k, v in curr.items():
                if k.lower() == p.lower():
                    curr = v
                    matched = True
                    break
            if not matched:
                return None
        else:
            return None
    return curr

def evaluate_json_node(node, data):
    if not isinstance(node, dict):
        return bool(node)
        
    if "and" in node:
        return all(evaluate_json_node(item, data) for item in node["and"])
    if "or" in node:
        return any(evaluate_json_node(item, data) for item in node["or"])
        
    for op, args in node.items():
        if op in (">", "<", ">=", "<=", "==", "!=", "contains", "CONTAINS"):
            if not isinstance(args, list) or len(args) != 2:
                continue
            lhs, rhs = args[0], args[1]
            
            # Resolve LHS
            if isinstance(lhs, dict) and "var" in lhs:
                lhs_val = resolve_var(lhs["var"], data)
            else:
                lhs_val = lhs
                
            # Resolve RHS
            if isinstance(rhs, dict) and "var" in rhs:
                rhs_val = resolve_var(rhs["var"], data)
            else:
                rhs_val = rhs
                
            return evaluate_condition(lhs_val, op.upper() if op.lower() == "contains" else op, rhs_val)
            
    return False

import re
def evaluate_string_condition(cond_str, data):
    cond_str = cond_str.strip()
    m = re.match(r"^([a-zA-Z0-9_\.]+)\s*(>=|<=|>|<|=|contains|CONTAINS)\s*(.+)$", cond_str, re.IGNORECASE)
    if not m:
        return False
    var_path, op_str, val_str = m.groups()
    val_str = val_str.strip().strip("'\"")
    lhs_val = resolve_var(var_path, data)
    return evaluate_condition(lhs_val, op_str.upper(), val_str)

def check_hits_in_db(game_pk):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM game_play WHERE game_pk = ? AND event_type = 'hit'", (str(game_pk),))
        count = c.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"[TMI DAEMON] Error checking hits in DB: {e}")
        return False

def get_matching_asset(target_asset_type):
    if not os.path.exists(MAM_DB_PATH):
        return None
    try:
        conn = sqlite3.connect(MAM_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM media_assets 
            WHERE mime_type LIKE ? OR file_path LIKE ? 
            ORDER BY created_at DESC LIMIT 1
        """, (f"%{target_asset_type}%", f"%{target_asset_type}%"))
        row = c.fetchone()
        
        # Fallback to any recent asset if none matched specifically
        if not row:
            c.execute("SELECT * FROM media_assets ORDER BY created_at DESC LIMIT 1")
            row = c.fetchone()
            
        if row:
            asset_dict = dict(row)
            metadata_rows = c.execute(
                "SELECT key, value FROM asset_metadata WHERE asset_id = ?", 
                (asset_dict["asset_id"],)
            ).fetchall()
            meta = {}
            for r in metadata_rows:
                try:
                    meta[r["key"]] = json.loads(r["value"])
                except Exception:
                    meta[r["key"]] = r["value"]
            asset_dict["metadata"] = meta
            conn.close()
            return asset_dict
        conn.close()
    except Exception as e:
        print(f"[TMI DAEMON] Error matching asset: {e}")
    return None

async def evaluate_rules(ws, game_pk, event_frame):
    event_type = event_frame.get("event_type", "pitch")
    batting_team = event_frame.get("batting_team", "")
    inning = event_frame.get("inning", "")
    outs = event_frame.get("outs", 0)
    balls = event_frame.get("balls", 0)
    strikes = event_frame.get("strikes", 0)
    game_status = str(event_frame.get("game_status", "live")).lower()
    
    # A. Evaluate Legacy Rules from sys_tmi_telemetry_map
    legacy_rules = []
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        c = con.cursor()
        c.execute("""
            SELECT id, trigger_rule_name, statcast_event_type, telemetry_field, 
                   operator_comparison, comparison_value, batting_team_filter, 
                   target_webslinger_event_id
            FROM sys_tmi_telemetry_map
            WHERE active_status = 1 AND is_automated_ingress = 1
        """)
        legacy_rules = [dict(r) for r in c.fetchall()]
        con.close()
    except Exception as e:
        print(f"[TMI DAEMON] Legacy DB query error: {e}")

    for rule in legacy_rules:
        rule_id = rule["id"]
        rule_event_type = rule["statcast_event_type"]
        rule_team_filter = rule["batting_team_filter"]
        rule_name = rule["trigger_rule_name"]
        
        if game_status == "final":
            trigger_key = f"{game_pk}_{rule_id}_final"
        else:
            trigger_key = f"{game_pk}_{rule_id}_{inning}_{outs}_{balls}_{strikes}"

        if trigger_key in triggered_cache:
            continue
            
        event_match = False
        if rule_event_type in ('runs_scored', 'score'):
            if int(event_frame.get("runs_scored") or 0) > 0:
                event_match = True
        elif rule_event_type == event_type:
            event_match = True
        elif rule_event_type == 'hit' and event_type == 'home_run':
            event_match = True
            
        if not event_match:
            continue

        if rule_team_filter and batting_team != rule_team_filter:
            triggered_cache.add(trigger_key)
            continue
            
        current_val = get_telemetry_value(rule["telemetry_field"], event_frame)
        comparison_op = rule["operator_comparison"]
        threshold_val = rule["comparison_value"]
        if current_val is None or current_val == "---":
            continue
            
        print(f"[TMI DEBUG] Ingested rule '{rule_name}' (ID {rule_id}). Field: '{rule['telemetry_field']}' = {current_val} {comparison_op} {threshold_val}. Game Status: '{game_status}'")

        if evaluate_condition(current_val, comparison_op, threshold_val):
            try:
                con = sqlite3.connect(DB_PATH)
                c = con.cursor()
                c.execute("""
                    SELECT event_name, payload_template 
                    FROM sys_webslinger_event 
                    WHERE id = ?
                """, (rule["target_webslinger_event_id"],))
                row = c.fetchone()
                con.close()
            except Exception as e:
                print(f"[TMI DAEMON] Failed to fetch webslinger event details: {e}")
                continue
                
            if row:
                ws_event_name, payload_template_str = row
                
                # Strict Game-Status Gating for Post-Game Overlays
                if ws_event_name in ("METS_WIN_OVERLAY", "METS_BLOW_IT_OVERLAY") and game_status != "final":
                    print(f"[TMI DEBUG] Suppressed trigger '{ws_event_name}' for rule '{rule_name}' (ID {rule_id}): game_status is '{game_status}' (requires 'final')")
                    triggered_cache.add(trigger_key)
                    continue

                try:
                    payload_data = json.loads(payload_template_str)
                except Exception:
                    payload_data = {}
                    
                print(f"[TMI DAEMON] Rule '{rule_name}' MATCHED! Telemetry value {current_val} {comparison_op} {threshold_val} for {batting_team}.")
                
                trigger_msg = {
                    "event": "webslinger_trigger",
                    "event_name": ws_event_name,
                    "room_id": str(game_pk),
                    "data": payload_data
                }
                try:
                    await ws.send(json.dumps(trigger_msg))
                    print(f"[TMI DAEMON] Broadcast webslinger_trigger '{ws_event_name}' to room {game_pk}")
                except Exception as ws_err:
                    print(f"[TMI DAEMON] Failed to send trigger over websocket: {ws_err}")
                
                try:
                    event_id = uuid.uuid4().hex
                    triggered_at = datetime.utcnow().isoformat()
                    payload_json = json.dumps({
                        "webslinger_trigger": trigger_msg,
                        "statcast_frame": event_frame
                    })
                    
                    con = sqlite3.connect(DB_PATH)
                    c = con.cursor()
                    c.execute("""
                        INSERT INTO game_tmi_event (
                            id, game_pk, name, description, payload, 
                            icon, triggered, triggered_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event_id,
                        str(game_pk),
                        ws_event_name,
                        f"Rule '{rule_name}' triggered webslinger event '{ws_event_name}'",
                        payload_json,
                        "webslinger",
                        1,
                        triggered_at
                    ))
                    con.commit()
                    con.close()
                except Exception as db_err:
                    print(f"[TMI DAEMON] Failed to log webslinger trigger to database: {db_err}")
                
                triggered_cache.add(trigger_key)

    # B. Evaluate Unified MAM Rules from mam_warehouse.db
    mam_rules = []
    if os.path.exists(MAM_DB_PATH):
        try:
            conn = sqlite3.connect(MAM_DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
                SELECT rule_id, condition, conditions_json, action, target_asset_type
                FROM tmi_rules
                WHERE active_status = 1
            """)
            mam_rules = [dict(r) for r in c.fetchall()]
            conn.close()
        except Exception as e:
            print(f"[TMI DAEMON] MAM DB query error: {e}")

    for rule in mam_rules:
        rule_id = rule["rule_id"]
        action = rule["action"]
        target_asset_type = rule["target_asset_type"]
        
        if game_status == "final":
            trigger_key = f"{game_pk}_mam_{rule_id}_final"
        else:
            trigger_key = f"{game_pk}_mam_{rule_id}_{inning}_{outs}_{balls}_{strikes}"

        if trigger_key in triggered_cache:
            continue
            
        matched = False
        if rule.get("conditions_json"):
            try:
                node = json.loads(rule["conditions_json"])
                matched = evaluate_json_node(node, event_frame)
            except Exception as le:
                print(f"[TMI DAEMON] Error parsing/evaluating JSON Logic: {le}")
        
        if not matched and rule.get("condition"):
            try:
                matched = evaluate_string_condition(rule["condition"], event_frame)
            except Exception as se:
                print(f"[TMI DAEMON] Error parsing/evaluating string condition: {se}")
                
        if matched:
            print(f"[TMI DAEMON] MAM Rule '{rule_id}' MATCHED!")
            asset = get_matching_asset(target_asset_type)
            
            asset_id = asset["asset_id"] if asset else None
            file_path = asset["file_path"] if asset else None
            mime_type = asset["mime_type"] if asset else None
            metadata = asset["metadata"] if asset else {}
            
            trigger_msg = {
                "event": "media_trigger",
                "room_id": str(game_pk),
                "data": {
                    "rule_id": rule_id,
                    "action": action,
                    "asset_id": asset_id,
                    "file_path": file_path,
                    "mime_type": mime_type,
                    "metadata": metadata
                }
            }
            try:
                await ws.send(json.dumps(trigger_msg))
                print(f"[TMI DAEMON] Broadcast media_trigger to room {game_pk} for asset {asset_id}")
            except Exception as ws_err:
                print(f"[TMI DAEMON] Failed to send media_trigger: {ws_err}")
                
            try:
                event_id = uuid.uuid4().hex
                triggered_at = datetime.utcnow().isoformat()
                payload_json = json.dumps({
                    "media_trigger": trigger_msg,
                    "statcast_frame": event_frame
                })
                
                con = sqlite3.connect(DB_PATH)
                c = con.cursor()
                c.execute("""
                    INSERT INTO game_tmi_event (
                        id, game_pk, name, description, payload, 
                        icon, triggered, triggered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    str(game_pk),
                    f"MAM Rule {rule_id}",
                    f"MAM Rule '{rule_id}' triggered media action '{action}' on asset '{asset_id}'",
                    payload_json,
                    "media",
                    1,
                    triggered_at
                ))
                con.commit()
                con.close()
            except Exception as db_err:
                print(f"[TMI DAEMON] Failed to log media trigger: {db_err}")
                
            triggered_cache.add(trigger_key)

async def main_loop():
    print("🤖 Sovereign OS TMI Telemetry Daemon booting...")
    print(f"[*] Target DB: {DB_PATH}")
    print(f"[*] Target WS: {WS_URL}")
    
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                print("[✔] Connected to Sovereign WebSocket Relay.")
                
                # Join the global pool
                join_msg = {"type": "JOIN_ROOM", "room_id": "GLOBAL"}
                await ws.send(json.dumps(join_msg))
                
                async for message in ws:
                    try:
                        data = json.loads(message)
                    except Exception:
                        continue
                        
                    if data.get("type") == "STATE_UPDATE":
                        event_frame = data.get("data", {})
                        game_pk = data.get("target_game_pk")
                        if event_frame and game_pk:
                            # Extract scores
                            away_score = 0
                            home_score = 0
                            try:
                                away_score = int(event_frame.get("away_score") or 0)
                            except (ValueError, TypeError):
                                pass
                            try:
                                home_score = int(event_frame.get("home_score") or 0)
                            except (ValueError, TypeError):
                                pass
                            
                            runs_scored = 0
                            if game_pk in score_cache:
                                prev_away, prev_home = score_cache[game_pk]
                                batting_team = event_frame.get("batting_team", "")
                                away_team = event_frame.get("away_team", "")
                                home_team = event_frame.get("home_team", "")
                                
                                # If batting team matches away or home, check if they scored
                                if batting_team and batting_team == away_team:
                                    runs_scored = max(0, away_score - prev_away)
                                elif batting_team and batting_team == home_team:
                                    runs_scored = max(0, home_score - prev_home)
                                else:
                                    # Fallback: sum of both scores
                                    runs_scored = max(0, (away_score + home_score) - (prev_away + prev_home))
                            
                            # Update cache
                            score_cache[game_pk] = (away_score, home_score)
                            
                            # Inject runs_scored
                            event_frame["runs_scored"] = runs_scored
                            
                            await evaluate_rules(ws, game_pk, event_frame)
                            await evaluate_precog(ws, game_pk, event_frame)
                            
                            # --- Custom Evaluation WO-2026-117: Sudden Momentum Shift ---
                            event_type = event_frame.get("event_type")
                            delta_score = event_frame.get("delta_score")
                            try:
                                if delta_score is not None:
                                    delta_score = int(delta_score)
                                else:
                                    delta_score = runs_scored
                            except (ValueError, TypeError):
                                delta_score = runs_scored

                            inning_half = event_frame.get("inning_half") or event_frame.get("half") or ""
                            if inning_half:
                                inning_half = inning_half.lower()

                            if event_type == "scoring" and delta_score >= 3 and "bot" in inning_half:
                                current_time = time.time()
                                last_trigger = last_momentum_trigger.get(str(game_pk), 0)
                                if current_time - last_trigger >= 600:
                                    last_momentum_trigger[str(game_pk)] = current_time
                                    asset = get_matching_asset("RALLY_SKELETON_DANCE")
                                    trigger_msg = {
                                        "event": "media_trigger",
                                        "room_id": str(game_pk),
                                        "data": {
                                            "rule_id": "rule_momentum_shift",
                                            "action": "overlay_play",
                                            "asset_id": asset["asset_id"] if asset else "RALLY_SKELETON_DANCE",
                                            "file_path": asset["file_path"] if asset else "/production/assets/sprint4/[PROCESSED]_RALLY_SKELETON_DANCE.mp4",
                                            "mime_type": "video/mp4",
                                            "metadata": {}
                                        }
                                    }
                                    await ws.send(json.dumps(trigger_msg))
                                    print(f"[TMI DAEMON] Momentum shift matched. Sent media_trigger for RALLY_SKELETON_DANCE")

                            # --- Custom Evaluation WO-2026-119: No-Hitter Tension Gradient ---
                            inning_str = event_frame.get("inning", "1")
                            try:
                                inning_num = int(re.sub(r'\D', '', str(inning_str)))
                            except (ValueError, TypeError):
                                inning_num = 1

                            hit_occurred = check_hits_in_db(game_pk) or (event_type == "hit")
                            if hit_occurred:
                                if no_hitter_tension_triggered.get(str(game_pk), False):
                                    no_hitter_tension_triggered[str(game_pk)] = False
                                    trigger_msg = {
                                        "event": "media_trigger",
                                        "room_id": str(game_pk),
                                        "data": {
                                            "rule_id": "rule_no_hitter_tension",
                                            "action": "shader_tension_clear",
                                            "asset_id": None,
                                            "file_path": None,
                                            "mime_type": None,
                                            "metadata": {}
                                        }
                                    }
                                    await ws.send(json.dumps(trigger_msg))
                                    print(f"[TMI DAEMON] No-hitter broken! Deactivating level 3 tension shader.")
                            elif inning_num >= 7:
                                if not no_hitter_tension_triggered.get(str(game_pk), False):
                                    no_hitter_tension_triggered[str(game_pk)] = True
                                    asset = get_matching_asset("LEVEL_3_TENSION")
                                    trigger_msg = {
                                        "event": "media_trigger",
                                        "room_id": str(game_pk),
                                        "data": {
                                            "rule_id": "rule_no_hitter_tension",
                                            "action": "shader_tension_level_3",
                                            "asset_id": asset["asset_id"] if asset else "LEVEL_3_TENSION",
                                            "file_path": asset["file_path"] if asset else "/production/assets/sprint4/[PROCESSED]_LEVEL_3_TENSION.mp4",
                                            "mime_type": "video/mp4",
                                            "metadata": {}
                                        }
                                    }
                                    await ws.send(json.dumps(trigger_msg))
                                    print(f"[TMI DAEMON] Potential no-hitter in inning {inning_num}! Activating level 3 tension shader.")

                    # --- Custom Evaluation WO-2026-118: Umpire Review Handler ---
                    msg_type = data.get("type")
                    if msg_type == "official_review_start":
                        game_pk = data.get("target_game_pk") or data.get("game_pk")
                        if game_pk:
                            asset = get_matching_asset("REVIEW_IN_PROGRESS")
                            trigger_msg = {
                                "event": "media_trigger",
                                "room_id": str(game_pk),
                                "data": {
                                    "rule_id": "rule_umpire_review",
                                    "action": "overlay_loop",
                                    "asset_id": asset["asset_id"] if asset else "REVIEW_IN_PROGRESS",
                                    "file_path": asset["file_path"] if asset else "/production/assets/sprint4/[PROCESSED]_REVIEW_IN_PROGRESS.mp4",
                                    "mime_type": "video/mp4",
                                    "metadata": {}
                                }
                            }
                            await ws.send(json.dumps(trigger_msg))
                            print(f"[TMI DAEMON] Official review started. Sent media_trigger for REVIEW_IN_PROGRESS")
                            
                    elif msg_type in ["official_review_end", "official_review_override", "official_review_clear"]:
                        game_pk = data.get("target_game_pk") or data.get("game_pk")
                        if game_pk:
                            trigger_msg = {
                                "event": "media_trigger",
                                "room_id": str(game_pk),
                                "data": {
                                    "rule_id": "rule_umpire_review",
                                    "action": "overlay_clear",
                                    "asset_id": None,
                                    "file_path": None,
                                    "mime_type": None,
                                    "metadata": {}
                                }
                            }
                            await ws.send(json.dumps(trigger_msg))
                            print(f"[TMI DAEMON] Official review ended/cleared. Sent media_clear")

                    elif msg_type in ("PRECOG_INGRESS", "STATCAST_FRAME", "NFL_FRAME", "PRECOG_TRIGGER"):
                        event_frame = data.get("data") or data.get("telemetry") or data
                        sport = data.get("sport") or event_frame.get("sport") or ("NFL" if ("down_dist" in event_frame or "quarter" in event_frame) else "MLB")
                        game_id = data.get("game_id") or data.get("game_pk") or event_frame.get("game_pk") or "global"
                        await evaluate_precog(ws, game_id, event_frame, sport=sport)

        except (websockets.exceptions.ConnectionClosedError, OSError) as e:
            print(f"[!] WebSocket disconnected or connection failed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[ERROR] Daemon crash: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("[*] Daemon shut down by user.")

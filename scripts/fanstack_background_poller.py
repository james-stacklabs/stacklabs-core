import asyncio
import websockets
import json
import os
import datetime as dt
import traceback
import sys
import time
import requests
import argparse
import subprocess
import uuid
from pathlib import Path

SOVEREIGN_ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("--start-play-index", type=int, default=None, help="Index to start polling from")
parser.add_argument("--game-id", type=str, default=None, help="Specific game ID to poll")
parser.add_argument("--port", type=int, default=8008, help="WebSocket Relay port")
args, unknown = parser.parse_known_args()

WS_URL         = f"ws://localhost:{args.port}"
START_PLAY_INDEX = args.start_play_index
TARGET_GAME_ID = args.game_id

SCHEDULE_URL   = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
LIVE_FEED_BASE = "https://statsapi.mlb.com/api/v1.1/game/{}/feed/live"
GAME_STATE_DIR = "/home/james/stacklabs/game_states"

last_status_map = {}
last_sit_down_map = {}
delay_state_map = {}
blowout_state_map = {}
game_count_states = {}
game_payoff_batters = {}
game_payoff_pitchers = {}
game_payoff_batter_ids = {}
game_payoff_pitcher_ids = {}
extra_innings_notified = {}
whiff_anomalies_notified = {}
schedule_cache = None
last_schedule_time = 0
last_poll_times = {}
last_game_status = {}

_pitcher_stats_cache = {}

def get_pitcher_season_stats(person_id: int):
    if not person_id:
        return {}
    if person_id in _pitcher_stats_cache:
        return _pitcher_stats_cache[person_id]
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{person_id}?hydrate=stats(group=[pitching],type=[season])"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if res.status_code == 200:
            d = res.json()
            people = d.get("people", [])
            if people:
                stats_list = people[0].get("stats", [])
                if stats_list:
                    splits = stats_list[0].get("splits", [])
                    if splits:
                        stat = splits[0].get("stat", {})
                        era = str(stat.get("era", "---"))
                        w = stat.get("wins", 0)
                        l = stat.get("losses", 0)
                        result = {"era": era, "record": f"{w}-{l}", "wins": str(w), "losses": str(l)}
                        _pitcher_stats_cache[person_id] = result
                        return result
    except Exception as e:
        print(f"[POLLER] Error fetching season stats for pitcher {person_id}: {e}")
    return {}

async def _fetch_json(url):
    try:
        res = await asyncio.to_thread(requests.get, url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except Exception as e:
        return None


def _write_game_state_cache(game_pk: int, feed: dict, payload_data: dict) -> None:
    """
    Atomically serialize the live game state to a local disk cache.

    Called ONLY when state_hash changes — no disk I/O on no-op poll ticks.
    Uses write-to-tmp + os.replace() for atomic delivery: a reader in
    game_cache_reader.py always sees a complete document, never a partial write.

    Args:
        game_pk:      MLB game primary key (int).
        feed:         Full raw feed/live JSON dict from the MLB StatsAPI.
        payload_data: The already-computed thin summary dict (payload["data"]).
    """
    import datetime as _dt

    os.makedirs(GAME_STATE_DIR, exist_ok=True)
    target_path = os.path.join(GAME_STATE_DIR, f"{game_pk}.json")

    # Extract inning-by-inning scoring detail from the full linescore.
    # This is what get_inning_context() in game_cache_reader.py consumes.
    innings_data = feed.get("liveData", {}).get("linescore", {}).get("innings", [])

    # Build a ring buffer of the last 10 play descriptions.
    # This is what get_recent_plays() in game_cache_reader.py consumes.
    all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    recent_plays = []
    for play in all_plays[-10:]:
        result  = play.get("result", {})
        desc    = result.get("description", "")
        event   = result.get("event", "")
        inn_num = play.get("about", {}).get("inning", "?")
        half    = "Top" if play.get("about", {}).get("isTopInning", True) else "Bot"
        if desc:
            recent_plays.append({
                "inning":      f"{half} {inn_num}",
                "event":       event,
                "description": desc,
            })

    doc = {
        "game_pk":        game_pk,
        "last_updated":   _dt.datetime.utcnow().isoformat() + "Z",
        "status":         (payload_data.get("game_status") or "Live").title(),
        "game_status":    payload_data.get("game_status", "live"),
        "detailed_status": payload_data.get("detailed_status", ""),
        "away_team":      payload_data.get("away_team"),
        "home_team":      payload_data.get("home_team"),
        "away_score":     payload_data.get("away_score"),
        "home_score":     payload_data.get("home_score"),
        "inning":         payload_data.get("inning"),
        "outs":           payload_data.get("outs"),
        "balls":          payload_data.get("balls"),
        "strikes":        payload_data.get("strikes"),
        "pitcher":        payload_data.get("pitcher"),
        "batter":         payload_data.get("batter"),
        "pitch_name":     payload_data.get("pitch_name"),
        "pitch_speed":    payload_data.get("pitch_speed"),
        "hit_speed":      payload_data.get("hit_speed"),
        "hit_distance":   payload_data.get("hit_distance"),
        "launch_angle":   payload_data.get("launch_angle"),
        "hit_coord_x":    payload_data.get("hit_coord_x"),
        "hit_coord_y":    payload_data.get("hit_coord_y"),
        "status_msg":     payload_data.get("status_msg"),
        "innings_detail": innings_data,
        "recent_plays":   recent_plays,
        "venue_name":     payload_data.get("venue_name"),
        "venue_location": payload_data.get("venue_location"),
        "batter_id":      payload_data.get("batter_id"),
        "pitcher_id":     payload_data.get("pitcher_id"),
        "batter_avg":      payload_data.get("batter_avg"),
        "batter_obp":      payload_data.get("batter_obp"),
        "batter_slg":      payload_data.get("batter_slg"),
        "batter_ops":      payload_data.get("batter_ops"),
        "batter_hr":       payload_data.get("batter_hr"),
        "batter_rbi":      payload_data.get("batter_rbi"),
        "pitcher_era":     payload_data.get("pitcher_era"),
        "pitcher_whip":    payload_data.get("pitcher_whip"),
        "pitcher_wins":    payload_data.get("pitcher_wins"),
        "pitcher_losses":  payload_data.get("pitcher_losses"),
        "pitcher_so":      payload_data.get("pitcher_so"),
        "pitcher_ip":      payload_data.get("pitcher_ip"),
        "away_record":     payload_data.get("away_record"),
        "home_record":     payload_data.get("home_record"),
        "probable_pitcher_away": payload_data.get("probable_pitcher_away"),
        "probable_pitcher_home": payload_data.get("probable_pitcher_home"),
        "pitches_this_ab":       payload_data.get("pitches_this_ab", []),
    }

    # Atomic write: tmp file → os.replace().
    # os.replace() is a POSIX rename — atomic on the same filesystem.
    # Readers in game_cache_reader.py can never observe a half-written file.
    tmp_path = target_path + ".tmp"
    with open(tmp_path, "w") as fh:
        json.dump(doc, fh)
    os.replace(tmp_path, target_path)


DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def get_db(row_factory=True):
    import sqlite3
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def _record_telemetry_audit(game_pk: int, feed: dict, payload_data: dict) -> None:
    """
    Persist an audit comparison record into mlb_telemetry_audit_ledger.
    Compares our broadcast payload against raw MLB StatsAPI ground-truth.
    """
    try:
        import uuid
        linescore = feed.get("liveData", {}).get("linescore", {})
        plays = feed.get("liveData", {}).get("plays", {})
        targetPlay = plays.get("currentPlay", {})
        
        mlb_inning_state = linescore.get("inningState", "")
        mlb_is_top = 1 if linescore.get("isTopInning", True) else 0
        mlb_outs = linescore.get("outs", 0)
        mlb_balls = linescore.get("balls", 0)
        mlb_strikes = linescore.get("strikes", 0)
        mlb_batter = targetPlay.get("matchup", {}).get("batter", {}).get("fullName", "")
        mlb_pitcher = targetPlay.get("matchup", {}).get("pitcher", {}).get("fullName", "")
        
        events = targetPlay.get("playEvents", [])
        mlb_p_speed = None
        mlb_p_name = None
        for ev in reversed(events):
            if ev.get("pitchData") and mlb_p_speed is None:
                mlb_p_speed = ev["pitchData"].get("startSpeed")
                mlb_p_name = ev.get("details", {}).get("type", {}).get("description")
                break
        mlb_play_desc = targetPlay.get("result", {}).get("description", "")
        
        our_inning = str(payload_data.get("inning", ""))
        our_half = our_inning.split()[0] if our_inning else ""
        our_outs = int(payload_data.get("outs", 0))
        our_balls = int(payload_data.get("balls", 0))
        our_strikes = int(payload_data.get("strikes", 0))
        our_batter = str(payload_data.get("batter", ""))
        our_batter_id = payload_data.get("batter_id")
        our_pitcher = str(payload_data.get("pitcher", ""))
        our_pitcher_id = payload_data.get("pitcher_id")
        
        try:
            our_pitch_speed = float(payload_data.get("pitch_speed")) if payload_data.get("pitch_speed") not in ("---", None) else None
        except:
            our_pitch_speed = None
        our_pitch_name = str(payload_data.get("pitch_name", ""))
        
        try:
            our_hit_speed = float(payload_data.get("hit_speed")) if payload_data.get("hit_speed") not in ("---", None) else None
        except:
            our_hit_speed = None
            
        try:
            our_hit_distance = float(payload_data.get("hit_distance")) if payload_data.get("hit_distance") not in ("---", None) else None
        except:
            our_hit_distance = None
            
        our_play_desc = str(payload_data.get("status_msg", ""))
        last_ev = events[-1] if events else {}
        play_id = last_ev.get("playId") or str(uuid.uuid4().hex[:12])
        at_bat_idx = targetPlay.get("about", {}).get("atBatIndex")
        pitch_number = last_ev.get("pitchNumber")
        
        # Check synchronization
        discrepancies = []
        is_break = mlb_inning_state.lower() in ("middle", "mid", "end") or our_outs == 3 or mlb_outs == 3
        if not is_break:
            if our_outs != mlb_outs:
                discrepancies.append(f"outs mismatch: our={our_outs} mlb={mlb_outs}")
            if our_balls != mlb_balls:
                discrepancies.append(f"balls mismatch: our={our_balls} mlb={mlb_balls}")
            if our_strikes != mlb_strikes:
                discrepancies.append(f"strikes mismatch: our={our_strikes} mlb={mlb_strikes}")
        
        is_synchronized = 1 if len(discrepancies) == 0 else 0
        disc_json = json.dumps(discrepancies) if discrepancies else None
        
        rec_id = f"aud_{game_pk}_{int(time.time()*1000)}"
        now_iso = dt.datetime.utcnow().isoformat() + "Z"
        
        conn = get_db(row_factory=False)
        try:
            conn.execute("""
                INSERT INTO mlb_telemetry_audit_ledger (
                    id, game_pk, timestamp, play_id, at_bat_index, pitch_number,
                    our_inning, our_half, our_outs, our_balls, our_strikes,
                    our_batter, our_batter_id, our_pitcher, our_pitcher_id,
                    our_pitch_speed, our_pitch_name, our_hit_speed, our_hit_distance,
                    our_play_desc, mlb_inning_state, mlb_is_top, mlb_outs,
                    mlb_balls, mlb_strikes, mlb_batter, mlb_pitcher,
                    mlb_pitch_speed, mlb_pitch_name, mlb_play_desc,
                    is_synchronized, discrepancy_json, sys_created_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec_id, str(game_pk), now_iso, play_id, at_bat_idx, pitch_number,
                our_inning, our_half, our_outs, our_balls, our_strikes,
                our_batter, our_batter_id, our_pitcher, our_pitcher_id,
                our_pitch_speed, our_pitch_name, our_hit_speed, our_hit_distance,
                our_play_desc, mlb_inning_state, mlb_is_top, mlb_outs,
                mlb_balls, mlb_strikes, mlb_batter, mlb_pitcher,
                mlb_p_speed, mlb_p_name, mlb_play_desc,
                is_synchronized, disc_json, now_iso
            ))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"[POLLER AUDIT] Non-fatal error recording audit: {e}")

stateful_triggers_notified = {}
reconciled_games_dispatched = set()
_last_seen_play_desc = ""

def _write_fanstack_heartbeat(active_games_count: int, last_play_desc: str = ""):
    """Atomic heartbeat emitter for Sovereign OS Poller HUD (WO0010108)."""
    global _last_seen_play_desc
    if last_play_desc:
        _last_seen_play_desc = last_play_desc
    try:
        hb_path = Path("/home/james/stacklabs/logs/fanstack_poller_heartbeat.json")
        hb_tmp = Path("/home/james/stacklabs/logs/fanstack_poller_heartbeat.json.tmp")
        payload = {
            "timestamp": time.time(),
            "iso_time": dt.datetime.now(dt.timezone.utc).isoformat(),
            "pid": os.getpid(),
            "active_games_count": active_games_count,
            "last_play_desc": _last_seen_play_desc[:120] if _last_seen_play_desc else "Active polling",
            "status": "STREAMING"
        }
        with open(hb_tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(hb_tmp, hb_path)
    except Exception as e:
        pass

def check_trigger_enabled(trigger_name):
    try:
        conn = get_db(row_factory=False)
        row = conn.execute("SELECT value FROM sys_user_preference WHERE user_name = 'james' AND name = 'tmi_configured_events'").fetchone()
        conn.close()
        if row:
            configured = json.loads(row[0])
            return trigger_name in configured
    except Exception:
        pass
    return True

async def log_stateful_anomaly(trigger_type, game_pk, markdown_details):
    try:
        log_dir = "/home/james/stacklabs_inbox/today"
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "statcast_telemetry.log")
        with open(log_path, "a") as log_file:
            timestamp = dt.datetime.now().strftime("%H:%M:%S")
            log_file.write(f"\n[{timestamp}] [TMI_TRIGGER] {trigger_type} (Game {game_pk})\n")
            log_file.write(markdown_details)
            log_file.write("\n\n")
    except Exception as e:
        print(f"[POLLER] Failed to write stateful anomaly log: {e}")

async def _post_json(url, payload):
    try:
        res = await asyncio.to_thread(requests.post, url, json=payload, timeout=10)
        return res.json() if res.status_code in (200, 201) else None
    except Exception as e:
        print(f"[POLLER] POST failed to {url}: {e}")
        return None

async def broadcast_to_mesh(ws, game_pk, tmi_payload, update_text):
    try:
        await ws.send(json.dumps(tmi_payload))
    except Exception as e:
        print(f"[POLLER] Failed to broadcast TMI_ANOMALY: {e}")
        
    ctx_msg = {
        "type": "update_context",
        "text": update_text,
        "target_nodes": ["ALL"],
        "target_game_pk": str(game_pk)
    }
    try:
        await ws.send(json.dumps(ctx_msg))
    except Exception as e:
        print(f"[POLLER] Failed to send update_context: {e}")



class GameStateAccumulator:
    def __init__(self, game_pk, feed, game_status):
        self.game_pk = game_pk
        self.feed = feed
        self.game_status = game_status
        self.all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
        
        gd_teams = feed.get("gameData", {}).get("teams", {})
        self.away_team = gd_teams.get("away", {}).get("abbreviation", "AWY")
        self.home_team = gd_teams.get("home", {}).get("abbreviation", "HME")

    async def evaluate_triggers(self, ws):
        await self._check_rule_a(ws)
        await self._check_rule_b(ws)
        await self._check_rule_c(ws)

    async def _check_rule_a(self, ws):
        if not check_trigger_enabled('Full-Count Strikeout'):
            return
            
        for play in self.all_plays:
            play_id = play.get("about", {}).get("playId")
            if not play_id:
                continue
                
            notify_key = f"{self.game_pk}_ruleA_{play_id}"
            if notify_key in stateful_triggers_notified:
                continue
                
            result = play.get("result", {})
            event_type = result.get("eventType", "")
            if event_type not in ["strikeout", "strikeout_double_play"]:
                continue
                
            events = play.get("playEvents", [])
            final_pitch_idx = -1
            for idx in range(len(events) - 1, -1, -1):
                if events[idx].get("isPitch", False):
                    final_pitch_idx = idx
                    break
                    
            if final_pitch_idx == -1:
                continue
                
            if final_pitch_idx > 0:
                prev_count = events[final_pitch_idx - 1].get("count", {})
                balls = prev_count.get("balls", 0)
                strikes = prev_count.get("strikes", 0)
                if balls == 3 and strikes == 2:
                    stateful_triggers_notified[notify_key] = True
                    
                    pitcher = play.get("matchup", {}).get("pitcher", {}).get("fullName", "Pitcher")
                    batter = play.get("matchup", {}).get("batter", {}).get("fullName", "Batter")
                    about = play.get("about", {})
                    inning_half = "Top" if about.get("isTopInning", True) else "Bot"
                    inning_num = about.get("inning", 1)
                    play_desc = result.get("description", "")
                    
                    markdown_details = (
                        f"### 📡 STATEFUL TMI ANOMALY DETECTED\n"
                        f"**Event**: Full-Count Strikeout\n"
                        f"**Game PK**: {self.game_pk} ({self.away_team}@{self.home_team})\n"
                        f"**Inning**: {inning_half} {inning_num}\n"
                        f"**Count**: 3-2 (Full Count)\n"
                        f"**Batter**: {batter}\n"
                        f"**Pitcher**: {pitcher}\n"
                        f"**Play Description**: {play_desc}"
                    )
                    
                    await log_stateful_anomaly("Full-Count Strikeout", self.game_pk, markdown_details)
                    
                    tmi_payload = {
                        "id": f"anom-fc-{self.game_pk}-{play_id}",
                        "game_pk": str(self.game_pk),
                        "event": f"[{self.away_team}@{self.home_team}] Full-Count Strikeout",
                        "time": f"LIVE — {inning_half} {inning_num}",
                        "persona": "BatteryBarf",
                        "format": "Format A (Standard)",
                        "script": f"Full-Count Punchout! {batter} strikes out on a 3-2 count pitch from {pitcher}! High tension pay-off!",
                        "prompt": f"Cinematic close-up of a pitcher celebrating after striking out the batter on a 3-2 full count pitch.",
                        "target_game_pk": str(self.game_pk)
                    }
                    
                    await _post_json("http://localhost:8095/api/tmi_anomalies", tmi_payload)
                    await broadcast_to_mesh(ws, self.game_pk, tmi_payload, update_text=f"MOMENTUM SHIFT (TMI ANOMALY): Full-Count Strikeout! {batter} strikes out on a 3-2 payoff pitch from {pitcher}!")

    async def _check_rule_b(self, ws):
        if not check_trigger_enabled('Bases-Loaded Inning-Ending Jam'):
            return
            
        jam_active = False
        jam_start_score = 0
        jam_half_inning = None
        jam_play_id = None
        
        for idx, play in enumerate(self.all_plays):
            about = play.get("about", {})
            inning = about.get("inning")
            is_top = about.get("isTopInning")
            current_half = (inning, is_top)
            
            if idx > 0:
                prev_play = self.all_plays[idx - 1]
                prev_about = prev_play.get("about", {})
                prev_half = (prev_about.get("inning"), prev_about.get("isTopInning"))
                if prev_half == current_half:
                    starting_outs = prev_play.get("count", {}).get("outs", 0)
                else:
                    starting_outs = 0
            else:
                starting_outs = 0
                
            score_key = "awayScore" if is_top else "homeScore"
            current_score = play.get("result", {}).get(score_key, 0)
            
            if jam_active:
                notify_key = f"{self.game_pk}_ruleB_{jam_play_id}"
                
                if current_half != jam_half_inning:
                    if notify_key not in stateful_triggers_notified:
                        stateful_triggers_notified[notify_key] = True
                        await self._fire_rule_b(ws, jam_play_id, jam_half_inning, jam_start_score)
                    jam_active = False
                elif current_score > jam_start_score:
                    jam_active = False
                elif play.get("count", {}).get("outs", 0) == 3:
                    if notify_key not in stateful_triggers_notified:
                        stateful_triggers_notified[notify_key] = True
                        await self._fire_rule_b(ws, jam_play_id, jam_half_inning, jam_start_score)
                    jam_active = False
                    
            if not jam_active:
                matchup = play.get("matchup", {})
                has_bases_loaded = (
                    matchup.get("postOnFirst") is not None and
                    matchup.get("postOnSecond") is not None and
                    matchup.get("postOnThird") is not None
                )
                if has_bases_loaded and starting_outs < 2:
                    jam_active = True
                    if idx > 0:
                        prev_play = self.all_plays[idx - 1]
                        prev_about = prev_play.get("about", {})
                        prev_half = (prev_about.get("inning"), prev_about.get("isTopInning"))
                        if prev_half == current_half:
                            jam_start_score = prev_play.get("result", {}).get(score_key, 0)
                        else:
                            jam_start_score = 0
                    else:
                        jam_start_score = 0
                    jam_half_inning = current_half
                    jam_play_id = play.get("about", {}).get("playId") or f"play-{idx}"
                    
        if jam_active and self.game_status == "Final":
            notify_key = f"{self.game_pk}_ruleB_{jam_play_id}"
            if notify_key not in stateful_triggers_notified:
                stateful_triggers_notified[notify_key] = True
                await self._fire_rule_b(ws, jam_play_id, jam_half_inning, jam_start_score)

    async def _fire_rule_b(self, ws, play_id, half_inning, start_score):
        inning_num, is_top = half_inning
        inning_half = "Top" if is_top else "Bot"
        defending_team = self.home_team if is_top else self.away_team
        
        markdown_details = (
            f"### 📡 STATEFUL TMI ANOMALY DETECTED\n"
            f"**Event**: Houdini Escape\n"
            f"**Game PK**: {self.game_pk} ({self.away_team}@{self.home_team})\n"
            f"**Inning**: {inning_half} {inning_num}\n"
            f"**Defending Team**: {defending_team}\n"
            f"**Escape Scenario**: Escaped a bases-loaded jam with < 2 outs without conceding any runs."
        )
        
        await log_stateful_anomaly("Houdini Escape", self.game_pk, markdown_details)
        
        tmi_payload = {
            "id": f"anom-he-{self.game_pk}-{play_id}",
            "game_pk": str(self.game_pk),
            "event": f"[{self.away_team}@{self.home_team}] Bases-Loaded Inning-Ending Jam",
            "time": f"LIVE — {inning_half} {inning_num}",
            "persona": "Terry the Boomer",
            "format": "Format E (Hyper-Realistic Human)",
            "script": f"A magnificent Houdini escape! The defense gets out of a bases-loaded, low-out jam without conceding a single run! Incredible poise by {defending_team}!",
            "prompt": f"Distressed home fans high-fiving and celebrating in the stands of a baseball stadium.",
            "target_game_pk": str(self.game_pk)
        }
        
        await _post_json("http://localhost:8095/api/tmi_anomalies", tmi_payload)
        await broadcast_to_mesh(ws, self.game_pk, tmi_payload, update_text=f"MOMENTUM SHIFT (TMI ANOMALY): Houdini Escape! {defending_team} successfully escapes a bases-loaded jam in the {inning_half} {inning_num} without conceding a single run!")

    async def _check_rule_c(self, ws):
        if not check_trigger_enabled('Late-Inning Comeback Rally'):
            return
            
        away_rally_candidate = False
        home_rally_candidate = False
        away_rally_play_id = None
        home_rally_play_id = None
        
        for play in self.all_plays:
            about = play.get("about", {})
            inning = about.get("inning", 1)
            play_id = about.get("playId")
            if not play_id:
                continue
                
            result = play.get("result", {})
            away_score = result.get("awayScore", 0)
            home_score = result.get("homeScore", 0)
            
            if inning >= 7:
                diff = away_score - home_score
                if diff <= -3:
                    if not away_rally_candidate:
                        away_rally_candidate = True
                        away_rally_play_id = play_id
                elif diff >= 3:
                    if not home_rally_candidate:
                        home_rally_candidate = True
                        home_rally_play_id = play_id
                        
                if away_rally_candidate and diff >= 0:
                    notify_key = f"{self.game_pk}_ruleC_{away_rally_play_id}"
                    if notify_key not in stateful_triggers_notified:
                        stateful_triggers_notified[notify_key] = True
                        await self._fire_rule_c(ws, away_rally_play_id, "away", inning, away_score, home_score)
                    away_rally_candidate = False
                    
                if home_rally_candidate and diff <= 0:
                    notify_key = f"{self.game_pk}_ruleC_{home_rally_play_id}"
                    if notify_key not in stateful_triggers_notified:
                        stateful_triggers_notified[notify_key] = True
                        await self._fire_rule_c(ws, home_rally_play_id, "home", inning, away_score, home_score)
                    home_rally_candidate = False

    async def _fire_rule_c(self, ws, play_id, team_side, inning_num, away_score, home_score):
        rallying_team = self.away_team if team_side == "away" else self.home_team
        
        markdown_details = (
            f"### 📡 STATEFUL TMI ANOMALY DETECTED\n"
            f"**Event**: Miracle Rally\n"
            f"**Game PK**: {self.game_pk} ({self.away_team}@{self.home_team})\n"
            f"**Inning**: {inning_num}\n"
            f"**Rallying Team**: {rallying_team}\n"
            f"**Score**: {away_score} - {home_score}\n"
            f"**Rally Scenario**: Overcame a 3+ run deficit in the 7th inning or later to tie or take the lead."
        )
        
        await log_stateful_anomaly("Miracle Rally", self.game_pk, markdown_details)
        
        tmi_payload = {
            "id": f"anom-mr-{self.game_pk}-{play_id}",
            "game_pk": str(self.game_pk),
            "event": f"[{self.away_team}@{self.home_team}] Late-Inning Comeback Rally",
            "time": f"LIVE — Inning {inning_num}",
            "persona": "Dr. Kosmos",
            "format": "Format C (Dynamic Flow)",
            "script": f"A miracle rally! {rallying_team} has overcome a 3+ run deficit in the late innings to tie or take the lead! Pure magic on the field!",
            "prompt": f"A dramatic baseball moment. Players in the dugout leaping and screaming in excitement.",
            "target_game_pk": str(self.game_pk)
        }
        
        await _post_json("http://localhost:8095/api/tmi_anomalies", tmi_payload)
        await broadcast_to_mesh(ws, self.game_pk, tmi_payload, update_text=f"MOMENTUM SHIFT (TMI ANOMALY): Miracle Comeback! {rallying_team} rallies from a 3+ run deficit in the 7th inning or later to tie or take the lead!")


async def poll_games(ws):
    global schedule_cache, last_schedule_time, last_poll_times, last_game_status
    now = time.time()
    
    if not schedule_cache or now - last_schedule_time > 300:
        import datetime
        today_dt = datetime.datetime.utcnow() - datetime.timedelta(hours=6)
        today = today_dt.strftime("%Y-%m-%d")
        yesterday = (today_dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={yesterday}&endDate={today}"
        data = await _fetch_json(url)
        if data:
            schedule_cache = data
            last_schedule_time = now
            print(f"[POLLER] Schedule refreshed for {yesterday} -> {today}: {sum(len(d.get('games',[])) for d in data.get('dates',[]))} games found")
    else:
        data = schedule_cache
        
    if not data: return
    games = []
    for d_obj in data.get("dates", []):
        games.extend(d_obj.get("games", []))
    
    active_games = []
    from datetime import datetime, timezone
    for g in games:
        pk = g.get("gamePk")
        if not pk: continue
        status = g.get("status", {}).get("abstractGameState", "")
        detailed_status = g.get("status", {}).get("detailedState", "")
        
        if status in ["Postponed", "Cancelled"]:
            continue
            
        delta_mins = 999
        if status in ["Scheduled", "Preview"]:
            game_time_str = g.get("gameDate")
            if game_time_str:
                game_time = datetime.strptime(game_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                now_utc = datetime.now(timezone.utc)
                delta_mins = (game_time - now_utc).total_seconds() / 60
                if delta_mins > 1440:
                    continue
            else:
                continue

        # Adaptive Polling: Determine wait interval based on status and start time
        prev_status = last_game_status.get(pk)
        status_changed = (prev_status != status)
        
        if status == "Live":
            interval = 5.0      # Poll active live games every 5 seconds
        elif delta_mins < 15:
            interval = 15.0     # Poll pre-game / warmup games every 15 seconds
        elif status == "Final":
            interval = 600.0    # Finished games: check once every 10 minutes
        else:
            interval = 60.0     # Far scheduled games: check once every 60 seconds

        last_fetched = last_poll_times.get(pk, 0.0)
        if not status_changed and (now - last_fetched < interval):
            continue

        active_games.append((pk, status, detailed_status, delta_mins))
        last_game_status[pk] = status
        last_poll_times[pk] = now

    _write_fanstack_heartbeat(len(active_games))

    if not active_games:
        return

    tasks = [_fetch_json(LIVE_FEED_BASE.format(pk)) for (pk, _, _, _) in active_games]
    feeds = await asyncio.gather(*tasks)

    for i, feed in enumerate(feeds):
        if not feed: continue
        pk, status, detailed_status, delta_mins = active_games[i]
        
        # Check start-play-index limit if specified
        if TARGET_GAME_ID and str(pk) == str(TARGET_GAME_ID) and START_PLAY_INDEX is not None:
            plays = feed.get("liveData", {}).get("plays", {})
            targetPlay = plays.get("currentPlay", {})
            current_idx = targetPlay.get("about", {}).get("atBatIndex")
            if current_idx is not None and current_idx < START_PLAY_INDEX:
                continue
        
        linescore = feed.get("liveData", {}).get("linescore", {})
        inning_ord = linescore.get("currentInningOrdinal", "-")
        current_inning_num = linescore.get("currentInning", 1) or 1
        inning_state = linescore.get("inningState", "")
        is_top = linescore.get("isTopInning", True)
        outs = linescore.get("outs", 0)
        balls = linescore.get("balls", 0)
        strikes = linescore.get("strikes", 0)

        teams = linescore.get("teams", {})
        away_score = teams.get("away", {}).get("runs", 0)
        home_score = teams.get("home", {}).get("runs", 0)

        # ── KROGER SPEC (ENHC2026082608): Terminal State Machine Guard ──
        is_direct_final = (status == "Final" or detailed_status in ["Game Over", "Final", "Completed Early"])
        is_math_closure = (current_inning_num >= 9 and is_top and outs == 3 and home_score > away_score)
        is_walk_off = (current_inning_num >= 9 and not is_top and home_score > away_score)
        is_game_terminated = is_direct_final or is_math_closure or is_walk_off

        if is_game_terminated:
            status = "Final"
            detailed_status = "Final"
            half = "Final"
            inning = "Final"
            is_inning_break = False
            outs = 0
            balls = 0
            strikes = 0
            onFirst = False
            onSecond = False
            onThird = False

            # Asynchronously dispatch post-game reconciliation harvester once per game
            if pk not in reconciled_games_dispatched:
                reconciled_games_dispatched.add(pk)
                try:
                    reconcile_script = str(SOVEREIGN_ROOT / "scripts" / "telemetry_reconciliation_harvester.py")
                    subprocess.Popen(
                        [sys.executable, reconcile_script, "--game_pk", str(pk)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    print(f"[TERMINAL GUARD] Dispatched automated post-game reconciliation for game {pk} (math_closure={is_math_closure}, walk_off={is_walk_off}, direct_final={is_direct_final})")
                except Exception as rec_err:
                    print(f"[TERMINAL GUARD ERROR] Failed to dispatch reconciliation for game {pk}: {rec_err}")
        else:
            # Inning transition detection (DFCT2026082603)
            # Check for half-inning completion: inningState "Middle"/"End" or 3 outs recorded
            is_mid = inning_state.lower() in ("middle", "mid") or (outs == 3 and is_top)
            is_end = inning_state.lower() in ("end",) or (outs == 3 and not is_top)
            is_inning_break = is_mid or is_end

            if is_mid:
                half = "Mid"
                inning = inning_ord
                outs = 0
                balls = 0
                strikes = 0
                onFirst = False
                onSecond = False
                onThird = False
            elif is_end:
                half = "End"
                inning = inning_ord
                outs = 0
                balls = 0
                strikes = 0
                onFirst = False
                onSecond = False
                onThird = False
            else:
                half = "Top" if is_top else "Bot"
                inning = inning_ord
                offense = linescore.get("offense", {})
                onFirst = "first" in offense
                onSecond = "second" in offense
                onThird = "third" in offense
        
        gd_teams = feed.get("gameData", {}).get("teams", {})
        away_team = gd_teams.get("away", {}).get("abbreviation", "AWY")
        home_team = gd_teams.get("home", {}).get("abbreviation", "HME")

        # Extract authentic team win/loss records
        away_rec = gd_teams.get("away", {}).get("record", {})
        away_wins = away_rec.get("wins") if away_rec.get("wins") is not None else away_rec.get("leagueRecord", {}).get("wins")
        away_losses = away_rec.get("losses") if away_rec.get("losses") is not None else away_rec.get("leagueRecord", {}).get("losses")
        away_record = f"{away_wins}-{away_losses}" if away_wins is not None and away_losses is not None else None

        home_rec = gd_teams.get("home", {}).get("record", {})
        home_wins = home_rec.get("wins") if home_rec.get("wins") is not None else home_rec.get("leagueRecord", {}).get("wins")
        home_losses = home_rec.get("losses") if home_rec.get("losses") is not None else home_rec.get("leagueRecord", {}).get("losses")
        home_record = f"{home_wins}-{home_losses}" if home_wins is not None and home_losses is not None else None

        # Extract probable pitchers for pregame intelligence
        gd_probables = feed.get("gameData", {}).get("probablePitchers", {})
        away_prob = gd_probables.get("away", {})
        home_prob = gd_probables.get("home", {})

        probable_pitcher_away = None
        if away_prob and away_prob.get("fullName"):
            a_id = away_prob.get("id")
            a_stats = get_pitcher_season_stats(a_id) if a_id else {}
            probable_pitcher_away = {
                "id": a_id,
                "name": away_prob.get("fullName"),
                "era": a_stats.get("era", "---"),
                "record": a_stats.get("record", "---")
            }

        probable_pitcher_home = None
        if home_prob and home_prob.get("fullName"):
            h_id = home_prob.get("id")
            h_stats = get_pitcher_season_stats(h_id) if h_id else {}
            probable_pitcher_home = {
                "id": h_id,
                "name": home_prob.get("fullName"),
                "era": h_stats.get("era", "---"),
                "record": h_stats.get("record", "---")
            }
        
        # 1. Ingest Venue Telemetry (WO-2026-094)
        gd_venue = feed.get("gameData", {}).get("venue", {})
        venue_name = gd_venue.get("name", "")
        gd_loc = gd_venue.get("location", {})
        city = gd_loc.get("city", "")
        state_abbrev = gd_loc.get("stateAbbrev", "")
        
        TEAM_STADIUMS = {
            "LAD": ("Dodger Stadium", "Los Angeles, CA"),
            "NYY": ("Yankee Stadium", "Bronx, NY"),
            "CHC": ("Wrigley Field", "Chicago, IL"),
            "NYM": ("Citi Field", "Flushing, NY"),
            "MIN": ("Target Field", "Minneapolis, MN"),
            "DET": ("Comerica Park", "Detroit, MI"),
            "PIT": ("PNC Park", "Pittsburgh, PA"),
            "SF":  ("Oracle Park", "San Francisco, CA"),
            "TEX": ("Globe Life Field", "Arlington, TX"),
            "TOR": ("Rogers Centre", "Toronto, ON"),
            "OAK": ("Sutter Health Park", "Sacramento, CA"),
            "PHI": ("Citizens Bank Park", "Philadelphia, PA"),
            "MIA": ("loanDepot park", "Miami, FL"),
            "ATL": ("Truist Park", "Atlanta, GA"),
            "COL": ("Coors Field", "Denver, CO"),
            "SD":  ("Petco Park", "San Diego, CA"),
            "MIL": ("American Family Field", "Milwaukee, WI"),
            "CWS": ("Guaranteed Rate Field", "Chicago, IL"),
            "BAL": ("Oriole Park at Camden Yards", "Baltimore, MD"),
            "CIN": ("Great American Ball Park", "Cincinnati, OH"),
            "HOU": ("Daikin Park", "Houston, TX"),
            "STL": ("Busch Stadium", "St. Louis, MO"),
            "WSH": ("Nationals Park", "Washington, DC"),
            "ARI": ("Chase Field", "Phoenix, AZ"),
            "CLE": ("Progressive Field", "Cleveland, OH"),
            "LAA": ("Angel Stadium", "Anaheim, CA"),
            "TB":  ("Tropicana Field", "St. Petersburg, FL"),
            "KC":  ("Kauffman Stadium", "Kansas City, MO"),
            "SEA": ("T-Mobile Park", "Seattle, WA"),
            "BOS": ("Fenway Park", "Boston, MA"),
        }

        VENUE_LOCATIONS = {
            "Oracle Park": "San Francisco, CA",
            "Citi Field": "Flushing, NY",
            "American Family Field": "Milwaukee, WI",
            "Wrigley Field": "Chicago, IL",
            "Oriole Park at Camden Yards": "Baltimore, MD",
            "Great American Ball Park": "Cincinnati, OH",
            "Daikin Park": "Houston, TX",
            "Petco Park": "San Diego, CA",
            "Busch Stadium": "St. Louis, MO",
            "Citizens Bank Park": "Philadelphia, PA",
            "UNIQLO Field at Dodger Stadium": "Los Angeles, CA",
            "Dodger Stadium": "Los Angeles, CA",
            "T-Mobile Park": "Seattle, WA",
            "Rogers Centre": "Toronto, ON",
            "loanDepot park": "Miami, FL",
            "Truist Park": "Atlanta, GA",
            "Kauffman Stadium": "Kansas City, MO",
            "Chase Field": "Phoenix, AZ",
            "Rate Field": "Chicago, IL",
            "Guaranteed Rate Field": "Chicago, IL",
            "Nationals Park": "Washington, DC",
            "Comerica Park": "Detroit, MI",
            "Yankee Stadium": "Bronx, NY",
            "Fenway Park": "Boston, MA",
            "Globe Life Field": "Arlington, TX",
            "Progressive Field": "Cleveland, OH",
            "Target Field": "Minneapolis, MN",
            "Coors Field": "Denver, CO",
            "PNC Park": "Pittsburgh, PA",
            "Angel Stadium": "Anaheim, CA",
            "Sutter Health Park": "Sacramento, CA",
            "Tropicana Field": "St. Petersburg, FL",
            "Estadio Alfredo Harp Helu": "Mexico City, Mexico",
            "Las Vegas Ballpark": "Las Vegas, NV",
            "Field of Dreams": "Dyersville, IA",
            "Journey Bank Ballpark": "Williamsport, PA",
            "MetLife Stadium": "East Rutherford, NJ",
            "The BattleDome": "Simulated Void",
            "The Simulation Chamber": "Simulated Void",
            "Augusta National": "Augusta, GA",
            "Pinehurst No. 2": "Pinehurst, NC",
            "Allianz Arena": "Munich, Germany"
        }

        if home_team and (not venue_name or venue_name in ("Home", "N/A", "")):
            default_stadium, default_loc = TEAM_STADIUMS.get(home_team.upper(), ("Home Stadium", "Home City"))
            venue_name = default_stadium
            venue_location = default_loc
        else:
            if city and state_abbrev:
                venue_location = f"{city}, {state_abbrev}"
            elif city:
                venue_location = city
            else:
                venue_location = VENUE_LOCATIONS.get(venue_name, "Home City")
        
        weather = feed.get("gameData", {}).get("weather", {})
        wind = weather.get("wind", "---")
        
        plays = feed.get("liveData", {}).get("plays", {})
        targetPlay = plays.get("currentPlay", {})
        allPlays = plays.get("allPlays", [])
        
        batterName = targetPlay.get("matchup", {}).get("batter", {}).get("fullName", "Awaiting Batter")
        pitcherName = targetPlay.get("matchup", {}).get("pitcher", {}).get("fullName", "Awaiting Pitcher")

        # Inning break override: display upcoming due-up batter and pitcher from linescore
        if is_inning_break:
            off_batter = linescore.get("offense", {}).get("batter", {})
            def_pitcher = linescore.get("defense", {}).get("pitcher", {})
            batterName = off_batter.get("fullName") or "Due Up"
            pitcherName = def_pitcher.get("fullName") or pitcherName
            playDesc = f"Mid {inning} - Inning Break" if is_mid else f"End {inning} - Inning Break"
        else:
            # PRE-GAME WARMUP FALLBACK (MLB API doesn't populate currentPlay until first pitch)
            if batterName == "Awaiting Batter" and linescore.get("offense", {}).get("batter", {}).get("fullName"):
                batterName = linescore.get("offense", {}).get("batter", {}).get("fullName")
                
            if pitcherName == "Awaiting Pitcher" and linescore.get("defense", {}).get("pitcher", {}).get("fullName"):
                pitcherName = linescore.get("defense", {}).get("pitcher", {}).get("fullName")
            elif pitcherName == "Awaiting Pitcher":
                if probable_pitcher_home and probable_pitcher_home.get("name"):
                    pitcherName = probable_pitcher_home["name"]
                elif probable_pitcher_away and probable_pitcher_away.get("name"):
                    pitcherName = probable_pitcher_away["name"]
                
            playDesc = targetPlay.get("result", {}).get("description", "Awaiting Pitches...")
            
            if playDesc == "Awaiting Pitches...":
                if status in ["Scheduled", "Preview"]:
                    current_min = int(time.time() / 60)
                    if detailed_status == "Warmup":
                        playDesc = f"Pre-Game Warmup [{current_min}]"
                    else:
                        playDesc = f"Scheduled (T-Minus {int(delta_mins)}m) [{current_min}]"
                else:
                    if targetPlay.get("playEvents", []) and len(targetPlay["playEvents"]) > 0:
                        playDesc = targetPlay["playEvents"][-1].get("details", {}).get("description", "In Play...")
                    elif len(allPlays) > 1:
                        playDesc = allPlays[-2].get("result", {}).get("description", "Awaiting Pitches...")
                        
            playDesc = playDesc.replace("**[LIVE SECURE FEED]**\n", "").replace("**[LIVE SECURE FEED]**", "").strip()
        
        events = targetPlay.get("playEvents", [])
        speed = "---"
        pName = "---"
        hit_speed = "---"
        hit_distance = "---"
        launch_angle = "---"
        hit_coord_x = None
        hit_coord_y = None
        
        # Whiff detection parameters
        bat_speed = "---"
        miss_distance = None
        timing_class = "---"
        timing_delta = 0.0
        vert_align = "---"
        vert_delta = 0.0
        horiz_align = "---"
        horiz_delta = 0.0
        whiff_image_url = None
        
        # STRY-WHIFF-OVERLAY custom metrics
        horizontal_break_inches = 0.0
        vertical_break_inches = 0.0
        swing_status = "TAKE"
        bat_speed_mph = 0.0
        whiff_distance_inches = 0.0
        is_sword = False
        
        for ev in reversed(events):
            if ev.get("hitData") and hit_speed == "---":
                hit_speed = ev["hitData"].get("launchSpeed", "---")
                hit_distance = ev["hitData"].get("totalDistance", "---")
                launch_angle = ev["hitData"].get("launchAngle", "---")
                _hit_coords = ev["hitData"].get("coordinates") or ev.get("coordinates") or {}
                if _hit_coords.get("coordX") is not None:
                    hit_coord_x = _hit_coords.get("coordX")
                    hit_coord_y = _hit_coords.get("coordY")
            if ev.get("pitchData"):
                if speed == "---" and ev["pitchData"].get("startSpeed"):
                    speed = ev["pitchData"].get("startSpeed", "---")
                if pName == "---" and ev.get("details", {}).get("type", {}).get("description"):
                    pName = ev.get("details", {}).get("type", {}).get("description", "---")
                
                # Ingest break data
                pd = ev.get("pitchData")
                if pd:
                    breaks = pd.get("breaks") or {}
                    if horizontal_break_inches == 0.0:
                        horizontal_break_inches = breaks.get("breakHorizontal") or breaks.get("break_horizontal") or 0.0
                    if vertical_break_inches == 0.0:
                        vertical_break_inches = breaks.get("breakVertical") or breaks.get("break_vertical") or 0.0

            # Determine swing_status, is_sword
            details = ev.get("details") or {}
            desc = details.get("description", "")
            code = details.get("type", {}).get("code", "")
            
            # Check is_sword
            if not is_sword:
                is_sword = details.get("isSword") or details.get("is_sword") or "sword" in desc.lower() or False

            # Determine swing_status
            if swing_status == "TAKE":
                if ev.get("hitData"):
                    swing_status = "HIT"
                elif "Swinging Strike" in desc or "Miss" in desc or "Swinging Pitchout" in desc or code in ["S", "W"]:
                    swing_status = "WHIFF"
                elif "Foul" in desc or "foul" in desc.lower() or code == "F":
                    swing_status = "FOUL"
            
            # Extract bat tracking if present
            bt = ev.get("batTracking") or ev.get("bat_tracking") or ev.get("pitchData", {}).get("batTracking") or ev.get("pitchData", {}).get("bat_tracking")
            if bt and miss_distance is None:
                bat_speed = bt.get("bat_speed_mph") or bt.get("batSpeedMph") or "---"
                ca = bt.get("closest_approach") or bt.get("closestApproach")
                if ca:
                    miss_distance = ca.get("miss_distance_in") or ca.get("miss_distance") or ca.get("missDistanceIn")
                    timing_class = ca.get("timing_classification") or ca.get("timingClassification") or "---"
                    timing_delta = ca.get("timing_delta_ms") or ca.get("timingDeltaMs") or 0.0
                    vert_align = ca.get("vertical_alignment") or ca.get("verticalAlignment") or "---"
                    vert_delta = ca.get("vertical_delta_in") or ca.get("verticalDeltaIn") or 0.0
                    horiz_align = ca.get("horizontal_alignment") or ca.get("horizontalAlignment") or "---"
                    horiz_delta = ca.get("horizontal_delta_in") or ca.get("horizontalDeltaIn") or 0.0
                    
        # Parse bat speed / miss distance to float
        if bat_speed != "---":
            try:
                bat_speed_mph = float(bat_speed)
            except:
                pass
        if miss_distance is not None:
            try:
                whiff_distance_inches = float(miss_distance)
            except:
                pass

        # Fallback to targetPlay coordinates if hit coordinates not found in events
        if hit_coord_x is None and targetPlay.get("coordinates"):
            _tp_coords = targetPlay.get("coordinates", {})
            if _tp_coords.get("coordX") is not None:
                hit_coord_x = _tp_coords.get("coordX")
                hit_coord_y = _tp_coords.get("coordY")
                    
        # Pivot to Hit Telemetry if Pitch Data is missing (suppressed during inning break)
        if not is_inning_break and (pName == "---" or speed == "---") and hit_speed != "---":
            pName = f"EXIT VELO ({hit_distance}ft)" if hit_distance != "---" else "EXIT VELOCITY"
            speed = hit_speed

        if is_inning_break:
            speed = "---"
            pName = "---"
            hit_speed = "---"
            hit_distance = "---"
            launch_angle = "---"
            hit_coord_x = None
            hit_coord_y = None
            bat_speed = "---"
            miss_distance = None
            timing_class = "---"
            horizontal_break_inches = 0.0
            vertical_break_inches = 0.0
            swing_status = "TAKE"
            bat_speed_mph = 0.0
            whiff_distance_inches = 0.0
            is_sword = False
            
        # Check if this is a Ghost Pitch Whiff Anomaly and generate graphic
        if miss_distance is not None and miss_distance >= 8.0 and vert_align == 'OVER':
            event_id = len(events)
            whiff_key = f"{pk}_{inning}_{outs}_{balls}_{strikes}_{event_id}"
            if whiff_key not in whiff_anomalies_notified:
                whiff_anomalies_notified[whiff_key] = True
                try:
                    img_id = f"{pk}_{int(time.time())}"
                    out_path1 = f"/home/james/stacklabs/15_FanStack/public/images/whiff_{img_id}.png"
                    out_path2 = f"/home/james/stacklabs/19_Sovereign_Sports/public/images/whiff_{img_id}.png"
                    
                    cmd = [
                        "/home/james/stacklabs/.venv/bin/python3",
                        "/home/james/stacklabs/scripts/auto_image_generator.py",
                        "--miss_distance", str(miss_distance),
                        "--vertical_alignment", str(vert_align),
                        "--vertical_delta", str(vert_delta),
                        "--horizontal_alignment", str(horiz_align),
                        "--horizontal_delta", str(horiz_delta),
                        "--swing_speed", str(bat_speed) if bat_speed != "---" else "78.2",
                        "--pitch_speed", str(speed) if speed != "---" else "90.5",
                        "--pitch_name", str(pName) if pName != "---" else "Fastball",
                        "--batter", str(batterName),
                        "--pitcher", str(pitcherName),
                        "--output", out_path1
                    ]
                    subprocess.run(cmd, check=True)
                    os.makedirs(os.path.dirname(out_path2), exist_ok=True)
                    import shutil
                    shutil.copy(out_path1, out_path2)
                    
                    whiff_image_url = f"/images/whiff_{img_id}.png"
                    print(f"[POLLER] Ghost pitch anomaly image generated: {whiff_image_url}")
                except Exception as img_err:
                    print(f"[POLLER] Failed to generate whiff image: {img_err}")
                
        # P2 FIX: Include DB room_state in hash so staged→active transition forces a re-broadcast
        # Root cause: chatbots slept for 50min because Pre-Game state_hash never changed after room activation
        db_room_state = "staged"
        try:
            _con = get_db(row_factory=False)
            _cur = _con.cursor()
            _cur.execute("SELECT room_state FROM mlb_schedule WHERE game_pk = ?", (str(pk),))
            _row = _cur.fetchone()
            if _row and _row[0]:
                db_room_state = _row[0]
            else:
                _cur.execute("SELECT room_state FROM cmdb_ci_fanstack_room WHERE game_pk = ?", (str(pk),))
                _row_fallback = _cur.fetchone()
                if _row_fallback and _row_fallback[0]:
                    db_room_state = _row_fallback[0]
            _con.close()
        except Exception:
            pass

        # Determine batting team and event type for triggers
        batting_team = away_team if is_top else home_team
        raw_event_type = targetPlay.get("result", {}).get("eventType", "")
        if raw_event_type == "home_run":
            event_type = "home_run"
        elif raw_event_type in ["hit", "single", "double", "triple"]:
            event_type = "hit"
        elif raw_event_type in ["strikeout", "strikeout_double_play"]:
            event_type = "strikeout"
        else:
            event_type = "pitch"

        # ── WO0010087: Build pitches_this_ab from MLB playEvents ──
        # Authoritative at-bat pitch sequence from MLB StatsAPI (plate_x/plate_z included)
        _pitches_this_ab = []
        _pitch_counter = 0
        for _ev in events:
            if not _ev.get("isPitch", False):
                continue
            _details = _ev.get("details", {})
            _pd = _ev.get("pitchData", {})
            _coords = _pd.get("coordinates", {})

            # Resolve pitch result
            if _details.get("isInPlay"):
                _result = "IN_PLAY"
            elif _details.get("isBall"):
                _result = "BALL"
            elif _details.get("isStrike"):
                _desc_lower = _details.get("description", "").lower()
                _result = "FOUL" if "foul" in _desc_lower else "STRIKE"
            else:
                _desc_lower = _details.get("description", "").lower()
                if "ball" in _desc_lower:
                    _result = "BALL"
                elif "foul" in _desc_lower:
                    _result = "FOUL"
                elif "strike" in _desc_lower or "swinging" in _desc_lower:
                    _result = "STRIKE"
                elif "in play" in _desc_lower:
                    _result = "IN_PLAY"
                else:
                    continue  # Skip non-pitch events (pickoffs, etc.)

            _p_type_obj = _details.get("type") or {}
            _p_code = _p_type_obj.get("code", "") or ""
            _p_full_name = _p_type_obj.get("description", "") or pName
            _p_speed_raw = _pd.get("startSpeed")
            _p_speed = str(round(float(_p_speed_raw), 1)) if _p_speed_raw is not None else "---"
            _px = _coords.get("pX") if _coords.get("pX") is not None else _coords.get("x")
            _pz = _coords.get("pZ") if _coords.get("pZ") is not None else _coords.get("y")

            # ── WO0010164: Jake Taylor Blown Call Detection ──
            sz_top = float(_pd.get("strikeZoneTop") or 3.4)
            sz_bot = float(_pd.get("strikeZoneBottom") or 1.5)
            _blown_call = None
            if "called strike" in _details.get("description", "").lower():
                try:
                    if _px is not None and _pz is not None:
                        px = float(_px)
                        pz = float(_pz)
                        try:
                            from core.jake_taylor_engine import audit_pitch_strike_zone
                        except ImportError:
                            from scripts.core.jake_taylor_engine import audit_pitch_strike_zone
                        audit = audit_pitch_strike_zone(px, pz, sz_top, sz_bot, "called_strike")
                        if audit.get("accuracy") == "MISSED_STRIKE":
                            miss_amt = max(audit.get("miss_x_inches", 0.0), audit.get("miss_z_inches", 0.0))
                            if miss_amt >= 1.2:
                                _blown_call = {
                                    "is_blown": True,
                                    "miss_inches": miss_amt,
                                    "miss_direction": audit.get("miss_direction", "outside"),
                                    "plate_x": px,
                                    "plate_z": pz,
                                    "sz_top": sz_top,
                                    "sz_bot": sz_bot,
                                    "determination": audit["determination"]
                                }
                                _ev["blown_call"] = _blown_call
                except Exception as _b_err:
                    print(f"[POLLER] Error auditing pitch strike zone: {_b_err}")

            _pitch_counter += 1
            _pitch_dict = {
                "n": _pitch_counter,
                "type": _p_code[:2].upper() if len(_p_code) >= 2 else _p_code.upper(),
                "speed": _p_speed,
                "result": _result,
                "plate_x": round(float(_px), 3) if _px is not None else None,
                "plate_z": round(float(_pz), 3) if _pz is not None else None,
                "name": _p_full_name
            }
            if _blown_call:
                _pitch_dict["blown_call"] = _blown_call
            _pitches_this_ab.append(_pitch_dict)

        if is_inning_break:
            _pitches_this_ab = []

        _current_blown_call = _pitches_this_ab[-1].get("blown_call") if _pitches_this_ab else None
        if _current_blown_call:
            targetPlay["blown_call"] = _current_blown_call

        # Extract season stats from boxscore
        boxscore = feed.get("liveData", {}).get("boxscore", {})
        box_teams = boxscore.get("teams", {})
        home_players = box_teams.get("home", {}).get("players", {})
        away_players = box_teams.get("away", {}).get("players", {})
        
        def find_player(p_id):
            if not p_id: return None
            key = f"ID{p_id}"
            return home_players.get(key) or away_players.get(key)
            
        if is_inning_break:
            batter_id = linescore.get("offense", {}).get("batter", {}).get("id")
            pitcher_id = linescore.get("defense", {}).get("pitcher", {}).get("id")
        else:
            batter_id = targetPlay.get("matchup", {}).get("batter", {}).get("id")
            if not batter_id and linescore.get("offense", {}).get("batter", {}).get("id"):
                batter_id = linescore.get("offense", {}).get("batter", {}).get("id")
                
            pitcher_id = targetPlay.get("matchup", {}).get("pitcher", {}).get("id")
            if not pitcher_id and linescore.get("defense", {}).get("pitcher", {}).get("id"):
                pitcher_id = linescore.get("defense", {}).get("pitcher", {}).get("id")
            
        b_player = find_player(batter_id)
        p_player = find_player(pitcher_id)
        
        # Teammate Collision Prevention
        is_teammate_collision = False
        if batter_id and pitcher_id:
            # Check boxscore home/away players
            batter_is_home = f"ID{batter_id}" in home_players
            batter_is_away = f"ID{batter_id}" in away_players
            pitcher_is_home = f"ID{pitcher_id}" in home_players
            pitcher_is_away = f"ID{pitcher_id}" in away_players
            
            b_team = "home" if batter_is_home else ("away" if batter_is_away else None)
            p_team = "home" if pitcher_is_home else ("away" if pitcher_is_away else None)
            
            # Fallback to mlb_rosters database to determine team_abbr
            if not b_team:
                try:
                    conn = get_db(row_factory=False)
                    c = conn.cursor()
                    c.execute("SELECT team_abbr FROM mlb_rosters WHERE sys_id LIKE ?", (f"%_{batter_id}",))
                    row = c.fetchone()
                    if row:
                        b_team = row[0].upper()
                    conn.close()
                except Exception:
                    pass
            else:
                b_team = home_team.upper() if b_team == "home" else away_team.upper()
                
            if not p_team:
                try:
                    conn = get_db(row_factory=False)
                    c = conn.cursor()
                    c.execute("SELECT team_abbr FROM mlb_rosters WHERE sys_id LIKE ?", (f"%_{pitcher_id}",))
                    row = c.fetchone()
                    if row:
                        p_team = row[0].upper()
                    conn.close()
                except Exception:
                    pass
            else:
                p_team = home_team.upper() if p_team == "home" else away_team.upper()
                
            if b_team and p_team and b_team == p_team:
                print(f"[POLLER WARNING] Teammate collision detected (both on {b_team}): batter={batterName} ({batter_id}), pitcher={pitcherName} ({pitcher_id}). Skipping play payload.")
                is_teammate_collision = True

        if is_teammate_collision:
            continue
        
        batter_avg = "---"
        batter_obp = "---"
        batter_slg = "---"
        batter_ops = "---"
        batter_hr = "0"
        batter_rbi = "0"
        batter_jersey = str(b_player.get("jerseyNumber", "")) if b_player else ""
        batter_position = str(b_player.get("position", {}).get("abbreviation", "")) if b_player else ""
        
        if b_player and b_player.get("seasonStats", {}).get("batting"):
            bat_stats = b_player["seasonStats"]["batting"]
            batter_avg = str(bat_stats.get("avg", "---"))
            batter_obp = str(bat_stats.get("obp", "---"))
            batter_slg = str(bat_stats.get("slg", "---"))
            batter_ops = str(bat_stats.get("ops", "---"))
            batter_hr = str(bat_stats.get("homeRuns", "0"))
            batter_rbi = str(bat_stats.get("rbi", "0"))
            
        pitcher_era = "---"
        pitcher_whip = "---"
        pitcher_wins = "0"
        pitcher_losses = "0"
        pitcher_so = "0"
        pitcher_ip = "0.0"
        
        if p_player and p_player.get("seasonStats", {}).get("pitching"):
            pit_stats = p_player["seasonStats"]["pitching"]
            pitcher_era = str(pit_stats.get("era", "---"))
            pitcher_whip = str(pit_stats.get("whip", "---"))
            pitcher_wins = str(pit_stats.get("wins", "0"))
            pitcher_losses = str(pit_stats.get("losses", "0"))
            pitcher_so = str(pit_stats.get("strikeOuts", "0"))
            pitcher_ip = str(pit_stats.get("inningsPitched", "0.0"))

        state_hash = f"{playDesc}|{inning}|{inning_state}|{balls}|{strikes}|{outs}|{away_score}|{home_score}|{pName}|{speed}|{batterName}|room:{db_room_state}|bc:{bool(_current_blown_call)}"
        cache_file_exists = os.path.exists(os.path.join(GAME_STATE_DIR, f"{pk}.json"))
        if pk not in last_status_map or last_status_map[pk] != state_hash or not cache_file_exists:
            source_info = {
                "type": "mlb",
                "id": str(pk),
                "badge": f"{away_team}@{home_team}",
                "sport": "mlb",
                "color": "#E81828" if ("PHI" in str(away_team) or "PHI" in str(home_team)) else "#00F0FF",
                "statusDetail": inning_state
            }
            payload = {
                "type": "CMD_SYNC_STATE",
                "source": source_info,
                "force_global": False,
                "target_game_pk": str(pk),
                "data": {
                    "game_status": status.lower(),
                    "detailed_status": detailed_status.lower(),
                    "pitcher": pitcherName,
                    "batter": batterName,
                    "status_msg": playDesc,
                    "away_score": away_score,
                    "home_score": home_score,
                    "away_team": away_team,
                    "home_team": home_team,
                    "inning": f"{half} {inning}",
                    "inning_state": inning_state,
                    "outs": outs,
                    "balls": balls,
                    "strikes": strikes,
                    "onFirst": onFirst,
                    "onSecond": onSecond,
                    "onThird": onThird,
                    "pitch_name": pName,
                    "pitch_speed": speed,
                    "hit_speed": hit_speed,
                    "hit_distance": hit_distance,
                    "launch_angle": launch_angle,
                    "hit_coord_x": hit_coord_x,
                    "hit_coord_y": hit_coord_y,
                    "event_type": event_type,
                    "batting_team": batting_team,
                    "horizontal_break_inches": horizontal_break_inches,
                    "vertical_break_inches": vertical_break_inches,
                    "swing_status": swing_status,
                    "bat_speed_mph": bat_speed_mph,
                    "whiff_distance_inches": whiff_distance_inches,
                    "is_sword": is_sword,
                    "wind": wind,
                    "venue_name": venue_name,
                    "venue_location": venue_location,
                    "batter_id": batter_id,
                    "batter_jersey": batter_jersey,
                    "batter_position": batter_position,
                    "pitcher_id": pitcher_id,
                    "batter_avg": batter_avg,
                    "batter_obp": batter_obp,
                    "batter_slg": batter_slg,
                    "batter_ops": batter_ops,
                    "batter_hr": batter_hr,
                    "batter_rbi": batter_rbi,
                    "pitcher_era": pitcher_era,
                    "pitcher_whip": pitcher_whip,
                    "pitcher_wins": pitcher_wins,
                    "pitcher_losses": pitcher_losses,
                    "pitcher_so": pitcher_so,
                    "pitcher_ip": pitcher_ip,
                    "away_record": away_record,
                    "home_record": home_record,
                    "probable_pitcher_away": probable_pitcher_away,
                    "probable_pitcher_home": probable_pitcher_home,
                    "pitches_this_ab": _pitches_this_ab,
                    "last_pitch": _pitches_this_ab[-1] if _pitches_this_ab else {},
                    "blown_call": _current_blown_call,
                    "source": source_info
                }
            }
            print(f"[POLLER] New play for {away_team}@{home_team} (Game {pk}): {playDesc}")
            
            # Write to daily telemetry log
            try:
                today_folder_date = dt.datetime.now().strftime("%Y-%m-%d")
                log_dir = "/home/james/stacklabs_inbox/today"
                if not os.path.isdir(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, "statcast_telemetry.log")
                with open(log_path, "a") as log_file:
                    timestamp = dt.datetime.now().strftime("%H:%M:%S")
                    log_file.write(f"[{timestamp}] [STATE] {away_team} {away_score} - {home_score} {home_team} | {playDesc}\\n")
                    if pName != '---' or speed != '---':
                        log_file.write(f"[{timestamp}] STATCAST 📡 {pName} {speed}mph | Hit: {hit_speed}mph {hit_distance}ft\\n")
                    log_file.write(f"RAW PAYLOAD: {json.dumps(payload['data'])}\\n\\n")
            except Exception as e:
                print(f"[POLLER] Failed to write to statcast telemetry log: {e}")
            try:
                import uuid
                msg_id = uuid.uuid4().hex
                payload["msg_id"] = msg_id
                await ws.send(json.dumps(payload))
                
                # Application-layer ACK handshake
                ack_received = False
                try:
                    # Wait for CMD_SYNC_ACK
                    while True:
                        response_str = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        resp = json.loads(response_str)
                        if resp.get("type") == "CMD_SYNC_ACK" and resp.get("msg_id") == msg_id:
                            print(f"[POLLER] Received ACK for state sync {msg_id}")
                            ack_received = True
                            break
                except asyncio.TimeoutError:
                    print(f"[POLLER] ACK timeout/missing for state_hash: {state_hash}")
                except Exception as read_err:
                    print(f"[POLLER] Error reading ACK response: {read_err}")
                
                if ack_received:
                    last_status_map[pk] = state_hash

                # Air Bender Takeover Overlay trigger (Remapped to Devon Williams pitching)
                if pitcherName in ("Devon Williams", "Devin Williams") and db_room_state == 'active':
                    airbender_payload = {
                        "type": "webslinger_trigger",
                        "event_name": "AIRBENDER_OVERLAY",
                        "data": {
                            "trigger": "AIRBENDER_OVERLAY",
                            "animation": "airbender",
                            "batter": batterName,
                            "pitcher": pitcherName
                        },
                        "room_id": str(pk)
                    }
                    try:
                        await ws.send(json.dumps(airbender_payload))
                        print(f"[POLLER] Air Bender overlay triggered for Devon Williams pitching in game {pk}!")
                    except Exception as airbender_err:
                        print(f"[POLLER] Failed to send Air Bender overlay: {airbender_err}")

                # Keith Hernandez "Go Sit Down" Takeover Overlay trigger (WO0010025)
                # Fires when a batter strikes out on a called strike, challenges via ABS, and is wrong (call confirmed/stands)
                try:
                    p_desc_lower = playDesc.lower()
                    is_abs_challenge = "challenged" in p_desc_lower and ("pitch result" in p_desc_lower or "abs" in p_desc_lower)
                    is_challenge_lost = (
                        "call on the field was confirmed" in p_desc_lower
                        or "call on the field stands" in p_desc_lower
                        or "call stands" in p_desc_lower
                        or "call was confirmed" in p_desc_lower
                    )
                    is_called_strikeout = "called out on strikes" in p_desc_lower or ("strikes out" in p_desc_lower and strikes == 3)
                    
                    if is_abs_challenge and is_challenge_lost and is_called_strikeout:
                        sit_down_payload = {
                            "type": "CMD_SIT_DOWN",
                            "media_url": "/media/Keith_thrusts_arm__GO_SIT_202606201553.mp4",
                            "sprite_url": "/media/go_sit_down_keith_fanboy_transparent.png",
                            "duration_ms": 4500,
                            "game_pk": str(pk),
                            "batter": batterName,
                            "pitcher": pitcherName,
                            "play_desc": playDesc
                        }
                        await ws.send(json.dumps(sit_down_payload))
                        print(f"[POLLER] Keith Hernandez 'Go Sit Down' overlay triggered for game {pk}: {playDesc}")
                except Exception as sit_down_err:
                    print(f"[POLLER] Failed to process/send CMD_SIT_DOWN: {sit_down_err}")

                # PRECOG 50-SECOND PREDICTIVE VIDEO PIPELINE TRIGGER (DISABLED)
                pass

                # HOT CACHE WRITE: Atomically persist full game state to disk.
                # Gated by the state_hash delta check above — only fires on real changes.
                # Non-fatal: a disk error must never drop the active WebSocket connection.
                try:
                    _write_game_state_cache(pk, feed, payload["data"])
                    _record_telemetry_audit(pk, feed, payload["data"])
                    _write_fanstack_heartbeat(len(active_games), playDesc)
                except Exception as _cache_err:
                    print(f"[CACHE WRITE] Non-fatal error for game {pk}: {_cache_err}")

                # RECONCILE FINAL STATE: When game concludes, close room and mark Final in database
                if status == "Final":
                    try:
                        _con = get_db(row_factory=False)
                        try:
                            with _con:
                                _con.execute(
                                    "UPDATE sport_schedule SET status = 'Final', room_state = 'staged', away_score = ?, home_score = ?, sys_updated_on = datetime('now') WHERE game_pk = ?",
                                    (away_score, home_score, str(pk))
                                )
                                _con.execute("UPDATE mlb_schedule SET status = 'Final' WHERE game_pk = ?", (str(pk),))
                                _con.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'staged', sys_updated_on = datetime('now') WHERE game_pk = ?", (str(pk),))
                                _con.execute("UPDATE active_game_rooms SET status = 'CLOSED', sys_updated_on = datetime('now') WHERE game_id = ?", (str(pk),))
                        finally:
                            _con.close()
                        print(f"[POLLER] Game {pk} marked Final & room staged in DB ({away_team} {away_score} - {home_score} {home_team})")
                    except Exception as db_final_err:
                        print(f"[POLLER] Error updating final status for game {pk}: {db_final_err}")

                try:
                    accumulator = GameStateAccumulator(pk, feed, status)
                    await accumulator.evaluate_triggers(ws)
                except Exception as accum_err:
                    print(f"[POLLER] GameStateAccumulator error for game {pk}: {accum_err}")

                # Update chatbot context on ghost pitch anomaly (without injecting raw chat messages)
                if playDesc and "Awaiting" not in playDesc and "Scheduled" not in playDesc and "Warmup" not in playDesc:
                    if whiff_image_url:
                        ctx_msg = {
                            "type": "update_context",
                            "text": f"GHOST PITCH ANOMALY: {batterName} just swung and completely missed a pitch from {pitcherName}. The ball passed under the bat with a whopping spatial gap of {miss_distance} inches! The bat speed was {bat_speed} MPH. The room is in shock! React to this crazy whiff!",
                            "target_nodes": ["ALL"],
                            "target_game_pk": str(pk)
                        }
                        try:
                            await ws.send(json.dumps(ctx_msg))
                        except Exception as ctx_err:
                            print(f"[POLLER] Failed to send context update: {ctx_err}")

                # Check for Extra Innings Trigger — fires when game enters 10th inning or higher
                current_inning = linescore.get("currentInning", 0)
                if current_inning >= 10 and db_room_state == 'active':
                    noti_key = f"{pk}_{current_inning}"
                    if not extra_innings_notified.get(noti_key, False):
                        extra_innings_notified[noti_key] = True
                        
                        # Set the room's Boggs Level to 4!
                        boggs_payload = {
                            "type": "BOGGS_LEVEL_UPDATE",
                            "level": 4,
                            "target_game_pk": str(pk)
                        }
                        try:
                            await ws.send(json.dumps(boggs_payload))
                        except Exception as e:
                            print(f"[POLLER] Failed to send extra inning boggs level: {e}")
                        
                        # Send an exciting Extra Innings sensory update to the chat
                        extra_msg = {
                            "type": "CHAT_MESSAGE",
                            "user": "SYSTEM",
                            "text": f"🚨 SENSORY OVERDRIVE: Game {pk} has entered EXTRA INNINGS ({inning} Inning)! BOGGS OVERDRIVE CRANKED TO MAX LEVEL 4!!!",
                            "color": "#FF003C",
                            "target_game_pk": str(pk),
                            "shake": True
                        }
                        try:
                            await ws.send(json.dumps(extra_msg))
                        except Exception as e:
                            print(f"[POLLER] Failed to send extra inning chat message: {e}")
                
                # Check for TMI Delay Triggers — fires for ALL live games, not just active rooms
                is_delayed = "Delay" in detailed_status
                if is_delayed and not delay_state_map.get(pk, False):
                    # Transition to Delayed! Fire TMI
                    delay_state_map[pk] = True
                    try:
                        con = get_db(row_factory=False)
                        cur = con.cursor()
                        # Favor scenarios specifically mapped to this game_pk, fallback to any random scenario if none found
                        cur.execute("SELECT name, payload FROM cmdb_ci_tmi_scenario WHERE game_pk = ? ORDER BY RANDOM() LIMIT 1", (str(pk),))
                        row = cur.fetchone()
                        if not row:
                            cur.execute("SELECT name, payload FROM cmdb_ci_tmi_scenario ORDER BY RANDOM() LIMIT 1")
                            row = cur.fetchone()
                        con.close()
                        
                        if row:
                            tmi_payload = row[1]
                            tmi_msg = {
                                "type": "TMI_ANOMALY",
                                "event": "Delay of Game (Rain / Unspecified)",
                                "time": f"LIVE (Game {pk})",
                                "persona": "BatteryBarf", 
                                "format": "Format B (2D Cartoon)",
                                "script": tmi_payload,
                                "prompt": "2D animation, flat comic-book coloring, cartoon style. An anthropomorphic dog wearing a thick medical neck brace...",
                                "id": f"anom-{pk}-{int(time.time())}",
                                "target_game_pk": "GLOBAL"
                            }
                            # Also dispatch standard update_context to local so Playcall Desk catches the override
                            local_msg = {
                                "type": "update_context",
                                "text": f"SYSTEM OVERRIDE (TMI TIMELINE BRANCH): {tmi_payload}",
                                "target_game_pk": str(pk)
                            }
                            await ws.send(json.dumps(local_msg))
                            await ws.send(json.dumps(tmi_msg))
                            print(f"[TMI] Executing Autonomous Timeline Prune for Game {pk}: {row[0]}")
                    except Exception as tmi_e:
                        print(f"TMI Execution Error: {tmi_e}")
                elif not is_delayed and delay_state_map.get(pk, False):
                    # Transition OUT of Delay
                    delay_state_map[pk] = False
                    
                # Catch-All TMI Sweeper — fires for ALL live games (feeds TMI News Desk regardless of active room)
                if playDesc:
                    l_desc = playDesc.lower()
                    is_hr = "homers" in l_desc or "home run" in l_desc or "grand slam" in l_desc
                    is_weird = "eject" in l_desc or "balk" in l_desc or "review" in l_desc or "interfere" in l_desc or "injur" in l_desc or "brawl" in l_desc or "fight" in l_desc or "benches clear" in l_desc
                    
                    run_diff = abs(away_score - home_score)
                    current_blowout_state = blowout_state_map.get(pk, 0)
                    is_blowout = False
                    blowout_level = 0
                    
                    if run_diff >= 15 and current_blowout_state < 15:
                        is_blowout = True; blowout_level = 15
                        blowout_state_map[pk] = 15
                    elif run_diff >= 10 and current_blowout_state < 10:
                        is_blowout = True; blowout_level = 10
                        blowout_state_map[pk] = 10
                    elif run_diff >= 7 and current_blowout_state < 7:
                        is_blowout = True; blowout_level = 7
                        blowout_state_map[pk] = 7

                    if (is_hr or is_weird or is_blowout):
                        if is_blowout:
                            event_title = f"Massive Blowout Alert ({blowout_level}+ Run Differential)"
                        elif is_hr:
                            event_title = "Home Run Detected" 
                        else:
                            event_title = "Game Anomaly / High Entropy Event"
                            
                        tmi_catchall_msg = {
                            "type": "TMI_ANOMALY",
                            "event": f"[{away_team}@{home_team}] {event_title}",
                            "time": f"{half} {inning}",
                            "persona": "Flowmercial Specialist", 
                            "format": "Format C (Dynamic Flow)",
                            "script": f"React dynamically to this: {playDesc}",
                            "prompt": f"A shocked or excited baseball fan reacting to a screen showing: {playDesc}. Extreme emotional expression, cinematic sports style.",
                            "id": f"anom-catchall-{pk}-{int(time.time())}",
                            "target_game_pk": "GLOBAL"
                        }
                        try:
                            await ws.send(json.dumps(tmi_catchall_msg))
                            print(f"[TMI] Captured High-Entropy Play: {event_title} for Game {pk}")
                        except: pass
                    
            except Exception as e:
                print(f"[SEND_ERROR] Dropping cache hash to force retry: {e}")
                raise e

async def main():
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=10, ping_timeout=20) as ws:
                print("[BACKGROUND POLLER] Connected to Sovereign Mesh!")
                # Register as a POLLER room to avoid receiving standard broadcasts
                await ws.send(json.dumps({
                    "type": "JOIN_ROOM",
                    "target_game_pk": "POLLER",
                    "room": "POLLER"
                }))
                # Clear state hash cache on new connection/reconnection to force state re-sync
                last_status_map.clear()
                while True:
                    await poll_games(ws)
                    await asyncio.sleep(1)  # 1s poll 
        except Exception as e:
            print(f"[RECONNECT] Lost connection to mesh, retrying in 10s... {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())

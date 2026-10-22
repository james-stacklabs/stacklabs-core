#!/usr/bin/env python3
"""
Sovereign Sentiment Circuit Breaker & Actuation Engine
Path: /home/james/stacklabs/scripts/sentiment_actuation_daemon.py
Architecture: Low-latency deterministic event-driven actuation on Clio metal.
Author: James Carroll, Lead Systems Architect, StackLabs LLC
"""

import os
import sys
import time
import json
import sqlite3
import re
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Canonical paths
DB_PATH = "/home/james/stacklabs/data/morning_wiretap.db"
ACTUATION_STATUS_PATH = "/home/james/stacklabs/data/actuation_status.json"
ACTUATION_LOG_PATH = "/home/james/stacklabs/data/actuation_log.json"
BULLETIN_PATH = "/home/james/stacklabs/data/snipes/cache/emergency_bulletin.json"
PREDICT_STATE_PATH = "/home/james/stacklabs/data/predict_market_state.json"

# Lexicons for deterministic sentiment categorization (Clio APU protection)
RAGE_PATTERNS = re.compile(
    r"\b(fire|bench|trash|garbage|choke|choked|choking|fraud|embarrassing|disaster|cut him|"
    r"worst|unbelievable|horrible|refs|rigged|blown|punt|season over|kill me|sell the team|"
    r"dennis allen|terrible|fire allen|pathetic|gross|fucking joke|ass|blown lead)\b",
    re.IGNORECASE
)

HYPE_PATTERNS = re.compile(
    r"\b(touchdown|td|holy shit|lfg|lets go|let\'s go|unreal|mvp|clutch|super bowl|who dat|"
    r"rise up|cooking|dime|pick six|interception|sack|boomed|stud|elite|money|perfection)\b",
    re.IGNORECASE
)

class SentimentActuationEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.last_evaluated_id = 0
        self.active_breaker = "CIRCUIT BREAKER: IDLE"
        self.breaker_cooldown_until = 0.0
        self.recent_events: List[Dict[str, Any]] = []
        
        # Ensure target directories exist
        os.makedirs(os.path.dirname(ACTUATION_STATUS_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(BULLETIN_PATH), exist_ok=True)
        
        # Initialize last_evaluated_id to most recent db record if present
        self._init_watermark()

    def _init_watermark(self):
        if not os.path.exists(self.db_path):
            return
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT MAX(id) FROM chat_telemetry")
            row = cur.fetchone()
            if row and row[0]:
                self.last_evaluated_id = max(0, row[0] - 50)
            conn.close()
        except Exception:
            self.last_evaluated_id = 0

    def query_recent_telemetry(self, window_seconds: float = 60.0) -> List[Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return []
        
        now = time.time()
        start_epoch = now - window_seconds
        results = []
        
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=2.0)
            cur = conn.cursor()
            cur.execute("""
                SELECT id, channel_key, stream_id, author, message, timestamp_str, epoch_time
                FROM chat_telemetry
                WHERE epoch_time >= ?
                ORDER BY id ASC
            """, (start_epoch,))
            rows = cur.fetchall()
            conn.close()
            
            for r in rows:
                results.append({
                    "id": r[0],
                    "channel_key": r[1],
                    "stream_id": r[2],
                    "author": r[3],
                    "message": r[4] or "",
                    "timestamp_str": r[5],
                    "epoch_time": r[6]
                })
        except Exception as e:
            # Non-blocking SQLite WAL contention fallback
            pass
            
        return results

    def compute_metrics(self, messages: List[Dict[str, Any]], window_seconds: float = 60.0) -> Dict[str, Any]:
        count = len(messages)
        if count == 0:
            return {
                "count": 0,
                "velocity_msgs_per_min": 0.0,
                "misery_index": 0.0,
                "joy_index": 0.0,
                "tilt_ratio": 0.0,
                "top_rage_quotes": [],
                "top_hype_quotes": []
            }
            
        velocity = (count / window_seconds) * 60.0
        rage_count = 0
        hype_count = 0
        rage_quotes = []
        hype_quotes = []
        
        for m in messages:
            txt = m["message"]
            has_rage = bool(RAGE_PATTERNS.search(txt))
            has_hype = bool(HYPE_PATTERNS.search(txt))
            
            if has_rage:
                rage_count += 1
                if len(rage_quotes) < 5:
                    rage_quotes.append(f"{m['author']}: \"{txt.strip()}\"")
            if has_hype:
                hype_count += 1
                if len(hype_quotes) < 5:
                    hype_quotes.append(f"{m['author']}: \"{txt.strip()}\"")
                    
        misery_index = round(rage_count / count, 3)
        joy_index = round(hype_count / count, 3)
        tilt_ratio = round(rage_count / max(1, hype_count), 2)
        
        return {
            "count": count,
            "velocity_msgs_per_min": round(velocity, 1),
            "misery_index": misery_index,
            "joy_index": joy_index,
            "tilt_ratio": tilt_ratio,
            "top_rage_quotes": rage_quotes,
            "top_hype_quotes": hype_quotes
        }

    def evaluate_circuit_breakers(self, metrics: Dict[str, Any]) -> Tuple[str, bool]:
        now = time.time()
        
        # Respect 45-second breaker cooldown to prevent flapping
        if now < self.breaker_cooldown_until:
            return self.active_breaker, False
            
        velocity = metrics["velocity_msgs_per_min"]
        misery = metrics["misery_index"]
        joy = metrics["joy_index"]
        
        # Minimum threshold: at least 15 msgs/min to avoid false positives on quiet chats
        if velocity < 15.0:
            self.active_breaker = "CIRCUIT BREAKER: IDLE"
            return self.active_breaker, False
            
        # Circuit Breaker 1: Mass Fan Meltdown
        if misery >= 0.55 and velocity >= 20.0:
            self.active_breaker = "CIRCUIT BREAKER: FAN MELTDOWN TRIPPED"
            self.breaker_cooldown_until = now + 45.0
            return self.active_breaker, True
            
        # Circuit Breaker 2: Surprise Triumph
        if joy >= 0.55 and velocity >= 20.0:
            self.active_breaker = "CIRCUIT BREAKER: SURPRISE TRIUMPH TRIPPED"
            self.breaker_cooldown_until = now + 45.0
            return self.active_breaker, True
            
        self.active_breaker = "CIRCUIT BREAKER: IDLE"
        return self.active_breaker, False

    def actuate(self, breaker_name: str, metrics: Dict[str, Any]):
        """Dispatches sovereign actions upon breaker trip."""
        now_iso = datetime.now(timezone.utc).isoformat()
        
        event_record = {
            "timestamp": now_iso,
            "breaker": breaker_name,
            "velocity": metrics["velocity_msgs_per_min"],
            "misery_index": metrics["misery_index"],
            "joy_index": metrics["joy_index"],
            "quotes": metrics["top_rage_quotes"] if "MELTDOWN" in breaker_name else metrics["top_hype_quotes"]
        }
        
        self.recent_events.insert(0, event_record)
        self.recent_events = self.recent_events[:20]
        
        # 1. Generate Emergency 3-Bullet Radio Dispatch
        headline = "EMERGENCY FAN BASE MELTDOWN IN PROGRESS" if "MELTDOWN" in breaker_name else "ECSTATIC STADIUM TRIUMPH WAVE"
        bullets = [
            f"Chat velocity accelerated to {metrics['velocity_msgs_per_min']} msgs/min with {int(metrics['misery_index']*100)}% emotional tilt.",
            f"Primary fan quote: {metrics['top_rage_quotes'][0] if metrics['top_rage_quotes'] else 'Chaos on field.'}",
            "Sovereign Actuation Engine locked circuit breaker; automated Sicko repricing engaged."
        ]
        
        bulletin_payload = {
            "timestamp": now_iso,
            "headline": headline,
            "bullets": bullets,
            "status": breaker_name,
            "scar_tissue_index": 9 if "MELTDOWN" in breaker_name else 2
        }
        
        tmp_bulletin = f"{BULLETIN_PATH}.tmp"
        with open(tmp_bulletin, "w") as f:
            json.dump(bulletin_payload, f, indent=2)
        os.replace(tmp_bulletin, BULLETIN_PATH)
        
        # 2. Append to historical actuation ledger
        try:
            log_entries = []
            if os.path.exists(ACTUATION_LOG_PATH):
                with open(ACTUATION_LOG_PATH, "r") as f:
                    log_entries = json.load(f)
            log_entries.append(event_record)
            tmp_log = f"{ACTUATION_LOG_PATH}.tmp"
            with open(tmp_log, "w") as f:
                json.dump(log_entries[-100:], f, indent=2)
            os.replace(tmp_log, ACTUATION_LOG_PATH)
        except Exception:
            pass

    def export_status(self, metrics: Dict[str, Any]):
        """Flushes atomic status JSON for Port 3033 / Direct Wire consumption."""
        payload = {
            "version": "1.0.0",
            "service": "SOVEREIGN ACTUATION ENGINE",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active_breaker": self.active_breaker,
            "cooldown_remaining_sec": max(0.0, round(self.breaker_cooldown_until - time.time(), 1)),
            "telemetry": {
                "active_window_sec": 60,
                "message_count": metrics["count"],
                "velocity_msgs_per_min": metrics["velocity_msgs_per_min"],
                "misery_index": metrics["misery_index"],
                "joy_index": metrics["joy_index"],
                "tilt_ratio": metrics["tilt_ratio"]
            },
            "top_quotes": {
                "rage": metrics["top_rage_quotes"],
                "hype": metrics["top_hype_quotes"]
            },
            "recent_trips": self.recent_events[:5]
        }
        
        tmp_status = f"{ACTUATION_STATUS_PATH}.tmp"
        with open(tmp_status, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_status, ACTUATION_STATUS_PATH)

    def tick(self):
        messages = self.query_recent_telemetry(window_seconds=60.0)
        metrics = self.compute_metrics(messages, window_seconds=60.0)
        breaker, tripped = self.evaluate_circuit_breakers(metrics)
        
        if tripped:
            self.actuate(breaker, metrics)
            
        self.export_status(metrics)

    def run_forever(self, interval_seconds: float = 2.5):
        print(f"[+] Sovereign Sentiment Actuation Daemon active. Ticking every {interval_seconds}s...")
        while True:
            try:
                self.tick()
            except Exception as e:
                print(f"[!] Error in actuation loop: {e}", file=sys.stderr)
            time.sleep(interval_seconds)

if __name__ == "__main__":
    engine = SentimentActuationEngine()
    engine.run_forever()

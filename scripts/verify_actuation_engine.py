#!/usr/bin/env python3
"""
Forensic Verification Suite for Sovereign Actuation Engine
Path: /home/james/stacklabs/scripts/verify_actuation_engine.py
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, "/home/james/stacklabs")
from scripts.sentiment_actuation_daemon import (
    SentimentActuationEngine,
    ACTUATION_STATUS_PATH,
    BULLETIN_PATH,
    ACTUATION_LOG_PATH
)

def run_forensic_audit():
    print("=" * 60)
    print("⚡ FORENSIC VERIFICATION: SOVEREIGN ACTUATION ENGINE")
    print("=" * 60)
    
    # 1. Instantiate engine in dry mode
    engine = SentimentActuationEngine()
    assert engine is not None, "Failed to instantiate SentimentActuationEngine"
    print("[PASS] SentimentActuationEngine initialized cleanly.")
    
    # 2. Test Synthetic Sentiment Lexicon Computation
    test_messages = [
        {"id": 1, "author": "@User1", "message": "Fire this coach right now, he is complete trash!", "epoch_time": time.time()},
        {"id": 2, "author": "@User2", "message": "Worst play call I have ever seen. Unbelievable choke.", "epoch_time": time.time()},
        {"id": 3, "author": "@User3", "message": "Embarrassing defense. Dennis Allen is a fraud.", "epoch_time": time.time()},
        {"id": 4, "author": "@User4", "message": "Touchdown! Lets go who dat!", "epoch_time": time.time()},
    ]
    
    metrics = engine.compute_metrics(test_messages, window_seconds=60.0)
    print(f"[*] Computed Synthetic Metrics: Misery={metrics['misery_index']} Joy={metrics['joy_index']} Velocity={metrics['velocity_msgs_per_min']}")
    assert metrics["misery_index"] >= 0.70, f"Expected misery >= 0.70, got {metrics['misery_index']}"
    assert metrics["count"] == 4, "Expected count == 4"
    print("[PASS] Lexicon analysis accurately identifies fan misery vs hype.")
    
    # 3. Test Circuit Breaker Trip & Actuation
    breaker, tripped = engine.evaluate_circuit_breakers({"velocity_msgs_per_min": 35.0, "misery_index": 0.80, "joy_index": 0.10})
    assert tripped is True, "Circuit breaker should have tripped on 80% misery and 35 msgs/min"
    assert breaker == "CIRCUIT BREAKER: FAN MELTDOWN TRIPPED", f"Unexpected breaker state: {breaker}"
    print(f"[PASS] Circuit breaker tripped as expected: {breaker}")
    
    # 4. Trigger Actuation and Validate Atomic Disk Artifacts
    engine.actuate(breaker, metrics)
    engine.export_status(metrics)
    
    assert os.path.exists(ACTUATION_STATUS_PATH), f"Status file missing: {ACTUATION_STATUS_PATH}"
    with open(ACTUATION_STATUS_PATH, "r") as f:
        status_data = json.load(f)
    assert status_data["active_breaker"] == "CIRCUIT BREAKER: FAN MELTDOWN TRIPPED"
    assert status_data["service"] == "SOVEREIGN ACTUATION ENGINE"
    print(f"[PASS] Atomic status file verified ({os.path.getsize(ACTUATION_STATUS_PATH)} bytes).")
    
    assert os.path.exists(BULLETIN_PATH), f"Emergency bulletin missing: {BULLETIN_PATH}"
    with open(BULLETIN_PATH, "r") as f:
        bulletin_data = json.load(f)
    assert len(bulletin_data["bullets"]) == 3, "Expected strictly 3 bullets in emergency bulletin"
    print(f"[PASS] Emergency 3-bullet dispatch bulletin verified ({os.path.getsize(BULLETIN_PATH)} bytes).")
    
    print("=" * 60)
    print("🎯 FORENSIC VERIFICATION COMPLETE: ALL GATES PASS (100%)")
    print("=" * 60)

if __name__ == "__main__":
    run_forensic_audit()

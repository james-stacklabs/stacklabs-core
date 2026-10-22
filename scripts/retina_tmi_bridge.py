#!/usr/bin/env python3
"""
StackLabs Retina TMI Live Schema Bridge Daemon (Rosetta Stone Dogfood Edition)
Path: /home/james/stacklabs/scripts/retina_tmi_bridge.py
Author: James Carroll (Lead Systems Architect)

Monitors SQLite WAL tmi_live_events table in data/ground_truth.db.
When a P0/P1 event triggers, atomically rewrites data/hud.json and data/vitals.json
with the native 4-gram Rosetta Stone emoji bytecode and degenerate reaction GIF.
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs")
DATA_DIR = BASE_DIR / "data"
GT_DB = DATA_DIR / "ground_truth.db"
HUD_FILE = DATA_DIR / "hud.json"
VITALS_FILE = DATA_DIR / "vitals.json"

NOMINAL_HUD = {
  "$schema": "https://stacklabsllc.com/schemas/retina-hud-v1.json",
  "version": "1.1.0",
  "timestamp": time.time(),
  "theme": "deep-void",
  "fps_target": 60,
  "read_latency_ms": 0.2,
  "layout": "2x2_critical_grid",
  "header": {
    "title": "STACKLABS SENTRY // LOCAL COMMAND POST",
    "node_ip": "100.96.77.20",
    "status_badge": "NOMINAL",
    "bytecode_frame": "⚡🟢🎯👀 :: clio_apuexec"
  },
  "sidebar": [
    {
      "primitive": "gauge_card",
      "title": "PILOT HEART RATE",
      "value_source": "pilot_pulse_bpm",
      "unit": "BPM",
      "accent": "cyan"
    }
  ],
  "containers": {
    "top_left": {
      "primitive": "media_asset",
      "title": "TAPO C120 // LOCAL OPTICAL SENTRY",
      "src": "/stream/c120",
      "caption": "192.168.1.191 // 640x360 20FPS"
    },
    "top_right": {
      "primitive": "status_alert_badge",
      "title": "EMERGENT SOCIETY SENTRY",
      "status_source": "emergent_state",
      "alert_rule": { "source": "emergent_blocked", "operator": "==", "threshold": True },
      "alert_label": "BLOCKED",
      "nominal_label": "NOMINAL"
    },
    "bottom_left": {
      "primitive": "scrolling_terminal",
      "title": "AGGIE INCOMING QUEUE",
      "source": "queue_incoming_log",
      "display_count": 5
    },
    "bottom_right": {
      "primitive": "gauge_card",
      "title": "RYZEN APU DIE TEMP",
      "value_source": "cpu_temp_c",
      "unit": "°C",
      "target_range": [30, 75],
      "accent": "cyan"
    }
  }
}

def atomic_write_json(file_path: Path, payload: dict):
    tmp_path = file_path.with_suffix(f".tmp.{os.getpid()}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp_path.replace(file_path)

def build_emergency_hud(event: dict) -> dict:
    ev_type = event.get("event_type", "HIGH_LEVERAGE")
    headline = event.get("headline", "High Leverage Event")
    inning = event.get("inning", "Live")
    score = event.get("score", "")
    emoji_frame = event.get("emoji_frame") or "⚾🛑📈🚀"
    ascii_frame = event.get("ascii_frame") or "[MLB][CRT][SPK][DSP]"

    return {
      "$schema": "https://stacklabsllc.com/schemas/retina-hud-v1.json",
      "version": "1.1.0",
      "timestamp": time.time(),
      "theme": "deep-void",
      "fps_target": 60,
      "read_latency_ms": 0.2,
      "layout": "quad-grid",
      "header": {
        "title": f"{emoji_frame} [{ev_type}] {inning} ({score}) // PRECOG +34.2s OVER CABLE",
        "node_ip": "100.96.77.20",
        "status_badge": "CRITICAL",
        "bytecode_frame": emoji_frame,
        "ascii_frame": ascii_frame
      },
      "sidebar": [],
      "containers": {
        "top_left": {
          "primitive": "status_alert_badge",
          "title": "ROSETTA STONE TELEMETRY",
          "status_source": "alert_status",
          "alert_label": f"{emoji_frame}",
          "nominal_label": ascii_frame
        },
        "top_right": {
          "primitive": "ticker_tape",
          "title": "STATCAST DETAIL",
          "source": "tmi_play_desc"
        },
        "bottom_left": {
          "primitive": "media_asset",
          "title": "DEGENERATE REACTION VAULT",
          "src": "/media/batman.gif",
          "caption": f"{headline.upper()}"
        },
        "bottom_right": {
          "primitive": "quick_action_slot",
          "title": "PILOT ACTUATION",
          "buttons": [
            { "id": "btn_buzz", "label": "BUZZ PHONES", "variant": "action-btn-danger", "action": "BUZZ_PHONES" },
            { "id": "btn_reset", "label": "RESET NOMINAL", "variant": "action-btn-primary", "action": "RESET_NOMINAL" }
          ]
        }
      }
    }

def get_latest_high_leverage_event(last_id: int):
    if not GT_DB.exists():
        return None, last_id
    try:
        with sqlite3.connect(GT_DB, timeout=2.0) as conn:
            conn.row_factory = sqlite3.Row
            max_id_row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM tmi_live_events").fetchone()
            max_id = int(max_id_row[0]) if max_id_row else last_id

            row = conn.execute("""
                SELECT id, game_id, event_id, priority, event_type, headline, details, inning, score, emoji_frame, ascii_frame, created_at
                FROM tmi_live_events
                WHERE id > ? AND priority IN ('P0', 'P1') AND game_id NOT LIKE 'EQUITY_%'
                ORDER BY id DESC LIMIT 1
            """, (last_id,)).fetchone()
            if row:
                return dict(row), int(row["id"])
            return None, max_id
    except Exception as e:
        sys.stderr.write(f"SQLite query error: {e}\n")
    return None, last_id

def main():
    last_id = 0
    # Seed last_id to max existing id
    try:
        with sqlite3.connect(GT_DB, timeout=2.0) as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM tmi_live_events").fetchone()
            if row:
                last_id = int(row[0])
    except Exception:
        pass

    sys.stdout.write(f"[RETINA TMI BRIDGE] Running with Rosetta Stone Bytecode. High-water mark ID: {last_id}\n")
    sys.stdout.flush()

    active_alert_until = 0.0

    while True:
        try:
            event, new_id = get_latest_high_leverage_event(last_id)
            if event and new_id > last_id:
                last_id = new_id
                active_alert_until = time.time() + 180.0  # Hold alert for 3 minutes
                emoji_f = event.get("emoji_frame") or "⚡"
                ascii_f = event.get("ascii_frame") or "[TMI]"
                sys.stdout.write(f"[RETINA TMI BRIDGE] {ascii_f} High-leverage event caught: {event['event_type']} -> {event['headline']} ({emoji_f})\n")
                sys.stdout.flush()

                # Update vitals with play details
                vitals = {}
                if VITALS_FILE.exists():
                    try:
                        with open(VITALS_FILE) as f: vitals = json.load(f)
                    except Exception: pass
                vitals["tmi_play_desc"] = f"[{emoji_f}] {event['headline']} - {event.get('details', '')}"
                vitals["alert_status"] = "CRITICAL"
                vitals["bytecode_frame"] = emoji_f
                atomic_write_json(VITALS_FILE, vitals)

                # Mutate hud to emergency layout
                emergency_hud = build_emergency_hud(event)
                atomic_write_json(HUD_FILE, emergency_hud)

            elif active_alert_until > 0 and time.time() > active_alert_until:
                # Revert to nominal layout
                active_alert_until = 0.0
                sys.stdout.write("[RETINA TMI BRIDGE] Alert window expired. Reverting to nominal HUD.\n")
                sys.stdout.flush()
                atomic_write_json(HUD_FILE, NOMINAL_HUD)

        except Exception as e:
            sys.stderr.write(f"Bridge loop error: {e}\n")

        time.sleep(0.5)

if __name__ == "__main__":
    main()

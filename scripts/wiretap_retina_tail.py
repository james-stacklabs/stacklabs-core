#!/usr/bin/env python3
"""
StackLabs Retina: Real-Time Wiretap Terminal Streamer
Path: /home/james/stacklabs/scripts/wiretap_retina_tail.py
Author: James Carroll (Lead Systems Architect)

Streams live allocator and counterparty events from /home/james/stacklabs/logs/retina_wiretap.log.
Highlights incoming page hits, pillar navigation, mobile touches, and Pawel Rudnicki activity.
Target: Clio (100.96.77.20) | Python 3.12 (.venv)
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path("/home/james/stacklabs/logs/retina_wiretap.log")

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_event(data: dict) -> str:
    ts = data.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    event = data.get("event", "UNKNOWN")
    source = data.get("source", "UNKNOWN")
    ip = data.get("ip", "unknown")
    country = data.get("country", "")
    device = data.get("device", "Desktop/Other")
    is_pawel = data.get("is_pawel", False)
    is_internal = data.get("is_internal", False)
    payload = data.get("data", {})

    # Badge selection
    if is_pawel:
        badge = f"{RED}{BOLD}⭐ [PAWEL RUDNICKI]{RESET}"
    elif event == "PAGE_MOUNT":
        badge = f"{CYAN}{BOLD}👀 [PAGE MOUNT]{RESET}"
    elif event == "PILLAR_NAVIGATE":
        badge = f"{GREEN}{BOLD}📱 [PILLAR NAV]{RESET}"
    elif event == "SCENARIO_ACTION":
        badge = f"{YELLOW}{BOLD}🎯 [SCENARIO ACTION]{RESET}"
    elif event == "DECK_SWITCH":
        badge = f"{MAGENTA}{BOLD}🔄 [DECK SWITCH]{RESET}"
    elif event == "STREAM_CONNECT":
        badge = f"{YELLOW}📹 [STREAM CONNECT]{RESET}"
    elif event == "PAGE_REQUEST":
        badge = f"{CYAN}🌐 [HTTP HIT]{RESET}"
    elif event == "HEARTBEAT":
        badge = f"{DIM}⏱️  [HEARTBEAT]{RESET}"
    elif event == "VISIBILITY_CHANGE":
        badge = f"{DIM}👁️  [VISIBILITY]{RESET}"
    else:
        badge = f"{DIM}[{event}]{RESET}"

    # Extract relevant details
    details = []
    if "quadrant" in payload or "label" in payload:
        details.append(f"Pillar: {BOLD}{payload.get('label') or payload.get('quadrant')}{RESET}")
    if "action" in payload:
        details.append(f"Action: {BOLD}{payload.get('action')}{RESET}")
    if "scenario" in payload:
        details.append(f"Scenario: {BOLD}{payload.get('scenario')}{RESET}")
    if "elapsedSeconds" in payload:
        details.append(f"Active: {payload.get('elapsedSeconds')}s")
    if "visibility" in payload:
        details.append(f"State: {payload.get('visibility')}")

    detail_str = " | ".join(details)
    detail_formatted = f" | {detail_str}" if detail_str else ""
    internal_marker = f" {DIM}[INTERNAL]{RESET}" if is_internal else ""

    return f"{badge} [{ts[11:19]} UTC] | IP: {BOLD}{ip}{RESET} ({country}){internal_marker} | Device: {device} | Event: {event}{detail_formatted}"


def main():
    parser = argparse.ArgumentParser(description="StackLabs Retina Wiretap Streamer")
    parser.add_argument("--all", action="store_true", help="Dump historical events before streaming")
    args = parser.parse_args()

    if not LOG_FILE.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.touch()

    print("=========================================================================")
    print(f"{BOLD}📡 STACKLABS RETINA // REAL-TIME WIRETAP TELEMETRY STREAM{RESET}")
    print(f"Log: {LOG_FILE}")
    print(f"Sentry: Monitoring hits from retina.stacklabsllc.com...")
    print("=========================================================================")

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        if not args.all:
            f.seek(0, os.SEEK_END)
        else:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        print(format_event(record))
                    except Exception:
                        pass

        while True:
            line = f.readline()
            if not line:
                time.sleep(0.3)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                print(format_event(record), flush=True)
            except Exception:
                print(f"[RAW] {line}", flush=True)


if __name__ == "__main__":
    main()

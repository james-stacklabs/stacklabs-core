#!/usr/bin/env python3
"""
Sovereign OS — Daemon Pulse Terminal TUI Monitor
Path: /home/james/stacklabs/scripts/poller_hud.py

A high-fidelity ANSI terminal HUD for real-time monitoring of Sovereign background daemons:
- scratch_pad_poller.py (Scratchpad / Pilot Drops)
- fanstack_background_poller.py (FanStack MLB Statcast)

Run directly in a Tilix split, tmux pane, or terminal tab:
    python3 scripts/poller_hud.py
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# ANSI Color Codes & Styles
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CLEAR_SCREEN = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# Sovereign Palette
CYAN = "\033[38;2;0;180;216m"
BRIGHT_CYAN = "\033[38;2;72;202;228m"
EMERALD = "\033[38;2;16;185;129m"
AMBER = "\033[38;2;245;158;11m"
ROSE = "\033[38;2;244;63;94m"
SLATE = "\033[38;2;148;163;184m"
DARK_SLATE = "\033[38;2;71;85;105m"
WHITE = "\033[38;2;248;250;252m"
BG_DARK = "\033[48;2;13;18;29m"

SP_HB_PATH = Path("/home/james/stacklabs/logs/scratch_pad_poller_heartbeat.json")
FS_HB_PATH = Path("/home/james/stacklabs/logs/fanstack_poller_heartbeat.json")
SP_LOG_PATH = Path("/home/james/stacklabs/logs/scratch_pad_poller.log")
SCRATCH_PAD_PATH = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")


def format_ago(seconds: float) -> str:
    if seconds is None:
        return f"{ROSE}--{RESET}"
    if seconds < 2.0:
        return f"{EMERALD}{seconds:.1f}s ago{RESET}"
    elif seconds < 8.0:
        return f"{BRIGHT_CYAN}{seconds:.1f}s ago{RESET}"
    elif seconds < 15.0:
        return f"{AMBER}{seconds:.1f}s ago{RESET}"
    else:
        return f"{ROSE}{seconds:.1f}s ago (STALE){RESET}"


def read_heartbeat(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_active_work_order() -> str:
    if not SCRATCH_PAD_PATH.exists():
        return "scratch_pad.md not found"
    try:
        with open(SCRATCH_PAD_PATH, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("- [ ]") or (stripped.startswith("### ") and "WO" in stripped) or (stripped.startswith("### ") and "ENHC" in stripped):
                    return stripped
        return "No pending work orders in queue"
    except Exception as e:
        return f"Error: {e}"


def get_log_tail(lines: int = 8) -> list:
    if not SP_LOG_PATH.exists():
        return ["Log file not found."]
    try:
        with open(SP_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-lines:]]
    except Exception as e:
        return [f"Error reading log: {e}"]


def render_hud():
    now = time.time()
    now_dt = datetime.now()
    clock_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Read heartbeats
    sp_data = read_heartbeat(SP_HB_PATH)
    fs_data = read_heartbeat(FS_HB_PATH)

    sp_ts = sp_data.get("timestamp")
    sp_ago = (now - sp_ts) if sp_ts else None
    sp_live = sp_ago is not None and sp_ago < 8.0

    fs_ts = fs_data.get("timestamp")
    fs_ago = (now - fs_ts) if fs_ts else None
    fs_live = fs_ago is not None and fs_ago < 12.0

    term_width = os.get_terminal_size().columns if hasattr(os, "get_terminal_size") else 80
    bar = "─" * min(term_width - 2, 78)

    output = []
    output.append(CLEAR_SCREEN)
    output.append(f"{CYAN}{BOLD}⚡ SOVEREIGN OS • DAEMON PULSE & HEARTBEAT HUD{RESET}  {DARK_SLATE}|{RESET}  {WHITE}{clock_str} EDT{RESET}")
    output.append(f"{DARK_SLATE}Workstation: {WHITE}clio (100.73.155.70){DARK_SLATE}  |  Web HUD: {BRIGHT_CYAN}http://clio.taila01894.ts.net:8088/pulse{RESET}")
    output.append(f"{DARK_SLATE}{bar}{RESET}")

    # Section 1: Scratchpad Poller
    sp_status_badge = f"{EMERALD}{BOLD}[● LISTENING]{RESET}" if sp_live else f"{ROSE}{BOLD}[● STALE/OFFLINE]{RESET}"
    if sp_live and sp_data.get("status") == "CLAIMED":
        sp_status_badge = f"{BRIGHT_CYAN}{BOLD}[● CLAIMED/ACTIVE]{RESET}"

    output.append(f"{BOLD}1. SCRATCHPAD & PILOT DROPS POLLER{RESET} {sp_status_badge}")
    output.append(f"   PID: {WHITE}{sp_data.get('pid', '--')}{RESET}  |  Polls: {CYAN}#{sp_data.get('poll_count', '--'):,}{RESET}" if isinstance(sp_data.get('poll_count'), int) else f"   PID: {WHITE}{sp_data.get('pid', '--')}{RESET}  |  Polls: {CYAN}--{RESET}")
    output.append(f"   Heartbeat: {format_ago(sp_ago)}  |  Service: {SLATE}scratch-pad-poller.service{RESET}")
    output.append(f"   Pad SHA: {DARK_SLATE}{sp_data.get('scratch_pad_sha256', '--')}{RESET}  |  Unresolved Tasks: {WHITE}{sp_data.get('unresolved_tasks_count', 0)}{RESET}")
    output.append("")

    # Section 2: FanStack Statcast Poller
    fs_status_badge = f"{EMERALD}{BOLD}[● STREAMING]{RESET}" if fs_live else f"{ROSE}{BOLD}[● STALE/OFFLINE]{RESET}"
    output.append(f"{BOLD}2. FANSTACK MLB STATCAST POLLER{RESET} {fs_status_badge}")
    output.append(f"   PID: {WHITE}{fs_data.get('pid', '--')}{RESET}  |  Active Games: {EMERALD}{fs_data.get('active_games_count', 0)} live{RESET}")
    output.append(f"   Heartbeat: {format_ago(fs_ago)}  |  Service: {SLATE}fanstack-poller.service{RESET}")
    last_play = fs_data.get('last_play_desc', 'In-between pitches')
    if len(last_play) > 55:
        last_play = last_play[:52] + "..."
    output.append(f"   Last Play: {WHITE}{last_play}{RESET}")
    output.append(f"{DARK_SLATE}{bar}{RESET}")

    # Section 3: Active Staging Buffer Task
    output.append(f"{BOLD}📝 ACTIVE STAGING TASK (scratch_pad.md):{RESET}")
    active_task = get_active_work_order()
    output.append(f"   {BRIGHT_CYAN}{active_task}{RESET}")
    output.append(f"{DARK_SLATE}{bar}{RESET}")

    # Section 4: Live Execution Log Tail
    output.append(f"{BOLD}⚡ ROLLING LOG STREAM (scratch_pad_poller.log):{RESET}")
    logs = get_log_tail(7)
    for log_line in logs:
        # Shorten or format line
        if len(log_line) > term_width - 5:
            log_line = log_line[:term_width - 8] + "..."
        if "[INFO]" in log_line:
            output.append(f"   {DARK_SLATE}{log_line}{RESET}")
        elif "[ERROR]" in log_line or "Exception" in log_line:
            output.append(f"   {ROSE}{log_line}{RESET}")
        else:
            output.append(f"   {SLATE}{log_line}{RESET}")

    output.append(f"{DARK_SLATE}{bar}{RESET}")
    output.append(f"{DARK_SLATE}Refreshing at 1.0Hz • Press {WHITE}Ctrl+C{DARK_SLATE} to exit{RESET}")

    sys.stdout.write("\n".join(output) + "\n")
    sys.stdout.flush()


def main():
    if "--once" in sys.argv:
        render_hud()
        return

    sys.stdout.write(HIDE_CURSOR)
    try:
        while True:
            render_hud()
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(SHOW_CURSOR + "\n" + RESET)
        sys.stdout.flush()


if __name__ == "__main__":
    main()

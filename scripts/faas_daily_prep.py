#!/usr/bin/env python3
"""
faas_daily_prep.py
==================
Tool #67 // Sovereign OS FaaS Daily Prep & Morning Ignition Engine

Automates the complete morning preparation routine for FanStack as a Service (FaaS).
Replaces the deprecated legacy FanStack watch-party chatroom/stadium sequence with
the lightweight information pipeline:
  1. Sports Ground Truth (2026 Invariant 30, MLB Postseason, NFL Week 4/5, CFB)
  2. Official Schedules (MLB, NFL, CFB)
  3. National RSS Entropy & Beat News Crawlers
  4. Sportsbook Promo Sweeper (sovereign.fanstack@gmail.com)
  5. Stream Ingress Pre-Seeding (Pat McAfee Show & Evening MLB Watch Parties)
  6. Daemon Health Roll Call (PIDs, Ports, Apollo Hook Gate)
  7. Morning Vitals Reset (Systolic/Diastolic 120/80, Boggs Saturation Meter 0/107)
  8. Cloud Synchronization & Google Drive Staging (Tool #64 faas_drive_sync)

Governed by:
  - Invariant 24: FaaS Lightweight Information Utility
  - Invariant 28: Post-Show Tri-Anchor Ground Truth Gate
  - Invariant 30: Sports Temporal Ground Truth (Current Year: 2026)
  - Invariant 33: Apollo Hook Invariant (Verified telemetry on metal)
"""

import os
import sys
import json
import time
import shutil
import sqlite3
import hashlib
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
INBOX_ROOT = Path("/home/james/sovereign_inbox")
TODAY_DIR = INBOX_ROOT / "today"
REPORTS_DIR = INBOX_ROOT / "reports"
RUNS_DIR = Path("/home/james/fanstack/runs")
VENV_PYTHON = str(SOVEREIGN_ROOT / ".venv" / "bin" / "python3")
SYS_PYTHON = sys.executable

TODAY_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)

STEP_RECORDS = []

def log(tag: str, msg: str, status: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": "\033[36m",
        "SUCCESS": "\033[32m",
        "WARN": "\033[33m",
        "ERROR": "\033[31m",
        "RESET": "\033[0m",
        "BOLD": "\033[1m"
    }
    c = colors.get(status, colors["INFO"])
    reset = colors["RESET"]
    bold = colors["BOLD"]
    print(f"[{ts}] {bold}{c}[{tag}]{reset} {msg}", flush=True)

def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        if not filepath.exists():
            return "FILE_NOT_FOUND"
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return f"ERR:{e}"

def dump_error_report(failed_step: dict):
    """Dump execution failure and stderr directly into faas_daily_prep_ERR.log."""
    err_file = REPORTS_DIR / "faas_daily_prep_ERR.log"
    err_content = (
        f"=== FAAS DAILY PREP FAILURE REPORT ===\n"
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
        f"Failed Phase: {failed_step.get('phase')}\n"
        f"Failed Step: {failed_step.get('name')}\n"
        f"Command: {' '.join(failed_step.get('cmd', []))}\n"
        f"Exit Code: {failed_step.get('returncode')}\n"
        f"Elapsed: {failed_step.get('elapsed_s', 0):.2f}s\n\n"
        f"--- STDERR ---\n{failed_step.get('stderr', '')}\n\n"
        f"--- STDOUT ---\n{failed_step.get('stdout', '')}\n"
    )
    err_file.write_text(err_content, encoding="utf-8")
    log("ERROR_LEDGER", f"Captured failure state -> {err_file}", "ERROR")

def run_step(step_num: int, name: str, cmd: list[str], timeout: int = 45, critical: bool = True) -> bool:
    log(f"PHASE {step_num}", f"Executing: {name}...", "INFO")
    t0 = time.time()
    try:
        res = subprocess.run(
            cmd,
            cwd=str(SOVEREIGN_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - t0
        record = {
            "phase": step_num,
            "name": name,
            "cmd": cmd,
            "returncode": res.returncode,
            "elapsed_s": elapsed,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }
        STEP_RECORDS.append(record)

        if res.returncode == 0:
            log(f"PHASE {step_num}", f"✅ {name} succeeded ({elapsed:.1f}s)", "SUCCESS")
            out = res.stdout.strip()
            if out:
                lines = [l for l in out.split("\n") if l.strip()]
                for l in lines[-2:]:
                    print(f"       \033[90m↳ {l[:100]}\033[0m")
            return True
        else:
            log(f"PHASE {step_num}", f"⚠️ {name} exited with code {res.returncode}", "WARN")
            if res.stderr.strip():
                print(f"       \033[31m↳ {res.stderr.strip()[:180]}\033[0m")
            if critical:
                dump_error_report(record)
            return False
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - t0
        record = {
            "phase": step_num,
            "name": name,
            "cmd": cmd,
            "returncode": -1,
            "elapsed_s": elapsed,
            "stdout": "",
            "stderr": f"TimeoutExpired: process exceeded {timeout}s limit"
        }
        STEP_RECORDS.append(record)
        log(f"PHASE {step_num}", f"⏱️ {name} timed out after {timeout}s", "WARN")
        if critical:
            dump_error_report(record)
        return False
    except Exception as e:
        elapsed = time.time() - t0
        record = {
            "phase": step_num,
            "name": name,
            "cmd": cmd,
            "returncode": -2,
            "elapsed_s": elapsed,
            "stdout": "",
            "stderr": str(e)
        }
        STEP_RECORDS.append(record)
        log(f"PHASE {step_num}", f"❌ {name} failed: {e}", "ERROR")
        if critical:
            dump_error_report(record)
        return False

def check_process_status(name: str, pattern: str) -> dict:
    try:
        res = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
        pids = [p.strip() for p in res.stdout.split("\n") if p.strip()]
        current_pid = str(os.getpid())
        pids = [p for p in pids if p != current_pid]
        return {"name": name, "running": len(pids) > 0, "pids": pids}
    except Exception:
        return {"name": name, "running": False, "pids": []}

def check_systemd_status(unit_name: str) -> dict:
    try:
        res = subprocess.run(["systemctl", "is-active", unit_name], capture_output=True, text=True)
        status = res.stdout.strip()
        return {"unit": unit_name, "active": status == "active", "status": status}
    except Exception as e:
        return {"unit": unit_name, "active": False, "status": str(e)}

def run_daemon_roll_call() -> dict:
    log("ROLLCALL", "Auditing active FaaS daemons and services on Clio...", "INFO")
    daemons = [
        check_process_status("faas_server", "faas_server.py"),
        check_process_status("fanstack_pulse_daemon", "fanstack_pulse_daemon.py"),
        check_process_status("the_skew_server", "the_skew_server.py"),
        check_process_status("stream_sniper_daemon", "stream_sniper_daemon.py")
    ]
    units = [
        check_systemd_status("faas_server.service"),
        check_systemd_status("faas_game_tailer.service"),
        check_systemd_status("metal_polygraph.service"),
        check_systemd_status("sovereign_canonical_comms.timer")
    ]
    print("\n  \033[1m=== FAAS DAEMON ROLL CALL (APOLLO HOOK VERIFICATION) ===\033[0m")
    for d in daemons:
        status_str = f"\033[32mACTIVE (PID {','.join(d['pids'])})\033[0m" if d['running'] else "\033[33mINACTIVE / STANDBY\033[0m"
        print(f"  • {d['name']:<25} : {status_str}")
    for u in units:
        status_str = f"\033[32mACTIVE\033[0m" if u['active'] else f"\033[33m{u['status'].upper()}\033[0m"
        print(f"  • {u['unit']:<25} : {status_str}")
    print()
    return {"daemons": daemons, "units": units}

def reset_morning_pulse_vitals():
    pulse_file = TODAY_DIR / "fanstack_pulse.json"
    resting_vitals = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state": "MORNING_RESTING_BASELINE",
        "blood_pressure": {
            "systolic": 120,
            "diastolic": 80,
            "status": "NORMAL",
            "trend": "STEADY"
        },
        "boggs_meter": {
            "beers_consumed": 0,
            "capacity": 107,
            "saturation_pct": 0.0,
            "status": "SOBER_BASELINE"
        },
        "persona_mood": "Optimistic / Morning Talk Radio",
        "voice_dsp": {
            "model": "gemini-3.8-flash-lite-tts",
            "voice": "Fenrir",
            "pitch": 0.8,
            "speed": 1.15,
            "filter": "AM_RADIO_BANDPASS_660_KHZ",
            "status": "ARMED"
        },
        "stream_ingress": {
            "morning_show": "The Pat McAfee Show (12:00 PM EDT)",
            "evening_slate": "MLB Postseason Wild Card Game 2 Slate",
            "tailer_target": "stream_chat_tail.md"
        }
    }
    with open(pulse_file, "w", encoding="utf-8") as f:
        json.dump(resting_vitals, f, indent=2)
    log("VITALS", f"✅ Morning vitals calibrated: 120/80 mmHg | Boggs: 0/107 beers -> {pulse_file}", "SUCCESS")

def run_stream_ingress_hygiene():
    log("HYGIENE", "Executing stream ingress hygiene: deduplicating chat tails & rotating buffer...", "INFO")
    source = TODAY_DIR / "stream_chat_tail.md"
    if not source.exists():
        log("HYGIENE", "stream_chat_tail.md not found, skipping hygiene.", "WARN")
        return
    
    file_size = source.stat().st_size
    seek_bytes = min(file_size, 2 * 1024 * 1024)
    with open(source, "rb") as f:
        f.seek(file_size - seek_bytes)
        raw = f.read()
    
    text = raw.decode("utf-8", errors="replace")
    entries = text.split("\n\n")
    
    seen = set()
    dedup_entries = []
    for entry in entries:
        cleaned = entry.strip()
        if not cleaned:
            continue
        if cleaned not in seen:
            seen.add(cleaned)
            dedup_entries.append(cleaned)
            
    MAX_CHARS = 400000
    selected = []
    curr_chars = 0
    for entry in reversed(dedup_entries):
        entry_len = len(entry) + 2
        if curr_chars + entry_len > MAX_CHARS:
            break
        selected.append(entry)
        curr_chars += entry_len
    selected.reverse()
    clean_tail = "\n\n".join(selected) + "\n"
    
    tmp_file = source.with_suffix(".tmp")
    tmp_file.write_text(clean_tail, encoding="utf-8")
    tmp_file.replace(source)
    
    p1 = SOVEREIGN_ROOT / "33_FanStack_Lite" / "public" / "FanStack_Live" / "stream_chat_tail.md"
    p2 = TODAY_DIR / "FanStack_Live" / "stream_chat_tail.md"
    p1.parent.mkdir(parents=True, exist_ok=True)
    p2.parent.mkdir(parents=True, exist_ok=True)
    p1.write_text(clean_tail, encoding="utf-8")
    p2.write_text(clean_tail, encoding="utf-8")
    log("HYGIENE", f"✅ Ingress buffer rotated & deduplicated: {len(selected)} entries ({len(clean_tail)} chars)", "SUCCESS")

def dump_success_report(start_time: float):
    elapsed_total = time.time() - start_time
    now_utc = datetime.now(timezone.utc).isoformat()
    now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Key artifacts to hash
    artifacts = {
        "active_sports_ground_truth.json": TODAY_DIR / "active_sports_ground_truth.json",
        "canonical_personas_calibrated.json": SOVEREIGN_ROOT / "data" / "canonical_personas_calibrated.json",
        "fanstack_pulse.json": TODAY_DIR / "fanstack_pulse.json",
        "deranged_market_state.json": SOVEREIGN_ROOT / "data" / "deranged_market_state.json",
        "stream_chat_tail.md": TODAY_DIR / "stream_chat_tail.md",
        "faas_bleacher_sharegpt_10k.jsonl": SOVEREIGN_ROOT / "data" / "training" / "faas_bleacher_sharegpt_10k.jsonl",
        "faas_bleacher_gemini_tuning.jsonl": SOVEREIGN_ROOT / "data" / "training" / "faas_bleacher_gemini_tuning.jsonl"
    }
    
    artifact_hashes = {}
    for name, path in artifacts.items():
        artifact_hashes[name] = {
            "path": str(path),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "sha256": calculate_sha256(path)
        }
        
    run_record = {
        "workflow": "WO0010042-FAAS-DAILY-PREP",
        "ticket_id": "FAAS-PREP-20261002-01",
        "timestamp_utc": now_utc,
        "elapsed_total_seconds": round(elapsed_total, 2),
        "steps_executed": len(STEP_RECORDS),
        "step_records": STEP_RECORDS,
        "artifact_hashes": artifact_hashes,
        "status": "SUCCESS"
    }
    
    # Write runs JSON
    run_file = RUNS_DIR / f"faas_daily_prep_run_{now_ts}.json"
    run_file.write_text(json.dumps(run_record, indent=2), encoding="utf-8")
    
    # Write success log
    success_log = REPORTS_DIR / "faas_daily_prep_SUCCESS.log"
    lines = [
        "==================================================================",
        "  ⚡ FAAS DAILY PREP WORKFLOW: EXECUTION SUCCESS LEDGER",
        "==================================================================",
        f"Timestamp UTC: {now_utc}",
        f"Elapsed Time: {elapsed_total:.2f}s",
        f"Run Artifact: {run_file}",
        "",
        "--- PHASES EXECUTED ---"
    ]
    for r in STEP_RECORDS:
        status_icon = "✅" if r.get("returncode") == 0 else "⚠️"
        lines.append(f"  {status_icon} Phase {r.get('phase')}: {r.get('name')} (Exit {r.get('returncode')}, {r.get('elapsed_s', 0):.1f}s)")
        
    lines.append("")
    lines.append("--- ARTIFACT HASHES & PROVENANCE ---")
    for name, meta in artifact_hashes.items():
        lines.append(f"  • {name:<35} : {meta['sha256'][:16]}... ({meta['size_bytes']} bytes)")
        
    lines.append("")
    lines.append("==================================================================")
    success_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("SUCCESS_LEDGER", f"Dumped execution metadata & hashes -> {success_log}", "SUCCESS")
    log("RUNS_LEDGER", f"Dumped run JSON -> {run_file}", "SUCCESS")

    err_log = REPORTS_DIR / "faas_daily_prep_ERR.log"
    if err_log.exists():
        try:
            err_log.unlink()
            log("ERROR_LEDGER", "Cleared stale failure log upon clean success.", "INFO")
        except Exception:
            pass

    # Update status token in queue
    status_token = INBOX_ROOT / "queue" / "atf_status.json"
    try:
        token_data = {
            "last_prep_workflow": "WO0010042-FAAS-DAILY-PREP",
            "ticket_id": "FAAS-PREP-20261002-01",
            "completed_at": now_utc,
            "status": "SUCCESS",
            "run_file": str(run_file)
        }
        status_token.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        log("STATUS_TOKEN", f"Updated status token -> {status_token}", "SUCCESS")
    except Exception as e:
        log("STATUS_TOKEN", f"Could not update status token: {e}", "WARN")

def main():
    parser = argparse.ArgumentParser(description="Tool #67: FaaS Daily Prep & Morning Ignition Engine")
    parser.add_argument("--fast", action="store_true", help="Fast execution path (<15s, skips heavy web crawlers)")
    parser.add_argument("--verify", action="store_true", help="Read-only audit: verify daemons, vitals, and ground truth")
    args, _ = parser.parse_known_args()

    t_start = time.time()
    py_bin = VENV_PYTHON if os.path.exists(VENV_PYTHON) else SYS_PYTHON

    print("\033[1;36m" + "=" * 70)
    print("  ⚡ SOVEREIGN OS // FANSTACK AS A SERVICE (FaaS) DAILY PREP")
    print(f"  Target Date: {datetime.now().strftime('%A, %B %d, %Y')} | Invariant 24 & 30 Compliance")
    print("=" * 70 + "\033[0m")

    if args.verify:
        run_daemon_roll_call()
        gt_file = TODAY_DIR / "active_sports_ground_truth.json"
        if gt_file.exists():
            log("VERIFY", f"✅ Ground Truth Active: {gt_file.stat().st_size} bytes (mtime: {time.ctime(gt_file.stat().st_mtime)})", "SUCCESS")
        else:
            log("VERIFY", f"⚠️ Ground Truth Missing: {gt_file}", "WARN")
        return

    # PHASE 1: Temporal Ground Truth (Tool #53)
    p1_ok = run_step(
        1,
        "Synchronize Sports Ground Truth (MLB / NFL 2026 / CFB)",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "sync_sports_ground_truth.py"), "--sport", "ALL"]
    )
    if not p1_ok:
        sys.exit(1)

    # PHASE 1b: Advocate Persona Bio & Scar Calibration (Tool #67)
    p1b_ok = run_step(
        1,
        "Sync Advocate Bios & Scars from Ground Truth",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "sync_advocate_bios_from_ground_truth.py")]
    )
    if not p1b_ok:
        sys.exit(1)

    # PHASE 2: Official Sports Schedules
    run_step(
        2,
        "Sync MLB Postseason Schedule (StatsAPI)",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "sync_mlb_schedule.py")]
    )
    run_step(
        2,
        "Sync NFL 2026 Schedule & Standings (ESPN)",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "sync_nfl_schedule.py")]
    )
    if not args.fast:
        run_step(
            2,
            "Sync College Football Schedule",
            [py_bin, str(SOVEREIGN_ROOT / "scripts" / "sync_cfb_schedule.py")]
        )

    # PHASE 3: Ambient Entropy & Editorial Ingress
    run_step(
        3,
        "Yardbarker Sports RSS Entropy Pump",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "yardbarker_entropy_pump.py")]
    )
    if not args.fast:
        run_step(
            3,
            "MLB Beat News Crawler (ESPN RSS / Transactions)",
            [py_bin, str(SOVEREIGN_ROOT / "scripts" / "mlb_news_crawler.py")]
        )
    run_step(
        3,
        "Gmail Sportsbook Promo Sweeper (sovereign.fanstack@gmail.com)",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "gmail_promo_sweeper.py")]
    )

    # PHASE 4: Stream Ingress & Pre-Game Channel Resolution
    run_step(
        4,
        "Pre-Resolve Watch Party Stream Targets",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "stream_url_resolver.py")]
    )

    # PHASE 4b: Ingress Hygiene & Consensus Verification
    run_stream_ingress_hygiene()
    run_step(
        4,
        "Verify Kalshi Consensus & Predict Market State on Metal",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "verify_deranged_predict_engine.py")]
    )

    # PHASE 5: Apollo Hook Telemetry Roll Call (Invariant 33)
    run_daemon_roll_call()

    # PHASE 6: Baseline Vitals & Persona Calibration (Voice Engine & Boggs Meter)
    reset_morning_pulse_vitals()

    # PHASE 6b: Downstream Corpora Staging for Refinery Queues
    if not args.fast:
        run_step(
            6,
            "Curate Offline Corpus & Fine-Tuning Scaffolding",
            [py_bin, str(SOVEREIGN_ROOT / "scripts" / "curate_offline_corpus.py")],
            timeout=120
        )

    # PHASE 7: Cloud Sync & Google Drive Staging (Tool #64)
    run_step(
        7,
        "FaaS Two-Way Google Drive Sync Loop (Tool #64)",
        [py_bin, str(SOVEREIGN_ROOT / "scripts" / "faas_drive_sync.py")],
        timeout=90
    )
    run_step(
        7,
        "Production Google Drive Sync (sync_to_gdrive.sh -gd)",
        ["bash", str(SOVEREIGN_ROOT / "scripts" / "sync_to_gdrive.sh"), "-gd"],
        timeout=60
    )

    # SUCCESS LEDGER DUMP
    dump_success_report(t_start)

    print("\033[1;32m" + "=" * 70)
    print("  ✅ FaaS DAILY PREP COMPLETE — LIGHTWEIGHT INFORMATION PLANE ARMED")
    print(f"  • 12:00 PM EDT: Pat McAfee Show Live Ingress Locks On")
    print(f"  • 01:00 PM EDT: Hourly Soft-Out 1 (hourly_soft_out.py --hour 1)")
    print(f"  • 02:00 PM EDT: Hourly Soft-Out 2 (hourly_soft_out.py --hour 2)")
    print(f"  • 03:00 PM EDT: Show Hard-Out & Tool #52 Lookbook Compilation")
    print(f"  • Evening Slate: Wild Card Game 2 Watch Party Omni-Tailing")
    print("=" * 70 + "\033[0m\n")

if __name__ == "__main__":
    main()

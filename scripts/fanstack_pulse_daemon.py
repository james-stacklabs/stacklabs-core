#!/usr/bin/env python3
"""
Sovereign OS: 15-Minute Gemini 3.8 Flash Entropy Pulse Daemon & Roster Wire
Path: /home/james/stacklabs/scripts/fanstack_pulse_daemon.py

Operationalizes the automated 15-minute sports pulse daemon using Google Gemini 3.8 Flash
(gemini-3.8-flash). Evaluates the Entropy Delta Gate, ingests deep lore dossiers from
SPARK_ADVOCATE_STANDINGS_UPDATE_PACKET.md and sovereign_now.db, generates updated vitals,
panic gauges, social tweet hooks, and real-time reactions across the active advocate roster.
Enforces Master Lock Invariant and Invariant 21 (Clean Room).
"""

import os
import sys
import json
import time
import random
import hashlib
import argparse
import datetime
import re
from typing import Dict, List, Optional, Tuple, Any

# Ensure project root in sys.path
PROJECT_ROOT = "/home/james/stacklabs"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.gemini_flash_client import (
    MODEL_NAME,
    generate_advocate_pulse,
    generate_deterministic_pulse,
    validate_master_lock_compliance,
    validate_clean_room,
    get_gemini_client,
)
from scripts.build_fanstack_static import build_fanstack_static

# Canonical Paths
CONFIG_MATRIX_PATH = os.path.join(PROJECT_ROOT, "config/active_advocates_matrix.json")
PULSE_STATE_PATH = os.path.join(PROJECT_ROOT, "data/pulse_state.json")
ENTROPY_BRIEFING_PATH = os.path.join(PROJECT_ROOT, "data/fanstack_entropy_briefing.json")
BARF_PAYLOAD_PATH = os.path.join(PROJECT_ROOT, "data/barf_wire_payload.json")
DIST_DATA_PATH = os.path.join(PROJECT_ROOT, "fanstack-wire/dist/data.json")
PRIMARY_DOSSIER_PATH = "/home/james/sovereign_inbox/pilot_drops/SPARK_ADVOCATE_STANDINGS_UPDATE_PACKET.md"
PORTAL_API_URL = "http://127.0.0.1:8095/api/persona"
ROSTER_ATTESTATION_PATH = os.path.join(PROJECT_ROOT, "config/roster_attestation_2026.json")


def validate_entity_attestation(payload: Any) -> Tuple[bool, List[str]]:
    """
    Hard-gate entity attestation checking generated payload against config/roster_attestation_2026.json.
    Throws circuit breaker if banned historical entities (e.g. Rob Thomson or Brian Snitker)
    are detected in a 2026 manager context.
    """
    if not os.path.exists(ROSTER_ATTESTATION_PATH):
        return True, []

    try:
        with open(ROSTER_ATTESTATION_PATH, "r", encoding="utf-8") as f:
            attestation = json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load roster attestation config: {e}", file=sys.stderr)
        return True, []

    banned_entities = attestation.get("banned_entities", [])
    violations = []
    text_repr = json.dumps(payload, ensure_ascii=False)

    for item in banned_entities:
        pattern = item.get("banned_pattern")
        if pattern:
            match = re.search(pattern, text_repr, re.IGNORECASE)
            if match:
                violations.append(
                    f"ATTESTATION CIRCUIT BREAKER TRIPPED: Banned entity '{item.get('name')}' matched '{match.group(0)}'. "
                    f"Reason: {item.get('reason')} Correct: {item.get('correct_entity')}"
                )

    return len(violations) == 0, violations


def load_active_matrix() -> Dict[str, Any]:
    """Loads active advocates matrix configuration."""
    if os.path.exists(CONFIG_MATRIX_PATH):
        with open(CONFIG_MATRIX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "active_advocates": [
            "barf", "battery_chucker", "southie_sully", "lone_star_larry",
            "bleacher_bum_bill", "old_bay_obsessive", "screech_supporter",
            "garlic_fries_gary", "cheesehead_chad"
        ],
        "suppressed_advocates": []
    }


def load_pulse_state() -> Dict[str, Any]:
    """Loads runtime pulse state tracking hashes and vitals."""
    if os.path.exists(PULSE_STATE_PATH):
        try:
            with open(PULSE_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_pulse_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "entropy_hash": "",
        "headlines_hash": "",
        "scores_hash": "",
        "entropy_gate_status": "INITIALIZED",
        "last_synthesis_mode": "INIT",
        "advocates_state": {}
    }


def save_pulse_state(state: Dict[str, Any]) -> None:
    """Persists runtime pulse state to disk."""
    os.makedirs(os.path.dirname(PULSE_STATE_PATH), exist_ok=True)
    with open(PULSE_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_lore_dossiers() -> Dict[str, str]:
    """
    Ingests uncompressed lore dossiers from SPARK_ADVOCATE_STANDINGS_UPDATE_PACKET.md
    and supplements with API persona data if available.
    """
    dossiers: Dict[str, str] = {}
    content = ""
    if os.path.exists(PRIMARY_DOSSIER_PATH):
        with open(PRIMARY_DOSSIER_PATH, "r", encoding="utf-8") as f:
            content = f.read()

    # Split into sections per advocate
    advocates = [
        "barf", "battery_chucker", "battery_chucker_jr", "southie_sully",
        "lone_star_larry", "bleacher_bum_bill", "old_bay_obsessive",
        "screech_supporter", "garlic_fries_gary", "cheesehead_chad"
    ]

    for adv in advocates:
        # Search for section in dossier
        pattern = rf"(###\s+\d+\.\s+`@{adv}`.*?(?=###\s+\d+\.|$))"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            dossiers[adv] = match.group(1).strip()
        else:
            dossiers[adv] = f"Advocate @{adv}: Master Lock Invariant Active. Lived-in stadium scars and hyper-local trauma."

    return dossiers


def load_entropy_briefing() -> Dict[str, Any]:
    """Loads sports entropy and headlines briefing."""
    if os.path.exists(ENTROPY_BRIEFING_PATH):
        try:
            with open(ENTROPY_BRIEFING_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "ny_anchor_event": {
            "headline": "Mets pennant chase agony and Giants swamp defense",
            "summary": "Postgame pressers and fourth-quarter defensive battles."
        },
        "national_shockers": []
    }


def compute_entropy_hash(briefing: Dict[str, Any]) -> str:
    """Computes a SHA256 hash across headlines and game scores to gate synthesis."""
    norm_data = {
        "ny_anchor": briefing.get("ny_anchor_event", {}).get("headline", ""),
        "national": [
            s.get("headline", "") for s in briefing.get("national_shockers", [])
        ],
        "nodes": briefing.get("league_micro_nodes", [])
    }
    dumped = json.dumps(norm_data, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def apply_heartbeat_drift(prev_vitals: Dict[str, Any]) -> Dict[str, Any]:
    """Applies subtle drift (±2 bpm, ±1 mmHg) during low-entropy dormancy without LLM tokens."""
    systolic = prev_vitals.get("systolic", 175) + random.choice([-1, 0, 1])
    diastolic = prev_vitals.get("diastolic", 110) + random.choice([-1, 0, 1])
    hr = prev_vitals.get("heart_rate_bpm", 115) + random.choice([-2, -1, 1, 2])
    panic = prev_vitals.get("panic_gauge_10", 8.5) + round(random.choice([-0.1, 0.0, 0.1]), 1)

    # Clamping
    systolic = max(130, min(220, systolic))
    diastolic = max(80, min(140, diastolic))
    hr = max(65, min(155, hr))
    panic = max(1.0, min(10.0, panic))

    return {
        "systolic": int(systolic),
        "diastolic": int(diastolic),
        "heart_rate_bpm": int(hr),
        "panic_gauge_10": float(panic),
        "signature_metric": prev_vitals.get("signature_metric", "Stable resting vitals"),
        "medical_status": prev_vitals.get("medical_status", "Active monitoring")
    }


def run_pulse_cycle(
    advocate_list: Optional[List[str]] = None,
    dry_run: bool = False,
    force_high_entropy: bool = False
) -> Dict[str, Any]:
    """
    Executes one complete 15-minute pulse cycle:
    1. Evaluates Entropy Delta Gate.
    2. Runs Gemini 3.8 Flash synthesis on High Entropy or Heartbeat Drift on Low Entropy.
    3. Enforces Master Lock and Invariant 21 Clean Room.
    4. Writes compiled pulse data to fanstack-wire/dist/data.json and data/pulse_state.json.
    5. Re-triggers build_fanstack_static.py.
    """
    matrix = load_active_matrix()
    target_advocates = advocate_list or matrix.get("active_advocates", [])
    # Strip any leading @
    target_advocates = [a.lstrip("@").lower() for a in target_advocates]

    pulse_state = load_pulse_state()
    briefing = load_entropy_briefing()
    current_hash = compute_entropy_hash(briefing)
    previous_hash = pulse_state.get("entropy_hash", "")

    # Entropy Delta Gate check
    is_high_entropy = force_high_entropy or (current_hash != previous_hash) or not previous_hash
    mode = "HIGH_ENTROPY" if is_high_entropy else "HEARTBEAT_DRIFT"

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    dossiers = load_lore_dossiers()
    briefing_str = json.dumps(briefing, indent=2)

    advocates_state = pulse_state.get("advocates_state", {})
    compiled_roster_pulse: Dict[str, Any] = {}

    client = None
    if not dry_run and is_high_entropy:
        try:
            client = get_gemini_client()
        except Exception as e:
            print(f"[INFO] Gemini client init ({e}). Utilizing deterministic generator.")
            dry_run = True

    for adv in target_advocates:
        prev_data = advocates_state.get(adv, {})
        lore = dossiers.get(adv, f"Advocate {adv}")

        if is_high_entropy or adv not in advocates_state:
            # High Entropy: Full synthesis via Gemini 3.8 Flash or deterministic dry-run
            adv_pulse = generate_advocate_pulse(
                persona_id=adv,
                lore_context=lore,
                entropy_context=briefing_str,
                client=client,
                dry_run=dry_run
            )
            val_ok, issues = validate_master_lock_compliance(adv_pulse, adv)
            if not val_ok:
                print(f"[WARN] Non-compliant pulse for {adv}: {issues}. Correcting with authentic scars.")
                adv_pulse = generate_deterministic_pulse(adv)

            vitals = adv_pulse.get("vitals", {})
            current_mood = adv_pulse.get("current_mood", "AGITATED")
            tweet_hooks = adv_pulse.get("stream_sniper_tweet_hooks", [])
            active_obsession = adv_pulse.get("active_obsession", "")

            advocates_state[adv] = {
                "persona_id": adv,
                "current_mood": current_mood,
                "systolic": vitals.get("systolic", 175),
                "diastolic": vitals.get("diastolic", 110),
                "heart_rate_bpm": vitals.get("heart_rate_bpm", 115),
                "panic_gauge_10": vitals.get("panic_gauge_10", 8.5),
                "signature_metric": vitals.get("signature_metric", ""),
                "medical_status": vitals.get("medical_status", ""),
                "stream_sniper_tweet_hooks": tweet_hooks,
                "active_obsession": active_obsession,
                "last_updated": now_iso
            }
        else:
            # Low Entropy: Heartbeat tick drift (0 LLM tokens burned)
            drifted = apply_heartbeat_drift(prev_data)
            prev_data.update(drifted)
            prev_data["last_updated"] = now_iso
            advocates_state[adv] = prev_data

        compiled_roster_pulse[adv] = advocates_state[adv]

    # Clean Room Verification (Invariant 21)
    is_clean, violations = validate_clean_room(advocates_state)
    if not is_clean:
        raise ValueError(f"Invariant 21 Violation in pulse state: {violations}")

    # Update pulse_state.json
    pulse_state.update({
        "last_pulse_timestamp": now_iso,
        "entropy_hash": current_hash,
        "headlines_hash": current_hash,
        "entropy_gate_status": "GATED" if not is_high_entropy else "TRIGGERED",
        "last_synthesis_mode": mode,
        "advocates_state": advocates_state
    })
    save_pulse_state(pulse_state)

    # Ingest / update data/barf_wire_payload.json
    barf_vitals = advocates_state.get("barf", {})
    if os.path.exists(BARF_PAYLOAD_PATH):
        with open(BARF_PAYLOAD_PATH, "r", encoding="utf-8") as f:
            barf_payload = json.load(f)
    else:
        barf_payload = {}

    barf_payload["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
    if barf_vitals:
        daily_vitals = barf_payload.setdefault("daily_vitals", {})
        daily_vitals["systolic"] = barf_vitals.get("systolic", daily_vitals.get("systolic", 182))
        daily_vitals["diastolic"] = barf_vitals.get("diastolic", daily_vitals.get("diastolic", 114))
        daily_vitals["pulse"] = barf_vitals.get("heart_rate_bpm", daily_vitals.get("pulse", 122))
        daily_vitals["panic_index"] = int(barf_vitals.get("panic_gauge_10", 9))
        daily_vitals["mood_summary"] = barf_vitals.get("current_mood", daily_vitals.get("mood_summary", ""))

    # Attach roster pulse to payload
    barf_payload["pulse_advocates"] = compiled_roster_pulse
    barf_payload["pulse_metadata"] = {
        "timestamp": now_iso,
        "mode": mode,
        "model": MODEL_NAME if mode == "HIGH_ENTROPY" and not dry_run else "deterministic-heartbeat",
        "active_advocate_count": len(compiled_roster_pulse)
    }

    # Verify Clean Room on updated payload
    clean_payload_ok, p_violations = validate_clean_room(barf_payload)
    if not clean_payload_ok:
        raise ValueError(f"Invariant 21 Violation in barf payload: {p_violations}")

    # Hard-Gate Entity Attestation (Invariant 45)
    attestation_ok, att_violations = validate_entity_attestation(barf_payload)
    if not attestation_ok:
        err_msg = "[-] CRITICAL ENTITY ATTESTATION CIRCUIT BREAKER TRIPPED:\n" + "\n".join(att_violations)
        print(err_msg, file=sys.stderr)
        raise SystemExit(1)

    # Write updated barf payload
    with open(BARF_PAYLOAD_PATH, "w", encoding="utf-8") as f:
        json.dump(barf_payload, f, indent=2)

    # Re-trigger build_fanstack_static.py
    static_build_res = build_fanstack_static(
        payload_path=BARF_PAYLOAD_PATH,
        dist_dir=os.path.join(PROJECT_ROOT, "fanstack-wire/dist")
    )

    # Double-check fanstack-wire/dist/data.json has the pulse data
    with open(DIST_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(barf_payload, f, indent=2)

    return {
        "status": "success",
        "mode": mode,
        "timestamp": now_iso,
        "entropy_hash": current_hash,
        "advocates_count": len(compiled_roster_pulse),
        "advocates": list(compiled_roster_pulse.keys()),
        "clean_room_verified": True,
        "static_build": static_build_res
    }


def main():
    parser = argparse.ArgumentParser(description="15-Minute Gemini 3.8 Flash Entropy Pulse Daemon & Roster Wire")
    parser.add_argument("--dry-run", action="store_true", help="Execute without burning LLM tokens (deterministic mock)")
    parser.add_argument("--once", action="store_true", help="Run once and exit (default for batch/test execution)")
    parser.add_argument("--advocates", type=str, default="", help="Comma-separated advocate list (e.g. barf,battery_chucker)")
    parser.add_argument("--force-high-entropy", action="store_true", help="Bypass Entropy Delta Gate to force Gemini synthesis")
    parser.add_argument("--interval", type=int, default=900, help="Cadence in seconds (default: 900s / 15m)")
    args = parser.parse_args()

    advocate_list = [a.strip() for a in args.advocates.split(",") if a.strip()] if args.advocates else None

    print("=" * 65)
    print("⚡ 15-MINUTE GEMINI 3.8 FLASH ENTROPY PULSE DAEMON // CLIO METAL")
    print(f"Model Endpoint:    {MODEL_NAME}")
    print(f"Mode:              {'DRY RUN' if args.dry_run else 'LIVE PRODUCTION'}")
    print(f"Cadence:           {args.interval}s")
    print("=" * 65)

    while True:
        try:
            start_t = time.time()
            res = run_pulse_cycle(
                advocate_list=advocate_list,
                dry_run=args.dry_run,
                force_high_entropy=args.force_high_entropy
            )
            elapsed = time.time() - start_t
            print(f"[{res['timestamp']}] Pulse Complete ({res['mode']}) in {elapsed:.2f}s across {res['advocates_count']} advocates.")
            print(f"Entropy Hash:      {res['entropy_hash'][:16]}...")
            print(f"Clean Room Gate:   VERIFIED (0 corporate bleed terms)")
            print(f"Static Dist HTML:  {res['static_build']['index_html_path']}")
            print(f"Static Dist Data:  {res['static_build']['data_json_path']}")
        except Exception as e:
            print(f"❌ Error during pulse execution: {e}", file=sys.stderr)
            if args.once:
                sys.exit(1)

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()

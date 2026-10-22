#!/usr/bin/env python3
"""
Sovereign OS — Autonomous Error Learning & Remediation Reflex Cache Engine
Path: /home/james/stacklabs/scripts/core/remediation_engine.py

Core engine that pairs tool failures with subsequent successful fixes,
persisting reflexes in sys_agent_remediation_memory and short-circuiting
known failure traps at the Point of Action (PreToolUse).
"""

import os
import sys
import time
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Ensure scripts directory is in python path
SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT / "scripts"))

from core.db import get_db

EPHEMERAL_FAILURE_FILE = Path("/tmp/agent_last_failure.json")


def normalize_string(val: str) -> str:
    """Normalize whitespace and remove volatile ephemeral tokens."""
    if not val:
        return ""
    # Strip carriage returns and collapse redundant whitespace
    s = val.strip().replace("\r\n", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    return s


def compute_error_hash(tool_name: str, failed_payload: str, error_snippet: str) -> str:
    """Deterministic SHA256 signature for tool failure pattern."""
    norm_tool = tool_name.strip().lower()
    norm_payload = normalize_string(failed_payload)
    norm_err = normalize_string(error_snippet)[:200]
    raw = f"{norm_tool}|{norm_payload}|{norm_err}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def record_failure(tool_name: str, failed_payload: Any, error_snippet: str, subsystem: str = "general") -> Dict[str, Any]:
    """
    Record an ephemeral tool failure to /tmp/agent_last_failure.json.
    Awaits the next successful tool call to pair the remediation.
    """
    payload_str = json.dumps(failed_payload) if isinstance(failed_payload, (dict, list)) else str(failed_payload)
    err_hash = compute_error_hash(tool_name, payload_str, error_snippet)
    
    failure_record = {
        "timestamp": time.time(),
        "iso_time": datetime.now(timezone.utc).isoformat(),
        "error_hash": err_hash,
        "tool_name": tool_name.strip(),
        "failed_payload": payload_str,
        "error_snippet": error_snippet.strip()[:1000],
        "subsystem": subsystem
    }
    
    try:
        with open(EPHEMERAL_FAILURE_FILE, "w", encoding="utf-8") as f:
            json.dump(failure_record, f, indent=2)
    except Exception as e:
        print(f"[REMEDIATION-ENGINE] Warning: Could not write failure cache: {e}", file=sys.stderr)
        
    return failure_record


def pair_and_commit_success(tool_name: str, successful_payload: Any, custom_hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    If an ephemeral failure exists from the same tool within 5 minutes,
    pair it with this successful payload and persist into sys_agent_remediation_memory.
    """
    if not EPHEMERAL_FAILURE_FILE.exists():
        return None
        
    try:
        with open(EPHEMERAL_FAILURE_FILE, "r", encoding="utf-8") as f:
            failure = json.load(f)
    except Exception:
        return None
        
    now = time.time()
    if now - failure.get("timestamp", 0) > 300:  # 5 minute timeout window
        try:
            EPHEMERAL_FAILURE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return None
        
    # Check if tool matches
    if failure.get("tool_name") != tool_name.strip():
        return None
        
    succ_str = json.dumps(successful_payload) if isinstance(successful_payload, (dict, list)) else str(successful_payload)
    
    # Don't pair identical payloads
    if normalize_string(succ_str) == normalize_string(failure.get("failed_payload", "")):
        return None
        
    hint = custom_hint or f"Failed with: {failure.get('error_snippet')[:100]}. Verified resolution: {succ_str}"
    err_hash = failure.get("error_hash")
    
    record = None
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, hit_count FROM sys_agent_remediation_memory WHERE error_hash = ?",
            (err_hash,)
        ).fetchone()
        
        if existing:
            conn.execute(
                """
                UPDATE sys_agent_remediation_memory 
                SET successful_payload = ?,
                    remediation_hint = ?,
                    hit_count = hit_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE error_hash = ?
                """,
                (succ_str, hint, err_hash)
            )
        else:
            conn.execute(
                """
                INSERT INTO sys_agent_remediation_memory 
                    (error_hash, tool_name, failed_payload, error_snippet, successful_payload, remediation_hint, subsystem, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (err_hash, tool_name, failure.get("failed_payload"), failure.get("error_snippet"), succ_str, hint, failure.get("subsystem", "general"))
            )
        conn.commit()
        
        row = conn.execute("SELECT * FROM sys_agent_remediation_memory WHERE error_hash = ?", (err_hash,)).fetchone()
        if row:
            record = dict(row)
            
    # Clean up ephemeral file
    try:
        EPHEMERAL_FAILURE_FILE.unlink(missing_ok=True)
    except Exception:
        pass
        
    return record


def check_reflex(tool_name: str, proposed_payload: Any) -> Optional[Dict[str, Any]]:
    """
    Check if the proposed tool call matches a known failure pattern with a verified resolution.
    If so, increments hit_count and returns remediation advice.
    """
    norm_tool = tool_name.strip()
    payload_str = json.dumps(proposed_payload) if isinstance(proposed_payload, (dict, list)) else str(proposed_payload)
    norm_payload = normalize_string(payload_str)
    
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, error_hash, tool_name, failed_payload, error_snippet, successful_payload, remediation_hint, hit_count
            FROM sys_agent_remediation_memory
            WHERE tool_name = ? AND successful_payload IS NOT NULL
            ORDER BY hit_count DESC
            """,
            (norm_tool,)
        ).fetchall()
        
        for r in rows:
            failed = normalize_string(r["failed_payload"])
            matched = False
            if norm_payload == failed:
                matched = True
            elif norm_tool == "run_command":
                cmd_tokens = [c.strip() for c in re.split(r"[;&|]+", norm_payload)]
                for tok in cmd_tokens:
                    if tok == failed or tok.startswith(failed + " "):
                        matched = True
                        break

            if matched:
                # Increment hit count
                conn.execute(
                    "UPDATE sys_agent_remediation_memory SET hit_count = hit_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (r["id"],)
                )
                conn.commit()
                return {
                    "matched": True,
                    "error_hash": r["error_hash"],
                    "tool_name": r["tool_name"],
                    "failed_payload": r["failed_payload"],
                    "error_snippet": r["error_snippet"],
                    "successful_payload": r["successful_payload"],
                    "remediation_hint": r["remediation_hint"],
                    "hit_count": r["hit_count"] + 1
                }
                
    return None


def get_top_remediations(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve top failure traps and verified resolutions for prompt priming."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, error_hash, tool_name, failed_payload, error_snippet, successful_payload, remediation_hint, subsystem, hit_count, updated_at
            FROM sys_agent_remediation_memory
            ORDER BY hit_count DESC, updated_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

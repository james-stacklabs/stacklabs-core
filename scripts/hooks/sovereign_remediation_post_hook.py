#!/usr/bin/env python3
"""
Sovereign OS — Autonomous Error Learning & Remediation Reflex Post-Tool Hook
Path: /home/james/stacklabs/scripts/hooks/sovereign_remediation_post_hook.py

Captures tool execution failures and subsequent working successes,
persisting the pairs into sys_agent_remediation_memory.
"""

import sys
import os
import json
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT / "scripts"))

from core.remediation_engine import record_failure, pair_and_commit_success


def handle_post_tool_use(payload: dict):
    tool_call = payload.get("toolCall", {})
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    tool_result = payload.get("toolResult", {})
    
    # Extract payload string or dict
    if name == "run_command":
        cmd = args.get("CommandLine", "")
        # Strip HISTFILE prefix if present
        if cmd.startswith("HISTFILE=/dev/null "):
            cmd = cmd[len("HISTFILE=/dev/null "):]
        payload_data = cmd
    elif name in ["replace_file_content", "write_to_file", "multi_replace_file_content"]:
        payload_data = {
            "target": args.get("TargetFile", ""),
            "instruction": args.get("Instruction", "")
        }
    else:
        payload_data = args

    # Check for failure indicators
    content = ""
    if isinstance(tool_result, dict):
        content = tool_result.get("content", "") or tool_result.get("output", "") or tool_result.get("error", "")
        status = tool_result.get("status", "")
        exit_code = tool_result.get("exitCode")
    else:
        content = str(tool_result)
        status = ""
        exit_code = None

    is_failure = False
    error_snippet = ""

    if exit_code is not None and exit_code != 0:
        is_failure = True
        error_snippet = content
    elif status == "ERROR" or "error" in tool_result:
        is_failure = True
        error_snippet = content or str(tool_result.get("error", ""))
    elif "Traceback (most recent call last):" in content or "Error: " in content or "SyntaxError:" in content:
        # Check if the command itself was intended to find errors or if it actually failed
        if "The command exited with code 1" in content or "exited with code 2" in content or "exited with code 127" in content:
            is_failure = True
            error_snippet = content

    if is_failure:
        record_failure(name, payload_data, error_snippet)
    else:
        # On success, check if we can pair with an ephemeral failure
        pair_and_commit_success(name, payload_data)


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            return
        payload = json.loads(raw_input)
        handle_post_tool_use(payload)
    except Exception:
        pass


if __name__ == "__main__":
    main()

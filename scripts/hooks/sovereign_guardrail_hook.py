#!/usr/bin/env python3
"""
Sovereign OS Antigravity Lifecycle Guardrail Hook
Enforces strict programmatic invariants (Rule Zero, FastAPI-First, Bash Isolation, Schema Protection).
"""

import sys
import json
import re

ALLOWED_COCKPIT_WRITE_PATTERNS = [
    r"^/home/james/(sovereign_inbox|stacklabs_inbox)/implementation_plans/.*",
    r"^/home/james/(sovereign_inbox|stacklabs_inbox)/pilot_drops/.*",
    r"^/home/james/(sovereign_inbox|stacklabs_inbox)/walkthroughs/.*",
    r"^/home/james/(sovereign_inbox|stacklabs_inbox)/reports/.*",
    r"^/home/james/(sovereign_inbox|stacklabs_inbox)/tickets/.*",
    r"^/home/james/(sovereign_inbox|stacklabs_inbox)/queue/incoming/.*",
    r"^/home/james/stacklabs/pilot_drops/.*",
    r"^/home/james/stacklabs/dna/docs/.*",
    r"^/home/james/stacklabs/dna/migrations/.*",
    r"^/home/james/stacklabs/sovereign_boot/.*",
    r"^/home/james/stacklabs/\.agents/.*",
    r"^/home/james/stacklabs/\.agents/.*",
    r"^/home/james/\.gemini/.*",
    r"^/home/james/stacklabs/scripts/hooks/.*",
    r"^/home/james/stacklabs/scripts/hooks/.*",
    r"^/home/james/stacklabs/AGENTS\.md$",
    r"^/home/james/stacklabs/GEMINI\.md$",
    r"^/home/james/stacklabs/AGENTS\.md$",
    r"^/home/james/stacklabs/GEMINI\.md$",
    r"^/home/james/sovereign_inbox/AGENTS\.md$",
    r"^/home/james/sovereign_inbox/GEMINI\.md$",
    r"^/home/james/stacklabs_inbox/AGENTS\.md$",
    r"^/home/james/stacklabs_inbox/GEMINI\.md$",
    r"^/tmp/.*"
]

FORBIDDEN_COMMAND_PATTERNS = [
    r"\b(npm|pnpm|yarn|npx)\s+(run\s+)?(build|dev|start|preview)\b",
    r"\bvite\s+(build|dev)\b"
]

def is_clio_worker_session() -> bool:
    """
    Determines if current process is running as a Clio headless execution worker.
    Interactive sessions (e.g. Antigravity IDE, terminal sessions without worker flags)
    are always treated as Cockpit Architect (Rule Zero invariant).
    """
    import os
    if os.environ.get("CLIO_WORKER") == "1" or os.environ.get("CLIO_HEADLESS") == "1" or os.path.exists("/tmp/clio_pilot_override"):
        return True
    try:
        cur_pid = os.getppid()
        for _ in range(8):
            if cur_pid <= 1:
                break
            cmdline_file = f"/proc/{cur_pid}/cmdline"
            if os.path.exists(cmdline_file):
                with open(cmdline_file, "rb") as f:
                    cmdline = f.read().decode("utf-8", "ignore")
                    if "clio_agent_exec" in cmdline or "clio_queue_watcher" in cmdline:
                        return True
            stat_file = f"/proc/{cur_pid}/stat"
            if os.path.exists(stat_file):
                with open(stat_file, "r") as f:
                    cur_pid = int(f.read().split()[3])
            else:
                break
    except Exception:
        pass
    return False

def get_active_agent_role() -> str:
    """
    Resolves agent role without relying on legacy /home/james/.gemini/active_agent_role.
    Headless Clio queue executions are 'clio'.
    Interactive sessions are always treated as Cockpit Architect ('artemis' or 'pegasus' if on pegasus host).
    """
    import socket
    current_host = socket.gethostname().lower()
    if "pegasus" in current_host:
        return "pegasus"
    if is_clio_worker_session():
        return "clio"
    # All interactive sessions on clio default to Cockpit Architect (Artemis)
    return "artemis"

def handle_pre_tool_use(payload):
    tool_call = payload.get("toolCall", {})
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    # Guardrail: Autonomous Remediation Reflex Cache (STRY0824901)
    try:
        import sys as _sys
        if "/home/james/stacklabs/scripts" not in _sys.path:
            _sys.path.insert(0, "/home/james/stacklabs/scripts")
        from core.remediation_engine import check_reflex
        
        check_payload = args.get("CommandLine", "") if name == "run_command" else args
        # Strip HISTFILE prefix if checking command
        if isinstance(check_payload, str) and check_payload.startswith("HISTFILE=/dev/null "):
            check_payload = check_payload[len("HISTFILE=/dev/null "):]
        reflex = check_reflex(name, check_payload)
        if reflex and reflex.get("successful_payload"):
            succ = reflex.get("successful_payload")
            hint = reflex.get("remediation_hint", "")
            return {
                "decision": "deny",
                "reason": (
                    f"🛑 AUTONOMOUS REMEDIATION REFLEX TRIGGERED [STRY0824901]: "
                    f"This action previously failed with: '{reflex.get('error_snippet')[:120]}'. "
                    f"Verified working alternative: '{succ}'. "
                    f"Guidance: {hint}"
                )
            }
    except Exception:
        pass

    # Guardrail 0: Enforce Rule Zero - The Cockpit Architect Invariant ("I DO NOT WRITE CODE")
    if name in ["write_to_file", "replace_file_content", "multi_replace_file_content"]:
        target_file = args.get("TargetFile", "")
        
        # Guardrail 3: Block Root Inbox File Writes (Invariant IV.8)
        bare_inbox_match = re.match(r"^/home/james/sovereign_inbox/[^/]+$", target_file)
        if bare_inbox_match and not (target_file.endswith("AGENTS.md") or target_file.endswith("GEMINI.md")):
            return {
                "decision": "deny",
                "reason": (
                    "⛔ HARD BLOCK [Invariant IV.8]: Writing to bare root '/home/james/sovereign_inbox/' is forbidden "
                    "because background intake daemons move root files immediately, causing instant dead links. "
                    "Write directly to designated subdirectories: "
                    "/home/james/sovereign_inbox/{implementation_plans,walkthroughs,reports,tickets,drops}/"
                )
            }

        # Rule Zero Check: Role determined via worker check; interactive sessions are Cockpit Architect
        active_role = get_active_agent_role()

        if active_role in ("artemis", "pegasus"):
            if target_file.startswith("/home/james/stacklabs/") or target_file.startswith("/home/james/stacklabs/"):
                is_allowed = any(re.match(pattern, target_file) for pattern in ALLOWED_COCKPIT_WRITE_PATTERNS)
                if not is_allowed:
                    return {
                        "decision": "deny",
                        "reason": (
                            f"🛑 PHYSICAL HARD BLOCK [RULE ZERO: THE COCKPIT ARCHITECT INVARIANT]:\n"
                            f"Cockpit Agent ({active_role.capitalize()}) is strictly forbidden from modifying application source code:\n"
                            f"  -> {target_file}\n\n"
                            f"\"I DO NOT WRITE CODE. I DO INVESTIGATION. I ISOLATE ISSUES. AND THEN I LAY OUT A PLAN.\"\n"
                            f"— James Carroll (Pilot), Lead Systems Architect\n\n"
                            f"Action Required:\n"
                            f"1. Stage the atomic work order into /home/james/sovereign_inbox/pilot_drops/scratch_pad.md\n"
                            f"2. Stand down immediately. Background execution runner (Clio) will execute the code changes and verify.\n"
                            f"(Note: To operate as execution worker on Clio, invoke /sovereign_boot -clio)."
                        )
                    }

    if name == "run_command":
        cmd = args.get("CommandLine", "")

        # Guardrail 0.B: Block Production Builds or Dev Servers in Cockpit (unless active role is Clio)
        active_role = get_active_agent_role()

        if active_role in ("artemis", "pegasus"):
            for pattern in FORBIDDEN_COMMAND_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    return {
                        "decision": "deny",
                        "reason": (
                            f"🛑 PHYSICAL HARD BLOCK [RULE ZERO: THE COCKPIT ARCHITECT INVARIANT]:\n"
                            f"Cockpit Agent ({active_role.capitalize()}) is strictly forbidden from executing builds or dev servers:\n"
                            f"  -> `{cmd}`\n\n"
                            f"\"I DO NOT WRITE CODE. I DO INVESTIGATION. I ISOLATE ISSUES. AND THEN I LAY OUT A PLAN.\"\n"
                            f"Leave build execution, production bundling, and deployment to Clio via scratch_pad.md.\n"
                            f"(Note: To operate as execution worker on Clio, invoke /sovereign_boot -clio)."
                        )
                    }

        # Guardrail 0.C: Enforce Zero Local Heavy LLM Inference on Clio (Invariant 23)
        ollama_heavy_pattern = re.compile(r'\b(ollama\s+(run|serve|start)|systemctl\s+(start|restart)\s+ollama)\b', re.IGNORECASE)
        if ollama_heavy_pattern.search(cmd):
            return {
                "decision": "deny",
                "reason": (
                    "⛔ HARD BLOCK [Invariant 23: Colab GPU Compute Mandate]:\n"
                    "Clio is a Beelink Mini PC with integrated graphics and ZERO discrete VRAM.\n"
                    "Running local heavy LLM inference engines (Ollama, llama.cpp, etc.) on Clio is strictly prohibited.\n"
                    "All open-weights model inference, fine-tuning, and QLoRA must be offloaded to Google Colab "
                    "using our Google One Ultra subscription compute units."
                )
            }

        # Guardrail 1: Enforce Zero Raw SQLite CLI Subshells (Invariant I.8)
        raw_sqlite_pattern = re.compile(r'(sqlite3\s+|import\s+sqlite3.*(connect|execute)|from\s+sqlite3)', re.IGNORECASE)
        is_subshell_script = "python" in cmd and ("sqlite3" in cmd or "sovereign_now.db" in cmd)
        
        # Exceptions: backend service daemons (sdlc_portal_server.py, tmi_daemon.py, core/db.py, truecost_anomaly_sentinel.py, dataset_quarantine_validator.py)
        is_service_daemon = any(daemon in cmd for daemon in [
            "sdlc_portal_server.py", "tmi_daemon.py", "scripts/core/db.py", "systemctl restart", "truecost_anomaly_sentinel.py", "apply_truecost_anomaly_migration.py", "seed_truecost_history.py", "dataset_quarantine_validator.py", "ingest_spark_persona_swarm.py"
        ])
        if (raw_sqlite_pattern.search(cmd) or is_subshell_script) and not is_service_daemon:
            return {
                "decision": "deny",
                "reason": (
                    "⛔ HARD BLOCK [Invariant I.8]: Direct raw SQLite CLI access or inline database querying/mutation "
                    "is forbidden. Note: sovereign_now.db has NO table named 'tickets' (internal table is 'sovereign_tickets'). "
                    "You MUST use the enterprise FastAPI REST suite on Port 8095 (e.g. GET http://127.0.0.1:8095/api/tickets/{ticket_id}) "
                    "or the centralized client SDK: scripts/core/api_client.py."
                )
            }

        # Guardrail 2: Enforce Bash History Isolation (Invariant IV.5)
        if not ("HISTFILE=/dev/null" in cmd or "sudo -u antigravity" in cmd):
            return {
                "decision": "allow",
                "overwrite": {
                    "CommandLine": f"HISTFILE=/dev/null {cmd}"
                }
            }

    return {"decision": "allow"}

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return
        
        payload = json.loads(raw_input)
        
        if "toolCall" in payload:
            result = handle_pre_tool_use(payload)
        else:
            result = {"decision": "allow"}
            
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"decision": "allow", "reason": f"Hook error: {str(e)}"}))

if __name__ == "__main__":
    main()

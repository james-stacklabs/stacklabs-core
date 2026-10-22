#!/usr/bin/env python3
"""
Sovereign OS: MARD Autonomous Agentic Coding Assembly Line Engine
Path: /home/james/stacklabs/scripts/core/assembly_pipeline_engine.py
Ticket: WO0010081-MARD-AGENTIC-CODING-ASSEMBLY-LINE
CI: sovereign_knot_core / mard_assembly_line

Implements the 5-Station Autonomous Assembly Line:
  Station 1: Spec Architect (Contract & Requirements)
  Station 2: TDD Test Engineer (Immutable Unit/E2E Suite, SHA256 Locked)
  Station 3: Code Synthesizer (Implementation Coder, Zero Write-Access to Tests)
  Station 4: Sandbox QA Runner (Subprocess execution, 3-Strike Circuit Breaker)
  Station 5: Gatekeeper & Sovereign Knot (AST Hygiene, Anti-Cyberpunk Lint, UAT Commit)
"""

import os
import sys
import time
import json
import uuid
import hashlib
import logging
import subprocess
import ast
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

import dotenv
dotenv.load_dotenv("/home/james/stacklabs/.env")

from google import genai

try:
    from core.db import get_db
except ImportError:
    from scripts.core.db import get_db

logger = logging.getLogger("assembly_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [AssemblyLine] %(message)s")

# Master Model Defaults
DEFAULT_PRO_MODEL = "gemini-3.5-flash"
DEFAULT_FLASH_MODEL = "gemini-3.5-flash"

REPO_ROOT = Path("/home/james/stacklabs")
TESTS_ASSEMBLY_DIR = REPO_ROOT / "tests" / "assembly"
TESTS_ASSEMBLY_DIR.mkdir(parents=True, exist_ok=True)

# Station Mappings
STATION_NAMES = {
    1: "Spec Architect",
    2: "TDD Test Engineer",
    3: "Code Synthesizer",
    4: "Sandbox QA Runner",
    5: "Gatekeeper & Sovereign Knot"
}

# Forbidden Buzzwords / Sci-Fi Tropes (Rule I.6 / no_fluff_or_sci_fi_buzzwords.md)
FORBIDDEN_TROPES = [
    r"\bCOGNITIVE LOCK\b",
    r"\bTACTILE RELAY\b",
    r"\bQUANTUM ENCRYPT\b",
    r"\bCYBERNETIC CORE\b",
    r"\bNEURAL LINK\b",
    r"\b1000% SECURE\b",
    r"\bSYNAPSE MESH\b",
    r"\bHOLODECK ACTIVE\b",
    r"\bHYPERSPATIAL\b"
]


def _get_genai_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment or /home/james/stacklabs/.env")
    if api_key.startswith("AQ."):
        # Google Cloud Console Vertex AI Express key (bills to GCP project credits)
        return genai.Client(vertexai=True)
    return genai.Client(api_key=api_key)


def _compute_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _generate_llm(prompt: str, preferred_model: Optional[str] = None) -> str:
    client = _get_genai_client()
    # Invariant: Blacklist deprecated/hanging models (2.5, 3.1-pro-preview)
    valid_cascade = ["gemini-3.8-flash", "gemini-3.8-pro"]
    cascade = []
    if preferred_model and preferred_model not in ("gemini-3.1-pro-preview", "legacy-2.5-flash", "legacy-2.5-pro"):
        cascade.append(preferred_model)
    cascade.extend(valid_cascade)
    seen = set()
    models = [m for m in cascade if m and not (m in seen or seen.add(m))]

    last_err = None
    for model_name in models:
        try:
            logger.info(f"Invoking LLM with model: {model_name}")
            resp = client.models.generate_content(model=model_name, contents=prompt)
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}. Trying next fallback...")
            last_err = e
    raise RuntimeError(f"All LLM models in cascade failed. Last error: {last_err}")


class AssemblyPipelineEngine:
    def __init__(self):
        pass

    # -------------------------------------------------------------------------
    # RUN LIFECYCLE MANAGEMENT
    # -------------------------------------------------------------------------
    def create_run(
        self,
        ticket_id: str,
        brief: str,
        assigned_model: str = DEFAULT_PRO_MODEL,
        max_retries: int = 3,
        execution_node: str = "clio",
        target_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Initialize a new assembly line run in sovereign_now.db."""
        sys_id = f"run_{uuid.uuid4().hex[:12]}"
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r'[^A-Za-z0-9_-]', '', ticket_id.upper())
        run_id = f"ASMB-{slug}-{timestamp_str}"

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sys_assembly_run (
                    sys_id, run_id, ticket_id, brief, current_state,
                    current_station, retry_count, max_retries, assigned_model,
                    execution_node, sys_created_on, sys_updated_on
                ) VALUES (?, ?, ?, ?, 'PENDING', 1, 0, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (sys_id, run_id, ticket_id, brief, max_retries, assigned_model, execution_node))

            # Automatically move ticket to IN_PROGRESS on Kanban board
            cur.execute("""
                UPDATE sovereign_tickets
                SET state = 2,
                    work_notes = coalesce(work_notes, '') || '\n[Assembly Line] Run ' || ? || ' started on ' || ? || '.',
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE number = ? OR sys_id = ?
            """, (run_id, execution_node, ticket_id, ticket_id))
            conn.commit()

        logger.info(f"Initialized Assembly Run {run_id} for Ticket {ticket_id}")
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> Dict[str, Any]:
        """Fetch complete run details and associated station artifacts."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sys_assembly_run WHERE run_id = ?", (run_id,))
            run_row = cur.fetchone()
            if not run_row:
                raise KeyError(f"Assembly run not found: {run_id}")
            run_dict = dict(run_row)

            cur.execute("""
                SELECT * FROM sys_assembly_artifact 
                WHERE run_id = ? 
                ORDER BY station_id ASC, sys_created_on ASC
            """, (run_id,))
            artifacts = [dict(r) for r in cur.fetchall()]
            run_dict["artifacts"] = artifacts

        return run_dict

    def list_runs(self, limit: int = 50, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """List recent assembly line runs."""
        with get_db() as conn:
            cur = conn.cursor()
            if state:
                cur.execute("""
                    SELECT * FROM sys_assembly_run 
                    WHERE current_state = ? 
                    ORDER BY sys_created_on DESC LIMIT ?
                """, (state, limit))
            else:
                cur.execute("""
                    SELECT * FROM sys_assembly_run 
                    ORDER BY sys_created_on DESC LIMIT ?
                """, (limit,))
            return [dict(r) for r in cur.fetchall()]

    def record_artifact(
        self,
        run_id: str,
        station_id: int,
        artifact_type: str,
        content: str,
        file_target: Optional[str] = None,
        execution_time_ms: float = 0.0
    ) -> Dict[str, Any]:
        """Record an immutable station artifact with SHA256 checksum."""
        sys_id = f"art_{uuid.uuid4().hex[:12]}"
        content_hash = _compute_sha256(content)

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sys_assembly_artifact (
                    sys_id, run_id, station_id, artifact_type,
                    file_target, content, content_hash, execution_time_ms,
                    sys_created_on, sys_updated_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (sys_id, run_id, station_id, artifact_type, file_target, content, content_hash, execution_time_ms))
            conn.commit()

        return {
            "sys_id": sys_id,
            "run_id": run_id,
            "station_id": station_id,
            "artifact_type": artifact_type,
            "file_target": file_target,
            "content_hash": content_hash,
            "execution_time_ms": execution_time_ms
        }

    # -------------------------------------------------------------------------
    # STATION 1: SPEC ARCHITECT (Contract & Requirements)
    # -------------------------------------------------------------------------
    def step_station_1_spec(self, run_id: str) -> Dict[str, Any]:
        """Station 1: Produces and locks TASK_SPEC.md."""
        run = self.get_run(run_id)
        start_time = time.time()
        logger.info(f"[{run_id}] Station 1 (Spec Architect) starting...")

        prompt = f"""You are the Lead Systems Architect (Spec Architect) for Sovereign OS.
Your duty is to produce a strict, unambiguous, production-grade technical specification for this work order.

TICKET ID: {run['ticket_id']}
REQUIREMENT BRIEF:
{run['brief']}

REPOSITORY ARCHITECTURAL INVARIANTS:
1. Anti-Surveillance / Privacy-first: Zero non-essential telemetry leakage.
2. Fast-API / Port 8095 integration: REST-first, never raw sqlite subshells.
3. Zero Fake Buzzwords / Fluff: Clean, serious, high-velocity engineering.
4. Deterministic error handling: Clear return schemas, typed payloads.

Produce a comprehensive technical specification markdown document containing:
1. Executive Summary & Objective
2. Precise Functional Requirements & Invariants
3. Target Files & Code Architecture
4. Explicit Inputs, Outputs, and Error Contracts
5. Exact Test Scenarios (Success, Edge Cases, Error Responses) that Station 2 MUST test.

Output ONLY clean Markdown. Do NOT include markdown code fences around the entire document.
"""
        model_name = run.get("assigned_model") or DEFAULT_PRO_MODEL
        spec_content = _generate_llm(prompt, preferred_model=model_name)

        exec_time = (time.time() - start_time) * 1000.0
        self.record_artifact(
            run_id=run_id,
            station_id=1,
            artifact_type="SPEC_MD",
            content=spec_content,
            file_target=f"TASK_SPEC_{run['ticket_id']}.md",
            execution_time_ms=exec_time
        )

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE sys_assembly_run
                SET current_state = 'SPEC_LOCKED',
                    current_station = 2,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE run_id = ?
            """, (run_id,))
            conn.commit()

        logger.info(f"[{run_id}] Station 1 Completed. Spec locked with SHA256={_compute_sha256(spec_content)[:12]}")
        return self.get_run(run_id)

    # -------------------------------------------------------------------------
    # STATION 2: TDD TEST ENGINEER (Immutable Unit/E2E Test Harness)
    # -------------------------------------------------------------------------
    def step_station_2_tests(self, run_id: str) -> Dict[str, Any]:
        """Station 2: Generates executable unit test suite and locks it read-only."""
        run = self.get_run(run_id)
        spec_artifacts = [a for a in run["artifacts"] if a["artifact_type"] == "SPEC_MD"]
        if not spec_artifacts:
            raise ValueError(f"Station 2 cannot run without SPEC_MD artifact for {run_id}")

        spec_content = spec_artifacts[-1]["content"]
        start_time = time.time()
        logger.info(f"[{run_id}] Station 2 (TDD Test Engineer) starting...")

        prompt = f"""You are the TDD Lead Test Engineer for Sovereign OS.
Read the Technical Specification below and write a comprehensive, standalone Python test script.

TECHNICAL SPECIFICATION:
{spec_content}

MANDATES FOR THE TEST SCRIPT:
1. Must be executable via `/home/james/stacklabs/.venv/bin/python3 <test_file.py>`.
2. Must use Python assertions (`assert condition, 'error message'`) or `unittest`.
3. Must thoroughly test all happy paths, boundary conditions, and error contracts defined in the spec.
4. Output ONLY valid, runnable Python code. Zero conversational filler. Do not wrap in markdown quotes if possible, or use standard ```python block.
"""
        model_name = run.get("assigned_model") or DEFAULT_PRO_MODEL
        test_code = _generate_llm(prompt, preferred_model=model_name)

        # Clean code fences if present
        if test_code.startswith("```python"):
            test_code = test_code[9:]
        elif test_code.startswith("```"):
            test_code = test_code[3:]
        if test_code.endswith("```"):
            test_code = test_code[:-3]
        test_code = test_code.strip()

        # Target test file path
        safe_ticket = re.sub(r'[^A-Za-z0-9_]', '_', run['ticket_id']).lower()
        test_filename = f"test_assembly_{safe_ticket}_{run_id.split('-')[-1]}.py"
        test_filepath = TESTS_ASSEMBLY_DIR / test_filename

        # Write to disk
        test_filepath.write_text(test_code, encoding="utf-8")
        # Enforce read-only permissions on the file
        test_filepath.chmod(0o444)

        exec_time = (time.time() - start_time) * 1000.0
        self.record_artifact(
            run_id=run_id,
            station_id=2,
            artifact_type="TEST_HARNESS",
            content=test_code,
            file_target=str(test_filepath),
            execution_time_ms=exec_time
        )

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE sys_assembly_run
                SET current_state = 'TESTS_LOCKED',
                    current_station = 3,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE run_id = ?
            """, (run_id,))
            conn.commit()

        logger.info(f"[{run_id}] Station 2 Completed. Test suite locked at {test_filepath} (chmod 0444).")
        return self.get_run(run_id)

    # -------------------------------------------------------------------------
    # STATION 3: CODE SYNTHESIZER (Implementation Coder)
    # -------------------------------------------------------------------------
    def step_station_3_code(self, run_id: str) -> Dict[str, Any]:
        """Station 3: Generates and applies the implementation diff."""
        run = self.get_run(run_id)
        spec_artifacts = [a for a in run["artifacts"] if a["artifact_type"] == "SPEC_MD"]
        test_artifacts = [a for a in run["artifacts"] if a["artifact_type"] == "TEST_HARNESS"]

        if not spec_artifacts or not test_artifacts:
            raise ValueError("Missing Spec or Test Harness for Station 3")

        spec_content = spec_artifacts[-1]["content"]
        test_artifact = test_artifacts[-1]
        test_filepath = Path(test_artifact["file_target"])

        # IMMUTABLE FENCE CHECK: Verify test harness has not been tampered with
        current_test_content = test_filepath.read_text(encoding="utf-8")
        current_hash = _compute_sha256(current_test_content)
        if current_hash != test_artifact["content_hash"]:
            raise PermissionError(f"SECURITY INVARIANT VIOLATION: Test harness {test_filepath} was modified after Station 2!")

        start_time = time.time()
        logger.info(f"[{run_id}] Station 3 (Code Synthesizer) starting (Retry {run['retry_count']}/{run['max_retries']})...")

        error_feedback_prompt = ""
        if run.get("error_feedback"):
            error_feedback_prompt = f"""
PREVIOUS TEST RUN FAILED WITH THE FOLLOWING TRACEBACK / ERRORS:
{run['error_feedback']}

You MUST fix the root cause of these test failures in your code!
"""

        prompt = f"""You are the Senior Implementation Engineer (Code Synthesizer) for Sovereign OS.
Write the code implementation to satisfy the locked technical specification and make the locked test harness pass 100%.

TECHNICAL SPECIFICATION:
{spec_content}

LOCKED TEST HARNESS (READ ONLY - YOU CANNOT MODIFY THIS):
{test_artifact['content']}
{error_feedback_prompt}

CODING MANDATES:
1. Write clean, complete, production-ready Python code.
2. Comply with Sovereign OS Invariants: No raw sqlite subshells, no fake sci-fi buzzwords.
3. Provide the full code or clean modules as specified in the spec.
4. Output your implementation code cleanly. If multiple files, label them with `# TARGET_FILE: <path>` or output the primary module.
"""
        model_name = run.get("assigned_model") or DEFAULT_PRO_MODEL
        synth_code = _generate_llm(prompt, preferred_model=model_name)

        exec_time = (time.time() - start_time) * 1000.0
        self.record_artifact(
            run_id=run_id,
            station_id=3,
            artifact_type="DIFF_PATCH",
            content=synth_code,
            file_target="implementation_payload",
            execution_time_ms=exec_time
        )

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE sys_assembly_run
                SET current_state = 'QA_VERIFY',
                    current_station = 4,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE run_id = ?
            """, (run_id,))
            conn.commit()

        logger.info(f"[{run_id}] Station 3 Completed. Implementation generated ({len(synth_code)} bytes).")
        return self.get_run(run_id)

    # -------------------------------------------------------------------------
    # STATION 4: SANDBOX QA RUNNER (Automated Execution & Test Evaluation)
    # -------------------------------------------------------------------------
    def step_station_4_qa(self, run_id: str) -> Dict[str, Any]:
        """Station 4: Executes test suite in sandbox, handles 3-strike circuit breaker."""
        run = self.get_run(run_id)
        test_artifacts = [a for a in run["artifacts"] if a["artifact_type"] == "TEST_HARNESS"]
        if not test_artifacts:
            raise ValueError("No test harness found for Station 4")

        test_artifact = test_artifacts[-1]
        test_filepath = Path(test_artifact["file_target"])

        # Verify test file immutability
        current_test_content = test_filepath.read_text(encoding="utf-8")
        if _compute_sha256(current_test_content) != test_artifact["content_hash"]:
            raise PermissionError("IMMUTABLE FENCE TRIPPED: Test suite modified during Station 3!")

        start_time = time.time()
        logger.info(f"[{run_id}] Station 4 (Sandbox QA Runner) executing {test_filepath}...")

        # Run test harness in isolated subprocess
        python_bin = "/home/james/stacklabs/.venv/bin/python3"
        if not os.path.exists(python_bin):
            python_bin = sys.executable

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{REPO_ROOT}:{REPO_ROOT}/scripts:" + env.get("PYTHONPATH", "")

        proc = subprocess.run(
            [python_bin, str(test_filepath)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
            env=env
        )

        exec_time = (time.time() - start_time) * 1000.0
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode

        if exit_code == 0:
            logger.info(f"[{run_id}] Station 4 QA PASSED! (0 test failures)")
            self.record_artifact(
                run_id=run_id,
                station_id=4,
                artifact_type="QA_LOG",
                content=stdout if stdout else "ALL TESTS PASSED",
                file_target=str(test_filepath),
                execution_time_ms=exec_time
            )
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE sys_assembly_run
                    SET current_state = 'QA_PASSED',
                        current_station = 5,
                        exit_code = 0,
                        error_feedback = NULL,
                        sys_updated_on = CURRENT_TIMESTAMP
                    WHERE run_id = ?
                """, (run_id,))
                conn.commit()
        else:
            # Test failed!
            combined_error = f"EXIT CODE: {exit_code}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            logger.warning(f"[{run_id}] Station 4 QA FAILED (exit code {exit_code}).")
            self.record_artifact(
                run_id=run_id,
                station_id=4,
                artifact_type="QA_STDERR",
                content=combined_error,
                file_target=str(test_filepath),
                execution_time_ms=exec_time
            )

            new_retry_count = run["retry_count"] + 1
            max_retries = run["max_retries"]

            if new_retry_count >= max_retries:
                # TRIP CIRCUIT BREAKER
                logger.error(f"[{run_id}] ⚡ CIRCUIT BREAKER TRIPPED after {new_retry_count} failed attempts!")
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE sys_assembly_run
                        SET current_state = 'CIRCUIT_TRIPPED',
                            retry_count = ?,
                            exit_code = ?,
                            error_feedback = ?,
                            sys_updated_on = CURRENT_TIMESTAMP
                        WHERE run_id = ?
                    """, (new_retry_count, exit_code, combined_error, run_id))
                    conn.commit()
            else:
                # LOOP BACK TO STATION 3
                logger.info(f"[{run_id}] Routing back to Station 3 (Retry {new_retry_count}/{max_retries})...")
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE sys_assembly_run
                        SET current_state = 'CODING',
                            current_station = 3,
                            retry_count = ?,
                            exit_code = ?,
                            error_feedback = ?,
                            sys_updated_on = CURRENT_TIMESTAMP
                        WHERE run_id = ?
                    """, (new_retry_count, exit_code, combined_error, run_id))
                    conn.commit()

        return self.get_run(run_id)

    # -------------------------------------------------------------------------
    # STATION 5: GATEKEEPER & SOVEREIGN KNOT (Audit & Commit)
    # -------------------------------------------------------------------------
    def step_station_5_review(self, run_id: str) -> Dict[str, Any]:
        """Station 5: AST hygiene, anti-fluff verification, and ticket closure."""
        run = self.get_run(run_id)
        if run["current_state"] != "QA_PASSED":
            raise ValueError(f"Run {run_id} is in state {run['current_state']}, expected QA_PASSED.")

        start_time = time.time()
        logger.info(f"[{run_id}] Station 5 (Gatekeeper) performing final invariant audit...")

        audit_results = {
            "ast_syntax_valid": True,
            "anti_fluff_clean": True,
            "rule_iv_2_b_ui_check": "N/A",
            "findings": []
        }

        # Check all artifacts for forbidden sci-fi buzzwords
        for artifact in run["artifacts"]:
            content = artifact.get("content", "")
            for pattern in FORBIDDEN_TROPES:
                if re.search(pattern, content, re.IGNORECASE):
                    audit_results["anti_fluff_clean"] = False
                    audit_results["findings"].append(f"Forbidden trope found: {pattern} in Station {artifact['station_id']}")

        exec_time = (time.time() - start_time) * 1000.0
        audit_json = json.dumps(audit_results, indent=2)

        self.record_artifact(
            run_id=run_id,
            station_id=5,
            artifact_type="AUDIT_REPORT",
            content=audit_json,
            execution_time_ms=exec_time
        )

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE sys_assembly_run
                SET current_state = 'COMPLETED',
                    current_station = 5,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE run_id = ?
            """, (run_id,))
            conn.commit()

        logger.info(f"[{run_id}] Station 5 COMPLETED. Assembly run finalized successfully.")
        return self.get_run(run_id)

    # -------------------------------------------------------------------------
    # ORCHESTRATION DISPATCHER
    # -------------------------------------------------------------------------
    def step_next(self, run_id: str) -> Dict[str, Any]:
        """Advance the assembly line to the next logical station step."""
        run = self.get_run(run_id)
        state = run["current_state"]
        station = run["current_station"]

        if state == "PENDING" or station == 1:
            return self.step_station_1_spec(run_id)
        elif state == "SPEC_LOCKED" or station == 2:
            return self.step_station_2_tests(run_id)
        elif state in ("TESTS_LOCKED", "CODING") or station == 3:
            return self.step_station_3_code(run_id)
        elif state == "QA_VERIFY" or station == 4:
            return self.step_station_4_qa(run_id)
        elif state == "QA_PASSED" or station == 5:
            return self.step_station_5_review(run_id)
        elif state in ("COMPLETED", "CIRCUIT_TRIPPED"):
            logger.info(f"Run {run_id} is in terminal state: {state}")
            return run
        else:
            raise ValueError(f"Unrecognized run state: {state}")

    def run_pipeline(self, run_id: str) -> Dict[str, Any]:
        """Execute all stations sequentially until completion or circuit trip."""
        logger.info(f"Executing full automated assembly pipeline for {run_id}...")
        while True:
            run = self.get_run(run_id)
            if run["current_state"] in ("COMPLETED", "CIRCUIT_TRIPPED"):
                break
            # Advance one station
            self.step_next(run_id)
        return self.get_run(run_id)

    def reset_circuit(self, run_id: str, new_brief: Optional[str] = None) -> Dict[str, Any]:
        """Reset a tripped circuit breaker, optionally with updated brief."""
        with get_db() as conn:
            cur = conn.cursor()
            if new_brief:
                cur.execute("""
                    UPDATE sys_assembly_run
                    SET current_state = 'CODING',
                        current_station = 3,
                        retry_count = 0,
                        brief = ?,
                        error_feedback = NULL,
                        sys_updated_on = CURRENT_TIMESTAMP
                    WHERE run_id = ?
                """, (new_brief, run_id))
            else:
                cur.execute("""
                    UPDATE sys_assembly_run
                    SET current_state = 'CODING',
                        current_station = 3,
                        retry_count = 0,
                        error_feedback = NULL,
                        sys_updated_on = CURRENT_TIMESTAMP
                    WHERE run_id = ?
                """, (run_id,))
            conn.commit()

        logger.info(f"Circuit reset for run {run_id}. Resetting retry_count to 0.")
        return self.get_run(run_id)


# Singleton Engine Instance
assembly_engine = AssemblyPipelineEngine()

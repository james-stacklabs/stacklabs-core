#!/usr/bin/env python3
"""
scripts/gemini_editorial_sentry.py
==================================
The "Brain" Linter: Semantic Editorial & Institutional Sentry for StackLabs.
Powered by Gemini API (gemini-3.8-flash) via GEMINI_API_KEY in .env.

Audits markdown specs, dossiers, work orders, and email drafts against:
1. Invariant 1.8: No hardware box / mini-PC / appliance sales talk (100% Enterprise Software).
2. Invariant 38.1: No sci-fi / cyberpunk / tabletop RPG cosplay (e.g. Omega Gate, Reflex Coprocessor).
3. Invariant 32: The Law of "I" (Solo builder voice; zero corporate "we/our").
4. Invariant 0: Grounded metal reality (zero unclosed deal puffery or fake client claims).
5. Invariant 8 / Rule 07: No ASCII box-drawing flowcharts (mandates Mermaid or tables).

Usage:
  python3 scripts/gemini_editorial_sentry.py <file_or_dir_path>
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env from stacklabs root
STACKLABS_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(STACKLABS_ROOT / ".env")

import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("\033[91m[-] FATAL: GEMINI_API_KEY not found in environment or .env!\033[0m")
    sys.exit(1)

genai.configure(api_key=api_key)

SYSTEM_PROMPT = """You are the Senior Institutional Editor and Enterprise Sentry for StackLabs LLC.
Your sole duty is to protect James Carroll (Lead Systems Architect, solo founder) from 'LLM creative debt', comic-book cosplay, and ungrounded tech puffery before documents leave the lab.

Evaluate the submitted document against these 5 STACKLABS CONSTITUTIONAL INVARIANTS:

1. INVARIANT 1.8: ENTERPRISE SOFTWARE ONLY (NO HARDWARE SALES / NO MINI-PC TALK)
   - StackLabs sells enterprise software running on standard x86 Linux (from on-prem rack servers to edge nodes).
   - STRICTLY FORBIDDEN: Framing StackLabs as a hardware box company, pitching "mini PC", "35W appliance", "less power than a light bulb", or "$600 retail box".

2. INVARIANT 38.1: NO SCI-FI / CYBERPUNK / TABLETOP RPG COSPLAY
   - STRICTLY FORBIDDEN: Comic-book or tabletop naming such as "Omega Gate", "Reflex Coprocessor", "Spinal Cord", "Nervous System", "Ripperdoc", "Cyberware", "Zeus Conduit", or similar theatrical inventions.
   - MANDATORY REPLACEMENT: Use grounded ITIL/enterprise software terms: "Human Approval Queue", "Manual Review Gate", "In-Memory State Plane", "Decoupled Read Replica".

3. INVARIANT 32: THE LAW OF "I" (SOLO BUILDER VOICE)
   - James Carroll is a solo systems architect operating on bare metal.
   - STRICTLY FORBIDDEN: Corporate "we", "our team", "our company".
   - Use "I", "my", "a", or "the".

4. INVARIANT 0: STAY BEHIND YOUR SKIS (ZERO DEAL PUFFERY)
   - Exactly zero active enterprise clients; exactly zero field deployments.
   - Exploratory prospect discussions (e.g. Jeremy Malone / Davidson Homes, Pawel Rudnicki) must be framed as prospective models, never signed commercial reality.

5. INVARIANT 8 / RULE 07: NO ASCII BOX-DRAWING DIAGRAMS
   - Text boxes using characters like ┌, ─, ┐, │, └, ┘, +---+ are banned.
   - Architectural diagrams must use valid Mermaid (```mermaid) or clean markdown tables.

RESPOND STRICTLY IN VALID JSON WITH THIS EXACT SCHEMA:
{
  "verdict": "PASSED" | "VIOLATIONS_FOUND",
  "score": <integer 0-100, where 100 is pristine institutional enterprise grade>,
  "summary": "<1-2 sentence executive summary of document compliance>",
  "violations": [
    {
      "invariant": "<Invariant Name>",
      "quote": "<exact quote from text showing violation>",
      "issue": "<plain English explanation of why this violates enterprise grounding>",
      "suggested_fix": "<concrete professional rewrite>"
    }
  ]
}
"""

def audit_file(file_path: Path) -> dict:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"error": f"Could not read file: {e}"}

    if len(text.strip()) == 0:
        return {"verdict": "PASSED", "score": 100, "summary": "Empty file.", "violations": []}

    # Use production 2026 model: gemini-3.8-flash
    model = genai.GenerativeModel(
        model_name="gemini-3.8-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json", "temperature": 0.1}
    )

    prompt = f"DOCUMENT PATH: {file_path.name}\n\nDOCUMENT CONTENT:\n{text[:60000]}"
    try:
        response = model.generate_content(prompt)
        res_json = json.loads(response.text)
        return res_json
    except Exception as e:
        return {"error": f"Gemini API generation failed: {e}"}

def run_sentry(paths: list[Path]):
    print("=" * 80)
    print("🧠 STACKLABS SEMANTIC EDITORIAL SENTRY (GEMINI 3.8 FLASH)")
    print("=" * 80)

    total_checked = 0
    total_violations = 0

    for target in paths:
        if not target.exists():
            print(f"[-] Path not found: {target}")
            continue

        files_to_scan = []
        if target.is_file():
            files_to_scan.append(target)
        else:
            for ext in [".md", ".txt"]:
                files_to_scan.extend(target.rglob(f"*{ext}"))

        for f in files_to_scan:
            # Skip templates or relics
            if "relics/" in str(f) or ".system_generated" in str(f) or "node_modules" in str(f):
                continue

            total_checked += 1
            print(f"\n🔍 Auditing: {f.relative_to(STACKLABS_ROOT) if STACKLABS_ROOT in f.parents else f}")
            result = audit_file(f)

            if "error" in result:
                print(f"   \033[91m[ERROR] {result['error']}\033[0m")
                continue

            verdict = result.get("verdict", "UNKNOWN")
            score = result.get("score", 0)
            summary = result.get("summary", "")
            violations = result.get("violations", [])

            if verdict == "PASSED" and len(violations) == 0:
                print(f"   \033[92m✔ PASSED (Score: {score}/100) — {summary}\033[0m")
            else:
                total_violations += len(violations)
                print(f"   \033[91m❌ VIOLATIONS FOUND (Score: {score}/100) — {summary}\033[0m")
                for v in violations:
                    print(f"     • \033[93m[{v.get('invariant')}]\033[0m \"{v.get('quote')}\"")
                    print(f"       \033[90mIssue:\033[0m {v.get('issue')}")
                    print(f"       \033[92mFix:\033[0m   {v.get('suggested_fix')}")

    print("\n" + "=" * 80)
    print(f"📊 SENTRY SUMMARY: Audited {total_checked} files | {total_violations} total violations detected.")
    print("=" * 80)
    return 1 if total_violations > 0 else 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StackLabs Gemini Editorial Sentry")
    parser.add_argument("paths", nargs="+", type=str, help="Files or directories to audit")
    args = parser.parse_args()

    target_paths = [Path(p).resolve() for p in args.paths]
    sys.exit(run_sentry(target_paths))

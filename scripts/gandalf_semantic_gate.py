#!/usr/bin/env python3
"""
Gandalf Semantic Sentry & Anti-Slop Cognitive Gate (Tier 2)
StackLabs Sovereign OS // Clio Metal Forge

Uses Gemini 3.8 Flash to semantically inspect extracted user-facing JSX/HTML UI
strings for condescending AI slop, Invariant 1.9 outbound hardware buzzwords,
and Invariant 38 chat analogies that slip past static regex filters.

Includes SHA-256 disk caching to ensure unchanged files run in <10ms.
"""

import sys
import os
import re
import json
import hashlib
from pathlib import Path

# Load credentials
import dotenv
dotenv.load_dotenv('/home/james/stacklabs/.env')
dotenv.load_dotenv('/home/james/stacklabs/scripts/.env.auth')

from google import genai

CACHE_DIR = Path("/home/james/stacklabs/.cache/gandalf_semantic")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "gemini-3.8-flash"

SYSTEM_INSTRUCTION = """You are the Gandalf Semantic Gatekeeper for an enterprise data systems engineering firm (StackLabs).
Your sole purpose is to ruthlessly reject condescending AI slop, conversational analogies, outward hardware buzzwords, and prompt leakage from user-facing frontend code.

Evaluate the provided user-facing UI text snippets against these 4 STRICT CONSTITUTIONAL VIOLATIONS:

1. CONDESCENDING_AI_SLOP:
   - Patronizing explanations of AI latency or execution ("throttled so human retinas can observe", "for human comprehension", "observing causal timeline pruning").
   - Treating the human user as slow, weak, or biologically limited.
   - Robotic or sci-fi narrator posturing.

2. INVARIANT_1_9_HARDWARE_FLEX:
   - Outward-facing use of "bare metal", "on metal", "bare-metal", "35-watt appliance", "turnkey appliance" in customer-facing UI.
   - "Bare metal" describes internal execution on Clio NVMe only; it is strictly banned on customer portals and demo screens.

3. INVARIANT_38_CHAT_ANALOGIES:
   - Internal dev chat metaphors: "Pepe Silvia", "Best Buy", "Ant Farm", "Zeus", "Comic Book", "Toy App", "Trash Can".
   - Cyberpunk sci-fi jargon: "Reflex Coprocessor", "Ripperdoc", "Cyberware", "Wetware", "Arasaka".

4. UNCLOSED_DEAL_PUFFERY:
   - Claiming unclosed prospects (e.g. Davidson Homes, Jeremy Malone, Pawel Rudnicki) as active clients or production realities.

INSTRUCTIONS:
- You will receive a list of items: {"id": int, "file": str, "line": int, "text": str}.
- Return a strict JSON object with:
  "passed": boolean,
  "violations": [
     {
       "id": int,
       "category": string, // One of the 4 above
       "offending_phrase": string,
       "reason": string
     }
  ]
- If all strings are professional, clean enterprise engineering copy, return {"passed": true, "violations": []}.
- Be decisive. Do NOT flag standard engineering terms like "In-Memory", "POSIX VFS", "Latency", "Replay", "Cache", "Trace".
"""

# Extract user-facing string candidates from TSX/JSX/HTML
REGEX_JSX_TEXT = re.compile(r'>([^<>{}\n]+)<')
REGEX_ATTR_STRING = re.compile(r'\b(?:title|label|placeholder|description|notice|banner|tooltip)=["\']([^"\']+)["\']')
REGEX_PROP_STRING = re.compile(r'["\']([A-Z][a-zA-Z0-9\s.,!?:;/()#_-]{12,})["\']')

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def extract_ui_strings(file_path: Path) -> list[dict]:
    snippets = []
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return snippets

    lines = content.splitlines()
    snippet_id = 1
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Skip pure code comments or imports
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*') or stripped.startswith('import '):
            continue

        # Extract JSX text
        for match in REGEX_JSX_TEXT.finditer(line):
            text = match.group(1).strip()
            if len(text) > 3 and not text.startswith('&') and not text.isdigit():
                snippets.append({
                    "id": snippet_id,
                    "file": str(file_path),
                    "line": line_no,
                    "text": text
                })
                snippet_id += 1

        # Extract string attributes
        for match in REGEX_ATTR_STRING.finditer(line):
            text = match.group(1).strip()
            if len(text) > 3:
                snippets.append({
                    "id": snippet_id,
                    "file": str(file_path),
                    "line": line_no,
                    "text": text
                })
                snippet_id += 1

    return snippets

def scan_target(target_path: Path, force: bool = False, verbose: bool = False) -> tuple[bool, list[dict]]:
    valid_exts = {'.tsx', '.jsx', '.html'}
    ignore_dirs = {'node_modules', 'dist', '.git', '.wrangler', '.venv', '__pycache__', 'archive'}
    
    files_to_scan = []
    if target_path.is_file():
        if target_path.suffix in valid_exts:
            files_to_scan.append(target_path)
    else:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for f in files:
                p = Path(root) / f
                if p.suffix in valid_exts and not p.name.endswith('.d.ts'):
                    files_to_scan.append(p)

    all_snippets = []
    cached_clean = 0
    scanned_file_hashes = []

    for file_p in files_to_scan:
        content = file_p.read_text(encoding='utf-8', errors='ignore')
        file_hash = compute_hash(content)
        cache_file = CACHE_DIR / f"{file_p.stem}_{file_hash}.clean"

        if not force and cache_file.exists():
            cached_clean += 1
            continue

        scanned_file_hashes.append((file_p, cache_file))
        file_snippets = extract_ui_strings(file_p)
        if file_snippets:
            all_snippets.extend(file_snippets)
        else:
            # No UI strings, mark clean immediately
            cache_file.touch()

    if verbose:
        print(f"[Gandalf Semantic Sentry] Files checked: {len(files_to_scan)} (Cached Clean: {cached_clean}, Scanning: {len(files_to_scan) - cached_clean})")

    if not all_snippets:
        for _, c_file in scanned_file_hashes:
            c_file.touch()
        return True, []

    # Re-index globally so each snippet has a unique ID across files
    for idx, snip in enumerate(all_snippets, start=1):
        snip["id"] = idx

    if verbose:
        print(f"[Gandalf Semantic Sentry] Extracted {len(all_snippets)} UI snippets. Invoking {MODEL_NAME}...")

    client = genai.Client()
    payload = json.dumps(all_snippets, indent=2)

    prompt = f"{SYSTEM_INSTRUCTION}\n\nUI STRINGS TO EVALUATE:\n{payload}"

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        raw_text = response.text.strip() if response.text else "{}"
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)
        result = json.loads(raw_text)
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
    except Exception as e:
        print(f"\033[93m⚠ [Gandalf Semantic Gate] Cloud inference error: {e}. Failing closed.\033[0m")
        return False, [{"category": "API_ERROR", "offending_phrase": str(e), "file": str(target_path), "line": 0, "reason": "Failed to verify semantic compliance with Gemini"}]

    violations = result.get("violations", []) if isinstance(result, dict) else []
    passed = result.get("passed", False) and len(violations) == 0 if isinstance(result, dict) else False

    if passed:
        # Cache clean status for all scanned files
        for _, c_file in scanned_file_hashes:
            c_file.touch()
        return True, []
    else:
        # Map violations back to snippets
        enriched_violations = []
        snippet_map = {s["id"]: s for s in all_snippets}
        for v in violations:
            snip_id = v.get("id")
            snip = snippet_map.get(snip_id, {})
            enriched_violations.append({
                "file": snip.get("file", "unknown"),
                "line": snip.get("line", 0),
                "text": snip.get("text", ""),
                "category": v.get("category", "SLOP"),
                "offending_phrase": v.get("offending_phrase", ""),
                "reason": v.get("reason", "")
            })
        return False, enriched_violations

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gandalf Semantic Sentry (Tier 2)")
    parser.add_argument("target", nargs="?", default="/home/james/stacklabs/apps/cmdb_studio/src", help="File or directory to scan")
    parser.add_argument("--force", action="store_true", help="Bypass local cache and force API evaluation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose log output")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}")
        sys.exit(1)

    passed, violations = scan_target(target_path, force=args.force, verbose=args.verbose)

    if not passed:
        print("\033[91m\033[1m" + "=" * 80)
        print("🧙‍♂️ [GANDALF SEMANTIC GATE] YOU SHALL NOT PASS!")
        print("=" * 80 + "\033[0m")
        for v in violations:
            print(f" ❌ \033[93m{v['file']}:{v['line']}\033[0m")
            print(f"    Category:  \033[95m{v['category']}\033[0m")
            print(f"    Offending: \033[91m\"{v['offending_phrase']}\"\033[0m")
            print(f"    Context:   \033[90m{v['text']}\033[0m")
            print(f"    Reason:    \033[97m{v['reason']}\033[0m\n")
        print("\033[91mBuild blocked by Gandalf Semantic Circuit Breaker.\033[0m\n")
        sys.exit(1)
    else:
        print("\033[92m✔ [GANDALF SEMANTIC GATE] PASSED: All user-facing copy semantically verified against Sovereign Constitution.\033[0m")
        sys.exit(0)

if __name__ == "__main__":
    main()

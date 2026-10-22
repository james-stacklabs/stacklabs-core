#!/usr/bin/env python3
"""
scripts/core/code_hygiene_scanner.py
=============================================================================
SOVEREIGN OS: COMPREHENSIVE AST & PATTERN CODE HYGIENE SCANNER
=============================================================================
Scans Python scripts in SovereignOS against the 7 Invariant Anti-Patterns:
1. Unmanaged sqlite3.connect() handles
2. Inline scoped imports (inside functions/loops)
3. Hardcoded system paths and raw IP addresses
4. Cowardly exception swallowers (except: pass)
5. Manual .env text parsing
6. Deprecated LLM model strings & unguarded thinking_config
7. Whack-a-mole entity checks (if "gonzalez" in text)
=============================================================================
"""

import os
import sys
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Regex patterns for string literal checks
RAW_IP_PATTERN = re.compile(r"""\b(?:192\.168\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})\b""")
HARDCODED_HOME_PATTERN = re.compile(r"""/(?:home/james/(?:SovereignOS|sovereign_inbox)[a-zA-Z0-9_\-/\.]*)""")
DEPRECATED_MODELS = re.compile(r"""["'](?:gemini-[12]\.[0-9].*|gemini-3\.[0-7].*|text-bison)["']""")
MANUAL_ENV_PATTERN = re.compile(r"""(?:\.env["']|open\s*\(\s*["'][^"']*\.env["']\s*\))""")
WHACK_A_MOLE_PATTERN = re.compile(r"""if\s+["'](?:gonzalez|barf|metsy|judge|ohtani)["']\s+in\s+""")

class CodeHygieneVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.unmanaged_sqlite: List[Dict[str, Any]] = []
        self.inline_imports: List[Dict[str, Any]] = []
        self.swallowed_exceptions: List[Dict[str, Any]] = []
        self.deprecated_models: List[Dict[str, Any]] = []
        self.hardcoded_paths: List[Dict[str, Any]] = []
        self.manual_env_reads: List[Dict[str, Any]] = []
        self.whack_a_mole: List[Dict[str, Any]] = []
        
        self._scope_depth = 0
        self._inside_with = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1

    def visit_Import(self, node: ast.Import):
        if self._scope_depth > 0:
            names = [alias.name for alias in node.names]
            self.inline_imports.append({
                "line": node.lineno,
                "names": names,
                "type": "import"
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if self._scope_depth > 0:
            module = node.module or ""
            names = [alias.name for alias in node.names]
            self.inline_imports.append({
                "line": node.lineno,
                "names": [f"{module}.{n}" if module else n for n in names],
                "type": "from_import"
            })
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        prev = self._inside_with
        self._inside_with = True
        self.generic_visit(node)
        self._inside_with = prev

    def visit_Call(self, node: ast.Call):
        # Check for sqlite3.connect()
        is_sqlite_connect = False
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "connect":
                if isinstance(node.func.value, ast.Name) and node.func.value.id in ("sqlite3", "sqlite"):
                    is_sqlite_connect = True
        elif isinstance(node.func, ast.Name) and node.func.id == "sqlite3_connect":
            is_sqlite_connect = True

        if is_sqlite_connect and not self._inside_with:
            self.unmanaged_sqlite.append({
                "line": node.lineno,
                "detail": "sqlite3.connect() called outside context manager"
            })

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Check for bare except: pass or except Exception: pass
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            exc_name = "bare"
            if node.type:
                if isinstance(node.type, ast.Name):
                    exc_name = node.type.id
                elif isinstance(node.type, ast.Attribute):
                    exc_name = f"{getattr(node.type.value, 'id', '')}.{node.type.attr}"
            self.swallowed_exceptions.append({
                "line": node.lineno,
                "type": exc_name
            })
        self.generic_visit(node)

def audit_file(file_path: Path) -> Dict[str, Any]:
    rel_path = str(file_path.relative_to(REPO_ROOT))
    result = {
        "file": rel_path,
        "unmanaged_sqlite": [],
        "inline_imports": [],
        "swallowed_exceptions": [],
        "deprecated_models": [],
        "hardcoded_paths": [],
        "manual_env_reads": [],
        "whack_a_mole": [],
        "parse_error": None
    }

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        result["parse_error"] = f"Read error: {str(e)}"
        return result

    # 1. Regex string-level checks
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        # Hardcoded paths and IPs
        for match in HARDCODED_HOME_PATTERN.finditer(line):
            result["hardcoded_paths"].append({
                "line": idx,
                "match": match.group(0),
                "type": "hardcoded_home_path"
            })
        for match in RAW_IP_PATTERN.finditer(line):
            result["hardcoded_paths"].append({
                "line": idx,
                "match": match.group(0),
                "type": "raw_ip"
            })
        # Deprecated models
        if DEPRECATED_MODELS.search(line):
            result["deprecated_models"].append({
                "line": idx,
                "snippet": line.strip()[:80]
            })
        # Manual .env parsing
        if MANUAL_ENV_PATTERN.search(line) and "os.environ" not in line and "pydantic" not in line:
            if "open(" in line and ".env" in line:
                result["manual_env_reads"].append({
                    "line": idx,
                    "snippet": line.strip()[:80]
                })
        # Whack-a-mole
        if WHACK_A_MOLE_PATTERN.search(line):
            result["whack_a_mole"].append({
                "line": idx,
                "snippet": line.strip()[:80]
            })

    # 2. AST parsing checks
    try:
        tree = ast.parse(content, filename=str(file_path))
        visitor = CodeHygieneVisitor(file_path)
        visitor.visit(tree)
        result["unmanaged_sqlite"] = visitor.unmanaged_sqlite
        result["inline_imports"] = visitor.inline_imports
        result["swallowed_exceptions"] = visitor.swallowed_exceptions
    except SyntaxError as se:
        result["parse_error"] = f"Syntax error line {se.lineno}: {se.msg}"
    except Exception as ex:
        result["parse_error"] = f"AST error: {str(ex)}"

    return result

def run_scan(target_dir: Path) -> Dict[str, Any]:
    findings = []
    py_files = sorted(target_dir.rglob("*.py"))
    
    total_files = len(py_files)
    total_unmanaged_sqlite = 0
    total_inline_imports = 0
    total_swallowed_exceptions = 0
    total_deprecated_models = 0
    total_hardcoded_paths = 0
    total_manual_env = 0
    total_whack_a_mole = 0

    for py_file in py_files:
        # Skip pycache and virtual environments
        if "__pycache__" in py_file.parts or ".venv" in py_file.parts:
            continue
        res = audit_file(py_file)
        
        has_violations = (
            res["unmanaged_sqlite"] or 
            res["inline_imports"] or 
            res["swallowed_exceptions"] or 
            res["deprecated_models"] or 
            res["hardcoded_paths"] or 
            res["manual_env_reads"] or 
            res["whack_a_mole"]
        )
        
        if has_violations:
            findings.append(res)
            total_unmanaged_sqlite += len(res["unmanaged_sqlite"])
            total_inline_imports += len(res["inline_imports"])
            total_swallowed_exceptions += len(res["swallowed_exceptions"])
            total_deprecated_models += len(res["deprecated_models"])
            total_hardcoded_paths += len(res["hardcoded_paths"])
            total_manual_env += len(res["manual_env_reads"])
            total_whack_a_mole += len(res["whack_a_mole"])

    summary = {
        "target_dir": str(target_dir),
        "total_python_files": total_files,
        "files_with_violations": len(findings),
        "clean_files": total_files - len(findings),
        "totals": {
            "unmanaged_sqlite": total_unmanaged_sqlite,
            "inline_imports": total_inline_imports,
            "swallowed_exceptions": total_swallowed_exceptions,
            "deprecated_models": total_deprecated_models,
            "hardcoded_paths_and_ips": total_hardcoded_paths,
            "manual_env_reads": total_manual_env,
            "whack_a_mole_filters": total_whack_a_mole
        },
        "findings": findings
    }
    return summary

def generate_markdown_report(summary: Dict[str, Any]) -> str:
    totals = summary["totals"]
    lines = [
        "# 🛡️ SOVEREIGN OS: CODE HYGIENE AUDIT SCORECARD",
        f"**Target Directory**: `{summary['target_dir']}`",
        f"**Total Python Files Analyzed**: `{summary['total_python_files']}`",
        f"**Files With Violations**: `{summary['files_with_violations']}` | **Clean Files**: `{summary['clean_files']}`\n",
        "## 📊 The 7 Anti-Patterns Totals",
        "| Anti-Pattern | Severity | Detected Instances | Invariant Reference |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Unmanaged SQLite Handles** | CRITICAL | **{totals['unmanaged_sqlite']}** | `SMELLS_LIKE_FERAL_INTERNS #1` |",
        f"| **Inline Scoped Imports** | MAJOR | **{totals['inline_imports']}** | `SMELLS_LIKE_FERAL_INTERNS #2` |",
        f"| **Hardcoded Paths & Raw IPs** | MAJOR | **{totals['hardcoded_paths_and_ips']}** | `SMELLS_LIKE_FERAL_INTERNS #3` & `KI-001` |",
        f"| **Swallowed Exceptions (`pass`)** | MAJOR | **{totals['swallowed_exceptions']}** | `SMELLS_LIKE_FERAL_INTERNS #4` |",
        f"| **Manual `.env` File Reading** | MINOR | **{totals['manual_env_reads']}** | `SMELLS_LIKE_FERAL_INTERNS #5` |",
        f"| **Deprecated Models & Configs** | CRITICAL | **{totals['deprecated_models']}** | Legacy Model Eradication Mandate |",
        f"| **Whack-a-Mole String Filters** | MAJOR | **{totals['whack_a_mole_filters']}** | `ANTI_WHACK_A_MOLE_DOCTRINE.md` |\n",
        "## 🚨 Top Offending Files (Hall of Infamy)",
        "| File Path | Unmanaged SQLite | Inline Imports | Swallowed Excs | Hardcoded Paths | Deprecated Models |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    # Sort files by total violations count
    sorted_files = sorted(
        summary["findings"], 
        key=lambda f: (
            len(f["unmanaged_sqlite"]) + 
            len(f["inline_imports"]) + 
            len(f["swallowed_exceptions"]) + 
            len(f["hardcoded_paths"]) + 
            len(f["deprecated_models"])
        ), 
        reverse=True
    )

    for item in sorted_files[:25]:
        lines.append(
            f"| `{item['file']}` | {len(item['unmanaged_sqlite'])} | {len(item['inline_imports'])} | "
            f"{len(item['swallowed_exceptions'])} | {len(item['hardcoded_paths'])} | {len(item['deprecated_models'])} |"
        )

    lines.append("\n## 🛠️ Remediation Strategy")
    lines.append("1. **Phase 1 (Domain Segregation)**: Partition `scripts/` into domain sub-packages (`fanstack/`, `samtracker/`, `cinema/`, `ops/`, `core/`) with root forwarder shims.")
    lines.append("2. **Phase 2 (AST Auto-Hoisting)**: Programmatically hoist inline scoped imports to module headers.")
    lines.append("3. **Phase 3 (DB Context Wrapping)**: Refactor unmanaged SQLite handles to `with get_db() as conn:` or FastAPI REST calls.")
    lines.append("4. **Phase 4 (Model & Path Normalization)**: Replace hardcoded paths with `Path(__file__).resolve()` and normalize LLM model constants to `GAME_TIME_MODEL`.")
    return "\n".join(lines)

def main():
    target = SCRIPTS_DIR
    if len(sys.argv) > 1:
        target = Path(sys.argv[1]).resolve()

    print(f"[*] Starting AST Code Hygiene Scan on: {target}")
    summary = run_scan(target)
    
    # Write JSON report
    out_dir = REPO_ROOT.parent / "sovereign_inbox" / "tickets" / "STRY0010015-SCRIPTS-DIRECTORY-DOMAIN-SEGREGATION-AND-AI-SWEEP" / "audit_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = out_dir / "hygiene_audit_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[+] JSON findings saved to: {json_path}")

    # Write Markdown report
    md_path = out_dir / "HYGIENE_SCORECARD.md"
    md_content = generate_markdown_report(summary)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[+] Markdown scorecard saved to: {md_path}")

    # Also output summary to stdout
    print("\n" + md_content[:2000] + "\n... [truncated for display]")

if __name__ == "__main__":
    main()

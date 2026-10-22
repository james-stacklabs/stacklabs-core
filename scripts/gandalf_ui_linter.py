#!/usr/bin/env python3
"""
StackLabs Gandalf UI Linter & Zero-Port Sentry
Enforces Invariant 26 (Gandalf UI Craft) and Zero Hardcoded Ports in client code.
Target: Clio / Python 3.12 (.venv)
"""
import sys
import os
import re
from pathlib import Path

# Unyielding regex patterns for forbidden client-side port connections
FORBIDDEN_PORT_PATTERNS = [
    re.compile(r'https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|clio\.[a-z0-9]+\.ts\.net):[0-9]{4,5}', re.IGNORECASE),
    re.compile(r'fetch\s*\(\s*[\'"`]https?://[^\'"`]*:[0-9]{4,5}', re.IGNORECASE),
    re.compile(r'EventSource\s*\(\s*[\'"`]https?://[^\'"`]*:[0-9]{4,5}', re.IGNORECASE),
]

SCAN_EXTENSIONS = {'.tsx', '.ts', '.jsx', '.js', '.html'}
IGNORE_DIRS = {
    'node_modules', 'dist', '.git', '.wrangler', '.venv', '__pycache__',
    'archive', 'legacy', '.staging'
}
IGNORE_FILES = {'vite.config.ts', 'vite.config.js', 'SovereignConfig.ts'}

def scan_file_for_ports(file_path: Path) -> list[tuple[int, str, str]]:
    violations = []
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return violations
    for line_no, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        # Skip pure comments
        if stripped.startswith('//') or stripped.startswith('#') or stripped.startswith('/*'):
            continue
        for pattern in FORBIDDEN_PORT_PATTERNS:
            match = pattern.search(line)
            if match:
                violations.append((line_no, line.strip(), match.group(0)))
                break
    return violations

def run_linter(base_dir: Path) -> int:
    all_violations = []

    if base_dir.is_file():
        v = scan_file_for_ports(base_dir)
        if v:
            for line_no, code_line, matched in v:
                all_violations.append((str(base_dir), line_no, code_line, matched))
    else:
        # Target active app and frontend directories
        target_paths = [
            base_dir / "apps",
            base_dir / "frontend",
            base_dir / "scripts" / "templates",
            base_dir / "scripts" / "hailo_dropzone_ui.html",
        ]
        for target in target_paths:
            if not target.exists():
                continue
            if target.is_file():
                v = scan_file_for_ports(target)
                if v:
                    try:
                        rel = target.relative_to(base_dir)
                    except ValueError:
                        rel = target
                    for line_no, code_line, matched in v:
                        all_violations.append((str(rel), line_no, code_line, matched))
                continue
            for root, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    p = Path(root) / f
                    if p.name in IGNORE_FILES or p.name.endswith('.config.ts') or p.name.endswith('.config.js'):
                        continue
                    if p.suffix in SCAN_EXTENSIONS:
                        v = scan_file_for_ports(p)
                        if v:
                            try:
                                rel = p.relative_to(base_dir)
                            except ValueError:
                                rel = p
                            for line_no, code_line, matched in v:
                                all_violations.append((str(rel), line_no, code_line, matched))

    if all_violations:
        print("\033[91m\033[1m" + "=" * 80)
        print("🧙‍♂️ GANDALF ZERO-PORT GATE: \"YOU SHALL NOT PASS!\"")
        print("=" * 80 + "\033[0m")
        for file_path, line_no, code_line, matched in all_violations:
            print(f"\033[93m❌ HARDCODED PORT LEAK DETECTED:\033[0m {file_path}:{line_no}")
            print(f"   \033[91m-> {code_line}\033[0m (Trigger: {matched})")
        print("\n\033[91mRule: Frontend client code must strictly use relative paths (/api/...) or canonical subdomains.\033[0m\n")
        return 1

    print("\033[92m✔ [GANDALF ZERO-PORT GATE] PASSED: Zero hardcoded client ports detected across active surface.\033[0m")
    return 0

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    if len(sys.argv) > 1:
        repo_root = Path(sys.argv[1]).resolve()
    sys.exit(run_linter(repo_root))

#!/home/james/stacklabs/.venv/bin/python3
"""
Permanent CSS Theme-Token & Dark/Light Contrast Gate (WO0011163)
Path: /home/james/stacklabs/scripts/css_theme_contrast_gate.py
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC

Scans TSX/CSS files in apps/cmdb_studio/src to block:
1. Undefined legacy CSS variable names (--card-bg, --canvas-bg, --border-color) that fall back to #FFFFFF in Dark Mode.
2. Un-themed inline style or SVG fill/background attributes using hardcoded white/alabaster (#fff, #ffffff, #f8fafc, #f3f5f8) without an explicit isDarkMode / themeMode ternary on the same line or variable assignment.
3. Un-themed Tailwind bg-white or bg-slate-50 classes without a themeMode ternary or dark: variant.
"""

import pathlib
import re
import sys

DEAD_CSS_VARS = [
    (r"--card-bg\b", "Undefined CSS variable '--card-bg' (must use 'var(--bg-card)')"),
    (r"--canvas-bg\b", "Undefined CSS variable '--canvas-bg' (must use 'var(--bg-subcard)' or 'var(--bg-canvas)')"),
    (r"--border-color\b", "Undefined CSS variable '--border-color' (must use 'var(--border-card)' or 'var(--border-subtle)')"),
]

UNTHEMED_INLINE_LIGHT_BG = re.compile(
    r"(?:backgroundColor\s*:\s*['\"](?:#fff|#ffffff|#f8fafc|#f3f5f8|#f1f5f9)['\"]|"
    r"\bfill\s*=\s*['\"](?:#fff|#ffffff|#f8fafc|#f3f5f8|#fee2e2)['\"])",
    re.IGNORECASE,
)

UNTHEMED_TAILWIND_WHITE = re.compile(r"\bbg-(?:white|slate-50|slate-100)\b(?![/])")


def scan_tsx_file(path: pathlib.Path) -> list[str]:
    violations: list[str] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        for pat, msg in DEAD_CSS_VARS:
            if re.search(pat, line):
                violations.append(f"{path}:{idx}: {msg}")

        if UNTHEMED_INLINE_LIGHT_BG.search(line):
            window = "\n".join(lines[max(0, idx - 3) : min(len(lines), idx + 2)])
            if "isDarkMode" not in window and "themeMode" not in window:
                violations.append(
                    f"{path}:{idx}: Un-themed hardcoded light background/fill '{stripped}' without isDarkMode/themeMode guard."
                )

        if UNTHEMED_TAILWIND_WHITE.search(line):
            window = "\n".join(lines[max(0, idx - 4) : min(len(lines), idx + 3)])
            if "themeMode" not in window and "isDarkMode" not in window and "dark:" not in line:
                violations.append(
                    f"{path}:{idx}: Un-themed Tailwind light class in '{stripped}' without themeMode/isDarkMode/dark: guard."
                )

    return violations


def main() -> int:
    targets = sys.argv[1:] or ["/home/james/stacklabs/apps/cmdb_studio/src"]
    all_violations: list[str] = []

    for t in targets:
        p = pathlib.Path(t)
        if p.is_file() and p.suffix in (".tsx", ".jsx"):
            all_violations.extend(scan_tsx_file(p))
        elif p.is_dir():
            for f in sorted(p.rglob("*.tsx")):
                all_violations.extend(scan_tsx_file(f))

    if all_violations:
        print("❌ [CSS THEME CONTRAST GATE] FAILED:")
        for v in all_violations:
            print(f"  - {v}")
        return 1

    print("✔ [CSS THEME CONTRAST GATE] PASSED: Zero un-themed white backgrounds or dead CSS variables detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

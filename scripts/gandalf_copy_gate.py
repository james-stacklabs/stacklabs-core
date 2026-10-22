#!/usr/bin/env python3
"""
Gandalf Lexical Trap & Pre-Deploy Gate (Upgraded with Invariant 38 Anti-Metaphor Doctrine)
StackLabs Sovereign OS / Clio Forge

Runs O(N) Aho-Corasick string matching on frontend directories before
builds and deployments to prevent AI buzzwords, chat analogies, D&D slop,
and pseudo-industrial marketing phrases from reaching production.
"""

import sys
import os
from pathlib import Path

# Compound slop phrases & chat analogies (strictly lowercase)
SLOP_PHRASES = [
    # Invariant 38: Chat Analogies & Pop Culture Slang
    "best buy",
    "best buy showroom",
    "pepe silvia",
    "ant farm",
    "shaking the ant farm",
    "zeus on mount olympus",
    "trash can",
    "cosplay",
    "toy app",
    "comic book",
    "script kiddie",
    "charlie kelly",
    "mailroom conspiracy",
    "yarn strings",
    "whiteboard yarn",

    # Coordinate & Port Leakage
    "port 3025",
    "port 3033",
    "port 8088",
    "port 8095",
    "port 8008",
    "clio metal",
    "clio forge",
    "100.96.77.20",
    "rule zero",
    "invariant 26",
    "invariant 38",

    # Bracket Badges
    "[dual-runner]",
    "[l1 reflex metal]",
    "[wan rest]",
    "[posix symlink mesh]",
    "[active failover]",

    # Invariant 1.9 Outbound Banned Phrases
    "bare metal",
    "bare-metal",
    "on metal",
    "human retinas",
    "living canvas",
    "retinal slow-mo",

    # Historical AI Marketing Slop
    "bare metal forge",
    "local appliance core",
    "quantum data nexus",
    "hyper-scale engine",
    "frictionless pipeline",
    "sovereign data vault",
    "seamlessly integrate",
    "seamlessly integrates",
    "unlock the power",
    "harness the potential",
    "bulletproof architecture",
    "in today's rapidly evolving",
    "a testament to",
    "direct partner ingress",
    "direct partner channel",
    "rapid problem ingress",
    "council takedown",
    "consult the council",
    "consult council",
    "consult sovereign council",
    "before dinner",
    "wishing well",
    "make a wish",
    "1 troy oz",
    "ingress problem statement",
    "ingress confirmed",
    "supercharge",
    "revolutionary synergies",
    "energy diligence",
    "direct diligence",
    "secure vault",
    "entity attested",
    "entity field",
    "robotic entity",
    "model-s",
    "model s",
    "turnkey edge appliance",
    "compute appliance",
    "domestic compute appliance",
    "household facility lease",
]

class GandalfLexicalTrap:
    def __init__(self, phrases):
        self.phrases = phrases
        self.use_ahocorasick = False
        try:
            import ahocorasick
            self.automaton = ahocorasick.Automaton()
            for idx, phrase in enumerate(phrases):
                self.automaton.add_word(phrase, (idx, phrase))
            self.automaton.make_automaton()
            self.use_ahocorasick = True
        except ImportError:
            pass

    def scan(self, text: str) -> tuple[bool, str | None]:
        text_lower = text.lower()
        if self.use_ahocorasick:
            for end_index, (idx, original_phrase) in self.automaton.iter(text_lower):
                return False, original_phrase
            return True, None
        else:
            for phrase in self.phrases:
                if phrase in text_lower:
                    return False, phrase
            return True, None

def scan_target(target: Path, trap: GandalfLexicalTrap) -> list[tuple[str, int, str]]:
    violations = []
    valid_exts = {".html", ".tsx", ".ts", ".jsx", ".js", ".json"}
    ignore_dirs = {"node_modules", "dist", ".git", ".wrangler", ".venv", "__pycache__"}

    if target.is_file():
        if target.suffix in valid_exts or not target.suffix:
            try:
                lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
                for line_no, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("#"):
                        continue
                    is_clean, matched_slop = trap.scan(line)
                    if not is_clean:
                        violations.append((str(target), line_no, matched_slop))
            except Exception:
                pass
        return violations

    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            p = Path(root) / f
            if p.suffix in valid_exts:
                try:
                    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
                    for line_no, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("#"):
                            continue
                        is_clean, matched_slop = trap.scan(line)
                        if not is_clean:
                            try:
                                rel_path = str(p.relative_to(target))
                            except ValueError:
                                rel_path = str(p)
                            violations.append((rel_path, line_no, matched_slop))
                except Exception:
                    continue
    return violations

def main():
    enable_semantic = False
    args = list(sys.argv[1:])
    if "--semantic" in args:
        enable_semantic = True
        args.remove("--semantic")

    trap = GandalfLexicalTrap(SLOP_PHRASES)

    if args:
        scan_targets = [Path(arg).resolve() for arg in args]
    else:
        root = Path(__file__).resolve().parent.parent
        scan_targets = [
            root / "apps" / "cmdb_studio" / "src",
            root / "apps" / "faas" / "src",
            root / "frontend",
            root / "dossiers" / "05_StackLabs_Internal" / "src"
        ]

    all_violations = []
    for target in scan_targets:
        if target.exists():
            all_violations.extend(scan_target(target, trap))

    if all_violations:
        print("\033[91m\033[1m" + "=" * 80)
        print("🧙‍♂️ [GANDALF ANTI-SLOP GATE] YOU SHALL NOT PASS!")
        print("=" * 80 + "\033[0m")
        for file_path, line_no, slop in all_violations:
            print(f" ❌ \033[93m{file_path}:{line_no}\033[0m -> \033[91m'{slop}'\033[0m")
        print("\n\033[91mBuild blocked by Sovereign Lexical Circuit Breaker (Invariant 38).\033[0m\n")
        sys.exit(1)
    else:
        print("\033[92m✔ [GANDALF GATE] PASSED: Zero forbidden metaphors or AI slop phrases detected.\033[0m")

    if enable_semantic:
        import subprocess
        semantic_gate = Path(__file__).parent / "gandalf_semantic_gate.py"
        py_bin = sys.executable or "/home/james/stacklabs/.venv/bin/python3"
        for target in scan_targets:
            if target.exists():
                res = subprocess.run([py_bin, str(semantic_gate), str(target)])
                if res.returncode != 0:
                    sys.exit(res.returncode)

    sys.exit(0)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
de_hype_terminology.py
StackLabs Sovereign OS / Clio Forge

Executes codebase-wide audit and deterministic string substitution
to purge gratuitous/cosmetic uses of 'bare metal' and 'bare-metal'
with precise systems engineering terminology.
"""

import sys
import os
import re
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs")

# Scopes to scan
TARGET_DIRS = [
    BASE_DIR / "dossiers/05_StackLabs_Internal",
    BASE_DIR / "scripts",
    BASE_DIR / "docs",
    BASE_DIR / "dossiers/01_Pawel_Rudnicki_Horizon",
    BASE_DIR / "dossiers/04_ArkleVet",
    BASE_DIR / "dossiers/06_The_Bare_Metal_Blueprint",
    BASE_DIR / "dossiers/XX_Gyroscope_as_a_Service",
]

# Files explicitly exempt from mutation
EXCLUDED_FILES = {
    BASE_DIR / "scripts/gandalf_copy_gate.py",  # Slop trap definitions
    BASE_DIR / "scripts/de_hype_terminology.py",
}

# Directories to skip
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".tempmediaStorage",
    "archive",
    "walkthroughs",
}

# Ordered replacement tuples (most specific to least specific)
REPLACEMENTS = [
    # 1. 05_StackLabs_Internal exact strings
    ("STACKLABS // BARE METAL", "STACKLABS // DEDICATED PLATFORM"),
    ("BARE METAL ARCHITECTURE", "DEDICATED ARCHITECTURE"),
    ("CLIO BARE-METAL PULSE", "CLIO HARDWARE PULSE"),
    ('"tag": "Bare-Metal Silicon"', '"tag": "AMD Zen 4 APU"'),
    ("Deterministic Bare-Metal Interlock", "Deterministic Hardware Interlock"),
    ("deterministic bare-metal interlock", "deterministic hardware interlock"),
    ("Deterministic Bare-Metal Architecture", "Deterministic Hardware Architecture"),
    ("Bare-Metal Architecture Overview", "Dedicated Architecture Overview"),
    ("BARE-METAL EMPIRICAL BENCHMARKS", "DEDICATED HARDWARE EMPIRICAL BENCHMARKS"),
    ("Dedicated 35W Bare-Metal Silicon", "Dedicated 35W AMD Zen 4 APU"),
    ("35W Bare-Metal Node", "35W Dedicated Node"),
    ("FIG. 1 Bare-Metal Node", "FIG. 1 StackLabs Dedicated Node"),
    ("Bare-Metal Compute Node", "StackLabs Dedicated Node"),
    ("bare-metal compute node", "StackLabs Dedicated Node"),
    ("BARE-METAL COMPUTE NODE", "STACKLABS DEDICATED NODE"),
    ("BARE-METAL NODE", "STACKLABS DEDICATED NODE"),
    ("Commodity Bare Metal vs Hyperscale", "Commodity x86-64 Hardware vs Hyperscale"),
    ("Architecture: x86 Bare-Metal", "Architecture: x86-64 Linux (AMD Zen 4)"),
    ("operating on air-gapped bare metal", "operating on dedicated local hardware"),
    ("air-gapped bare metal", "dedicated local hardware"),
    ("local bare-metal silicon", "dedicated local silicon"),
    ("distributed bare-metal compute nodes", "distributed dedicated compute nodes"),
    ("Distributed bare-metal compute nodes", "Distributed dedicated compute nodes"),
    ("bare-metal edge silicon", "dedicated AMD Zen 4 APU silicon"),
    ("Bare-metal edge silicon", "Dedicated AMD Zen 4 APU silicon"),
    ("</i> BARE-METAL", "</i> DEDICATED HARDWARE"),
    
    # 2. Runtimes & OS
    ("offline-first bare-metal software runtimes", "offline-first POSIX-native software runtimes"),
    ("offline-first bare-metal nodes", "offline-first StackLabs Nodes"),
    ("bare-metal software runtimes", "POSIX-native software runtimes"),
    ("Bare-Metal Software Runtimes", "POSIX-Native Software Runtimes"),
    ("bare-metal software", "POSIX-native software"),
    ("Bare-Metal Software", "POSIX-Native Software"),
    ("bare-metal runtime", "POSIX-native runtime"),
    ("Bare-Metal Runtime", "POSIX-Native Runtime"),
    ("bare-metal Linux logging", "POSIX Linux logging"),
    ("bare-metal Linux", "dedicated Linux environment"),
    ("bare metal Linux", "dedicated Linux environment"),
    ("bare-metal Python .venv", "dedicated Python .venv"),
    ("bare-metal operating system", "lean Linux runtime"),
    ("bare-metal gate", "deterministic hardware gate"),
    ("Bare-Metal Gate", "Deterministic Hardware Gate"),
    ("The Bare-Metal Invariant", "The Hardware Invariant"),
    ("the Bare-Metal Invariant", "the Hardware Invariant"),
    ("bare-metal invariant", "hardware invariant"),
    ("Bare-Metal Invariants", "Hardware Invariants"),
    
    # 3. Hardware & Silicon
    ("bare-metal commodity x86 hardware", "dedicated commodity x86-64 hardware"),
    ("commodity bare-metal x86 hardware", "dedicated commodity x86-64 hardware"),
    ("commodity bare-metal x86 software runtimes", "dedicated commodity x86-64 POSIX software runtimes"),
    ("commodity bare-metal x86", "commodity x86-64 hardware"),
    ("bare-metal x86", "commodity x86-64 hardware"),
    ("bare metal x86", "commodity x86-64 hardware"),
    ("bare-metal silicon", "dedicated AMD Zen 4 APU silicon"),
    ("bare metal silicon", "dedicated AMD Zen 4 APU silicon"),
    ("Bare-Metal Silicon", "AMD Zen 4 APU"),
    ("bare-metal hardware", "dedicated local hardware"),
    ("bare metal hardware", "dedicated local hardware"),
    ("Bare-Metal Hardware", "Dedicated Local Hardware"),
    ("Bare Metal Hardware", "Dedicated Local Hardware"),
    ("Clio Bare-Metal NVMe", "Clio PCIe 4.0 NVMe"),
    ("BARE METAL — CLIO", "NODE CLIO — AMD ZEN 4"),
    ("BARE-METAL — CLIO", "NODE CLIO — AMD ZEN 4"),
    ("CLIO BARE-METAL", "CLIO DEDICATED APPLIANCE"),
    ("CLIO BARE METAL", "CLIO DEDICATED APPLIANCE"),
    
    # 4. Storage & Execution
    ("sub-millisecond execution on bare metal", "sub-millisecond execution on dedicated local hardware"),
    ("sub-millisecond execution on bare-metal", "sub-millisecond execution on dedicated local hardware"),
    ("verified on Clio bare metal", "verified on dedicated Clio hardware"),
    ("verified on bare metal", "verified on dedicated local hardware"),
    ("VERIFIED ON BARE METAL", "VERIFIED ON DEDICATED HARDWARE"),
    ("PASSED successfully on bare metal", "PASSED successfully on dedicated local hardware"),
    ("execution on bare metal", "local execution"),
    ("execution on bare-metal", "local execution"),
    ("executing on bare metal", "executing on dedicated local hardware"),
    ("executing on bare-metal", "executing on dedicated local hardware"),
    ("bare-metal execution", "local execution"),
    ("bare metal execution", "local execution"),
    ("Bare-Metal Execution", "Local Execution"),
    ("Bare Metal Execution", "Local Execution"),
    ("bare-metal ingestion", "on-premises ingestion"),
    ("bare metal ingestion", "on-premises ingestion"),
    ("local bare metal storage", "local NVMe storage"),
    ("local bare-metal storage", "local NVMe storage"),
    ("bare metal storage", "dedicated local NVMe storage"),
    ("bare-metal storage", "dedicated local NVMe storage"),
    ("bare-metal fallback", "dedicated local fallback"),
    ("bare metal fallback", "dedicated local fallback"),
    ("bare-metal pipeline", "dedicated local pipeline"),
    ("Bare-Metal Pipeline", "Dedicated Local Pipeline"),
    
    # 5. Generic Platform
    ("bare-metal platform", "StackLabs Dedicated Platform"),
    ("bare metal platform", "StackLabs Dedicated Platform"),
    ("Bare-Metal Platform", "StackLabs Dedicated Platform"),
    ("Bare Metal Platform", "StackLabs Dedicated Platform"),
    ("Small Ball on Bare Metal", "Small Ball on Dedicated Hardware"),
    ("Small-Ball on Bare Metal", "Small-Ball on Dedicated Hardware"),
    ("small ball on bare metal", "small ball on dedicated hardware"),
    ("small-ball on bare metal", "small-ball on dedicated hardware"),
    ("bare-metal architecture", "dedicated local architecture"),
    ("Bare-Metal Architecture", "Dedicated Local Architecture"),
    ("bare-metal appliances", "dedicated local appliances"),
    ("bare-metal appliance", "dedicated local appliance"),
    ("Bare-Metal Appliance", "Dedicated Local Appliance"),
    ("bare-metal nodes", "StackLabs Nodes"),
    ("bare metal nodes", "StackLabs Nodes"),
    ("Bare-Metal Nodes", "StackLabs Nodes"),
    ("bare-metal node", "StackLabs Node"),
    ("bare metal node", "StackLabs Node"),
    ("Bare-Metal Node", "StackLabs Node"),
    ("bare-metal mesh", "dedicated Tailscale node mesh"),
    ("bare metal mesh", "dedicated Tailscale node mesh"),
    ("bare-metal fleet", "dedicated appliance fleet"),
    ("bare metal fleet", "dedicated appliance fleet"),
    ("bare-metal systems", "dedicated systems"),
    ("Bare-Metal Systems", "Dedicated Systems"),
    ("bare metal systems", "dedicated systems"),
    ("Bare Metal Systems", "Dedicated Systems"),
    ("on bare metal", "on dedicated local hardware"),
    ("on bare-metal", "on dedicated local hardware"),
    ("On bare metal", "On dedicated local hardware"),
    ("On bare-metal", "On dedicated local hardware"),
]

def should_process(file_path: Path) -> bool:
    if file_path in EXCLUDED_FILES:
        return False
    if any(part in file_path.parts for part in EXCLUDED_DIRS):
        return False
    if file_path.suffix in [
        ".png", ".jpg", ".jpeg", ".ico", ".db", ".sqlite", ".sqlite3",
        ".pyc", ".bak", ".log", ".gif", ".pdf", ".m4a", ".mp4", ".zip", ".gz"
    ]:
        return False
    return True

def apply_de_hyping():
    print("[*] Starting De-Hyping Codebase Audit & Terminology Purge...")
    modified_files = []
    total_replacements = 0

    for target_dir in TARGET_DIRS:
        if not target_dir.exists():
            continue
        for file_path in target_dir.rglob("*"):
            if not file_path.is_file() or not should_process(file_path):
                continue
            
            try:
                original_text = file_path.read_text(encoding="utf-8")
            except Exception as e:
                continue

            updated_text = original_text
            file_replacement_count = 0

            # Preserve Founder Manifesto direct quote in public/index.html & test
            manifesto_marker = "99% of developers today have never touched bare metal"
            has_manifesto = manifesto_marker in original_text
            
            for target_pattern, replacement in REPLACEMENTS:
                if target_pattern in updated_text:
                    # If this file has the manifesto quote, protect it
                    if has_manifesto and ("bare metal" in target_pattern or "bare-metal" in target_pattern):
                        # Protect the exact quote with a sentinel token
                        sentinel = "__MANIFESTO_QUOTE_SENTINEL__"
                        updated_text = updated_text.replace(manifesto_marker, sentinel)
                        count = updated_text.count(target_pattern)
                        updated_text = updated_text.replace(target_pattern, replacement)
                        updated_text = updated_text.replace(sentinel, manifesto_marker)
                        file_replacement_count += count
                    else:
                        count = updated_text.count(target_pattern)
                        updated_text = updated_text.replace(target_pattern, replacement)
                        file_replacement_count += count

            if file_replacement_count > 0:
                file_path.write_text(updated_text, encoding="utf-8")
                modified_files.append((str(file_path.relative_to(BASE_DIR)), file_replacement_count))
                total_replacements += file_replacement_count

    print(f"\n[+] De-Hyping Complete: {len(modified_files)} files modified, {total_replacements} replacements made.")
    for fpath, cnt in sorted(modified_files):
        print(f"  - {fpath} ({cnt} replacements)")

    # Also update CJS test verifiers in 05_StackLabs_Internal if needed
    p1_cjs = BASE_DIR / "dossiers/05_StackLabs_Internal/verify_wo0010986_pillar01.cjs"
    if p1_cjs.exists():
        c = p1_cjs.read_text()
        if "Deterministic Bare-Metal Interlock" in c:
            p1_cjs.write_text(c.replace("Deterministic Bare-Metal Interlock", "Deterministic Hardware Interlock"))
            print("[+] Updated verify_wo0010986_pillar01.cjs assertion to 'Deterministic Hardware Interlock'")

    bench_cjs = BASE_DIR / "dossiers/05_StackLabs_Internal/scripts/verify_benchmarks.cjs"
    if bench_cjs.exists():
        c = bench_cjs.read_text()
        if "bare-metal architecture" in c:
            bench_cjs.write_text(c.replace("bare-metal architecture", "dedicated local architecture"))
            print("[+] Updated verify_benchmarks.cjs assertion to 'dedicated local architecture'")

    beacon_cjs = BASE_DIR / "dossiers/05_StackLabs_Internal/verify_wo0010925_silicon_beacon.cjs"
    if beacon_cjs.exists():
        c = beacon_cjs.read_text()
        if "CLIO BARE-METAL PULSE" in c:
            beacon_cjs.write_text(c.replace("CLIO BARE-METAL PULSE", "CLIO HARDWARE PULSE"))
            print("[+] Updated verify_wo0010925_silicon_beacon.cjs assertion to 'CLIO HARDWARE PULSE'")

if __name__ == "__main__":
    apply_de_hyping()

#!/usr/bin/env python3
"""
Sovereign OS: Ground-Truth Documentation Authenticity Triage
Path: /home/james/stacklabs/scripts/audit_docs_authenticity.py

Scans all active documentation, walkthroughs, implementation plans, and specs
for ungrounded AI hallucinations, sci-fi tropes, fake hardware specs, and corporate fiction.
"""

import os
import re
import json
import glob
from pathlib import Path
from collections import defaultdict

TARGET_DIRS = [
    "/home/james/sovereign_inbox/walkthroughs",
    "/home/james/sovereign_inbox/implementation_plans",
    "/home/james/stacklabs/dna/docs",
    "/home/james/sovereign_inbox/reports",
    "/home/james/sovereign_inbox/executed",
    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/docs",
    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/walkthroughs",
    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/implementation_plans",
    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/patents",
]

# Patterns for ungrounded AI fiction / cosplay / hallucinated mechanics
SUSPICIOUS_PATTERNS = {
    "TECHNOBABBLE_PATENT_TROPES": [
        r"\bpromo chainsaw\b",
        r"\bregex chainsaw\b",
        r"\bcosmic sieve\b",
        r"\bstateless arithmetic logic units?\b",
        r"\blatency arbitrage\b",
        r"\bcpu-register regex\b",
        r"\bpromotional entropy\b",
    ],
    "CONSPIRACY_OR_SYNDICATE": [
        r"\bsecret syndicate\b",
        r"\btake down.*cloud providers\b",
        r"\bshadow protocol\b",
        r"\bblack-hat.*cabal\b",
        r"\bclandestine operative\b",
        r"\bglobal espionage\b",
    ],
    "FAKE_HARDWARE_OR_PHYSICS": [
        r"\b5\.1v\b",
        r"\bvoltage sag\b",
        r"\bquantum teleport\b",
        r"\bquantum.*dwell\b",
        r"\bphysical silicon damage\b",
    ],
    "CYPHER_OR_RAP_TOKEN_FICTION": [
        r"\baabb (rhym|format|scheme)\b",
        r"\brap battle escape\b",
        r"\bcipher cell discipline\b",
        r"\bconstrain token usage by forcing\b",
        r"\b8-mile penalty box\b",
    ],
    "FABRICATED_VALUATIONS_OR_MA": [
        r"\b78\.5m\b",
        r"\bacquisition suitors?\b",
        r"\bpatent valuation dossier\b",
        r"\bbuyout bid\b",
        r"\bterm sheet.*(aethelgard|vanguard tactical|omnihealth)\b",
    ],
    "BANNED_CYBERPUNK_TROPES": [
        r"\bCOGNITIVE LOCK\b",
        r"\b1000% SECURE\b",
        r"\bTACTILE RELAY ACTIVE\b",
        r"\bNEURAL MATRIX OVERRIDE\b",
    ],
    "PAWEL_SYNDICATE_FICTION": [
        r"\b(pawel|rudnicki|rud ranch).*(syndicate|cabal|conspiracy|espionage|illicit)\b",
    ]
}

def scan_file(filepath):
    hits = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        for line_idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            for category, pattern_list in SUSPICIOUS_PATTERNS.items():
                for pat in pattern_list:
                    if re.search(pat, line_str, re.IGNORECASE):
                        hits.append({
                            "category": category,
                            "pattern": pat,
                            "line_num": line_idx,
                            "snippet": line_str[:160]
                        })
    except Exception as e:
        pass
    return hits

def run_triage():
    results = defaultdict(list)
    total_scanned = 0
    
    seen_files = set()
    for d in TARGET_DIRS:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            # Skip already quarantined directories
            if "quarantine" in root.lower() or "quarantine_ai_fiction" in root.lower():
                continue
            for fname in files:
                if fname.endswith((".md", ".txt", ".json", ".sql", ".rst")):
                    fpath = os.path.join(root, fname)
                    real_path = os.path.realpath(fpath)
                    if real_path in seen_files:
                        continue
                    seen_files.add(real_path)
                    total_scanned += 1
                    
                    hits = scan_file(real_path)
                    if hits:
                        results[real_path] = hits

    print(f"Total Scanned Files: {total_scanned}")
    print(f"Total Flagged Files: {len(results)}\n")
    
    report_data = []
    for fpath, hits in sorted(results.items()):
        categories = list(set(h["category"] for h in hits))
        print(f"🚨 FLAGGED: {fpath}")
        print(f"   Categories: {', '.join(categories)}")
        for h in hits[:3]:  # Print first 3 matches
            print(f"   Line {h['line_num']} [{h['category']}]: \"{h['snippet']}\"")
        if len(hits) > 3:
            print(f"   ... and {len(hits) - 3} more match(es)")
        print("-" * 80)
        report_data.append({
            "file": fpath,
            "categories": categories,
            "hit_count": len(hits),
            "hits": hits
        })
        
    out_json = "/home/james/sovereign_inbox/reports/DOCS_AUTHENTICITY_HIT_LIST.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nSaved structured audit JSON to: {out_json}")

if __name__ == "__main__":
    run_triage()

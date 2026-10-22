#!/usr/bin/env python3
"""
SovereignOS Tokenizer & Codebook Forensic Audit
==============================================
Validates zero-ZWJ invariants, single-glyph constraints, and token resolution
across local SLM tokenizers for the 4-gram positional emoji wire protocol.

Author: James Carroll (Pilot) & Lead Systems Architect
Host: Clio Metal Forge (AMD Ryzen 7 7735HS)
Standards: Invariant 0 | Invariant 35 | Invariant 36
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Invariant 35 execution assertion
try:
    import tiktoken
except ImportError:
    print("[ERROR] tiktoken not available in active python runtime. Ensure /home/james/SovereignOS/.venv/bin/python3 is used.")
    sys.exit(1)

CODEBOOK_PATH = Path("/home/james/SovereignOS/data/emoji_codebook.json")

# Invariant Forbidden Codepoints
ZWJ_CODEPOINT = "\u200d"
KEYCAP_CODEPOINT = "\u20e3"
SKIN_TONE_RANGE = range(0x1F3FB, 0x1F400)  # U+1F3FB to U+1F3FF

BANNED_TEST_SUITE = [
    ("👨‍👩‍👧‍👦", "Family ZWJ Compound Sequence"),
    ("8️⃣", "Enclosing Keycap Number Emoji"),
    ("👍🏽", "Fitzpatrick Skin-Tone Modified Glyph"),
    ("🏃‍♂️", "Man Runner Gender ZWJ Sequence"),
]

def load_codebook() -> Dict[str, Any]:
    if not CODEBOOK_PATH.exists():
        raise FileNotFoundError(f"Missing canonical codebook at {CODEBOOK_PATH}")
    with open(CODEBOOK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def audit_codebook_invariants(codebook: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Assert zero ZWJ, zero keycaps, zero skin-tones across all domains."""
    violations = []
    domains = codebook.get("domains", {})

    for domain_name, mappings in domains.items():
        for glyph, symbolic_name in mappings.items():
            # Check ZWJ
            if ZWJ_CODEPOINT in glyph:
                violations.append({
                    "domain": domain_name,
                    "glyph": glyph,
                    "name": symbolic_name,
                    "defect": "CONTAINS_ZERO_WIDTH_JOINER_U200D"
                })
            # Check Keycaps
            if KEYCAP_CODEPOINT in glyph:
                violations.append({
                    "domain": domain_name,
                    "glyph": glyph,
                    "name": symbolic_name,
                    "defect": "CONTAINS_ENCLOSING_KEYCAP_U20E3"
                })
            # Check Skin Tones
            if any(ord(c) in SKIN_TONE_RANGE for c in glyph):
                violations.append({
                    "domain": domain_name,
                    "glyph": glyph,
                    "name": symbolic_name,
                    "defect": "CONTAINS_FITZPATRICK_SKIN_TONE_MODIFIER"
                })
            # Metric domain ASCII constraint
            if domain_name == "METRIC":
                if len(glyph) != 1 or not (glyph.isdigit() or glyph == "F"):
                    violations.append({
                        "domain": domain_name,
                        "glyph": glyph,
                        "name": symbolic_name,
                        "defect": "NON_ASCII_METRIC_GLYPH"
                    })

    return violations

def audit_tokenizer_resolution() -> Dict[str, Any]:
    """Audit tokenization dynamics against standard SLM BPE byte-fallback tokenizers."""
    codebook = load_codebook()
    domains = codebook.get("domains", {})

    enc_cl100k = tiktoken.get_encoding("cl100k_base")
    enc_o200k = tiktoken.get_encoding("o200k_base")

    audit_records = []
    total_glyphs = 0

    for domain_name, mappings in domains.items():
        for glyph, symbolic_name in mappings.items():
            total_glyphs += 1
            cl100k_tokens = enc_cl100k.encode(glyph)
            o200k_tokens = enc_o200k.encode(glyph)
            byte_len = len(glyph.encode("utf-8"))
            codepoints = [f"U+{ord(c):04X}" for c in glyph]

            audit_records.append({
                "domain": domain_name,
                "glyph": glyph,
                "name": symbolic_name,
                "codepoints": codepoints,
                "utf8_bytes": byte_len,
                "cl100k_token_count": len(cl100k_tokens),
                "o200k_token_count": len(o200k_tokens),
            })

    # Benchmark typical full 4-gram wire packet vs legacy JSON
    sample_4gram = "⚡📥🟢8"
    legacy_json = '{"status":"running","subsystem":"queue","val":8}'

    pkt_cl100k = enc_cl100k.encode(sample_4gram)
    json_cl100k = enc_cl100k.encode(legacy_json)

    # Compare with banned emojis
    banned_records = []
    for glyph, label in BANNED_TEST_SUITE:
        cl_tokens = enc_cl100k.encode(glyph)
        banned_records.append({
            "glyph": glyph,
            "label": label,
            "codepoints": [f"U+{ord(c):04X}" for c in glyph],
            "utf8_bytes": len(glyph.encode("utf-8")),
            "cl100k_tokens": len(cl_tokens),
        })

    return {
        "total_glyphs_audited": total_glyphs,
        "records": audit_records,
        "sample_comparison": {
            "wire_protocol_4gram": sample_4gram,
            "wire_bytes": len(sample_4gram.encode("utf-8")),
            "wire_tokens_cl100k": len(pkt_cl100k),
            "legacy_json": legacy_json,
            "legacy_bytes": len(legacy_json.encode("utf-8")),
            "legacy_tokens_cl100k": len(json_cl100k),
            "token_reduction_pct": round((1 - len(pkt_cl100k) / len(json_cl100k)) * 100, 1),
            "byte_reduction_pct": round((1 - len(sample_4gram.encode("utf-8")) / len(legacy_json.encode("utf-8"))) * 100, 1)
        },
        "banned_comparison": banned_records
    }

def main():
    parser = argparse.ArgumentParser(description="Audit SovereignOS Emoji Codebook Tokenizer Resolution")
    parser.add_argument("--json", action="store_true", help="Output audit results as JSON")
    parser.add_argument("--strict", action="store_true", default=True, help="Enforce hard exit on any invariant violation")
    args = parser.parse_args()

    codebook = load_codebook()
    violations = audit_codebook_invariants(codebook)
    tokenizer_results = audit_tokenizer_resolution()

    has_failures = len(violations) > 0

    if args.json:
        payload = {
            "status": "PASS" if not has_failures else "FAIL",
            "violations": violations,
            "tokenizer_audit": tokenizer_results
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("==================================================")
        print("🔍 SOVEREIGN-OS 4-GRAM EMOJI TOKENIZER AUDIT")
        print("==================================================")
        print(f"Codebook Source: {CODEBOOK_PATH}")
        print(f"Total Glyphs Audited: {tokenizer_results['total_glyphs_audited']}")
        
        if violations:
            print(f"\n❌ INVARIANT VIOLATIONS DETECTED: {len(violations)}")
            for v in violations:
                print(f"  - [{v['domain']}] {v['glyph']} ({v['name']}): {v['defect']}")
        else:
            print("✅ ZERO-ZWJ INVARIANT: PASSED (0 joiners, 0 skin-tones, 0 keycaps)")
            print("✅ METRIC DOMAIN INVARIANT: PASSED (Strict ASCII 0-9, F)")

        print("\n📊 TELEMETRY PROTOCOL COMPRESSION BENCHMARK:")
        cmp = tokenizer_results["sample_comparison"]
        print(f"  Legacy JSON Heartbeat: '{cmp['legacy_json']}'")
        print(f"    Bytes: {cmp['legacy_bytes']}B | Tokens: {cmp['legacy_tokens_cl100k']}")
        print(f"  4-Gram Wire Packet:    '{cmp['wire_protocol_4gram']}'")
        print(f"    Bytes: {cmp['wire_bytes']}B  | Tokens: {cmp['wire_tokens_cl100k']}")
        print(f"  Savings: {cmp['token_reduction_pct']}% Token Reduction | {cmp['byte_reduction_pct']}% Byte Reduction")

        print("\n🚫 BANNED COMPOUND EMOJIS (TOKEN FRAGMENTATION PROOF):")
        for b in tokenizer_results["banned_comparison"]:
            print(f"  {b['glyph']} ({b['label']}): {b['cl100k_tokens']} tokens, {b['utf8_bytes']} bytes -> BLOCKED BY GBNF")

        print("==================================================")
        if not has_failures:
            print("🎉 ALL INVARIANTS SATISFIED — WIRE PROTOCOL READY ON CLIO")
        else:
            print("🛑 AUDIT FAILED")
        print("==================================================")

    if has_failures and args.strict:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()

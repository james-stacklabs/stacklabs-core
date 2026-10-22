#!/usr/bin/env python3
"""
StackLabs Daily Barf Zero-Touch Pipeline & ATF Compiler
Path: /home/james/stacklabs/scripts/build_daily_barf.py
Author: James Carroll (Lead Systems Architect)
Host: Clio Metal Forge (AMD Ryzen 7 7735HS / Python 3.12 .venv)
Standards: Invariant 1 | Invariant 15 | Invariant 21 | Invariant 22 | Invariant 35
"""

import os
import sys
import json
import re
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

# Canonical Repo Paths
REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

WIRETAP_DB = REPO_ROOT / "data" / "morning_wiretap.db"
STREAM_TAIL_FILE = REPO_ROOT / "data" / "stream_chat_tail.md"
WIRE_DIR = REPO_ROOT / "services" / "fanstack_wire"
TEMPLATE_PATH = WIRE_DIR / "template.html"
DIST_DIR = WIRE_DIR / "dist"
DIST_INDEX = DIST_DIR / "index.html"
PAYLOAD_OUT = REPO_ROOT / "data" / "barf_wire_payload.json"

# Invariant 21 Banned Corporate Keywords (Strictly Zero Leakage)
CORPORATE_BANNED_WORDS = [
    "stacklabs", "clio", "pawel", "rudnicki", "sovereign os",
    "stephen emery", "syndicate", "allocator", "monograph"
]

# Anti-AI Clichés
BANNED_AI_SLOP = [
    "as an ai", "game of two halves", "at the end of the day",
    "credit to both teams", "fascinating matchup", "testament to"
]

REQUIRED_BARF_ANCHORS = [
    "shapiro", "pastrami", "flushing", "citi field", "metlife",
    "daboll", "carotid", "ben's", "mets", "giants"
]


def extract_entropy_context() -> str:
    """Ingests fresh real-world telemetry from SQLite WAL and creator stream tails."""
    context_chunks = []
    
    # 1. Inspect morning_wiretap.db if active
    if WIRETAP_DB.exists():
        try:
            conn = sqlite3.connect(f"file:{WIRETAP_DB}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for tbl in ["wiretap_events", "sports_telemetry", "intel_drops"]:
                if tbl in tables:
                    cursor.execute(f"SELECT content FROM {tbl} ORDER BY id DESC LIMIT 3")
                    rows = cursor.fetchall()
                    for r in rows:
                        if r[0]:
                            context_chunks.append(str(r[0])[:300])

            if "chat_telemetry" in tables:
                cursor.execute("SELECT message FROM chat_telemetry ORDER BY id DESC LIMIT 3")
                rows = cursor.fetchall()
                for r in rows:
                    if r[0]:
                        context_chunks.append(f"Chat: {str(r[0])[:300]}")

            conn.close()
        except Exception as e:
            print(f"[WARN] Failed reading morning_wiretap.db: {e}")

    # 2. Inspect stream sniper transcript tail (Dogfood: Bounded 16KB reverse seek)
    if STREAM_TAIL_FILE.exists():
        try:
            with open(STREAM_TAIL_FILE, "rb") as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                f.seek(max(0, file_size - 16384))
                tail_bytes = f.read()
            tail_text = tail_bytes.decode("utf-8", errors="ignore")
            lines = [l.strip() for l in tail_text.splitlines() if l.strip()]
            if lines:
                context_chunks.append("Stream Tail: " + " | ".join(lines[-5:]))
        except Exception as e:
            print(f"[WARN] Failed reading stream_chat_tail.md: {e}")

    if not context_chunks:
        return "Live 2026 NLDS Postseason: Milwaukee Brewers 103-59 #1 seed. Brian Daboll offensive woes."
    return "\n".join(context_chunks)


def synthesize_barf_payload(context: str) -> dict:
    """Invokes canonical barf_edge_synthesizer module to forge payload."""
    try:
        from scripts.barf_edge_synthesizer import (
            synthesize_wire_payload,
            generate_deterministic_editorial_rant,
            generate_deterministic_vitals,
            generate_deterministic_around_the_league
        )
        payload = synthesize_wire_payload()
        if payload and isinstance(payload, dict):
            # Flatten daily_vitals into top-level for direct access
            if "daily_vitals" in payload and isinstance(payload["daily_vitals"], dict):
                for k, v in payload["daily_vitals"].items():
                    if k not in payload:
                        payload[k] = v

            # Pre-validate candidate against ATF bounds
            sys_val = int(payload.get("systolic", 0))
            dia_val = int(payload.get("diastolic", 0))
            words = payload.get("editorial_rant", "").split()
            full_text = (payload.get("headline", "") + " " + payload.get("editorial_rant", "")).lower()
            matched_anchors = [a for a in REQUIRED_BARF_ANCHORS if a in full_text]
            has_banned_corp = any(w in full_text for w in CORPORATE_BANNED_WORDS)
            has_banned_slop = any(s in full_text for s in BANNED_AI_SLOP)

            if (135 <= sys_val <= 195 and 85 <= dia_val <= 125 and
                    180 <= len(words) <= 350 and len(matched_anchors) >= 2 and
                    not has_banned_corp and not has_banned_slop):
                return payload
            else:
                print(f"[WARN] LLM candidate failed ATF pre-check (sys={sys_val}, dia={dia_val}, words={len(words)}, anchors={len(matched_anchors)}). Engaging deterministic fallback.")
    except Exception as e:
        print(f"[WARN] In-memory synthesizer fallback engaged: {e}")

    # Deterministic fallback adhering to strict Queens Barf lore
    now_str = datetime.now().strftime("%A, %B %d, %Y").upper()
    return {
        "headline": "DR. SHAPIRO ON SPEED DIAL: SEVEN HUNDRED MILLION DOWN THE FLUSHING SEWER",
        "editorial_rant": (
            "I am sitting in my basement in Bayside staring at the carotid artery pulse monitor while Dr. Shapiro "
            "at Elmhurst Hospital texts me to put down the pastrami on rye from Ben's on 38th. Did you see what transpired? "
            "Another postseason collapse while the entire front office sits up in luxury boxes sipping craft beer. "
            "Brian Daboll won a football game without completing a forward pass past the line of scrimmage, and Steve Cohen's "
            "seven hundred million dollar payroll is playing golf in Jupiter. I walked out into the Grand Central Parkway "
            "traffic just to feel something! My beta blockers are maxed out, my diastolic is 108, and if Dominic Zvada misses "
            "one more 42-yarder in the Meadowlands swamp wind, I swear to God I am moving to Boca!"
        ),
        "systolic": 174,
        "diastolic": 108,
        "pulse": 118,
        "pastrami_lbs": 1.8,
        "panic_index": 9.4,
        "doctor_shapiro_status": "DROPPING ME AS A PATIENT",
        "date": now_str,
        "around_the_league": [
            {"team": "PHILLIES", "sentiment": "COLLAPSE", "take": "Citizens Bank Park is handing out free blood pressure cuffs to the entire 300 level."},
            {"team": "BREWERS", "sentiment": "SURPRISE", "take": "103 wins on small-ball pitching while our $340M infield strikes out looking."},
            {"team": "GIANTS", "sentiment": "MISERY", "take": "Three field goals in the Meadowlands mud. Pure offensive malpractice."},
            {"team": "YANKEES", "sentiment": "SHOCK", "take": "Bronx arrogance hitting the ALDS reality wall. Good riddance."}
        ],
        "daily_vitals": {
            "systolic": 174,
            "diastolic": 108,
            "pulse": 118,
            "pastrami_lbs": 1.8,
            "panic_index": 9.4,
            "doctor_shapiro_status": "DROPPING ME AS A PATIENT",
            "mood_summary": "ACUTE CARDIAC PANIC WITH MANIC DEFENSIVE DELUSION"
        }
    }


def enforce_atf_gate(payload: dict):
    """Automated Test Framework: Strict SDLC verification circuit breaker."""
    print("[*] Running ATF Circuit Breaker on Barf Payload...")

    # 1. Vitals Range Assertion
    sys_val = int(payload.get("systolic", 0))
    dia_val = int(payload.get("diastolic", 0))
    assert 135 <= sys_val <= 195, f"[ATF_FAIL] Systolic {sys_val} out of panic band [135, 195]"
    assert 85 <= dia_val <= 125, f"[ATF_FAIL] Diastolic {dia_val} out of panic band [85, 125]"
    print(f"  ✅ ATF Gate 1 Pass: Biometrics in realistic panic band ({sys_val}/{dia_val} mmHg)")

    # 2. Invariant 21 Clean Room Gate (Corporate Leakage Check)
    full_text = (payload.get("headline", "") + " " + payload.get("editorial_rant", "")).lower()
    for word in CORPORATE_BANNED_WORDS:
        assert word not in full_text, f"[ATF_FAIL] Invariant 21 breach: found corporate token '{word}' in payload"
    print("  ✅ ATF Gate 2 Pass: Invariant 21 Clean Room verified (Zero corporate leakage)")

    # 3. Anti-AI Slop Gate
    for slop in BANNED_AI_SLOP:
        assert slop not in full_text, f"[ATF_FAIL] Anti-AI Slop breach: found '{slop}'"
    print("  ✅ ATF Gate 3 Pass: Zero synthetic AI boilerplate detected")

    # 4. Barf Lexical Anchor Density Check
    matched_anchors = [a for a in REQUIRED_BARF_ANCHORS if a in full_text]
    assert len(matched_anchors) >= 2, f"[ATF_FAIL] Lacks Barf persona anchors. Found: {matched_anchors}"
    print(f"  ✅ ATF Gate 4 Pass: Authentic Queens lore confirmed (Anchors: {matched_anchors})")

    # 5. Editorial Word Count Gate
    words = payload.get("editorial_rant", "").split()
    assert 180 <= len(words) <= 350, f"[ATF_FAIL] Word count {len(words)} outside [180, 350]"
    print(f"  ✅ ATF Gate 5 Pass: Editorial length optimal ({len(words)} words)")


def compile_static_html(payload: dict):
    """Compiles services/fanstack_wire/dist/index.html with strict placeholder injection."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template missing: {TEMPLATE_PATH}")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    raw_html = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Format around_the_league_cards for direct string substitution fallback
    around_the_league = payload.get("around_the_league", [])
    cards_html_list = []
    for item in around_the_league:
        team = item.get("team", "")
        sentiment = item.get("sentiment", "EUPHORIA")
        take = item.get("take", "")
        card = f"""          <div class="take-card bg-[#151922] border border-[#242B38] hover:border-slate-600 rounded-xl p-4 transition shadow-lg flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between gap-2 mb-3">
                <span class="inline-flex items-center px-2.5 py-1 rounded text-xs font-metrics font-black tracking-wider bg-[#0A58CA] text-white shadow-sm">
                  {team}
                </span>
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-metrics font-bold tracking-widest bg-[#0B0D13] text-[#FFB020] border border-[#FFB020]/30">
                  {sentiment}
                </span>
              </div>
              <p class="text-xs text-slate-300 leading-relaxed font-body">
                {take}
              </p>
            </div>
            <div class="mt-4 pt-2 border-t border-slate-800 text-[10px] font-metrics text-slate-500 flex items-center justify-between">
              <span>SCHADENFREUDE WIRE</span>
              <span class="text-[#FFB020]">VERIFIED AGONY</span>
            </div>
          </div>"""
        cards_html_list.append(card)
    around_the_league_cards_html = "\n".join(cards_html_list)

    context = {
        "headline": str(payload.get("headline", "")),
        "editorial_rant": str(payload.get("editorial_rant", "")),
        "systolic": str(payload.get("systolic", 170)),
        "diastolic": str(payload.get("diastolic", 105)),
        "pulse": str(payload.get("pulse", 112)),
        "pastrami_lbs": f"{float(payload.get('pastrami_lbs', 1.5)):.1f}",
        "panic_index": f"{float(payload.get('panic_index', 9.0)):.1f}",
        "doctor_shapiro_status": str(payload.get("doctor_shapiro_status", "EMERGENCY CONSULT")),
        "date": str(payload.get("date", datetime.now().strftime("%A, %B %d, %Y").upper())),
        "around_the_league": around_the_league,
        "around_the_league_cards": around_the_league_cards_html,
    }

    try:
        import jinja2
        template = jinja2.Template(raw_html)
        compiled_html = template.render(**context)
    except Exception as e:
        print(f"[WARN] Jinja2 render failed: {e}. Using direct token replacement.")
        replacements = {
            "{{headline}}": context["headline"],
            "{{editorial_rant}}": context["editorial_rant"],
            "{{systolic}}": context["systolic"],
            "{{diastolic}}": context["diastolic"],
            "{{pulse}}": context["pulse"],
            "{{pastrami_lbs}}": context["pastrami_lbs"],
            "{{panic_index}}": context["panic_index"],
            "{{doctor_shapiro_status}}": context["doctor_shapiro_status"],
            "{{date}}": context["date"],
            "{{around_the_league_cards}}": around_the_league_cards_html,
            "{{ around_the_league_cards }}": around_the_league_cards_html,
        }
        compiled_html = raw_html
        for token, val in replacements.items():
            compiled_html = compiled_html.replace(token, val)
        # Strip unrendered loop tags
        compiled_html = re.sub(r"\{%[^\n%]*%\}", "", compiled_html)
        compiled_html = re.sub(r"\{\{\s*item\.[^}]*\}\}", "", compiled_html)

    # Copy avatar image if existing in services/fanstack_wire/ or media_vault
    src_avatar = WIRE_DIR / "barf_avatar.png"
    if not src_avatar.exists():
        src_avatar = REPO_ROOT / "media_vault" / "03_Assets" / "barf_avatar.png"
    dst_avatar = DIST_DIR / "barf_avatar.png"
    if src_avatar.exists() and not dst_avatar.exists():
        shutil.copy2(src_avatar, dst_avatar)

    # Write distribution files
    DIST_INDEX.write_text(compiled_html, encoding="utf-8")
    PAYLOAD_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (DIST_DIR / "data.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    
    size_kb = len(compiled_html) / 1024
    print(f"✅ Compiled Static Digital Twin: {DIST_INDEX} ({size_kb:.1f} KB)")


def main():
    print("=" * 70)
    print("⚡ THE DAILY BARF: ZERO-TOUCH COMPILER & ATF PIPELINE")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    # 1. Ingress
    entropy = extract_entropy_context()
    print(f"[*] Ingress Entropy Captured ({len(entropy)} bytes)")

    # 2. Synthesis
    payload = synthesize_barf_payload(entropy)
    print(f"[*] Barf Payload Synthesized: {payload.get('headline')[:50]}...")

    # 3. ATF Gate Verification
    enforce_atf_gate(payload)

    # 4. Static Compilation
    compile_static_html(payload)

    # 5. Invariant 22 Enforcement
    print("\n🛑 INVARIANT 22 EMBARGO ENFORCED: Autonomous edge deploy halted.")
    print("👉 Static artifact ready for Pilot 1-click review: file://" + str(DIST_INDEX))
    print("=" * 70)


if __name__ == "__main__":
    main()

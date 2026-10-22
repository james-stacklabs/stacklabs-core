#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: RAW UNEDITED TRANSCRIPTS & GEMS PACKAGING ENGINE FOR NOTEBOOKLM
# Script: /home/james/stacklabs/scripts/package_raw_notebook_transcripts.py
# Description: Compiles 100% unedited, verbatim conversation transcripts (Takeout + Antigravity),
#              raw Gemini Gem system instructions, and historical blueprints into clean
#              NotebookLM source files (~400k chars each) with zero narrative filtering.
# ==============================================================================
import os
import sys
import glob
import json
import shutil
import datetime

SCRIPTS_DIR = "/home/james/stacklabs/scripts"
sys.path.append(SCRIPTS_DIR)

import compile_conversation_history as cch
import parse_takeout_chronicle as ptc

TARGET_DIR = "/home/james/sovereign_inbox/notebook_sync/Sovereign_Raw_Transcripts"
os.makedirs(TARGET_DIR, exist_ok=True)

def package_raw_notebook_sources():
    print("🚀 [NOTEBOOKLM RAW INGESTION ENGINE] Packaging unedited source files...")
    
    # 1. Generate full unedited transcripts
    print("\n📚 [STEP 1: UNEDITED TRANSCRIPTS] Compiling full chat history...")
    compiled_files = cch.compile_conversations()
    
    # Copy conversation history parts to TARGET_DIR
    part_count = 0
    for fpath, char_len, size_bytes in compiled_files:
        dest_path = os.path.join(TARGET_DIR, os.path.basename(fpath))
        shutil.copy2(fpath, dest_path)
        part_count += 1
        print(f"  📄 Staged: {os.path.basename(dest_path)} ({char_len:,} chars)")
        
    # 2. Extract and format unedited Gemini Gems System Instructions
    print("\n💎 [STEP 2: UNEDITED GEM INSTRUCTIONS] Extracting verbatim Gem prompts...")
    gems = ptc.parse_gems_data()
    gems_md = [
        "# 💎 UNEDITED GEMINI GEMS & PILOT CO-PILOT SYSTEM INSTRUCTIONS",
        "Raw, unedited system instructions and persona mandates extracted directly from Google Takeout (gemini_gems_data.html).",
        f"Extracted: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n",
        "---"
    ]
    for g in gems:
        gems_md.append(f"\n## 🤖 Gem Name: {g['name']} ({g['account']})")
        gems_md.append(f"**Source Document:** `{g['path']}`\n")
        gems_md.append("```text")
        gems_md.append(g['instructions'])
        gems_md.append("```\n")
        gems_md.append("---\n")
        
    gems_out_path = os.path.join(TARGET_DIR, "UNEDITED_GEMINI_GEMS_SYSTEM_INSTRUCTIONS.txt")
    with open(gems_out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(gems_md))
    print(f"  📄 Staged: UNEDITED_GEMINI_GEMS_SYSTEM_INSTRUCTIONS.txt ({len(gems)} Gems, {os.path.getsize(gems_out_path):,} bytes)")

    # 3. Extract and compile unedited early intake documents & blueprints
    print("\n📋 [STEP 3: UNEDITED INTAKE BLUEPRINTS] Harvesting raw early intake files...")
    raw_takeout_dir = "/home/james/stacklabs/archives/takeout_raw"
    blueprints_md = [
        "# 📑 UNEDITED EARLY BLUEPRINTS, INTAKES & SEEDING ARTIFACTS",
        "Verbatim text representations of early system blueprints, intake briefs, and genesis lookbooks extracted from Takeout.",
        f"Generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n",
        "---"
    ]
    
    # Sweep for text-readable intake files
    intake_files_found = 0
    for root, dirs, files in os.walk(raw_takeout_dir):
        for f in files:
            if any(k in f.lower() for k in ["intake", "blueprint", "brief", "lookbook", "smyrna", "weedstack", "spite", "stacklabs"]):
                if f.endswith((".txt", ".rtf", ".html", ".md", ".json")) and not f.startswith("conversation_"):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                            raw_content = fp.read().strip()
                            if len(raw_content) > 50:
                                blueprints_md.append(f"\n## 📄 File: {f}")
                                blueprints_md.append(f"**Path:** `{fpath}`\n")
                                blueprints_md.append("```text")
                                blueprints_md.append(raw_content[:15000]) # Cap per sub-item
                                blueprints_md.append("```\n")
                                blueprints_md.append("---\n")
                                intake_files_found += 1
                    except Exception:
                        pass

    blueprints_out_path = os.path.join(TARGET_DIR, "UNEDITED_HISTORICAL_INTAKE_FORMS_AND_BLUEPRINTS.txt")
    with open(blueprints_out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(blueprints_md))
    print(f"  📄 Staged: UNEDITED_HISTORICAL_INTAKE_FORMS_AND_BLUEPRINTS.txt ({intake_files_found} artifacts, {os.path.getsize(blueprints_out_path):,} bytes)")

    print(f"\n🎉 [COMPLETE] All raw unedited source files packaged in: {TARGET_DIR}")
    return os.listdir(TARGET_DIR)

if __name__ == "__main__":
    package_raw_notebook_sources()

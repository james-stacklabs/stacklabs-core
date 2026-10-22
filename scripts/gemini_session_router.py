#!/usr/bin/env python3
import os
import json
import hashlib
import shutil
import re

SOURCE_DIR = "/home/james/stacklabs_uat_gwen/dna/vault/quarantine/07_Home_Directory_Spaghetti/apiary/dna/archives/llm_sessions/models/Gemini"
TARGET_BASE = "/home/james/stacklabs/dna/agents"

# Basic persona keywords to route the sessions accurately based on the chat text
PERSONA_MAP = {
    "FERRIS": ["ferris", "chindōgu", "chindogu", "plie", "fancast", "dom bloat"],
    "GWEN": ["gwen", "zora", "airlock", "notebooklm", "oracle"],
    "ANTIGRAVITY": ["antigravity", "pm", "project manager", "polaris", "master codex"],
    "APEX_CMDR": ["apex", "cmdr", "commander", "squadron"],
    "SOVEREIGN_ORACLE": ["sovereign oracle", "sqlite", "cmdb"]
}

def guess_persona(text):
    text_lower = text.lower()
    best_match = "UNSORTED"
    max_hits = 0
    
    for agent, keywords in PERSONA_MAP.items():
        hits = sum(text_lower.count(kw) for kw in keywords)
        if hits > max_hits:
            max_hits = hits
            best_match = agent
            
    return best_match

def process_files(dry_run=True):
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory {SOURCE_DIR} not found.")
        return

    files = [f for f in os.listdir(SOURCE_DIR) if os.path.isfile(os.path.join(SOURCE_DIR, f))]
    print(f"Found {len(files)} files to process in {SOURCE_DIR}")
    
    routed_counts = {}

    for file in files:
        file_path = os.path.join(SOURCE_DIR, file)
        file_content = ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file.endswith('.json'):
                    data = json.load(f)
                    file_content = json.dumps(data)
                else:
                    file_content = f.read()
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue

        # Guestimating Agent Persona
        agent = guess_persona(file_content)
        
        # UUID generation (md5 of filename to keep it deterministic)
        session_uuid = hashlib.md5(file.encode()).hexdigest()[:16]
        
        target_dir = os.path.join(TARGET_BASE, agent, "active_sessions", session_uuid)
        target_path = os.path.join(target_dir, file)
        
        routed_counts[agent] = routed_counts.get(agent, 0) + 1

        if dry_run:
            print(f"[DRY-RUN] Would route {file} -> {target_path}")
        else:
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(file_path, target_path)
            # Find associated image outputs/prompts
            # Many images are loosely named or have timestamps.
            # We skip advanced grouping for now and just sort the main markdown/json session exports.
            # Note: Non-chat/json files will just be placed by text keyword match as well.

    print("\n--- Summary ---")
    for agent, count in routed_counts.items():
        print(f"{agent}: {count} files")

if __name__ == "__main__":
    import sys
    dry_run = "--run" not in sys.argv
    if dry_run:
        print("Running in DRY-RUN mode. Use --run to execute the moves.")
    process_files(dry_run)

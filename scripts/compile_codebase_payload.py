#!/usr/bin/env python3
"""
compile_codebase_payload.py
Traverses active production folders, counts words, and splits the codebase
into multiple files that strictly stay under NotebookLM's 500,000-word limit.
"""
import os
import datetime

ROOT_DIR = "/home/james/stacklabs"
OUTPUT_DIR = "/home/james/stacklabs/dna/notebook_lm_exports"
LIMIT_WORDS = 400000 # Defensive limit to stay safely under 500,000

def get_word_count(text_lines):
    return sum(len(line.split()) for line in text_lines)

def compile_codebase():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Remove old monolith file if it exists
    old_monolith = os.path.join(OUTPUT_DIR, "SOVEREIGN_CODEBASE_MONOLITH.md")
    if os.path.exists(old_monolith):
        os.remove(old_monolith)
        print("Removed obsolete single monolith file.")

    # Remove stale codebase part files
    import glob
    for old_part in glob.glob(os.path.join(OUTPUT_DIR, "SOVEREIGN_CODEBASE_PART_*.md")):
        try:
            os.remove(old_part)
        except Exception:
            pass

    # Target directories to search
    target_dirs = [
        "01_Sovereign_Portal/src",
        "04_Sovereign_Core",
        "14_SamTracker/src",
        "15_FanStack",
        "15_FanStackCreator/src",
        "16_StackLabsLLC/src",
        "19_FanStackArena/src",
        "19_Sovereign_Sports/src",
        "20_AetherVet/src",
        "21_Wildseed_GardenStack/src",
        "24_TesseractStack/src",
        "25_CatnipWars/src",
        "25_CmdbStudio/src",
        "25_TrueCostStack/src",
        "26_MARD_Studio/src",
        "27_Sovereign_Legal/src",
        "28_MARD_TTRPG/src",
        "29_Sovereign_Sentinel/src",
        "30_HoloLink/src",
        "scripts"
    ]
    
    # Extensions to capture
    valid_exts = [".py", ".sh", ".tsx", ".ts", ".css", ".html", ".js", ".sql", ".json"]
    
    # Files to explicitly ignore
    ignore_files = {
        "package-lock.json",
        "package.json",
        "SOVEREIGN_CODEBASE_MONOLITH.md",
        "SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE.md",
        "SYNC_ANCHOR_TOKEN.txt"
    }

    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_part = 1
    current_lines = [
        f"**LAST SYNC TIME:** {timestamp_str} UTC\n",
        "# 🧬 SOVEREIGN OS / STACKLABS SOURCE CODEBASE - PART 1",
        "## CONSOLIDATED SOURCE CODE FOR NOTEBOOKLM INGESTION",
        "This document contains production scripts, configurations, and frontend structures.\n"
    ]
    current_words = get_word_count(current_lines)

    def save_current_part():
        nonlocal current_part, current_lines, current_words
        file_name = f"SOVEREIGN_CODEBASE_PART_{current_part}.md"
        out_path = os.path.join(OUTPUT_DIR, file_name)
        print(f"Writing {file_name} (Words: {current_words})...")
        with open(out_path, "w", encoding="utf-8") as out:
            out.write("\n".join(current_lines))
        current_part += 1
        current_lines = [
            f"**LAST SYNC TIME:** {timestamp_str} UTC\n",
            f"# 🧬 SOVEREIGN OS / STACKLABS SOURCE CODEBASE - PART {current_part}",
            "## CONSOLIDATED SOURCE CODE FOR NOTEBOOKLM INGESTION\n"
        ]
        current_words = get_word_count(current_lines)

    print("Beginning codebase compilation with word-limit protection...")
    for target in target_dirs:
        dir_path = os.path.join(ROOT_DIR, target)
        if not os.path.exists(dir_path):
            continue

        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in [
                "node_modules", ".git", ".venv", "venv", "__pycache__", 
                ".next", "build", "dist", "_archive", "logs", "scratch"
            ]]
            
            for file in files:
                if file in ignore_files:
                    continue
                    
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, ROOT_DIR)
                
                ext = os.path.splitext(file)[1].lower()
                if ext not in valid_exts:
                    continue
                
                if "logs/" in rel_path or "scratch/" in rel_path or "daily_" in rel_path:
                    continue
                
                # Read file content
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().strip()
                except Exception as e:
                    content = f"Error reading file: {e}"

                # Build the chunk
                file_chunk = [
                    f"\n## FILE: `{rel_path}`",
                    "```" + (ext[1:] if ext else "text"),
                    content,
                    "```",
                    "\n" + "="*80 + "\n"
                ]
                file_words = get_word_count(file_chunk)

                # Check if adding this file will push us over the defensive word limit
                if current_words + file_words > LIMIT_WORDS:
                    print(f"⚠️ Adding {rel_path} ({file_words} words) exceeds limit. Wrapping Part {current_part}.")
                    save_current_part()

                current_lines.extend(file_chunk)
                current_words += file_words

    # Save final remaining chunk
    if len(current_lines) > 2:
        save_current_part()

    print("✅ Codebase compilation and splitting completed successfully.")

if __name__ == "__main__":
    compile_codebase()

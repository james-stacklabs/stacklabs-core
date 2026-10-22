#!/usr/bin/env python3
import os
import glob
import subprocess

OUTPUT_DIR = '/home/james/stacklabs/dna/vault/barbs_birthday_lore'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Delete existing text files in output dir
for f in glob.glob(os.path.join(OUTPUT_DIR, '*.txt')):
    os.remove(f)

# Grab all the lore, new agent drops, and all artifact context
dynamic_patterns = [
    '/home/james/stacklabs/dna/agents/*/active_sessions/*/*.txt',
    '/home/james/stacklabs/dna/agents/*/active_sessions/*/*.md',
    '/home/james/stacklabs/dna/agents/SOVEREIGN_ORACLE/payloads/*.*',
    '/home/james/stacklabs/dna/dropzone/daily_*/*.md',
    '/home/james/stacklabs/dna/dropzone/daily_*/*.txt',
    '/home/james/.gemini/antigravity/knowledge/*/*.md',
    '/home/james/.gemini/antigravity/knowledge/*/artifacts/*/*.md',
    '/home/james/.gemini/antigravity/brain/*/*.md'
]

files_to_copy = set()
for dp in dynamic_patterns:
    for f in glob.glob(dp, recursive=True):
        files_to_copy.add(os.path.abspath(f))

processed = 0
current_words = 0
part_num = 1
MAX_WORDS = 300000  # NotebookLM max is 500k words per doc
current_file = None

def get_outfile():
    global current_file
    if current_file:
        return current_file
    f_path = os.path.join(OUTPUT_DIR, f'BARBS_BIRTHDAY_LORE_OMNIBUS_PART_{part_num}.txt')
    current_file = open(f_path, 'w', encoding='utf-8')
    current_file.write(f"### OMNIBUS KNOWLEDGE BASE: SPRINT 42 SOVEREIGN OPS - PART {part_num} ###\n\n")
    return current_file

print(f"Consolidating {len(files_to_copy)} files into Omnibus chunks...")

for f in sorted(list(files_to_copy)):
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as infile:
            content = infile.read()
            word_count = len(content.split())
            
            if current_words + word_count > MAX_WORDS:
                if current_file:
                    current_file.close()
                    current_file = None
                part_num += 1
                current_words = 0
            
            outfile = get_outfile()
            outfile.write(f"\n\n========================================================\n")
            outfile.write(f"SOURCE ARTIFACT: {os.path.basename(f)}\n")
            outfile.write(f"PATH DEEP: {f}\n")
            outfile.write(f"========================================================\n\n")
            outfile.write(content)
            outfile.write("\n")
            
            processed += 1
            current_words += word_count
    except Exception as e:
        pass

if current_file:
    current_file.close()

print(f"Successfully consolidated {processed} files into {part_num} chunks in {OUTPUT_DIR}.")
print("Pushing 'BARBS_BIRTHDAY_LORE' directly to Google Drive via rclone...")
subprocess.run(['rclone', 'copy', OUTPUT_DIR, 'sovereign_os:Sovereign_OS_Master_Payloads/BARBS_BIRTHDAY_LORE', '-v'])
print("Upload complete. The OMNIBUS chunks bypass the 50-source limit and are ready for NotebookLM ingestion.")

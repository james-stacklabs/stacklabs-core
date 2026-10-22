#!/usr/bin/env python3
import os
import glob
import shutil
import sqlite3
import re

# Target Directory
OUTPUT_DIR = '/home/james/stacklabs/dna/agents/SOVEREIGN_ORACLE/payloads'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define exact file paths to collect
hardcoded_files = [
    '/home/james/stacklabs/dna/vault/00_THE_CRAZY_AND_THE_GENIUS_BASELINE.md',
    '/home/james/stacklabs/dna/vault/00_GENESIS_CONTEXT_DUMP.md',
    '/home/james/stacklabs/dna/vault/protocols/BRO_PROTOCOL_LOG.md',
    '/home/james/stacklabs/dna/vault/BRO_PROTOCOL_LOG.md',
    '/home/james/stacklabs/fanstack_chat_uat.log',
    '/home/james/stacklabs/08_FanStack/fanstack_chat_uat.log',
    '/home/james/stacklabs/dna/fanstack_chat_uat.log',
    '/home/james/.gemini/antigravity/brain/0a82e682-fab9-41f7-a295-c35536bc59a0/fanstack_uat_rosetta_stone.md',
    '/home/james/stacklabs_dev/04_Sovereign_Core/THE_SOVEREIGN_CHRONICLE.md'
]

# We want to automatically grab the latest of these files from active sessions
dynamic_patterns = [
    '/home/james/stacklabs/dna/agents/*/active_sessions/*/!BC_SESSION_*.md',
    '/home/james/stacklabs/dna/agents/*/active_sessions/*/ORACLE_PROTOCOL_SEQUENCE_*',
    '/home/james/stacklabs/dna/agents/*/active_sessions/*/SOVEREIGN_*.md',
    '/home/james/stacklabs/dna/agents/*/active_sessions/*/*_MANIFEST.md',
    '/home/james/stacklabs/dna/agents/*/active_sessions/*/*_DNA.md'
]

files_to_copy = set()

for f in hardcoded_files:
    if os.path.exists(f):
        files_to_copy.add(os.path.abspath(f))

# Gather from Dynamic Patterns (like active session logs, Gemini-Oracle directives, etc.)
for dp in dynamic_patterns:
    for f in glob.glob(dp, recursive=True):
        if not re.search(r'\d{4}-\d{2}-\d{2}-\d{2}-\d{2}', f):
            files_to_copy.add(os.path.abspath(f))

# Also fetch sequences from the SQLite DB if it exists
try:
    conn = sqlite3.connect('/home/james/stacklabs/sovereign_core.db')
    cursor = conn.cursor()
    cursor.execute('SELECT filepath FROM oracle_sequences ORDER BY sequence_id ASC')
    for row in cursor.fetchall():
        if os.path.exists(row[0]):
            files_to_copy.add(os.path.abspath(row[0]))
    conn.close()
except Exception as e:
    print(f"DB Fetch Error: {e}")

processed = 0
errors = 0

print(f"Gathering {len(files_to_copy)} key Oracle sources into {OUTPUT_DIR}...")
for f in files_to_copy:
    try:
        basename = os.path.basename(f)
        if not basename.endswith('.txt'):
            basename = basename + '.txt'
        dest = os.path.join(OUTPUT_DIR, basename)
        
        # Check if the source and dest are the identical file path to prevent shutil.SameFileError
        if os.path.abspath(f) == os.path.abspath(dest):
            continue
            
        shutil.copy2(f, dest)
        processed += 1
    except Exception as e:
        print(f"Failed to copy {f}: {e}")
        errors += 1

print(f"Successfully staged {processed} files to the Payload Directory. The Watcher will automatically push them to Google Drive.")

#!/usr/bin/env python3
"""
Sovereign OS — Parameterized Persona Lore Injector CLI
======================================================
Author: Antigravity & The Pilot
Date: 2026-06-01

A highly flexible, ServiceNow-style dynamic utility script to inject 
enemies, catchphrases, and custom lore directly into any of the 130+ 
Sovereign AI personas dynamically.

Usage:
  python3 update_persona_lore_cli.py --persona barf --enemy "AAA Auxiliary Variants" --catchphrase "Oh great, another AAA variant."
"""

import os
import argparse
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Load Sovereign environment context
load_dotenv("/home/james/stacklabs/.env")
SOVEREIGN_HOME = Path(os.getenv("SOVEREIGN_HOME", "/home/james/stacklabs"))
DB_PATH = SOVEREIGN_HOME / "dna" / os.getenv("SOVEREIGN_DB_NAME", "sovereign_now.db")

def parse_args():
    parser = argparse.ArgumentParser(description="Inject dynamic lore variables into any Sovereign AI persona.")
    parser.add_argument(
        "--persona", "-p",
        required=True,
        help="The username of the target persona (e.g., barf, seven_train_terry, uncle_stevie_stan)"
    )
    parser.add_argument(
        "--enemy", "-e",
        help="An enemy string to inject into the persona's 'UPDATED ENEMIES LIST (2026)' section."
    )
    parser.add_argument(
        "--catchphrase", "-c",
        help="A catchphrase string to inject into the persona's '2026 CATCHPHRASE ADDITIONS' section."
    )
    return parser.parse_args()

def inject_section_item(deep_lore: str, header: str, item_text: str) -> str:
    """Inserts a bullet point item under a specified markdown header.
    If the header doesn't exist, appends the header and item to the end of the text.
    """
    if not item_text:
        return deep_lore

    # Clean the bullet text
    bullet = f"- {item_text.strip()}"
    
    # If the bullet is already in the deep_lore, avoid duplicates
    if item_text.strip() in deep_lore:
        return deep_lore

    if header in deep_lore:
        # Split deep_lore at the header, inject the bullet right after the header line
        parts = deep_lore.split(header, 1)
        header_section = parts[1]
        
        # We want to find the next section or empty space to insert our bullet point
        lines = header_section.split("\n")
        inserted = False
        
        for i, line in enumerate(lines):
            # If we hit another header or the end, insert the bullet before it
            if line.strip().startswith("#") or (i > 0 and line.strip() == "" and i == len(lines) - 1):
                lines.insert(i, bullet)
                inserted = True
                break
        
        if not inserted:
            lines.insert(0, bullet)
            
        return parts[0] + header + "\n" + "\n".join(lines)
    else:
        # Append header and item to the bottom of the deep lore
        return f"{deep_lore.strip()}\n\n{header}\n{bullet}\n"

def main():
    args = parse_args()
    # Strip any trailing '_prime' in case-insensitive fashion
    persona_base = args.persona
    if persona_base.lower().endswith("_prime"):
        persona_base = persona_base[:-6]
    
    # Identify both the standard persona and the prime counterpart
    personas_to_update = [persona_base, f"{persona_base}_prime"]
    
    if not os.path.exists(DB_PATH):
        print(f"❌ [DATABASE ERROR] SQLite DB not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    updated_count = 0
    
    for username in personas_to_update:
        # Match case-insensitively using COLLATE NOCASE
        cursor.execute("SELECT user_name, deep_lore FROM persona WHERE user_name = ? COLLATE NOCASE", (username,))
        row = cursor.fetchone()
        
        if not row:
            # Silently skip if the _prime version doesn't exist (not all personas have one)
            continue
            
        exact_username = row[0]
        current_lore = row[1] or ""
        new_lore = current_lore
        
        # Inject enemy if specified
        if args.enemy:
            new_lore = inject_section_item(
                new_lore, 
                "## UPDATED ENEMIES LIST (2026)", 
                args.enemy
            )
            
        # Inject catchphrase if specified
        if args.catchphrase:
            new_lore = inject_section_item(
                new_lore, 
                "## 2026 CATCHPHRASE ADDITIONS", 
                args.catchphrase
            )
            
        if new_lore != current_lore:
            cursor.execute(
                "UPDATE persona SET deep_lore = ? WHERE user_name = ?", 
                (new_lore, exact_username)
            )
            print(f"✅ [SUCCESS] Lore variables injected successfully into: @{exact_username}")
            updated_count += 1
            
    if updated_count > 0:
        conn.commit()
        print(f"🎉 [TRANSACTION LOCKED] Committed updates to {updated_count} persona records in CMDB.")
    else:
        print(f"ℹ️ [NO OP] No changes needed or persona '{persona_base}' not found.")
        
    conn.close()

if __name__ == "__main__":
    main()

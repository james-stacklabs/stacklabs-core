#!/usr/bin/env python3
import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def prune_puppet_lore():
    print("🔒 Opening database at:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find all personas in teams that are NOT sports/MLB teams
    # Anvil & Twine (ANVILANDTWINE) and Gonzo's Convenience (UNHINGEDCONVENIENCE) are key retail target zones
    targets = ["ANVILANDTWINE", "UNHINGEDCONVENIENCE", "BISTROSTACK", "WEEDSTACK", "MEETHREETHROUPLESAPP"]
    
    updated_count = 0
    for target in targets:
        # Get all personas for this team
        cur.execute("SELECT id, user_name, system_prompt, deep_lore, governance FROM persona WHERE team = ?", (target,))
        rows = cur.fetchall()
        for row in rows:
            p_id, user_name, sys_prompt, deep_lore, governance = row
            
            # Perform clean replacements to strip puppet references
            new_sys_prompt = sys_prompt or ""
            new_deep_lore = deep_lore or ""
            new_governance = governance or ""

            # Replace puppet/felt terms with premium realistic graphic novel terms
            replacements = {
                "1990s physical felt sports puppet": "highly detailed realistic character",
                "1990s physical felt puppet": "highly detailed realistic character",
                "physical felt puppet": "realistic hand-drawn character",
                "fuzzy felt puppet": "realistic hand-drawn character",
                "felt puppet": "realistic hand-drawn character",
                "puppet stitching": "weathered clothing lines",
                "felt stitching": "weathered stitching",
                "googly eyes": "expressive unblinking eyes",
                "matted fur": "weathered textured fur",
                "hot-glue": "stitched industrial",
                "sports broadcast desk": "rustic wooden shop counter",
                "sports broadcast console": "rustic wooden shop counter"
            }

            modified = False
            for old, new in replacements.items():
                if old in new_sys_prompt:
                    new_sys_prompt = new_sys_prompt.replace(old, new)
                    modified = True
                if old in new_deep_lore:
                    new_deep_lore = new_deep_lore.replace(old, new)
                    modified = True
                if old in new_governance:
                    new_governance = new_governance.replace(old, new)
                    modified = True

            if modified:
                print(f"  [PRUNE] Updating non-puppet descriptors for: {user_name} ({target})")
                cur.execute("""
                    UPDATE persona 
                    SET system_prompt = ?, deep_lore = ?, governance = ? 
                    WHERE id = ?
                """, (new_sys_prompt, new_deep_lore, new_governance, p_id))
                
                cur.execute("""
                    UPDATE cmdb_ci_ai_persona 
                    SET u_system_prompt = ?, u_deep_lore = ?, u_governance_boundaries = ? 
                    WHERE sys_id = ?
                """, (new_sys_prompt, new_deep_lore, new_governance, p_id))
                
                updated_count += 1

    conn.commit()
    conn.close()
    print(f"🏁 Pruning complete. Cleaned and updated {updated_count} persona records to ensure absolute non-puppet compliance!")

if __name__ == "__main__":
    prune_puppet_lore()

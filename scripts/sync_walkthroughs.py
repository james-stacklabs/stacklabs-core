import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
WALKTHROUGH_DIR = "/home/james/sovereign_inbox/walkthroughs"

def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.replace('T', ' ')
    if '.' in date_str:
        date_str = date_str.split('.')[0]
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except:
        try:
            return datetime.strptime(date_str.split(' ')[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except:
            return None

def main():
    if not os.path.exists(WALKTHROUGH_DIR):
        print(f"Error: Walkthrough directory {WALKTHROUGH_DIR} does not exist.")
        return

    print("Connecting to sovereign_now.db...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Query recently resolved tickets (updated since June 25, 2026, state 4 or 5)
    cutoff_date = datetime(2026, 6, 25, 0, 0, 0, tzinfo=timezone.utc)
    
    c.execute("SELECT number, state, sys_updated_on FROM sovereign_tickets WHERE state IN (4, 5)")
    resolved_tickets = set()
    for row in c.fetchall():
        dt = parse_date(row[2])
        if dt and dt >= cutoff_date:
            resolved_tickets.add(row[0].strip())

    print(f"Identified {len(resolved_tickets)} tickets resolved since June 25, 2026.")

    # 2. Scan walkthroughs directory
    walkthrough_files = []
    for filename in os.listdir(WALKTHROUGH_DIR):
        if filename.startswith("walkthrough_") and filename.endswith(".md"):
            filepath = os.path.join(WALKTHROUGH_DIR, filename)
            
            # Extract ticket ID
            # e.g., walkthrough_ENHC1789569.md -> ENHC1789569
            # e.g., walkthrough_DFCT-0628-ADVOCATE-STALE-CONTEXT.md -> DFCT-0628-ADVOCATE-STALE-CONTEXT
            ticket_id = filename[12:-3].strip()
            
            # Check modification time
            mtime = os.path.getmtime(filepath)
            mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
            
            # Sync if ticket is recently resolved, or file was modified recently
            if ticket_id in resolved_tickets or mtime_dt >= cutoff_date:
                walkthrough_files.append((ticket_id, filepath, mtime_dt))

    print(f"Found {len(walkthrough_files)} walkthrough files qualifying for sync.")

    synced_count = 0
    updated_count = 0

    for ticket_id, filepath, mtime_dt in walkthrough_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse markdown title (H1)
            title = f"Release Notes: {ticket_id}"
            title_match = re.search(r"^#\s+(.*)$", content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()

            # Parse short description (first non-header, non-blank line, or abstract summary)
            short_desc = ""
            lines = content.split('\n')
            # Look for summary callout or abstract summary
            summary_found = False
            for i, line in enumerate(lines):
                if "Abstract Summary" in line or "Summary" in line:
                    # Next non-empty line
                    for j in range(i+1, min(i+5, len(lines))):
                        if lines[j].strip() and not lines[j].strip().startswith(">"):
                            short_desc = lines[j].strip()
                            summary_found = True
                            break
                if summary_found:
                    break

            if not short_desc:
                # Fallback: find first paragraph
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith(">") and not stripped.startswith("-") and not stripped.startswith("*"):
                        short_desc = stripped
                        if len(short_desc) > 150:
                            short_desc = short_desc[:147] + "..."
                        break

            if not short_desc:
                short_desc = f"Walkthrough documentation and verification notes for ticket {ticket_id}."

            kb_number = f"KB_{ticket_id}"
            
            # Check if kb article already exists
            c.execute("SELECT sys_id, text FROM kb_knowledge WHERE number = ?", (kb_number,))
            row = c.fetchone()
            
            if row:
                sys_id, existing_text = row
                # If text has changed, update it
                if existing_text != content:
                    c.execute("""
                        UPDATE kb_knowledge 
                        SET topic = ?, short_description = ?, text = ?, sys_updated_on = ?, u_source = ?, u_tags = ?
                        WHERE sys_id = ?
                    """, (title, short_desc, content, mtime_dt.strftime('%Y-%m-%d %H:%M:%S'), 'system_operations', 'release-notes', sys_id))
                    updated_count += 1
            else:
                sys_id = f"sys_kb_{uuid.uuid4().hex}"
                c.execute("""
                    INSERT INTO kb_knowledge (sys_id, number, topic, short_description, text, workflow_state, sys_created_on, sys_updated_on, u_source, u_tags)
                    VALUES (?, ?, ?, ?, ?, 'published', ?, ?, 'system_operations', 'release-notes')
                """, (sys_id, kb_number, title, short_desc, content, mtime_dt.strftime('%Y-%m-%d %H:%M:%S'), mtime_dt.strftime('%Y-%m-%d %H:%M:%S')))
                synced_count += 1

        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    conn.commit()
    conn.close()

    print(f"Walkthrough sync completed: {synced_count} inserted, {updated_count} updated.")

if __name__ == "__main__":
    main()

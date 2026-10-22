import sqlite3
import datetime
import os

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
REPORT_DIR = "/home/james/sovereign_inbox/reports"
REPORT_PATH = os.path.join(REPORT_DIR, "advocate_updates_20260629.md")

def main():
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)
        
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    
    # Query updated personas today
    cursor.execute("""
        SELECT user_name, team, behavior_notes, updated_at 
        FROM persona 
        WHERE date(updated_at) = date('now') 
        ORDER BY team, user_name
    """)
    rows = cursor.fetchall()
    con.close()
    
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    report_content = f"""# 🤖 Sovereign OS Advocate Updates Report
**Date:** {today_str}
**Total Updated Advocates:** {len(rows)}

This report outlines the dynamic context updates applied to the active AI yapper/advocate roster during today's Vertex Persona Audit. These updates reflect their behavioral adaptations and reactions to today's major MLB events.

---

## 👥 Advocate Context Updates

"""
    
    by_team = {}
    for r in rows:
        team = r['team'] or "GLOBAL"
        if team not in by_team:
            by_team[team] = []
        by_team[team].append(r)
        
    for team, personas in sorted(by_team.items()):
        report_content += f"### {team} Team Advocates\n\n"
        report_content += "| Advocate | Daily Behavioral Update (Reaction to Today's News) |\n"
        report_content += "| :--- | :--- |\n"
        for p in personas:
            user_name = p['user_name']
            notes = p['behavior_notes'] or ""
            # Extract last line matching date format
            daily_update = "No update text parsed."
            lines = [l.strip() for l in notes.split('\n') if l.strip()]
            for line in reversed(lines):
                if line.startswith(today_str + ":"):
                    daily_update = line.replace(today_str + ":", "").strip()
                    break
                elif ":" in line:
                    parts = line.split(":", 1)
                    # check if the part before colon looks like a date or has today's date
                    if today_str in parts[0] or parts[0].strip().replace("-", "").isdigit():
                        daily_update = parts[1].strip()
                        break
            
            report_content += f"| **{user_name}** | {daily_update} |\n"
        report_content += "\n"
        
    with open(REPORT_PATH, "w") as f:
        f.write(report_content)
        
    print(f"Report successfully generated at: {REPORT_PATH}")

if __name__ == "__main__":
    main()

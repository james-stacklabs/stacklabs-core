import sqlite3
import os

def generate_report():
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    game_pk = "823448"
    
    # Query game details
    cursor.execute("SELECT home_team, away_team, game_date, room_state, status FROM mlb_schedule WHERE game_pk = ?", (game_pk,))
    game_row = cursor.fetchone()
    if not game_row:
        print("Error: Game not found.")
        return
    home_team, away_team, game_date, room_state, status = game_row

    # Query advocates in this room
    cursor.execute("""
        SELECT p.user_name, p.display_name, p.team, p.cadence, p.boggs_level, p.avatar_url, p.color, p.system_prompt, p.deep_lore, p.behavior_notes, p.governance
        FROM m2m_persona_room m
        JOIN persona p ON m.persona = p.id
        WHERE m.room = ?
        ORDER BY p.team, p.user_name
    """, (game_pk,))
    rows = cursor.fetchall()

    report_path = "/home/james/sovereign_inbox/reports/mets_phillies_advocate_bios.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 🏟️ Mets @ Phillies Game Room Provisioning & Advocate Bios\n\n")
        f.write(f"**Game PK:** `{game_pk}`  \n")
        f.write(f"**Matchup:** {away_team} @ {home_team}  \n")
        f.write(f"**Date:** {game_date}  \n")
        f.write(f"**Status:** {status} (`{room_state}`)  \n")
        f.write(f"**Total Seated Advocates:** {len(rows)}  \n\n")

        # Table Summary
        f.write("## 📋 Seated Advocate Roster Summary\n\n")
        f.write("| Username | Display Name | Team | Cadence | Boggs Level | Accent Color |\n")
        f.write("| :--- | :--- | :---: | :--- | :---: | :---: |\n")
        for r in rows:
            username, display_name, team, cadence, boggs_level, avatar_url, color, _, _, _, _ = r
            f.write(f"| `{username}` | {display_name} | **{team}** | `{cadence}` | {boggs_level} | `{color}` |\n")
        f.write("\n---\n\n")

        # Detailed Profiles
        f.write("## 🎭 Detailed Advocate Biographies & System Prompts\n\n")
        for idx, r in enumerate(rows, 1):
            username, display_name, team, cadence, boggs_level, avatar_url, color, system_prompt, deep_lore, behavior_notes, governance = r

            f.write(f"### {idx}. {display_name} (`@{username}`)\n\n")
            f.write(f"**Core Configuration:**\n")
            f.write(f"- **Team Affiliation:** {team}\n")
            f.write(f"- **Cadence:** `{cadence}`\n")
            f.write(f"- **Boggs Level:** `{boggs_level}`\n")
            f.write(f"- **Accent Color:** `{color}`\n")
            f.write(f"- **Avatar URL:** `{avatar_url}`\n\n")

            if deep_lore:
                f.write(f"#### 📜 Deep Lore / Character Dossier\n\n")
                f.write(f"{deep_lore.strip()}\n\n")

            if behavior_notes:
                f.write(f"#### 🧠 Behavioral Guidelines\n\n")
                f.write(f"{behavior_notes.strip()}\n\n")

            if governance:
                f.write(f"#### ⚖️ Governance Parameters\n\n")
                f.write(f"{governance.strip()}\n\n")

            if system_prompt:
                f.write(f"#### ⚙️ System Prompt\n\n")
                f.write(f"```markdown\n{system_prompt.strip()}\n```\n\n")

            f.write("---\n\n")

    conn.close()
    print(f"Successfully wrote advocate bios report to: {report_path}")

if __name__ == "__main__":
    generate_report()

import sqlite3

db_path = "/home/james/stacklabs/dna/sovereign_now.db"

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

triggers = [
    # trigger_rule_name, statcast_event_type, telemetry_field, operator_comparison, comparison_value, batting_team_filter, target_webslinger_event_id
    ("Juan Soto Launch Rocket", "hit", "hit_speed", ">=", "110.0", "NYM", 1),
    ("Harper Hard Hit", "hit", "hit_speed", ">=", "108.0", "PHI", 2),
    ("Mets Moonshot", "home_run", "hit_distance", ">=", "420.0", "NYM", 3),
    ("Schwarber Bomb Distance", "home_run", "hit_distance", ">=", "430.0", "PHI", 2),
    ("Diaz Gas Pitch", "pitch", "pitch_speed", ">=", "100.0", "NYM", 3),
    ("Alvarado Heat Pitch", "pitch", "pitch_speed", ">=", "100.5", "PHI", 3),
    ("Mets Base Runner Speed", "hit", "launch_angle", "<=", "10.0", "NYM", 4),
    ("Phillies Line Drive", "hit", "launch_angle", ">=", "15.0", "PHI", 2),
    ("Mets Clutch Run Scored", "runs_scored", "runs_scored", ">=", "1.0", "NYM", 3),
    ("Phillies Rally Run Scored", "runs_scored", "runs_scored", ">=", "1.0", "PHI", 2),
]

inserted_count = 0
for t in triggers:
    # Check if a trigger with the same rule name already exists
    cursor.execute("SELECT id FROM sys_tmi_telemetry_map WHERE trigger_rule_name = ?", (t[0],))
    row = cursor.fetchone()
    if row:
        print(f"Trigger rule '{t[0]}' already exists. Skipping.")
        continue
        
    cursor.execute("""
        INSERT INTO sys_tmi_telemetry_map (
            trigger_rule_name, statcast_event_type, telemetry_field, 
            operator_comparison, comparison_value, batting_team_filter, 
            target_webslinger_event_id, is_automated_ingress, active_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
    """, t)
    inserted_count += 1
    print(f"Created telemetry trigger: {t[0]}")

conn.commit()
conn.close()

print(f"Successfully seeded {inserted_count} TMI Telemetry Triggers.")

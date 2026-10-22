import sqlite3

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
cur = conn.cursor()
cur.execute("SELECT u_visual_style, count(*) FROM cmdb_ci_ai_persona GROUP BY u_visual_style;")
print("Styles in cmdb_ci_ai_persona:", cur.fetchall())
cur.execute("SELECT avatar_url, count(*) FROM persona GROUP BY avatar_url LIMIT 10;")
print("Avatars in persona:", cur.fetchall())
conn.close()

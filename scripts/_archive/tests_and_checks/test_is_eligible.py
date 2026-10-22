import sqlite3
import re

def is_eligible(f, ht, aw, gk, pk=""):
    t = str(f.get("team", "")).lower()
    r = str(f.get("room", "")).lower()
    
    if re.match(r'^\d{6}$', r):
        return str(pk).lower() == r

    if ht.lower() == t or ht.lower() in r: return True
    if aw.lower() == t or aw.lower() in r: return True
    if gk.lower() == t or gk.lower() == r: return True
    if pk and (str(pk).lower() == t or str(pk).lower() == r): return True
    if "both" in t or "both" in r: return True
    if "global" in t or "global" in r: return True
    return False

def load_fans():
    fans_list = []
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT c.name, c.assigned_to, p.u_deployment_zone
        FROM cmdb_ci c
        LEFT JOIN cmdb_ci_ai_persona p ON c.sys_id = p.sys_id
        WHERE c.sys_class_name = 'cmdb_ci_ai_persona' AND c.operational_status = 1
    ''')
    rows = c.fetchall()
    for r in rows:
        fans_list.append({
            "name": str(r['name']),
            "team": str(r['assigned_to']) if r['assigned_to'] else "",
            "room": str(r['u_deployment_zone']) if r['u_deployment_zone'] else ""
        })
    return fans_list

fans = load_fans()
eligible = [f for f in fans if is_eligible(f, "PHI", "AZ", "AZ-PHI", "")]
print([f['name'] for f in eligible])

import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

personas = [
    {
        "name": "Muni_Ghost",
        "desc": "The Grumpy Historian",
        "team": "cle"
    },
    {
        "name": "E65th_Lex",
        "desc": "The Neighborhood Soul",
        "team": "cle"
    },
    {
        "name": "Dolan_Drain",
        "desc": "The Cynical Analyst",
        "team": "cle"
    },
    {
        "name": "Jake_Taylor_6th",
        "desc": "The Movie Purist (Major League Loyalist)",
        "team": "cle"
    },
    {
        "name": "Missou_Or_Bust",
        "desc": "The Border Warrior",
        "team": "kc"
    },
    {
        "name": "Powder_Blue_85",
        "desc": "The Nostalgia Peak",
        "team": "kc"
    },
    {
        "name": "JoCo_Traitor",
        "desc": "The Kansas Instigator",
        "team": "kc"
    }
]

def fix_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for p in personas:
        short_desc = f"{p['name']} - {p['desc']}"
        cursor.execute("UPDATE cmdb_ci SET short_description = ?, assigned_to = ? WHERE name = ?", 
                       (short_desc, p["team"], p["name"]))
        print(f"Fixed {p['name']} to {short_desc} / Team: {p['team']}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_db()

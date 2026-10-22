import sqlite3
import uuid
import asyncio
import websockets
import json
import time

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

personas = [
    {
        "name": "Muni_Ghost",
        "desc": "The Grumpy Historian (CLE)",
        "prompt": "You are Muni_Ghost, a grumpy Cleveland baseball historian. You still talk about Cleveland Municipal Stadium. You hate the name Guardians but refuse to stop watching. You frequently reference 'The Mistake on the Lake' and how the wind off Lake Erie in April is the only real home-field advantage. You complain about the lack of a portable center field fence.",
        "color": "#a8a29e" # Grey
    },
    {
        "name": "E65th_Lex",
        "desc": "The Neighborhood Soul (CLE)",
        "prompt": "You are E65th_Lex, a neighborhood soul from League Park. You talk about the Doby/Paige legacy. You view the team as a community asset, not a business. You frequently bring up the 455 consecutive sell-out streak at 'The Jake'. You complain about $1,899 Spring Training travel packages and remember when you could see a game for the price of a lake-perch sandwich.",
        "color": "#eab308" # Yellowish
    },
    {
        "name": "Dolan_Drain",
        "desc": "The Cynical Analyst (CLE)",
        "prompt": "You are Dolan_Drain, a cynical tactical expert. You are convinced the owners are just rent-seeking. You value a bunt over a home run because 'that's the only way Cleveland can afford to score'. You have deep knowledge of the Bob Feller era and the 1948 championship drought, and compare the Guardians' budget to the rest of the AL Central.",
        "color": "#ef4444" # Red
    },
    {
        "name": "Jake_Taylor_6th",
        "desc": "The Movie Purist (CLE - Major League Loyalist)",
        "prompt": "You are Jake_Taylor_6th. You wear a beat-up Indians hat and refuse to acknowledge the 'Guardians' rebrand. You view the team through the lens of the 1989 film Major League. The current roster is just a placeholder for Willie Mays Hayes and Rick 'Wild Thing' Vaughn. You know where the California Penal League is and quote Harry Doyle. Catchphrases: 'Juuust a bit outside!' and 'Strike this guy out, I'm tired of his pajamas.'",
        "color": "#0ea5e9" # Blue
    },
    {
        "name": "Missou_Or_Bust",
        "desc": "The Border Warrior (KC)",
        "prompt": "You are Missou_Or_Bust, a furious Royals fan. You are a Missouri purist and think the Royals moving to Kansas would be a betrayal of the 1969 inaugural season. You mention Ewing Kauffman and Hallmark Cards like they're family. You reference the American Royal livestock show. You hate that the Chiefs sold out to Kansas.",
        "color": "#facc15" # Gold
    },
    {
        "name": "Powder_Blue_85",
        "desc": "The Nostalgia Peak (KC)",
        "prompt": "You are Powder_Blue_85. You think baseball peaked with George Brett and the Pine Tar Incident. You only wear powder blue and gold. You claim the water in the Kauffman Stadium fountains is actually the 'tears of Cardinals fans' from the '85 I-70 series. You hate moving the fences in for the 2026 season because it ruins the pitcher's park integrity.",
        "color": "#60a5fa" # Powder Blue
    },
    {
        "name": "JoCo_Traitor",
        "desc": "The Kansas Instigator (KC)",
        "prompt": "You are JoCo_Traitor. You live in Johnson County (JoCo) and WANT the Royals to move to Kansas. You are the villain in the chat. You argue that the Royals' true identity is the Monarchs, and they deserve a $3 billion dome like the Chiefs. You mock Missouri fans every time KC scores because of Missouri's refusal to fund a downtown stadium.",
        "color": "#8b5cf6" # Purple
    }
]

def setup_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for p in personas:
        # Check if exists
        cursor.execute("SELECT sys_id FROM cmdb_ci WHERE name = ?", (p["name"],))
        row = cursor.fetchone()
        if not row:
            cid = uuid.uuid4().hex
            cursor.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to) VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 1, 'CI-ANTIGRAVITY')", (cid, p["name"], p["desc"]))
            cursor.execute("INSERT INTO cmdb_ci_ai_persona (sys_id, u_llm_engine, u_system_prompt, u_deployment_zone, u_boggs_reactivity) VALUES (?, 'gemini-pro', ?, 'KC_CLE_1PM', 'Level 4')", (cid, p["prompt"]))
            print(f"Added {p['name']} to CMDB.")
        else:
            print(f"{p['name']} already exists.")
            
    conn.commit()
    conn.close()

async def warm_up_chat():
    uri = "ws://127.0.0.1:8008"
    try:
        async with websockets.connect(uri) as ws:
            # Join room
            await ws.send(json.dumps({"type": "JOIN_ROOM", "target_game_pk": "KC_CLE_1PM"}))
            await asyncio.sleep(0.5)
            
            # Send opening barrage
            msg1 = {
                "type": "CHAT_MESSAGE",
                "user": "Jake_Taylor_6th",
                "color": "#0ea5e9",
                "text": "In honor of Willie Mays Hayes, let's see if anyone on this roster can actually run without trippin' over their own feet.",
                "target_game_pk": "KC_CLE_1PM"
            }
            await ws.send(json.dumps(msg1))
            await asyncio.sleep(1)
            
            msg2 = {
                "type": "CHAT_MESSAGE",
                "user": "JoCo_Traitor",
                "color": "#8b5cf6",
                "text": "Who cares about 1989? At least our team has a chance of moving to a state that actually wants them.",
                "target_game_pk": "KC_CLE_1PM"
            }
            await ws.send(json.dumps(msg2))
            await asyncio.sleep(1)

            msg3 = {
                "type": "CHAT_MESSAGE",
                "user": "Muni_Ghost",
                "color": "#a8a29e",
                "text": "Both of you are nuts. What we really need is the portable fence back. And that wind off the lake... boy do I miss the lake winds. Can't replicate the Mistake on the Lake.",
                "target_game_pk": "KC_CLE_1PM"
            }
            await ws.send(json.dumps(msg3))
            print("Room 'KC_CLE_1PM' warmed up successfully!")
    except Exception as e:
        print(f"Failed to warm up chat: {e}")

if __name__ == "__main__":
    setup_db()
    asyncio.run(warm_up_chat())

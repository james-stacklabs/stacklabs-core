from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app) # Allow Vite React app to connect

PERSONAS_DIR = '/home/james/stacklabs/dna/agents/personas/'

# Load API Key
api_key = None
try:
    with open('/home/james/stacklabs/.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                api_key = line.strip().split('=', 1)[1]
                break
except Exception as e:
    print(f"Warning: Could not load API key: {e}")

client = None
if api_key:
    client = genai.Client(api_key=api_key)

def find_persona_file(tag):
    """Attempt to find a persona file matching the @tag."""
    tag = tag.lower().strip()
    if tag.endswith('_ci'):
        tag = tag[:-3]
    possible_files = [
        f"{tag}.md",
        f"{tag}_stan.md",
        f"{tag}_terry.md",
        tag # fallback
    ]
    
    # Check exact matches
    for pf in possible_files:
        if os.path.exists(os.path.join(PERSONAS_DIR, pf)):
            return pf
            
    # Check fuzzy matches
    all_files = [f for f in os.listdir(PERSONAS_DIR) if f.endswith('.md')]
    for f in all_files:
        if tag in f.lower():
            return f
            
    return None

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"error": "Missing message"}), 400

    # Extract @tag
    match = re.search(r'@(\w+)', user_message)
    
    if not match:
        return jsonify({
            "persona": "Scruffy (Bartender)",
            "text": "Hey pal, if you're gonna yell at someone in my bar, you gotta use their name. Tag them with @ (like @barf or @dot). Now buy a drink or get out.",
            "color": "#8B4513"
        })

    tag = match.group(1)
    persona_file = find_persona_file(tag)

    if not persona_file:
        return jsonify({
            "persona": "Scruffy (Bartender)",
            "text": f"Ain't nobody in this bar named {tag}. Try @barf, @dot, or @uncle_stevie.",
            "color": "#8B4513"
        })

    persona_path = os.path.join(PERSONAS_DIR, persona_file)
    try:
        with open(persona_path, 'r') as f:
            persona_lore = f.read()
    except Exception as e:
        return jsonify({"error": f"Could not load persona lore: {e}"}), 500

    try:
        # Load the latest Fan Stack context to ground the personas in reality!
        current_context = "No recent context available."
        try:
            with open('/home/james/stacklabs/dna/dropzone/daily_22042026/mardy_soto_comments.md', 'r') as f:
                current_context = f.read()[:5000] # Grab the first 5000 chars of latest fan meltdown
        except:
            pass

        prompt = f"""You are acting as the persona described below. You are currently sitting at "Scruffy's Bar", a local dive bar where sports fans come to complain or talk stats.

Persona Lore:
{persona_lore}

CURRENT REALITY (DO NOT HALLUCINATE STATS OR PROBABILITIES THAT CONTRADICT THIS):
The Mets are currently on an 11+ game losing streak. They are the worst team in MLB right now. Juan Soto has just returned for Game 2 vs Minnesota. 
Here is what the fans are currently screaming about in the live chat right now:
{current_context}

A fan just walked up to you in the bar and said:
"{user_message}"

Task: Write ONE single, highly punchy, character-accurate response to this fan. Speak directly to them. Do not use hashtags or emojis. Keep it STRICTLY UNDER 250 CHARACTERS. Ensure your response reflects the CURRENT REALITY provided above.
If the fan asks a statistical or factual question about current events or baseball, USE GOOGLE SEARCH to find the real answer before responding!"""

        if not client:
            return jsonify({"error": "Gemini API client not initialized"}), 500

        res = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.85,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        persona_name = persona_file.replace('.md', '').replace('_', ' ').title()
        
        return jsonify({
            "persona": persona_name,
            "text": res.text.strip(),
            "color": "#FF5910" if "barf" in persona_file.lower() else "#00E676" if "dot" in persona_file.lower() else "#E0E0E0"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import requests
from datetime import datetime, timedelta

@app.route('/api/scoreboard', methods=['GET'])
def get_scoreboard():
    try:
        # Get yesterday's date if before 11AM to avoid MLB rollover issue
        now = datetime.now()
        if now.hour < 11:
            target_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            target_date = now.strftime('%Y-%m-%d')
            
        schedule_url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=121&date={target_date}'
        sched_res = requests.get(schedule_url, timeout=5).json()
        
        if sched_res['totalGames'] == 0:
            return jsonify({"status": "No game today"})
            
        game_pk = request.args.get('gamePk')
        if not game_pk:
            game_pk = sched_res['dates'][0]['games'][0]['gamePk']
        live_url = f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
        live_res = requests.get(live_url, timeout=5).json()
        
        game_data = live_res['gameData']
        live_data = live_res['liveData']
        linescore = live_data['linescore']
        
        away_team = game_data['teams']['away']['abbreviation']
        home_team = game_data['teams']['home']['abbreviation']
        
        return jsonify({
            "status": game_data['status']['detailedState'],
            "away": {
                "name": away_team,
                "runs": linescore['teams']['away'].get('runs', 0),
                "hits": linescore['teams']['away'].get('hits', 0),
                "errors": linescore['teams']['away'].get('errors', 0)
            },
            "home": {
                "name": home_team,
                "runs": linescore['teams']['home'].get('runs', 0),
                "hits": linescore['teams']['home'].get('hits', 0),
                "errors": linescore['teams']['home'].get('errors', 0)
            },
            "inning": linescore.get('currentInningOrdinal', ''),
            "inningState": linescore.get('inningState', ''),
            "outs": linescore.get('outs', 0),
            "balls": linescore.get('balls', 0),
            "strikes": linescore.get('strikes', 0),
            "innings": linescore.get('innings', []),
            "offense": linescore.get('offense', {})
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import sqlite3

@app.route('/api/room_personas', methods=['GET'])
def get_room_personas():
    username = request.args.get('username')
    if username:
        clean_username = username.lstrip('@')
        try:
            conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
            c = conn.cursor()
            c.execute("SELECT avatar_blob, avatar_url FROM persona WHERE user_name = ? COLLATE NOCASE", (clean_username,))
            row = c.fetchone()
            conn.close()
            if row:
                return jsonify({"avatar_blob": row[0], "avatar_url": row[1]})
            return jsonify({"avatar_blob": None, "avatar_url": None})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    game_pk = request.args.get('gamePk')
    if not game_pk:
        return jsonify({"personas": ["@Dot", "@Coach_Shrubbs", "@Scruffy", "@Wardy", "@Uncle_Stevie", "@Barf"]})
        
    try:
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        c = conn.cursor()
        
        c.execute("""
            SELECT COALESCE(u.user_name, m.persona)
            FROM m2m_persona_room m
            LEFT JOIN sys_user u ON u.sys_id = m.persona
            WHERE m.room = ?
        """, (game_pk,))
        rows = c.fetchall()
        conn.close()
        
        # Only return what's actually in m2m for this room — no hardcoded fallbacks
        personas = []
        if rows:
            for r in rows:
                p_name = r[0]
                if p_name.endswith('_ci'):
                    p_name = p_name[:-3]
                formatted = "@" + p_name
                if formatted not in personas:
                    personas.append(formatted)
        
        return jsonify({"personas": personas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import json

@app.route('/api/feedback', methods=['POST'])
def save_feedback():
    try:
        data = request.json
        feedback_file = '/home/james/stacklabs/dna/dropzone/ui_feedback.json'
        
        # Load existing feedback
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r') as f:
                feedbacks = json.load(f)
        else:
            feedbacks = []
            
        # Add timestamp and append
        data['timestamp'] = datetime.now().isoformat()
        feedbacks.append(data)
        
        # Save back
        with open(feedback_file, 'w') as f:
            json.dump(feedbacks, f, indent=2)
            
        return jsonify({"status": "success", "message": "Feedback saved."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/all_personas', methods=['GET'])
def get_all_personas():
    try:
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        c = conn.cursor()
        c.execute("""
            SELECT s.sys_id, s.user_name, ci.assigned_to as team
            FROM sys_user s
            JOIN cmdb_ci ci ON s.user_name = ci.name COLLATE NOCASE
                AND ci.sys_class_name = 'cmdb_ci_ai_persona'
            WHERE s.active = 1
            GROUP BY s.sys_id, s.user_name
            ORDER BY ci.assigned_to, s.user_name
        """)
        rows = c.fetchall()
        personas = [{"sys_id": r[0], "user_name": r[1], "team": r[2]} for r in rows]
        conn.close()
        return jsonify({"personas": personas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save_room_personas', methods=['POST'])
def save_room_personas():
    data = request.json
    game_pk = str(data.get('gamePk'))
    selected = data.get('personas', []) # list of user_names
    
    try:
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        c = conn.cursor()
        
        # Get group_sys_id
        c.execute("SELECT sys_id FROM sys_user_group WHERE name LIKE ?", (f"%{game_pk}%",))
        group = c.fetchone()
        group_sys_id = group[0] if group else None
        
        if group_sys_id:
            c.execute("DELETE FROM sys_user_grmember WHERE group_id = ?", (group_sys_id,))
            
        c.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
        
        import uuid
        for p_name in selected:
            # find sys_id
            c.execute("SELECT sys_id, user_name FROM sys_user WHERE user_name COLLATE NOCASE = ?", (p_name,))
            user_row = c.fetchone()
            if not user_row: continue
            user_sys_id = user_row[0]
            actual_user_name = user_row[1]
            
            if group_sys_id:
                mem_id = str(uuid.uuid4()).replace('-', '')
                c.execute("INSERT INTO sys_user_grmember (sys_id, user, group_id) VALUES (?, ?, ?)",
                               (mem_id, user_sys_id, group_sys_id))
            
            m2m_sys_id = str(uuid.uuid4()).replace('-', '')
            # Store sys_id in persona column — load_fans() joins on s.sys_id = m2m.persona
            c.execute("INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?, ?, ?, ?)",
                           (m2m_sys_id, user_sys_id, game_pk, f"Deployed to Game {game_pk} via Room Builder"))
                           
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vertex_burn/status', methods=['GET'])
def get_vertex_status():
    is_on = os.path.exists('/home/james/stacklabs/config/vertex_burn.on')
    return jsonify({"vertex_burn_enabled": is_on})

@app.route('/api/vertex_burn/toggle', methods=['POST'])
def toggle_vertex():
    file_path = '/home/james/stacklabs/config/vertex_burn.on'
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"status": "success", "vertex_burn_enabled": False, "message": "Vertex Burn Mode Disabled"})
    else:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write("ON")
        return jsonify({"status": "success", "vertex_burn_enabled": True, "message": "Vertex Burn Mode Enabled"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007, debug=False)

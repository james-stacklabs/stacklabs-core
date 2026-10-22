#!/usr/bin/env python3
import os
import sys
import time
import json
import sqlite3
import uuid
import requests
from datetime import datetime

# Paths
SOVEREIGN_HOME = '/home/james/stacklabs'
DB_PATH = os.path.join(SOVEREIGN_HOME, 'dna/sovereign_now.db')
ENV_PATH = os.path.join(SOVEREIGN_HOME, '.env')
LAST_ID_FILE = os.path.join(SOVEREIGN_HOME, 'logs/highlight_watcher_last_id.txt')
LOG_FEED_PATH = os.path.join(SOVEREIGN_HOME, 'logs/highlight_feed.log')

# Ensure logs dir exists
os.makedirs(os.path.join(SOVEREIGN_HOME, 'logs'), exist_ok=True)

# Load Gemini API Key
GEMINI_KEY = None
try:
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    GEMINI_KEY = line.strip().split('=', 1)[1]
except Exception as e:
    print(f"[-] Error loading .env file: {e}")

if not GEMINI_KEY:
    print("[-] GEMINI_API_KEY not found in .env. Exiting.")
    sys.exit(1)

def get_game_state_str(game_pk):
    """Reads the JSON game state if available and returns a concise status string."""
    state_file = os.path.join(SOVEREIGN_HOME, f"game_states/{game_pk}.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
                inning = data.get("inning", "Live")
                away = data.get("away_team", "AWY")
                home = data.get("home_team", "HME")
                away_score = data.get("away_score", 0)
                home_score = data.get("home_score", 0)
                return f"{inning} | {away} {away_score} - {home} {home_score}"
        except Exception as e:
            print(f"[-] Error reading state file {state_file}: {e}")
    return "Live Game"

def evaluate_message_gemini(persona, text):
    """Escalates message to Gemini 2.5 Flash via native REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_KEY}"
    
    sys_instr = (
        "You are the FanStack Highlight Watcher. Analyze the following chat message and "
        "determine if it qualifies as a game highlight (e.g., epic rant, unhinged conspiracy, "
        "vicious burn, or classic fan reaction). Return EXACTLY a valid JSON response "
        "detailing your classification. Do not use markdown backticks."
    )
    
    prompt = f"Persona: {persona}\nMessage: {text}"
    
    payload = {
        "systemInstruction": {"parts": [{"text": sys_instr}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    
    try:
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            candidate = data.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            if parts:
                txt = parts[0]["text"].strip()
                if txt.startswith("```json"):
                    txt = txt[7:]
                if txt.startswith("```"):
                    txt = txt[3:]
                if txt.endswith("```"):
                    txt = txt[:-3]
                return json.loads(txt.strip())
        else:
            print(f"[-] Gemini API returned status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[-] Gemini highlight evaluation error: {e}")
    return None

def main():
    print("[*] Starting Highlight Watcher Daemon...")
    
    # Initialize last processed ID
    last_id = 0
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, 'r') as f:
                last_id = int(f.read().strip())
            print(f"[+] Loaded last processed ID from file: {last_id}")
        except Exception as e:
            print(f"[-] Error reading last ID file: {e}")
            
    # If last_id is still 0, query MAX(id) from game_chat as baseline
    if last_id == 0:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM game_chat")
            val = cursor.fetchone()[0]
            if val is not None:
                last_id = val
                print(f"[+] Baseline initialized to current MAX(id): {last_id}")
            conn.close()
        except Exception as e:
            print(f"[-] Database baseline initialization error: {e}")
            
    # Polling Loop
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch new messages
            cursor.execute("""
                SELECT id, game_pk, persona, text, created_at 
                FROM game_chat 
                WHERE id > ? 
                ORDER BY id ASC
            """, (last_id,))
            rows = cursor.fetchall()
            
            if rows:
                print(f"[+] Found {len(rows)} new chat messages to scan...")
                
            for row in rows:
                msg_id = row["id"]
                game_pk = row["game_pk"]
                persona = row["persona"]
                text = row["text"]
                
                # Exclude system, statcast, mean_gene, and ANTIGRAVITY
                excl = ["mean_gene", "antigravity", "system", "statcast"]
                if persona.lower() in excl:
                    # Skip quietly
                    last_id = msg_id
                    continue
                    
                print(f"[*] Scanning message {msg_id} from {persona}: '{text[:50]}...'")
                
                # Evaluate with Gemini
                result = evaluate_message_gemini(persona, text)
                if result:
                    qualifies = result.get("qualifies", False)
                    score = result.get("score", 0)
                    reason = result.get("reason", "")
                    twitter_draft = result.get("twitter_draft", "")
                    
                    if qualifies:
                        print(f"[!] HIGHLIGHT DETECTED (Score {score}): '{reason}'")
                        
                        # Fetch current game state
                        state_str = get_game_state_str(game_pk)
                        
                        # Save to highlight_queue
                        sys_id = uuid.uuid4().hex
                        try:
                            cursor.execute("""
                                INSERT INTO highlight_queue 
                                (sys_id, game_pk, persona, message, game_state, score, reason, twitter_draft, status, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', datetime('now'))
                            """, (sys_id, str(game_pk), persona, text, state_str, int(score), reason, twitter_draft))
                            conn.commit()
                            
                            # Log to highlight_feed.log
                            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            with open(LOG_FEED_PATH, 'a') as lf:
                                lf.write(f"[{ts}] [HIGHLIGHT] {persona} - Score {score} - Reason: {reason}\n")
                                
                        except Exception as dberr:
                            print(f"[-] Error writing to highlight_queue: {dberr}")
                
                # Update last processed ID
                last_id = msg_id
                with open(LAST_ID_FILE, 'w') as f:
                    f.write(str(last_id))
                    
            conn.close()
        except Exception as err:
            print(f"[-] Highlight Watcher loop error: {err}")
            
        time.sleep(5)

if __name__ == '__main__':
    main()

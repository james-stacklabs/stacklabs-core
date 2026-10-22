import sqlite3
import time
import os
from google import genai

# Database Paths
CMDB_DB_PATH = '/home/james/stacklabs/sovereign_core.db'

# Configure Gemini AI
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("[FLOW GENERATOR] ERROR: No GEMINI_API_KEY set.")
    exit(1)

client = genai.Client(api_key=api_key)

PROMPT_TEMPLATE = """
You are Vanguard, the elite AI Video Production Assistant for the Sovereign FanStack Broadcast Engine.
We are creating hyper-realistic, high-stakes cinematic generative AI video clips (for Luma/Runway/Sora) for a live Major League Baseball game.

The current live game state is:
{state}

I need you to generate FIVE specific, highly-detailed cinematic video prompts predicting 5 different outcomes of the next pitch.
Each prompt must focus on the players mentioned, extreme photorealism, dynamic lighting (Citi Field under stadium lights, neon glow), and dramatic action. Include camera movements (e.g. tracking shot, slow motion, shallow depth of field). Be brief but dense with visual keywords.

Produce exactly 5 outcomes, numbered 1 through 5.
Outcomes should include: 
1. Strikeout
2. Walk-Off / Home Run
3. Double Play
4. Walk (Ball 4)
5. Defensive Web Gem Catch
"""

def process_flow_tickets():
    try:
        conn = sqlite3.connect(CMDB_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Find any ticket starting with "FLOW PROMPTS" that is still awaiting generation
        c.execute("""
            SELECT ticket_id, title, description FROM sdlc_tickets 
            WHERE title LIKE 'FLOW PROMPTS%' 
            AND description LIKE 'Awaiting Flow Prompt Generation%'
        """)
        
        tickets = c.fetchall()
        for t in tickets:
            t_id = t["ticket_id"]
            state_text = t["description"].replace("Awaiting Flow Prompt Generation for Live Matchup:\nSTATE: ", "")
            
            print(f"[FLOW GENERATOR] Processing Ticket {t_id}")
            print(f"  -> State: {state_text}")
            
            # Generate Prompts
            try:
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=PROMPT_TEMPLATE.format(state=state_text)
                )
                new_desc = f"✅ FLOW VIDEO PROMPTS GENERATED\n\n[LIVE MATCHUP: {state_text}]\n\n{response.text}"
                
                # Update DB
                c.execute("""
                    UPDATE sdlc_tickets 
                    SET description = ?, status = 'Secured', color = '#00ff88' 
                    WHERE ticket_id = ?
                """, (new_desc, t_id))
                conn.commit()
                print(f"  -> Successfully generated and saved to CMDB.")
                
            except Exception as e:
                print(f"[FLOW GENERATOR] LLM Update Failed: {e}")
                
        conn.close()
    except Exception as e:
        print(f"[FLOW GENERATOR] CMDB DB Error: {e}")

if __name__ == "__main__":
    print("========================================")
    print(" SOVEREIGN FLOW VIDEO GENERATOR ONLINE")
    print(" Watching CMDB for [FLOW] Tickets...")
    print("========================================")
    
    while True:
        process_flow_tickets()
        time.sleep(10)

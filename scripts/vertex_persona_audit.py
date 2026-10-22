import os
import sqlite3
import datetime
import vertexai
from vertexai.generative_models import GenerativeModel
from concurrent.futures import ThreadPoolExecutor

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
CONTEXT_DB = "/home/james/stacklabs/dna/context_database.json"
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
PROJECT_ID = "gen-lang-client-0840454416"
LOCATION = "us-central1"

def get_mlb_news():
    import json
    if os.path.exists(CONTEXT_DB):
        try:
            with open(CONTEXT_DB, "r") as f:
                data = json.load(f)
                news = data.get("mlb_news", [])
                if news:
                    return "\n".join([f"- {item['title']}: {item['summary']}" for item in news])
        except Exception:
            pass
    return "No major MLB news right now."

def audit_single_persona(p, mlb_news):
    user_name = p['user_name']
    team = p['team']
    deep_lore = p['deep_lore'] or ""
    system_prompt = p['system_prompt'] or ""
    current_behavior = p['behavior_notes'] or ""
    
    prompt = f"""
You are auditing an AI persona in the Sovereign FanStack.
Persona Name: {user_name}
Team: {team}
System Prompt: {system_prompt}
Deep Lore: {deep_lore}

Today's MLB News:
{mlb_news}

Task:
1. Provide a short, 1-sentence contextual update that can be appended to their 'behavior_notes'. It should reflect how this specific character would react to the current MLB news. If the news doesn't mention their team, make it a general baseball complaint or superstition fitting their character.
2. Generate a 1-sentence in-character quote to verify they are functional.

Format exactly like this:
UPDATE: [Your 1 sentence update]
QUOTE: [Your 1 sentence in-character quote]
"""
    try:
        model = GenerativeModel("gemini-3.8-flash")
        response = model.generate_content(prompt, generation_config={"temperature": 0.7})
        parts_text = []
        if response and response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
        if parts_text:
            text = "".join(parts_text)
        else:
            try:
                text = response.text or ""
            except Exception:
                text = ""
        text = text.strip()
        
        update_line = ""
        quote_line = ""
        for line in text.split('\n'):
            if line.startswith("UPDATE:"):
                update_line = line.replace("UPDATE:", "").strip()
            elif line.startswith("QUOTE:"):
                quote_line = line.replace("QUOTE:", "").strip()
        
        if update_line and quote_line:
            import re
            cleaned_behavior = re.sub(r'^\d{4}-\d{2}-\d{2}:.*$', '', current_behavior, flags=re.MULTILINE).strip()
            if cleaned_behavior:
                new_behavior = f"{cleaned_behavior}\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {update_line}".strip()
            else:
                new_behavior = f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {update_line}".strip()
            return {
                "id": p['id'],
                "user_name": user_name,
                "behavior_notes": new_behavior,
                "quote": quote_line,
                "status": "success"
            }
        else:
            return {"user_name": user_name, "status": "failed", "error": "Invalid format"}
    except Exception as e:
        return {"user_name": user_name, "status": "failed", "error": str(e)}

def main():
    print(f"[{datetime.datetime.now()}] Starting Concurrent Vertex Persona Audit...")
    
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"Vertex AI init failed: {e}")
        return

    mlb_news = get_mlb_news()
    
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    cursor.execute("SELECT id, user_name, display_name, team, system_prompt, deep_lore, behavior_notes FROM persona")
    personas = [dict(r) for r in cursor.fetchall()]
    con.close()
    
    print(f"Auditing {len(personas)} personas in parallel...")
    
    results = []
    # Use max_workers=20 to parallelize safely and quickly without hit rate limits
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(audit_single_persona, p, mlb_news): p for p in personas}
        for future in futures:
            res = future.result()
            results.append(res)
            user_name = res["user_name"]
            if res["status"] == "success":
                print(f"[{user_name}] OK. Quote: \"{res['quote']}\"")
            else:
                print(f"[{user_name}] FAILED ({res.get('error')})")

    # Sequential DB Write
    print(f"[{datetime.datetime.now()}] Committing successful audits to database...")
    con = sqlite3.connect(DB_PATH)
    success_count = 0
    fail_count = 0
    for res in results:
        if res["status"] == "success":
            con.execute("UPDATE persona SET behavior_notes = ?, updated_at = ? WHERE id = ?", (res['behavior_notes'], datetime.datetime.now().isoformat(), res['id']))
            success_count += 1
        else:
            fail_count += 1
    con.commit()
    con.close()
    
    print("\n=== AUDIT COMPLETE ===")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    main()

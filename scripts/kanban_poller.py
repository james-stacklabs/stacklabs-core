import json
import time
import os
import google.genai as genai

# Load Gemini key
env_path = "/home/james/stacklabs/.env"
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                os.environ["GEMINI_API_KEY"] = line.strip().split("=", 1)[1]

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

KANBAN_FILE = "/home/james/stacklabs/01_Sovereign_Portal/public/agent_kanban.json"

print("Sovereign UI Poller initialized. Monitoring agent_kanban.json...")

def process_tickets():
    if not os.path.exists(KANBAN_FILE):
        return

    try:
        with open(KANBAN_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    changed = False
    for ticket in data.get("tasks", []):
        if ticket.get("status") == "Open":
            print(f"\n[!] New ticket detected: {ticket['id']}")
            
            # Immediately acknowledge and move to WIP to prevent duplicate processing
            ticket["status"] = "Work In Progress"
            try:
                with open(KANBAN_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
            except: pass
            
            # Formulate prompt for Gemini
            prompt = f"""
            You are the Sovereign M.A.R.D. automated background agent. 
            The user submitted an IT/Enhancement ticket from their phone.
            
            Ticket ID: {ticket['id']}
            Title: {ticket['title']}
            Description: {ticket['description']}
            
            Please acknowledge this ticket, state that you received it successfully via the new kanban poller daemon, and provide a brief friendly response or resolution plan. Keep it short (2-3 sentences max). This text will go into the 'Work Notes' field of the Service Operations Workspace UI.
            """
            
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt
                )
                reply_text = response.text.strip()
            except Exception as e:
                reply_text = f"Automated acknowledgment: Ticket received. (Error querying Gemini: {e})"
            
            print(f"[-] Resolution generated. Updating JSON.")
            ticket["status"] = "Resolved"
            ticket["work_notes"] = f"[Autonomous Daemon] {reply_text}"
            changed = True

    if changed:
        try:
            with open(KANBAN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            print("[+] Kanban updated and saved.")
        except Exception as e:
            print(f"Error saving JSON: {e}")

if __name__ == "__main__":
    while True:
        try:
            process_tickets()
        except Exception as e:
            print(f"Poller error: {e}")
        time.sleep(5)

#!/usr/bin/env python3
"""
Antigravity Ticket Watcher
Polls agent_kanban.json for Open tickets, assigns them to Antigravity, and marks them Resolved.
Run this while the pilot is mobile. Antigravity will action new tickets as they arrive.
"""

import json
import time
import os
import datetime

KANBAN_PATH = os.path.join(os.path.dirname(__file__), '../01_Sovereign_Portal/public/agent_kanban.json')
POLL_INTERVAL = 10  # seconds

def load_kanban():
    with open(KANBAN_PATH, 'r') as f:
        return json.load(f)

def save_kanban(data):
    with open(KANBAN_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def process_ticket(ticket):
    """
    Antigravity actions the ticket here.
    For now: acknowledge it, mark In Progress, then Resolved with work notes.
    Extend this with real work logic per ticket type.
    """
    title = ticket.get('title', '')
    description = ticket.get('description', '')
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n[ANTIGRAVITY] 🎫 New ticket: {ticket['id']} — {title}")
    
    # Mark WIP
    ticket['status'] = 'Work In Progress'
    ticket['assignee'] = 'Antigravity'
    ticket['updated'] = now
    save_kanban(load_kanban())  # reload to avoid stale state
    
    # Simulate work (real work dispatched by Antigravity in IDE)
    time.sleep(2)
    
    # Mark Resolved & shift to UAT Testing state via hook
    import sys
    import glob
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Dynamically find the walkthrough path
    search_patterns = [
        f"/home/james/.gemini/antigravity/brain/*/walkthrough_{ticket['id'].lower()}.md",
        f"/home/james/.gemini/antigravity/brain/*/walkthrough_{ticket['id'].upper()}.md",
        f"/home/james/stacklabs/walkthrough_{ticket['id'].lower()}.md",
        f"/home/james/stacklabs/walkthrough_{ticket['id'].upper()}.md",
    ]
    walkthrough_file = None
    for pattern in search_patterns:
        matches = glob.glob(pattern)
        if matches:
            walkthrough_file = os.path.abspath(matches[0])
            break
            
    success = False
    if walkthrough_file:
        try:
            from sdlc_completion_hook import execute_completion_hook
            success = execute_completion_hook(ticket['id'], walkthrough_file)
        except Exception as e:
            print(f"[ANTIGRAVITY] Hook execution error: {e}")
    else:
        print(f"[ANTIGRAVITY] No walkthrough found for ticket {ticket['id']}. Cannot reassign to UAT.")
        
    if success:
        ticket['status'] = 'Testing'
        ticket['assignee'] = 'Vertex_UAT_Agent'
        ticket['work_notes'] = f"[{now}] Actioned by Antigravity. Walkthrough registered and attached to sys_attachment. Ticket reassigned to Vertex_UAT_Agent for automated UAT."
        print(f"[ANTIGRAVITY] 🧪 State-shifted to Testing / Vertex_UAT_Agent: {ticket['id']}")
    else:
        # Fallback if completion hook fails (e.g. no walkthrough)
        ticket['status'] = 'Open'
        ticket['assignee'] = ''
        ticket['work_notes'] = f"[{now}] Actioned by Antigravity but walkthrough was missing. Placed back to Open."
        print(f"[ANTIGRAVITY] ⚠️ Walkthrough missing, ticket reset to Open: {ticket['id']}")
        
    ticket['updated'] = now
    return ticket

def run():
    print(f"[ANTIGRAVITY] 🔍 Ticket watcher active. Polling every {POLL_INTERVAL}s...")
    print(f"[ANTIGRAVITY] 📄 Watching: {os.path.abspath(KANBAN_PATH)}\n")
    
    while True:
        try:
            data = load_kanban()
            tasks = data.get('tasks', [])
            changed = False
            
            for ticket in tasks:
                if ticket.get('status') == 'Open':
                    ticket = process_ticket(ticket)
                    changed = True
            
            if changed:
                save_kanban(data)
                print(f"[ANTIGRAVITY] 💾 Kanban updated.")
            else:
                print(f"[ANTIGRAVITY] 💤 No open tickets. Sleeping...", end='\r')
                
        except Exception as e:
            print(f"[ANTIGRAVITY] ⚠️ Error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    run()

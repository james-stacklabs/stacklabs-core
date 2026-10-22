import requests
import os
import argparse

def close_ticket(number, work_notes, walkthrough_path=None):
    print(f"\n=======================================================")
    print(f"🔒 CLOSING TICKET: {number}")
    print(f"=======================================================")
    
    # 1. PUT to /api/tickets/{number}
    url = f"http://localhost:8095/api/tickets/{number}"
    payload = {
        "status": "RESOLVED",
        "work_notes": work_notes
    }
    
    try:
        r = requests.put(url, json=payload, timeout=10)
        print(f"Step 1: PUT status code: {r.status_code}")
        print(f"Response: {r.json()}")
    except Exception as e:
        print(f"❌ Step 1 FAILED: {e}")
        return False
        
    # 2. POST walkthrough.md as attachment to /api/tickets/{number}/attachments
    success = False
    if walkthrough_path and os.path.exists(walkthrough_path):
        url_att = f"http://localhost:8095/api/tickets/{number}/attachments"
        files = {
            "file": (os.path.basename(walkthrough_path), open(walkthrough_path, "rb"), "text/markdown")
        }
        try:
            r_att = requests.post(url_att, files=files, timeout=10)
            print(f"Step 2: POST Attachment status code: {r_att.status_code}")
            print(f"Response: {r_att.json()}")
            success = True
        except Exception as e:
            print(f"❌ Step 2 FAILED: {e}")
            success = False
    else:
        if walkthrough_path:
            print(f"❌ Walkthrough not found at: {walkthrough_path}")
        else:
            print("ℹ️ No walkthrough path provided/found. Resolving without attachment.")
        success = True

    if success:
        # 3. Trigger cloud sync to Google Drive for NotebookLM ingestion
        print("\n🔄 Triggering targeted cloud synchronization to Google Drive...")
        import subprocess
        try:
            res = subprocess.run(["/home/james/stacklabs/scripts/sync_to_gdrive.sh"], capture_output=True, text=True)
            if res.returncode == 0:
                print("🟢 Cloud synchronization completed successfully.")
            else:
                print(f"⚠️ Cloud synchronization exited with status code {res.returncode}")
                print(res.stderr)
        except Exception as e:
            print(f"❌ Failed to run sync_to_gdrive.sh: {e}")

    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign OS Ticket Closure CLI Tool")
    parser.add_argument("tickets", nargs="+", help="One or more ticket IDs (e.g. STRY1779973335)")
    parser.add_argument("-n", "--notes", required=True, help="Resolution work notes")
    parser.add_argument("-w", "--walkthrough", help="Optional explicit path to the walkthrough markdown file")
    
    args = parser.parse_args()
    
    for ticket in args.tickets:
        w_path = args.walkthrough
        if not w_path:
            # Check default locations in sovereign_inbox
            candidates = [
                f"/home/james/sovereign_inbox/walkthroughs/walkthrough_{ticket}.md",
                f"/home/james/sovereign_inbox/walkthroughs/walkthrough_{ticket.lower()}.md",
                f"/home/james/sovereign_inbox/walkthroughs/walkthrough_{ticket.upper()}.md",
                f"/home/james/sovereign_inbox/tickets/walkthrough_{ticket}.md",
                f"/home/james/sovereign_inbox/tickets/walkthrough_{ticket.lower()}.md",
                f"/home/james/sovereign_inbox/tickets/walkthrough_{ticket.upper()}.md",
                f"/home/james/sovereign_inbox/walkthrough_{ticket}.md",
                f"/home/james/sovereign_inbox/walkthrough_{ticket.lower()}.md",
                f"/home/james/sovereign_inbox/walkthrough_{ticket.upper()}.md",
            ]
            for cand in candidates:
                if os.path.exists(cand):
                    w_path = cand
                    break
        
        close_ticket(ticket, args.notes, w_path)


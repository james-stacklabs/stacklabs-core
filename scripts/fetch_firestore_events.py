#!/home/james/stacklabs/.venv/bin/python3
import json
import requests
import sys

def fetch_all_events():
    url = "https://firestore.googleapis.com/v1/projects/sam-tracker-1a9a6/databases/(default)/documents/events"
    params = {"pageSize": 100}
    all_docs = []

    print("Starting download of Firestore documents...")
    while True:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"Error fetching data: {resp.status_code} - {resp.text}")
            sys.exit(1)
        
        data = resp.json()
        docs = data.get("documents", [])
        all_docs.extend(docs)
        print(f"Retrieved {len(docs)} documents (Total so far: {len(all_docs)})")
        
        next_token = data.get("nextPageToken")
        if not next_token:
            break
        params["pageToken"] = next_token

    output_path = "/home/james/sovereign_inbox/firestore_events.json"
    with open(output_path, "w") as f:
        json.dump(all_docs, f, indent=2)
    
    print(f"\nSuccessfully exported {len(all_docs)} Firestore documents to: {output_path}")

if __name__ == "__main__":
    fetch_all_events()

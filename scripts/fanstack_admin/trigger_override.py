import requests
import json
import sys

API_URL = "http://127.0.0.1:5055/api/admin/override"

def send_override(json_filepath):
    """
    Reads a standalone JSON manifest file and fires it into the FanStack Admin Interface.
    """
    try:
        with open(json_filepath, 'r') as f:
            payload = json.load(f)
            
        print(f"📡 Sending Override Payload to {API_URL}...")
        
        response = requests.post(API_URL, json=payload, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            print(f"✅ Success: {response.json().get('message')}")
        else:
            print(f"❌ Failed ({response.status_code}): {response.json().get('message', response.text)}")
            
    except FileNotFoundError:
        print(f"Error: Payload file '{json_filepath}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{json_filepath}'.")
    except requests.ConnectionError:
        print(f"Error: Could not connect to FanStack Admin API at {API_URL}. Is the daemon running?")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 trigger_override.py <payload.json>")
        sys.exit(1)
        
    send_override(sys.argv[1])

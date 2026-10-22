import os
import json
import time
import requests
from dotenv import load_dotenv

# Initialize
load_dotenv('/home/james/stacklabs/.env')
TELEMETRY_PATH = '/home/james/stacklabs/04_Sovereign_Core/telemetry.json'

def init_telemetry():
    return {
        "timestamp": int(time.time()),
        "mesh_status": "SECURE",
        "tractive": {
            "status": "INITIALIZING",
            "battery": "--",
            "location": "Awaiting API"
        },
        "govee": {
            "status": "INITIALIZING"
        },
        "webcams": {
            "status": "AWAITING RTSP/NEST STREAM"
        }
    }

def fetch_govee(api_key):
    if not api_key:
        return {"status": "NO API KEY FOUND"}
    
    try:
        url = "https://developer-api.govee.com/v1/devices"
        headers = {
            "Govee-API-Key": api_key,
            "Content-Type": "application/json"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            # Just grabbing device counts/names for MVP
            devices = data.get("data", {}).get("devices", [])
            return {
                "status": "ONLINE",
                "device_count": len(devices),
                "list": [d.get("deviceName") for d in devices]
            }
        else:
            return {"status": f"API ERROR: {resp.status_code}"}
    except Exception as e:
        return {"status": f"SYNC FAILED: {str(e)}"}

def fetch_tractive():
    token = os.getenv('TRACTIVE_ACCESS_TOKEN')
    if not token:
        return {
            "status": "AWAITING CREDENTIALS",
            "battery": "--",
            "location": "Add TRACTIVE_ACCESS_TOKEN to .env"
        }
    
    # Simple Web API ping matching the DevTools session
    try:
        # XHRMVRYR is Metsy's Tracker ID
        url = "https://graph.tractive.com/4/tracker/XHRMVRYR"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-tractive-client": "web-app"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            # If successful, parse battery and location
            state = data.get('state', {})
            return {
                "status": "TRACKING",
                "battery": f"{state.get('battery_level', 0)}%",
                "location": f"LAT/LON SYNCED" # Mocked until real structure parsed
            }
        else:
            return {
                "status": f"API ERROR: {resp.status_code}",
                "battery": "--",
                "location": "Token possibly expired"
            }
    except Exception as e:
        return {"status": f"SYNC FAILED: {str(e)}", "battery": "--", "location": "Error"}

def update_telemetry():
    telemetry = init_telemetry()
    
    # Govee Fetch
    govee_key = os.getenv('GOVEE_API_KEY')
    telemetry["govee"] = fetch_govee(govee_key)
    
    # Tractive Fetch
    telemetry["tractive"] = fetch_tractive()

    # Save to JSON for UI
    os.makedirs(os.path.dirname(TELEMETRY_PATH), exist_ok=True)
    with open(TELEMETRY_PATH, 'w') as f:
        json.dump(telemetry, f, indent=4)

if __name__ == "__main__":
    print("[ULTRON] Synchronizing GreenStack Telemetry...")
    update_telemetry()
    print("[ULTRON] Telemetry sync complete. Payload saved to core.")

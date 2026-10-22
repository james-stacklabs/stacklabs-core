import os
import time
import json
import asyncio
import requests
from dotenv import load_dotenv
from google.cloud import pubsub_v1

load_dotenv('/home/james/stacklabs/.env')

# =========================================================================
# SOVEREIGN OS: NEST PUB/SUB DAEMON
# Subscribes to the SDM API Pub/Sub topic and forwards Familiar Face events
# to the local SamTracker core daemon.
# =========================================================================

# Credentials (to be populated)
CLIENT_ID = os.getenv("NEST_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("NEST_CLIENT_SECRET", "")
REFRESH_TOKEN = os.getenv("NEST_REFRESH_TOKEN", "")
PROJECT_ID = "sovereign-nest-bridge"
SUBSCRIPTION_NAME = f"projects/{PROJECT_ID}/subscriptions/sovereign-nest-sub"

# Configure Service Account Authentication for Pub/Sub
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/james/sovereign_inbox/today/sovereign-nest-bridge-b4107e3c7572.json"

SAM_TRACKER_URL = "http://127.0.0.1:8093/sam/api/internal/cat_alert"

def process_nest_event(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        
        # Check if this is an SDM event
        events = data.get("resourceUpdate", {}).get("events", {})
        
        # LOG EVERYTHING FOR DEBUGGING
        print(f"\n[NEST PULL] RAW EVENT RECEIVED:")
        print(json.dumps(events, indent=2))
        
        for event_type, event_data in events.items():
            if event_type == "sdm.devices.events.CameraPerson.Person":
                person_name = event_data.get("personName", "Unknown Person")
                print(f"[NEST PULL] Person detected: {person_name}")
                
                # Check for cats
                name_lower = person_name.lower()
                cat_detected = None
                if "sam" in name_lower:
                    cat_detected = "sam"
                elif "metsy" in name_lower:
                    cat_detected = "metsy"
                
                if cat_detected:
                    print(f"🐈 [NEST PULL] {cat_detected.upper()} DETECTED! Firing Webhook to SamTracker Core...")
                    payload = {"cat": cat_detected, "source": "nest_camera"}
                    try:
                        requests.post(SAM_TRACKER_URL, json=payload, timeout=5)
                    except Exception as e:
                        print(f"[NEST PULL] Failed to trigger SamTracker webhook: {e}")

        # Acknowledge the message so it doesn't get redelivered
        message.ack()
    except Exception as e:
        print(f"[NEST PULL] Error processing message: {e}")
        message.nack()

def listen_for_events():
    print("[NEST PULL] Initializing Sovereign Nest Bridge...")
    
    # We use the explicit Service Account JSON for Pub/Sub authentication
    subscriber = pubsub_v1.SubscriberClient()
    
    print(f"[NEST PULL] Listening for events on {SUBSCRIPTION_NAME}...\n")
    streaming_pull_future = subscriber.subscribe(SUBSCRIPTION_NAME, callback=process_nest_event)
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
    except Exception as e:
        print(f"[NEST PULL] Subscriber failed: {e}")

if __name__ == "__main__":
    if not REFRESH_TOKEN:
        print("Waiting for credentials to be populated in .env...")
    else:
        listen_for_events()

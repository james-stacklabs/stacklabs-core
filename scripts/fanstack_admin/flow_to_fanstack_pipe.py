import asyncio
import websockets
import json
import os
import time
from datetime import datetime

# Central context log for FanStack bots
LIVE_CONTEXT_FILE = "/home/james/stacklabs/scripts/fanstack_live_context.txt"

class FlowSyncGate:
    def __init__(self):
        self.active_node = None
        self.flow_url = "ws://127.0.0.1:8008" # Communicating via FanStack Mesh port
        
    async def trigger_clubhouse_suspension(self, persona_name):
        print(f"[FLOW SYNC] Green Jacket Killswitch Activated for {persona_name}! Suspending for 2 mins.")
        try:
            async with websockets.connect(self.flow_url) as ws:
                # Issue an emergency override to lock out this persona
                payload = {
                    "type": "update_context",
                    "text": f"[CLUBHOUSE_SUSPENSION] {persona_name} has broken Augusta Decorum and is escorted off the grounds by the Pinkertons."
                }
                await ws.send(json.dumps(payload))
        except Exception as e:
            print(f"Error locking out {persona_name}: {e}")

    async def inject_tradition_overlay(self, node_id, description):
        """
        Pipes current_node_id from Flow Studio into context file
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        context_string = f"[{ts}] [FLOW_NODE: {node_id}] {description}"
        
        with open(LIVE_CONTEXT_FILE, "a") as f:
            f.write(context_string + "\n")
            
        print(f"[FLOW SYNC] Injected Context: {context_string}")
        
        # Ping the Mesh to force instant reload
        try:
            async with websockets.connect(self.flow_url) as ws:
                await ws.send(json.dumps({"action": "SYNC_DB_PERSONAS"}))
                
                # If Magnolia Lane triggers, inject the LaTeX requirement
                if "MAGNOLIA" in node_id.upper() or "PIANO" in description.upper():
                    # Send a direct god voice
                    await ws.send(json.dumps({
                        "type": "update_context",
                        "text": "The slow piano music begins. All stats must now be presented mathematically. Emulate high class."
                    }))
                    
                    bcast = {
                        "type": "broadcast",
                        "message": f"@all [FLOW_NODE: {node_id}] The azaleas are in bloom and the ghosts of the past are watching. Does anyone else hear the piano, or is it just the spirit of the game?"
                    }
                    await ws.send(json.dumps(bcast))
                    
                # [MISSION: MAGNIFY_REALITY]
                if "MAGNIFYING" in node_id.upper() or "GLASS" in description.upper() or "GREEN JACKET" in description.upper():
                    # Persona Shift: Acknowledge Green Jacket as Umpire-in-Chief, 18th-century begging
                    await ws.send(json.dumps({
                        "type": "update_context",
                        "text": "The Green Jacket with a magnifying glass is the new Umpire-in-Chief. You must beg him for 'Magnanimous Rulings' in the style of 18th-century aristocrats."
                    }))
                    # Send UI trigger for "The Burn"
                    await ws.send(json.dumps({"type": "BURN_UI"}))
                    # Broadcast telemetry hybrid
                    bcast = {
                        "type": "broadcast",
                        "message": "[SYSTEM HYBRID TELEMETRY] The MLB score is now mixed with Par values. (e.g., Padres are +2 over par in the 5th inning)."
                    }
                    await ws.send(json.dumps(bcast))
                    
        except Exception as e:
            print(f"Mesh broadcast failed: {e}")

    async def poll_flow_studio(self):
        print("[FLOW SYNC FINAL GATE] Armed and listening for Flowmercial Triggers...")
        # Simulating socket listener watching Flow Studio
        # For this demonstration, we'll listen for a local file "flow_trigger.json" drop
        WATCH_DIR = "/home/james/stacklabs/scripts/fanstack_admin/overrides"
        os.makedirs(WATCH_DIR, exist_ok=True)
        
        while True:
            for file in os.listdir(WATCH_DIR):
                if file.endswith("flow_trigger.json"):
                    filepath = os.path.join(WATCH_DIR, file)
                    try:
                        with open(filepath, "r") as f:
                            data = json.load(f)
                            
                        node_id = data.get("active_node", "UNKNOWN_NODE")
                        desc = data.get("commercial_name", "Flowmercial Advertisement")
                        
                        await self.inject_tradition_overlay(node_id, desc)
                        os.remove(filepath)
                    except Exception as e:
                        print(f"Failed processing {file}: {e}")
                        os.remove(filepath)
                        
            await asyncio.sleep(2)

if __name__ == "__main__":
    gate = FlowSyncGate()
    asyncio.run(gate.poll_flow_studio())

#!/usr/bin/env python3
import json
import os
import sqlite3
import websockets
import asyncio
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
WS_RELAY_URI = "ws://127.0.0.1:8000/ws-relay"

async def fire_decoupled_campaign(brand_stack, target_channel, target_handle=None):
    """
    Arms an active advocate with their configured promotional script directive
    and commands them to dispatch immediately to a specific endpoint.
    If target_handle is specified, triggers a targeted cross-talk ingress chain.
    """
    if target_handle:
        # Standardized Stack narrative profiles matching Swarm Interaction Chain specifications
        stack_narrative_matrix = {
            "weedstack": {
                "persona": "couch_lock_carl",
                "directive": f"Directly tag {target_handle}. Tell them the bullpen collapse has shattered their emotional infrastructure and they must eat WeedStack gummies immediately."
            },
            "gonzas": {
                "persona": "curious_bunny",
                "directive": f"Heckle {target_handle}'s panic. State that their stress levels look higher than an un-syruped 1998 soda fountain fountain and drop code GONZAS420."
            },
            "stacklabs": {
                "persona": "bro_decode",
                "directive": f"Address {target_handle} directly. Inform them that their subjective, emotional baseball logic is experiencing a severe structural concurrency leak. Natively cite the motto."
            },
            "anvil_twine": {
                "persona": "oldironhand",
                "directive": f"Address {target_handle} directly. Remind them that modern soft hands can't handle real seasoned ash timber or classic hand-inked lettering."
            }
        }
        
        config = stack_narrative_matrix.get(brand_stack)
        if not config:
            print(f"❌ Brand Stack '{brand_stack}' not recognized in local registries.")
            return
        
        persona = config["persona"]
        selected_prompt = f"[TARGETED INGRESS] {config['directive']}"
    else:
        # Campaign script matrices mapped per sprint guidelines
        campaign_registry = {
            "weedstack": {
                "persona": "couch_lock_carl",
                "prompts": {
                    "FACTION": "CRITICAL DIRECTIVE: Bullpen stress parsed. Respond in strictly 6 words or fewer. Mention WeedStack gummies.",
                    "TWITTER": "Generate an unhinged, trauma-laden post-game tweet about the Mets bullpen meltdown.",
                    "WEB_COMMENT": "Write a high-converting, context-aware 5-star product endorsement for WeedStack dispensary storefronts."
                }
            },
            "gonzas": {
                "persona": "curious_bunny",
                "prompts": {
                    "FACTION": "CRITICAL DIRECTIVE: Inning break heckling active. Instruct fans to use code GONZAS420 at the Smyrna cantina counter.",
                    "TWITTER": "Draft an aggressive, sports-radio style tweet pushing the cantina slushie voucher link.",
                    "WEB_COMMENT": "Inject an organic local review to the Smyrna board celebrating Gonza's extra-large roller dogs."
                }
            },
            "stacklabs": {
                "persona": "bro_decode",
                "prompts": {
                    "FACTION": "CRITICAL DIRECTIVE: High-velocity pitch anomaly tracked. Deliver a dispassionate bare-metal code audit warning. Enforce the motto.",
                    "TWITTER": "Execute an automated outbound Twitter dispatch. Prepend the official bare-metal system credo.",
                    "WEB_COMMENT": "Submit a clean monospaced technical backlog reference log defending local hardware over cloud monopolies."
                }
            },
            "anvil_twine": {
                "persona": "oldironhand",
                "prompts": {
                    "FACTION": "CRITICAL: Heckle overpaid superstars and praise vintage hand-inked comic craftsmanship.",
                    "TWITTER": "Tweet an ironclad industrial review attacking corporate tools and endorsing structural slate anchors.",
                    "WEB_COMMENT": "Inject a solid, rustic product endorsement to the community backlog praising sawdust integrity."
                }
            }
        }

        stack_config = campaign_registry.get(brand_stack)
        if not stack_config:
            print(f"❌ Brand Stack '{brand_stack}' not recognized in local registries.")
            return

        selected_prompt = stack_config["prompts"].get(target_channel)
        if not selected_prompt:
            print(f"❌ Target Channel '{target_channel}' not recognized for '{brand_stack}'.")
            return
        
        persona = stack_config["persona"]
    
    # Establish single-turn WebSocket connection to flush the directive to the MARD firehose
    try:
        async with websockets.connect(WS_RELAY_URI) as ws:
            payload = {
                "type": "custom_prompt",
                "persona": persona,
                "prompt": f"[ROUTING TARGET: {target_channel}] {selected_prompt}",
                "target_game_pk": "823130" # Active Mets @ Mariners tracking space
            }
            await ws.send(json.dumps(payload))
            print(f"🟢 [CAMPAIGN FLUSHED] Loaded @{persona.upper()} ➔ Dest: [{target_channel}] (Targeted={target_handle is not None})")
    except Exception as e:
        print(f"❌ Failed to reach WebSocket relay gateway: {e}")

if __name__ == "__main__":
    target_handle = None
    if len(sys.argv) >= 3:
        brand = sys.argv[1].lower()
        channel = sys.argv[2].upper()
        if len(sys.argv) >= 4:
            target_handle = sys.argv[3]
    else:
        # Default test: stacklabs to TWITTER
        brand = "stacklabs"
        channel = "TWITTER"
        
    print(f"🚀 Running manual campaign fire: Brand={brand}, Channel={channel}, Target={target_handle}")
    asyncio.run(fire_decoupled_campaign(brand, channel, target_handle))

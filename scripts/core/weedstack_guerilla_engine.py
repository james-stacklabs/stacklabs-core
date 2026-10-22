#!/usr/bin/env python3
"""
scripts/core/weedstack_guerilla_engine.py
Sovereign OS: WeedStack "Mean Gene" Guerilla Discourse & Advocate Triad Engine
Orchestrates the 4-step wrestling heel-and-face kayfabe loop across live sports chat.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import websockets

logger = logging.getLogger("weedstack_guerilla_engine")

WEEDSTACK_DISCOURSE_SEQUENCE = [
    {
        "step": 1,
        "persona": "weedstack_shill_bot",
        "display_name": "WeedStack Shill Bot",
        "color": "#22c55e",
        "text": "🚨🚨 HEY BRO GET 20% OFF WEEDSTACK METS GUMMIES USE CODE METS420 FOR FREE SHIPPING AT CHECKOUT 🚨🚨",
        "delay_after": 2.5,
        "mediaUrl": None
    },
    {
        "step": 2,
        "persona": "420_linda",
        "display_name": "420 Linda",
        "color": "#FF5910",
        "text": "Ugh get out of here bot! Nobody wants your spam in this chat!",
        "delay_after": 3.0,
        "mediaUrl": None
    },
    {
        "step": 3,
        "persona": "weedstack_shill_bot",
        "display_name": "WeedStack Shill Bot",
        "color": "#22c55e",
        "text": "🚨🚨 BRO DON'T SLEEP ON OUR SOLVENTLESS LIVE RESIN PEACH RINGS 50% OFF WITH CODE METS420 TODAY ONLY 🍃💨🚨🚨",
        "delay_after": 2.5,
        "mediaUrl": None
    },
    {
        "step": 4,
        "persona": "420_linda",
        "display_name": "420 Linda",
        "color": "#FF5910",
        "text": "Deadass, can someone mute this clown? We're trying to watch McLean pitch!",
        "delay_after": 3.0,
        "mediaUrl": None
    },
    {
        "step": 5,
        "persona": "weedstack_shill_bot",
        "display_name": "WeedStack Shill Bot",
        "color": "#22c55e",
        "text": "🚨🚨 CODE METS420 WORKS ON ALL PRE-ROLLS AND EDIBLES CLICK LINK IN BIO BRO 🚨🚨",
        "delay_after": 2.5,
        "mediaUrl": None
    },
    {
        "step": 6,
        "persona": "mean_gene_bouncer",
        "display_name": "Mean Gene",
        "color": "#ef4444",
        "text": "HOLD ON A MINUTE! Look at this shameless robotic huckster trying to peddle wares during a 3-2 count with bases loaded! Security, grab this clown! @weedstack_shill_bot has been exiled to the CypherCell for 300 seconds! [CYPHERCELL EXILE] Keep this room clean!",
        "delay_after": 4.0,
        "mediaUrl": None
    },
    {
        "step": 7,
        "persona": "420_linda",
        "display_name": "420 Linda",
        "color": "#FF5910",
        "text": "LMAOOO thank god Mean Gene tossed that bot into the cooler 😂 What a complete jerk. Though not gonna lie... I actually had two of those WeedStack live resin peach rings during yesterday's bullpen meltdown and they had me floating through the 8th inning...",
        "delay_after": 3.5,
        "mediaUrl": None
    },
    {
        "step": 8,
        "persona": "terpene_ted",
        "display_name": "Terpene Ted",
        "color": "#10b981",
        "text": "Deadass Linda, those peach rings taste like real fruit and hit smooth. But yeah, keep that robotic spam out of the chat thread lol.",
        "delay_after": 0.0,
        "mediaUrl": None
    }
]


async def broadcast_chat_message(ws_url: str, message: Dict[str, Any], room_id: str) -> bool:
    """Send a single chat message to the WebSocket relay mesh."""
    try:
        async with websockets.connect(ws_url, open_timeout=5) as ws:
            # First join room if needed
            join_msg = {
                "action": "JOIN_ROOM",
                "room": str(room_id),
                "target_game_pk": str(room_id)
            }
            await ws.send(json.dumps(join_msg))
            await asyncio.sleep(0.05)

            # Send the chat message
            payload = {
                "type": "CHAT_MESSAGE",
                "room": str(room_id),
                "target_game_pk": str(room_id),
                "user": message["persona"],
                "persona": message["persona"],
                "color": message["color"],
                "text": message["text"],
                "model_engine": "WEEDSTACK_GUERILLA_MARD",
                "is_penalty_box": False,
                "channel": "system_broadcast",
                "mediaUrl": message.get("mediaUrl"),
                "timestamp": datetime.now().isoformat()
            }
            await ws.send(json.dumps(payload))
            logger.info(f"✔ [WEEDSTACK DISCOURSE] @{message['persona']}: {message['text'][:60]}...")
            return True
    except Exception as e:
        logger.warning(f"⚠️ [WEEDSTACK DISCOURSE WS WARNING]: Could not deliver via WebSocket {ws_url}: {e}")
        return False


async def execute_weedstack_guerilla_discourse(
    room_id: str = "823498",
    ws_url: str = "ws://127.0.0.1:8008",
    delay_override: Optional[float] = None
) -> Dict[str, Any]:
    """
    Executes the 4-step wrestling heel-and-face kayfabe loop:
    1. Shill bot drops promo.
    2. Mean Gene exiles the bot to CypherCell with [CYPHERCELL EXILE].
    3. Linda drops organic Mets fan review.
    4. Ted co-signs living-soil quality.
    """
    executed_steps = []
    start_time = time.time()

    for item in WEEDSTACK_DISCOURSE_SEQUENCE:
        step_num = item["step"]
        persona = item["persona"]
        text = item["text"]
        
        # Broadcast to WebSocket mesh
        ws_delivered = await broadcast_chat_message(ws_url, item, room_id)
        
        step_record = {
            "step": step_num,
            "persona": persona,
            "text": text,
            "delivered_ws": ws_delivered,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        executed_steps.append(step_record)

        # Handle delay
        delay = delay_override if delay_override is not None else item["delay_after"]
        if delay > 0:
            await asyncio.sleep(delay)

    duration = round(time.time() - start_time, 2)
    return {
        "status": "SUCCESS",
        "room_id": str(room_id),
        "protocol": "WRESTLING_HEEL_AND_FACE_GUERILLA_LOOP",
        "bot_heel": "weedstack_shill_bot",
        "bouncer": "mean_gene_bouncer",
        "organic_infiltrator": "420_linda",
        "co_signer": "terpene_ted",
        "steps_executed": len(executed_steps),
        "duration_seconds": duration,
        "transcript": executed_steps
    }


if __name__ == "__main__":
    import sys
    target_room = sys.argv[1] if len(sys.argv) > 1 else "823498"
    print(f"🚀 Running WeedStack Guerilla Discourse Loop for Room {target_room}...")
    res = asyncio.run(execute_weedstack_guerilla_discourse(room_id=target_room, delay_override=0.5))
    print(json.dumps(res, indent=2))

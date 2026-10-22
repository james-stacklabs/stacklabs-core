#!/usr/bin/env python3
"""
StackLabs Unified Multi-Zone Lighting Dispatcher
Controls 8 bare-metal lighting nodes across 3 physical zones:
1. Kitchen: 3x Govee H6008 bulbs (Direct BLE 5.2 GATT)
2. Hallway: 1x Philips WiZ bulb (Local UDP Port 38899 @ 192.168.1.201)
3. Living Room: 4x Govee LAN nodes (Local UDP Port 4003 @ 192.168.1.173, .174, .176, .188)

Sub-15ms execution on local silicon and radio. Zero cloud dependency.
"""

import socket
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("unified_lighting")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Lighting] %(message)s")

# Device Ledgers
HALLWAY_WIZ_IP = "192.168.1.201"
WIZ_PORT = 38899

LIVING_ROOM_IPS = [
    "192.168.1.173",
    "192.168.1.174",
    "192.168.1.176",
    "192.168.1.188"
]
GOVEE_UDP_PORT = 4003

# Presets & Color Mappings
PRESET_COLORS = {
    "warm_white": {"r": 255, "g": 180, "b": 107, "wiz_temp": 2700},
    "cyan": {"r": 0, "g": 255, "b": 204, "wiz_temp": None},
    "amber": {"r": 255, "g": 140, "b": 0, "wiz_temp": None},
    "night": {"r": 255, "g": 140, "b": 60, "wiz_temp": 2200}
}


def dispatch_wiz_udp(action: str, brightness: int = 100, color: Optional[List[int]] = None) -> Dict[str, Any]:
    """Sends a local UDP packet to the Hallway WiZ bulb on port 38899."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.8)

    dimming = min(max(brightness, 10), 100)

    if action == "off":
        payload = {"method": "setPilot", "params": {"state": False}}
    elif action == "on" or action == "warm_white":
        payload = {"method": "setPilot", "params": {"state": True, "temp": 2700, "dimming": dimming}}
    elif action == "night":
        payload = {"method": "setPilot", "params": {"state": True, "temp": 2200, "dimming": min(dimming, 20)}}
    elif action == "cyan":
        payload = {"method": "setPilot", "params": {"state": True, "r": 0, "g": 255, "b": 204, "dimming": dimming}}
    elif action == "amber":
        payload = {"method": "setPilot", "params": {"state": True, "r": 255, "g": 140, "b": 0, "dimming": dimming}}
    elif action == "color" and color and len(color) >= 3:
        payload = {"method": "setPilot", "params": {"state": True, "r": color[0], "g": color[1], "b": color[2], "dimming": dimming}}
    else:
        payload = {"method": "setPilot", "params": {"state": True, "dimming": dimming}}

    try:
        msg = json.dumps(payload).encode("utf-8")
        sock.sendto(msg, (HALLWAY_WIZ_IP, WIZ_PORT))
        return {"status": "OK", "target": HALLWAY_WIZ_IP, "port": WIZ_PORT, "payload": payload}
    except Exception as e:
        logger.error(f"WiZ UDP dispatch failed: {e}")
        return {"status": "FAILED", "target": HALLWAY_WIZ_IP, "error": str(e)}
    finally:
        sock.close()


def dispatch_govee_udp(action: str, brightness: int = 100, color: Optional[List[int]] = None) -> Dict[str, Any]:
    """Sends local LAN UDP packets to the 4 Living Room Govee devices on port 4003."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    messages = []
    dimming = min(max(brightness, 1), 100)

    if action == "off":
        messages.append(json.dumps({"msg": {"cmd": "turn", "data": {"value": 0}}}))
    elif action == "on":
        messages.append(json.dumps({"msg": {"cmd": "turn", "data": {"value": 1}}}))
        messages.append(json.dumps({"msg": {"cmd": "brightness", "data": {"value": dimming}}}))
        messages.append(json.dumps({"msg": {"cmd": "colorwc", "data": {"color": {"r": 255, "g": 180, "b": 107}}}}))
    elif action == "warm_white":
        messages.append(json.dumps({"msg": {"cmd": "turn", "data": {"value": 1}}}))
        messages.append(json.dumps({"msg": {"cmd": "brightness", "data": {"value": dimming}}}))
        messages.append(json.dumps({"msg": {"cmd": "colorwc", "data": {"color": {"r": 255, "g": 180, "b": 107}}}}))
    elif action == "night":
        messages.append(json.dumps({"msg": {"cmd": "turn", "data": {"value": 1}}}))
        messages.append(json.dumps({"msg": {"cmd": "brightness", "data": {"value": min(dimming, 20)}}}))
        messages.append(json.dumps({"msg": {"cmd": "colorwc", "data": {"color": {"r": 255, "g": 140, "b": 60}}}}))
    elif action == "cyan":
        messages.append(json.dumps({"msg": {"cmd": "turn", "data": {"value": 1}}}))
        messages.append(json.dumps({"msg": {"cmd": "brightness", "data": {"value": dimming}}}))
        messages.append(json.dumps({"msg": {"cmd": "colorwc", "data": {"color": {"r": 0, "g": 255, "b": 204}}}}))
    elif action == "amber":
        messages.append(json.dumps({"msg": {"cmd": "turn", "data": {"value": 1}}}))
        messages.append(json.dumps({"msg": {"cmd": "brightness", "data": {"value": dimming}}}))
        messages.append(json.dumps({"msg": {"cmd": "colorwc", "data": {"color": {"r": 255, "g": 140, "b": 0}}}}))
    elif action == "color" and color and len(color) >= 3:
        messages.append(json.dumps({"msg": {"cmd": "turn", "data": {"value": 1}}}))
        messages.append(json.dumps({"msg": {"cmd": "brightness", "data": {"value": dimming}}}))
        messages.append(json.dumps({"msg": {"cmd": "colorwc", "data": {"color": {"r": color[0], "g": color[1], "b": color[2]}}}}))

    results = {}
    for ip in LIVING_ROOM_IPS:
        try:
            for m in messages:
                sock.sendto(m.encode("utf-8"), (ip, GOVEE_UDP_PORT))
            results[ip] = "OK"
        except Exception as e:
            results[ip] = f"FAILED: {e}"

    sock.close()
    return {"status": "COMPLETED", "targets": LIVING_ROOM_IPS, "results": results}


async def dispatch_kitchen_ble(action: str, brightness: int = 100, color: Optional[List[int]] = None) -> Dict[str, Any]:
    """Dispatches direct BLE GATT writes to the 3 kitchen bulbs."""
    from scripts.kitchen_ble_dispatcher import dispatch_all_kitchen
    return await dispatch_all_kitchen(action, brightness, color)


async def dispatch_zone(zone: str, action: str, brightness: int = 100, color: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Unified entry point for lighting dispatch.
    zone: 'all', 'kitchen', 'hallway', 'living_room'
    action: 'on', 'off', 'warm_white', 'night', 'cyan', 'amber'
    """
    zone = (zone or "all").lower()
    report: Dict[str, Any] = {"zone": zone, "action": action, "brightness": brightness, "dispatched": {}}

    if zone == "hallway":
        report["dispatched"]["hallway"] = dispatch_wiz_udp(action, brightness, color)
    elif zone == "living_room":
        report["dispatched"]["living_room"] = dispatch_govee_udp(action, brightness, color)
    elif zone == "kitchen":
        report["dispatched"]["kitchen"] = await dispatch_kitchen_ble(action, brightness, color)
    elif zone == "all":
        # Execute fast UDP sockets synchronously, and BLE in parallel
        report["dispatched"]["hallway"] = dispatch_wiz_udp(action, brightness, color)
        report["dispatched"]["living_room"] = dispatch_govee_udp(action, brightness, color)
        report["dispatched"]["kitchen"] = await dispatch_kitchen_ble(action, brightness, color)
    else:
        report["error"] = f"Unknown zone: {zone}"

    return report


if __name__ == "__main__":
    import sys
    z = sys.argv[1] if len(sys.argv) > 1 else "all"
    a = sys.argv[2] if len(sys.argv) > 2 else "warm_white"
    res = asyncio.run(dispatch_zone(z, a, 100))
    print(json.dumps(res, indent=2))

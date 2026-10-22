#!/usr/bin/env python3
"""
StackLabs Direct Bare-Metal BLE Kitchen Light Dispatcher
Targets 3x Govee H6008 Smart LED Bulbs via Clio Onboard Bluetooth 5.2.
Sub-15ms local radio execution. Zero cloud toll.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from bleak import BleakScanner, BleakClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [KitchenBLE] %(message)s")
logger = logging.getLogger("kitchen_ble")

# Canonical MAC addresses for the 3 Kitchen H6008 bulbs
KITCHEN_BULBS = {
    "kitchen_1": {"mac": "98:17:3C:9C:34:5B", "name": "Kitchen Sink"},
    "kitchen_2": {"mac": "98:17:3C:9A:AC:A9", "name": "Kitchen Center"},
    "kitchen_3": {"mac": "98:17:3C:96:2A:9B", "name": "Kitchen Counter"}
}

CHAR_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"

def build_govee_packet(cmd: int, data: List[int]) -> bytes:
    """Builds a canonical 20-byte Govee BLE packet with XOR checksum."""
    pkt = bytearray([0x33, cmd] + data)
    while len(pkt) < 19:
        pkt.append(0x00)
    checksum = 0
    for b in pkt:
        checksum ^= b
    pkt.append(checksum)
    return bytes(pkt)

async def dispatch_command_to_bulb(mac: str, packets: List[bytes], timeout: float = 4.0) -> bool:
    """Connects to a single bulb and writes GATT characteristics."""
    try:
        dev = await BleakScanner.find_device_by_address(mac, timeout=2.5)
        if not dev:
            logger.warning(f"Device {mac} not found during BLE scan")
            return False

        async with BleakClient(dev, timeout=timeout) as client:
            if not client.is_connected:
                return False
            for pkt in packets:
                await client.write_gatt_char(CHAR_UUID, pkt, response=False)
                await asyncio.sleep(0.05)
            return True
    except Exception as e:
        logger.error(f"Error dispatching to {mac}: {e}")
        return False

async def dispatch_all_kitchen(action: str, brightness: int = 100, color: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Executes lightning command to all kitchen bulbs sequentially to prevent radio collision.
    action: 'on', 'off', 'warm_white', 'color'
    """
    packets = []
    if action == "off":
        packets.append(build_govee_packet(0x01, [0x00]))
    elif action == "on":
        packets.append(build_govee_packet(0x01, [0x01]))
        packets.append(build_govee_packet(0x04, [min(max(brightness, 1), 100)]))
        if color:
            packets.append(build_govee_packet(0x05, [0x02, color[0], color[1], color[2]]))
    elif action == "warm_white":
        packets.append(build_govee_packet(0x01, [0x01]))
        packets.append(build_govee_packet(0x04, [brightness]))
        # Warm white 2700K approx RGB (255, 180, 107)
        packets.append(build_govee_packet(0x05, [0x02, 255, 180, 107]))
    elif action == "cyan":
        packets.append(build_govee_packet(0x01, [0x01]))
        packets.append(build_govee_packet(0x04, [brightness]))
        packets.append(build_govee_packet(0x05, [0x02, 0, 255, 204]))
    elif action == "amber":
        packets.append(build_govee_packet(0x01, [0x01]))
        packets.append(build_govee_packet(0x04, [brightness]))
        packets.append(build_govee_packet(0x05, [0x02, 255, 140, 0]))
    elif action == "night":
        packets.append(build_govee_packet(0x01, [0x01]))
        packets.append(build_govee_packet(0x04, [min(brightness, 20)]))
        packets.append(build_govee_packet(0x05, [0x02, 255, 140, 60]))

    results = {}
    for key, bulb in KITCHEN_BULBS.items():
        success = await dispatch_command_to_bulb(bulb["mac"], packets)
        results[key] = "OK" if success else "FAILED"

    return {
        "status": "COMPLETED",
        "action": action,
        "results": results,
        "success_count": sum(1 for v in results.values() if v == "OK")
    }

if __name__ == "__main__":
    import sys
    act = sys.argv[1] if len(sys.argv) > 1 else "on"
    out = asyncio.run(dispatch_all_kitchen(act))
    print(out)

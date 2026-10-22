#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/james/stacklabs/scripts')
from core import api_client

def test():
    print("1. Testing set_fancast_banter_mode to broadcast_safe...")
    res_mode = api_client.set_fancast_banter_mode('broadcast_safe')
    print("   Mode:", res_mode.get('mode'))

    print("2. Testing get_fancast_banter_state...")
    state = api_client.get_fancast_banter_state()
    active_mode = state.get('state', {}).get('active_mode')
    print("   Active Mode:", active_mode)
    assert active_mode == 'broadcast_safe'

    print("3. Testing trigger_fancast_banter (YELLOW_FLAG)...")
    trigger_res = api_client.trigger_fancast_banter('YELLOW_FLAG', {'down': '2nd & 8'})
    print("   Governance:", trigger_res.get('governance'))
    print("   Turns Generated:", trigger_res.get('turns_generated'))
    assert trigger_res.get('turns_generated') == 2

    print("4. Testing interrupt_fancast_banter...")
    intr_res = api_client.interrupt_fancast_banter()
    print("   Status:", intr_res.get('status'), "State:", intr_res.get('state', {}).get('current_stoppage'))
    assert intr_res.get('state', {}).get('current_stoppage') == 'PLAY_ACTIVE'

    print("5. Testing get_fancast_banter_history...")
    history = api_client.get_fancast_banter_history(limit=5)
    print(f"   Retrieved {len(history)} recent dialogue logs.")
    print("🎉 ✅ Python SDK End-to-End Test PASSED!")

if __name__ == "__main__":
    test()

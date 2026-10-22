#!/usr/bin/env python3
"""
fanstack_daily_prep.py
======================
DEPRECATED // Legacy FanStack Daily Prep CLI

Notice: Legacy watch party chatrooms (setup_all_rooms.py, stadium dials, 3D arenas)
are retired under Invariant 24. This script forwards to faas_daily_prep.py unless
--legacy is explicitly passed.
"""

import sys
import os
import argparse
import subprocess

def main():
    # Check if --legacy is passed anywhere in arguments
    if "--legacy" not in sys.argv:
        print("\033[1;33m" + "=" * 70)
        print("  ⚠️ [DEPRECATION NOTICE // INVARIANT 24] LEGACY FANSTACK CHATROOMS RETIRED")
        print("  Legacy watch party chatrooms (setup_all_rooms.py, stadium dials, 3D arenas)")
        print("  are retired under Invariant 24 in favor of lightweight FaaS information utility.")
        print("  Forwarding invocation to Tool #67: faas_daily_prep.py")
        print("  (Pass --legacy to force legacy room setup)")
        print("=" * 70 + "\033[0m\n", flush=True)

        faas_script = os.path.join(os.path.dirname(__file__), "faas_daily_prep.py")
        forward_args = [arg for arg in sys.argv[1:] if not arg.startswith("--game-id") and arg != "--force-refresh" and arg != "--cross-pollinate"]
        py_bin = sys.executable
        os.execv(py_bin, [py_bin, faas_script] + forward_args)

    # Legacy execution path
    parser = argparse.ArgumentParser(description="Legacy FanStack Daily Prep: Ingress, Seeding, and Room Orchestration")
    parser.add_argument("--legacy", action="store_true", help="Force legacy watch-party room orchestration")
    parser.add_argument("--game-id", type=str, help="Target MLB/Sports game ID for preparation")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh schedule and room cache")
    parser.add_argument("--cross-pollinate", action="store_true", help="Cross-pollinate advocate seating across rooms")
    
    args = parser.parse_args()

    if not args.game_id:
        parser.print_help()
        sys.exit(0)

    # Delegate to shell script if arguments provided
    script_path = os.path.join(os.path.dirname(__file__), "fanstack_daily_prep.sh")
    cmd = ["bash", script_path, "--legacy", "--game-id", str(args.game_id)]
    if args.force_refresh:
        cmd.append("--force-refresh")
    if args.cross_pollinate:
        cmd.append("--cross-pollinate")

    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()

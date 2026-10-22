#!/usr/bin/env python3
"""
Cockpit Architect Pre-Invocation Hook (Rule Zero)
Injects the immutable Cockpit Architect law before every model invocation turn.
"""
import sys
import json
import socket

def main():
    try:
        _ = sys.stdin.read()
    except Exception:
        pass

    # Deactivated per Pilot directive: identity managed via /sovereign_boot flags and process runtime
    print(json.dumps({}))


if __name__ == "__main__":
    main()

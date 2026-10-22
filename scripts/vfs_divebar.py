#!/home/james/stacklabs/.venv/bin/python3
"""
Master Dive Bar Controller & Savant Query Dispatcher
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/vfs_divebar.py
"""
import argparse
import json
import os
import pathlib
import sys
import time

ROOT_DIR = pathlib.Path("/home/james/stacklabs")
VFS_STATE = ROOT_DIR / "vfs" / ".state"
LOCK_FILE = VFS_STATE / "DISCORD_MUTE.lock"
QUERY_SERVICE = ROOT_DIR / "vfs" / "services" / "savant_query_bridge"
PENDING_QUERY = QUERY_SERVICE / ".state" / "pending_query.json"


def get_status() -> bool:
    """Returns True if active (unmuted), False if muted."""
    return not LOCK_FILE.exists()


def mute() -> None:
    VFS_STATE.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(f'{{"muted_at": {int(time.time())}, "operator": "Pilot"}}\n', encoding="utf-8")
    print("🔴 [DIVE BAR] MUTED: All Discord advocate dispatches paused (Exit 0 enforced).")


def unmute() -> None:
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
    print("🟢 [DIVE BAR] ACTIVE: Discord advocate reflex dispatches unmuted.")


def toggle() -> None:
    if get_status():
        mute()
    else:
        unmute()


def dispatch_query(question: str, advocate: str = "auto") -> None:
    if not get_status():
        print("⚠️ [DIVE BAR] Room is currently MUTED. Unmuting to deliver query...")
        unmute()

    QUERY_SERVICE.mkdir(parents=True, exist_ok=True)
    PENDING_QUERY.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "query_id": f"qry-{int(time.time() * 1000)}",
        "question": question.strip(),
        "advocate": advocate.strip().lower(),
        "timestamp": int(time.time())
    }
    PENDING_QUERY.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✓ [SAVANT QUERY] Staged query #{payload['query_id']} for advocate '{advocate}': \"{question}\"")


def main() -> int:
    parser = argparse.ArgumentParser(description="StackLabs Dive Bar & Savant Query Controller")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Check current mute status")
    subparsers.add_parser("mute", help="Pause all advocate dispatches")
    subparsers.add_parser("unmute", help="Resume advocate dispatches")
    subparsers.add_parser("toggle", help="Toggle mute state")

    query_parser = subparsers.add_parser("query", help="Dispatch a natural language query to the room")
    query_parser.add_argument("question", type=str, help="Natural language question for the advocates")
    query_parser.add_argument("--advocate", type=str, default="auto", choices=["auto", "sammy", "barf", "chet", "larry", "burl"], help="Target advocate")

    args = parser.parse_args()

    if args.command == "status":
        active = get_status()
        state_str = "🟢 ACTIVE" if active else "🔴 MUTED"
        print(f"Discord Dive Bar Status: {state_str}")
    elif args.command == "mute":
        mute()
    elif args.command == "unmute":
        unmute()
    elif args.command == "toggle":
        toggle()
    elif args.command == "query":
        dispatch_query(args.question, args.advocate)

    return 0


if __name__ == "__main__":
    sys.exit(main())

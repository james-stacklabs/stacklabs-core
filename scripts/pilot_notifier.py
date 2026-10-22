#!/usr/bin/env python3
"""
StackLabs Platform: Centralized Pilot Notification Dispatcher
Path: /home/james/stacklabs/scripts/pilot_notifier.py

Dispatches real-time push alerts to Pilot's mobile device via ntfy.sh,
fires desktop toasts (notify-send), plays local audio chimes (paplay),
and records an immutable audit log to /home/james/stacklabs/logs/pilot_notifications.log.
"""

import os
import sys
import json
import argparse
import subprocess
import urllib.request
import urllib.error
import email.header
from datetime import datetime
from pathlib import Path
from typing import Optional, List

STACKLABS_ROOT = Path("/home/james/stacklabs")
LOG_FILE = STACKLABS_ROOT / "logs" / "pilot_notifications.log"
DEFAULT_NTFY_TOPIC = os.getenv("NTFY_TOPIC", "stacklabs-pilot-alerts")
NTFY_BASE_URL = os.getenv("NTFY_URL", f"https://ntfy.sh/{DEFAULT_NTFY_TOPIC}")


def _encode_header(val: Optional[str]) -> Optional[str]:
    """Encode header value using RFC 2047 if non-ASCII characters (e.g. emojis) are present."""
    if not val:
        return val
    try:
        val.encode("ascii")
        return val
    except UnicodeEncodeError:
        return email.header.Header(val, "utf-8").encode()


def dispatch_pilot_alert(
    title: str,
    body: str,
    priority: str = "default",
    tags: str = "bell",
    click_url: Optional[str] = None,
    sound: bool = True
) -> bool:
    """
    Dispatch multi-channel alert to Pilot:
    1. Mobile Push via ntfy.sh
    2. Linux Desktop Toast via notify-send (if display available)
    3. Audio Chime via paplay (if sound server available)
    4. Atomic audit entry in pilot_notifications.log
    """
    now = datetime.now()
    ts_str = now.strftime("%Y-%m-%d %H:%M:%S")
    success = True

    # 1. Log directory verification
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 2. Dispatch Mobile Push via ntfy.sh (HTTP POST)
    try:
        headers = {
            "Title": _encode_header(title),
            "Priority": priority,
            "Tags": _encode_header(tags),
            "User-Agent": "StackLabs-PilotNotifier/1.0"
        }
        if click_url:
            headers["Click"] = _encode_header(click_url)

        req = urllib.request.Request(
            NTFY_BASE_URL,
            data=body.encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            ntfy_status = resp.status
    except Exception as e:
        ntfy_status = f"ERR: {e}"
        success = False

    # 3. Dispatch Local Desktop Notification (notify-send)
    try:
        urgency = "critical" if priority in ["urgent", "high"] else "normal"
        # Probe display/dbus env
        target_display = os.environ.get("DISPLAY", ":0")
        target_wayland = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
        env_copy = os.environ.copy()
        env_copy["DISPLAY"] = target_display
        env_copy["WAYLAND_DISPLAY"] = target_wayland
        
        # Run notify-send non-blocking
        subprocess.Popen(
            ["notify-send", "-u", urgency, "-a", "StackLabs Cockpit", title, body],
            env=env_copy,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

    # 4. Dispatch Local Audio Chime (paplay)
    if sound:
        try:
            sound_file = "/usr/share/sounds/freedesktop/stereo/complete.oga"
            if priority in ["urgent", "high"]:
                sound_file = "/usr/share/sounds/freedesktop/stereo/message.oga"
            if Path(sound_file).exists():
                subprocess.Popen(
                    ["paplay", sound_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception:
            pass

    # 5. Atomic Audit Logging
    audit_entry = {
        "timestamp": now.isoformat(),
        "title": title,
        "body": body,
        "priority": priority,
        "tags": tags,
        "click_url": click_url,
        "ntfy_status": ntfy_status
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_entry) + "\n")
    except Exception as e:
        print(f"[PilotNotifier] Failed appending log: {e}", file=sys.stderr)

    return success


def main():
    parser = argparse.ArgumentParser(description="StackLabs Pilot Notification Dispatcher")
    parser.add_argument("--title", required=True, help="Notification title")
    parser.add_argument("--body", required=True, help="Notification body")
    parser.add_argument("--priority", default="default", choices=["min", "low", "default", "high", "urgent"])
    parser.add_argument("--tags", default="bell", help="Comma-separated emoji tags (e.g. eyes,headphones)")
    parser.add_argument("--url", default=None, help="Optional click target URL")
    parser.add_argument("--no-sound", action="store_true", help="Disable local audio chime")
    
    args = parser.parse_args()
    ok = dispatch_pilot_alert(
        title=args.title,
        body=args.body,
        priority=args.priority,
        tags=args.tags,
        click_url=args.url,
        sound=not args.no_sound
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

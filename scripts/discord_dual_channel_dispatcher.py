#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Dual-Channel Discord Advocate Dispatcher
Routes NFL reactions to Channel 1 (#nfl-war-room / #LFGM_Barf)
and CFB autopsies/toe-tags to Channel 2 (#cfb-carnage).
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/discord_dual_channel_dispatcher.py
"""
import argparse
import json
import logging
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

PROJECT_ROOT = pathlib.Path("/home/james/stacklabs")
sys.path.insert(0, str(PROJECT_ROOT))

ENV_PATH = PROJECT_ROOT / ".env"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("discord_dual_channel_dispatcher")


def get_env_val(key: str, default: str = "") -> str:
    if not ENV_PATH.exists():
        return default
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return default


# Channel 1: NFL War Room / LFGM Barf
NFL_WEBHOOK_URL = get_env_val(
    "DISCORD_NFL_WEBHOOK_URL",
    get_env_val("STACKLABS_PRIVATE_DISCORD_WEBHOOK", "")
)

# Channel 2: CFB Carnage / Executive Wire
CFB_WEBHOOK_URL = get_env_val(
    "DISCORD_CFB_WEBHOOK_URL",
    get_env_val("DISCORD_WEBHOOK_EXECUTIVE", "")
)


def dispatch_to_discord(webhook_url: str, payload: Dict[str, Any]) -> bool:
    if not webhook_url:
        logger.warning("Webhook URL is empty. Skipping dispatch.")
        return False
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "StackLabs-DualDispatcher/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            if resp.status in (200, 204):
                logger.info("Successfully dispatched message to Discord.")
                return True
            logger.warning(f"Discord returned unexpected status: {resp.status}")
            return False
    except Exception as e:
        logger.error(f"Failed to post to Discord webhook: {e}")
        return False


def post_nfl_reaction(matchup: str, headline: str, barf_quote: str, burl_perspective: str) -> bool:
    """Dispatches formatted two-host NFL banter to Channel 1."""
    embed = {
        "title": f"🏈 NFL Overreaction Tuesday: {matchup}",
        "description": headline,
        "color": 0xE25822,  # Flame orange
        "fields": [
            {
                "name": "🐶 Barf the Dog (@BarfFanStack)",
                "value": f"*{barf_quote}*",
                "inline": False
            },
            {
                "name": "🚜 Burl (The Porch)",
                "value": f"*{burl_perspective}*",
                "inline": False
            }
        ],
        "footer": {
            "text": "StackLabs FaaS NFL Telemetry • Low-Latency Holster Dispatch"
        }
    }
    payload = {"username": "NFL War Room Oracle", "embeds": [embed]}
    return dispatch_to_discord(NFL_WEBHOOK_URL, payload)


def post_cfb_toetag(matchup: str, score: str, flatline_sigma: float, shibboleth: str, autopsy: str, sammy_quant: str) -> bool:
    """Dispatches formal CFB Toe-Tag obituary to Channel 2."""
    embed = {
        "title": f"☠️ CFB Toe-Tag Autopsy: {matchup} ({score})",
        "description": f"**Time of Death**: Confirmed flatline (+{flatline_sigma:.1f}σ on `{shibboleth}`)",
        "color": 0x4A154B,  # Deep plum / toe-tag purple
        "fields": [
            {
                "name": "📋 Official Coroner Verdict",
                "value": autopsy,
                "inline": False
            },
            {
                "name": "📊 Sammy the Savant (Over/Under Quant)",
                "value": f"*{sammy_quant}*",
                "inline": False
            }
        ],
        "footer": {
            "text": "StackLabs CFB Carnage Coroner • Argon Law 3 WAL Verified"
        }
    }
    payload = {"username": "CFB Carnage Chapel", "embeds": [embed]}
    return dispatch_to_discord(CFB_WEBHOOK_URL, payload)


def main():
    parser = argparse.ArgumentParser(description="Dispatch test messages to dual Discord channels")
    parser.add_argument("--test-nfl", action="store_true", help="Send test payload to NFL Channel 1")
    parser.add_argument("--test-cfb", action="store_true", help="Send test payload to CFB Channel 2")
    args = parser.parse_args()

    if args.test_nfl:
        res = post_nfl_reaction(
            matchup="WSH @ SF (Week 7 MNF)",
            headline="San Francisco holds off Washington 23-17 as Daniels takes terminal 18-yard sack.",
            barf_quote="I watched Jayden Daniels run backward in circles for six whole seconds while Dan Quinn chewed his gum! Throw the ball into the bay!",
            burl_perspective="Y'all crowned a rookie before he ever saw a Nick Bosa stunt package in prime time. He'll learn."
        )
        print(f"NFL Dispatch Success: {res}")

    if args.test_cfb:
        res = post_cfb_toetag(
            matchup="MICH @ MINN",
            score="MINN 24, MICH 17",
            flatline_sigma=4.8,
            shibboleth="MINN_LITTLE_BROWN_JUG_49_YEAR_DROUGHT",
            autopsy="Michigan's 49-year dominance in Minneapolis officially flatlined. Sherrone Moore's offensive playbook looked like it was mimeographed during the Carter administration.",
            sammy_quant="The Under 41.5 was locked up before halftime. You don't lay points on a run-first offense with no third-and-long pulse. Total rookie hook trap."
        )
        print(f"CFB Dispatch Success: {res}")


if __name__ == "__main__":
    main()

#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Discord Snip Trigger and FanStack Advocate Roaster
Triggers retrograde snipe upon user reaction, invokes gemini-3.8-flash, and renders roast packet.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path("/home/james/stacklabs")
load_dotenv(REPO_ROOT / ".env")


def generate_advocate_roast(prompt_text: str, transcript: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return (
            f"[Barf the Dog]: BARK BARK! I saw that ridiculous broadcast stunt! "
            f"Transcript caught: '{transcript or 'Total chaos'}'!"
        )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        sys_prompt = """You are Barf the Dog (@BarfFanStack), an unhinged, sharp-witted New York sports hound.
The Lead Systems Architect (James) just dropped a reaction to something ridiculous that appeared on television during Monday Night Football.
Write an authentic, 2-to-3 sentence savage roast referencing what was on screen and what was said.
Use all-caps for emphatic dog barking. Zero corporate fluff, zero apologies."""

        user_content = f"Pilot comment: {prompt_text}\nAnnouncer transcript at that second: {transcript}"
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[sys_prompt, user_content],
        )
        return response.text.strip()
    except Exception as e:
        return f"[Barf the Dog]: BARK BARK! The broadcast went completely feral! (Error: {e})"


def main() -> None:
    parser = argparse.ArgumentParser(description="Discord Snip Trigger and Advocate Roaster")
    parser.add_argument("trigger", help="Pilot reaction text (e.g. 'that wildebeest on TV was crazy looking')")
    parser.add_argument("--tag", default="discord_drop", help="File tag")
    args = parser.parse_args()

    print(f"[*] Processing Pilot reaction: '{args.trigger}'")
    from precog_stream_sniper import snip_retrograde_window

    try:
        snip_data = snip_retrograde_window(num_segments=3, offset_back=1, tag=args.tag, run_artemis=True)
    except Exception as e:
        print(f"Error during retrograde snip: {e}", file=sys.stderr)
        sys.exit(1)

    roast = generate_advocate_roast(args.trigger, snip_data["transcript"])

    result_payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "trigger": args.trigger,
        "photo": snip_data["photo"],
        "video": snip_data["video"],
        "transcript": snip_data["transcript"],
        "advocate_roast": roast,
    }

    out_json = Path("/dev/shm/discord_snip_latest.json")
    out_json.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("🚀 DISCORD SNIP ROAST DISPATCH READY")
    print(f"📸 Image: {snip_data['photo']}")
    print(f"🎥 Video: {snip_data['video']}")
    print(f"🗣️  Roast: {roast}")
    print("=" * 70)


if __name__ == "__main__":
    main()

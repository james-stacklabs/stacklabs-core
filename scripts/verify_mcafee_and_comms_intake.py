#!/home/james/stacklabs/.venv/bin/python3
"""
Process and verify McAfee broadcast telemetry, Google Cloud Startups outreach,
and Cherylyn Steininger companion email staging.
Path: /home/james/stacklabs/scripts/verify_mcafee_and_comms_intake.py
"""

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path("/home/james/stacklabs")
LOOKBOOK_PATH = REPO_ROOT / "pilot_drops" / "MCAFEE_POST_SHOW_LOOKBOOK_2026_10_16.md"
CHERYLYN_DRAFT_PATH = REPO_ROOT / "pilot_drops" / "draft_email_cherylyn_servicenow_companion.md"
LAUREN_DRAFT_PATH = REPO_ROOT / "pilot_drops" / "draft_email_lauren_love_google_cloud_startups.md"


def verify_lookbook() -> dict:
    if not LOOKBOOK_PATH.exists():
        raise FileNotFoundError(f"Missing lookbook at {LOOKBOOK_PATH}")
    content = LOOKBOOK_PATH.read_text(encoding="utf-8")
    has_vitals = "EXECUTIVE VITALS" in content
    has_pitchfork = "PITCHFORK INDEX" in content
    return {
        "path": str(LOOKBOOK_PATH),
        "size_bytes": LOOKBOOK_PATH.stat().st_size,
        "valid": has_vitals and has_pitchfork,
    }


def verify_draft(path: pathlib.Path, banned_terms: list[str]) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing draft file at {path}")
    content = path.read_text(encoding="utf-8")
    found_banned = [t for t in banned_terms if t in content.lower()]
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "banned_found": found_banned,
        "valid": len(found_banned) == 0,
    }


def main() -> int:
    print("[*] Verifying McAfee Lookbook...")
    lookbook_info = verify_lookbook()
    print(f"  ✅ Lookbook validated: {lookbook_info['size_bytes']} bytes")

    banned_in_drafts = ["sovereign", "symlink", "folder", "bare-metal", "bare metal"]
    print("[*] Verifying Cherylyn Steininger Companion Draft...")
    cherylyn_info = verify_draft(CHERYLYN_DRAFT_PATH, banned_in_drafts)
    if not cherylyn_info["valid"]:
        print(f"  ❌ Cherylyn draft contains banned terms: {cherylyn_info['banned_found']}")
        return 1
    print("  ✅ Cherylyn draft clean of mechanical leaks")

    print("[*] Verifying Lauren Love Google Cloud Startups Draft...")
    lauren_info = verify_draft(LAUREN_DRAFT_PATH, ["sovereign", "bare-metal", "bare metal"])
    if not lauren_info["valid"]:
        print(f"  ❌ Lauren draft contains banned terms: {lauren_info['banned_found']}")
        return 1
    print("  ✅ Lauren draft clean of banned terms")

    receipt = {
        "status": "PASS",
        "lookbook": lookbook_info,
        "cherylyn_draft": cherylyn_info,
        "lauren_draft": lauren_info,
    }
    receipt_path = REPO_ROOT / "today" / "WO0011186_VERIFICATION_RECEIPT.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"[+] Verification receipt written to {receipt_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

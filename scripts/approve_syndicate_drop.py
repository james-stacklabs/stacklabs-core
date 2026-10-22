#!/usr/bin/env python3
"""
Pilot Approval Gate CLI: Promotes Approved Syndicate Drops to Live Listen Portal
Path: /home/james/stacklabs/scripts/approve_syndicate_drop.py
"""

import os
import sys
import json
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

APPROVAL_DIR = REPO_ROOT / "pilot_drops" / "pending_approval"
TRACKS_FILE = REPO_ROOT / "apps" / "listen" / "src" / "data" / "tracks.ts"


def list_pending():
    APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(list(APPROVAL_DIR.glob("*.json")))
    if not files:
        print("No pending syndicate dossiers awaiting approval.")
        return []
    print("\n=== PENDING PILOT APPROVAL DOSSIERS ===")
    for idx, f in enumerate(files, 1):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            print(f"[{idx}] {data.get('dossier_id')} — \"{data.get('title')}\" (Sender: {data.get('sender')}) [Status: {data.get('status')}]")
        except Exception as e:
            print(f"[{idx}] {f.name} — (Error reading json: {e})")
    return files


def approve_dossier(dossier_path: Path):
    data = json.loads(dossier_path.read_text(encoding="utf-8"))
    title = data["title"]
    audio_file = data["audio_filename"]
    slug = dossier_path.stem.lower().replace("_", "-")

    print(f"Approving dossier: {title} ({dossier_path.name})")

    # Update status in JSON
    data["status"] = "APPROVED_BY_PILOT"
    dossier_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Mount to tracks.ts if tracks file exists
    if TRACKS_FILE.exists():
        content = TRACKS_FILE.read_text(encoding="utf-8")
        if slug in content:
            print(f"Track '{slug}' is already registered in tracks.ts.")
            return

        escaped_title = title.replace('"', '\\"')
        short_title = title[:36].replace('"', '\\"')
        new_entry = f"""  {{
    id: '{slug}',
    title: "{escaped_title}",
    shortTitle: "{short_title}",
    subtitle: "Executive Syndicate Briefing • {escaped_title}",
    audioSrc: "/audio/{audio_file}",
    coverArt: "/assets/paul_visionary_surveyor_james_train.jpg",
    durationSeconds: 180,
    chapters: [
      {{ id: '{slug}-c1', number: '01', title: "Strategic Deconstruction", timestamp: '00:00', seconds: 0 }},
      {{ id: '{slug}-c2', number: '02', title: "Dedicated Local Architecture", timestamp: '01:00', seconds: 60 }},
    ],
  }},
"""
        marker = "export const TRACKS: Track[] = [\n"
        if marker in content:
            updated = content.replace(marker, marker + new_entry, 1)
            TRACKS_FILE.write_text(updated, encoding="utf-8")
            print(f"Successfully mounted '{slug}' to {TRACKS_FILE.name}")

    print(f"✅ Dossier {data['dossier_id']} approved and live.")


if __name__ == "__main__":
    pending = list_pending()
    if not pending:
        sys.exit(0)

    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if not target.is_absolute():
            target = APPROVAL_DIR / target
        if target.exists():
            approve_dossier(target)
        else:
            print(f"Target not found: {target}")
    else:
        print("\nRun: python3 scripts/approve_syndicate_drop.py <dossier_filename_or_path> to approve.")

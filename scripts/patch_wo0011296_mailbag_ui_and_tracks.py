#!/home/james/stacklabs/.venv/bin/python3
"""
Registers Track 05 ('4 AM Bleacher Morgue Mailbag') in apps/listen/src/data/tracks.ts
with exact synthesized turn timestamps, and updates stream_sniper_bp.py + apps/faas/src/App.tsx
so 'bleacher_morgue_mailbag' displays its multi-voice handle cleanly at catalog[0].
"""

import json
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
TRACKS_FILE = REPO_ROOT / "apps" / "listen" / "src" / "data" / "tracks.ts"
FAAS_APP = REPO_ROOT / "apps" / "faas" / "src" / "App.tsx"
BP_FILE = REPO_ROOT / "scripts" / "blueprints" / "stream_sniper_bp.py"
CHAPTERS_JSON = Path("/tmp/bleacher_morgue_mailbag_segments/chapters.json")


def update_tracks_ts() -> None:
    meta = json.loads(CHAPTERS_JSON.read_text(encoding="utf-8")) if CHAPTERS_JSON.exists() else {
        "duration_seconds": 158,
        "duration_str": "2:38",
        "chapters": [
            {"id": "morgue-c1", "number": "01", "title": "Turn 01: CFB Morgue — Bama Mustard Contagion & BYU 99.88% Provo Flatline", "timestamp": "00:00", "seconds": 0},
            {"id": "morgue-c2", "number": "02", "title": "Turn 02: Sammy at 2nd & Snyder — $40K Eagles Wipeout & Dak vs. Case Keenum", "timestamp": "00:36", "seconds": 36},
            {"id": "morgue-c3", "number": "03", "title": "Turn 03: Barf in Queens — 9 Tums Deep, 8-9 Pick 12 Purgatory & Raiders Clarity", "timestamp": "01:09", "seconds": 69},
            {"id": "morgue-c4", "number": "04", "title": "Turn 04: Rapid-Fire Speed Round — Browns Therapist, Jorts Flashbacks & Memphis Dry Rub", "timestamp": "01:39", "seconds": 99},
            {"id": "morgue-c5", "number": "05", "title": "Turn 05: Sammy Sign-Off — Dry White Toast, No Hook & The 1976 Quarter", "timestamp": "02:15", "seconds": 135},
        ],
    }

    chapters_ts_lines = []
    for c in meta["chapters"]:
        chapters_ts_lines.append(
            f"      {{ id: '{c['id']}', number: '{c['number']}', title: {json.dumps(c['title'])}, timestamp: '{c['timestamp']}', seconds: {c['seconds']} }},"
        )
    chapters_block = "\n".join(chapters_ts_lines)

    tracks_content = f"""import {{ Track }} from '../types';

export const TRACKS: Track[] = [
  {{
    id: 'track-05-bleacher-morgue-mailbag',
    title: "4 AM Bleacher Morgue Mailbag: 4 Days of CFB & NFL Chat Toe-Tags (Charon, Sammy & Barf)",
    shortTitle: "4 AM Bleacher Morgue Mailbag",
    subtitle: "{meta['duration_str']}",
    audioSrc: "/audio/track_05_bleacher_morgue_mailbag.mp3",
    coverArt: "/assets/wall_street_slang_cover.jpg",
    durationSeconds: {meta['duration_seconds']},
    chapters: [
{chapters_block}
    ],
  }},
  {{
    id: 'decoding-slang-to-beat-wall-street-19m',
    title: "Decoding Internet Slang to Beat Wall Street Algorithms",
    shortTitle: "Decoding Slang vs Wall Street",
    subtitle: "19:10",
    audioSrc: "/audio/Decoding_Slang_to_Beat_Wall_Street.m4a",
    coverArt: "/assets/wall_street_slang_cover.jpg",
    durationSeconds: 1151,
    chapters: [
      {{ id: 'slang-c1', number: '01', title: "The Mustard & Golf Balls Paradox: Wall Street's Blind Spot", timestamp: '00:00', seconds: 0 }},
      {{ id: 'slang-c2', number: '02', title: "Two Fatal Failure Modes: 100% Data Drop vs Literal Hallucination", timestamp: '01:32', seconds: 92 }},
      {{ id: 'slang-c3', number: '03', title: "The 4-Step Telemetry Pipeline", timestamp: '03:55', seconds: 235 }},
      {{ id: 'slang-c4', number: '04', title: "Adversarial Signaling: Gamma Ramps, Emojis & Bleacher Revolts", timestamp: '06:30', seconds: 390 }},
      {{ id: 'slang-c5', number: '05', title: "Kinetic Action: Tennessee Mustard Artillery & The Florida Cleat", timestamp: '08:20', seconds: 500 }},
      {{ id: 'slang-c6', number: '06', title: "Subcultural Evasion: BYU Soaking/Quaking & The Michigan Vacuum Manifesto", timestamp: '10:20', seconds: 620 }},
      {{ id: 'slang-c7', number: '07', title: "Fan Psychology: SurlyHorns Polecat & Alabama Pawl Finebaum", timestamp: '12:50', seconds: 770 }},
      {{ id: 'slang-c8', number: '08', title: "The Polymorphic Bridge: Small-Ball Silicon Outpacing Cloud Giants", timestamp: '16:30', seconds: 990 }},
    ],
  }},
  {{
    id: 'track-03-sammy-philly-meltdown',
    title: "Sammy The Savant: 2nd & Snyder WIP Meltdown (Hurts, Saquon & Tanner McKee)",
    shortTitle: "Sammy: Philly Overreaction Meltdown",
    subtitle: "0:42",
    audioSrc: "/audio/track_03_sammy_philly_meltdown.mp3",
    coverArt: "/assets/wall_street_slang_cover.jpg",
    durationSeconds: 42,
    chapters: [
      {{ id: 'sammy-c1', number: '01', title: "2nd & Snyder Call-In: Rich Eisen & Chris Brockman Overreaction", timestamp: '00:00', seconds: 0 }},
      {{ id: 'sammy-c2', number: '02', title: "Eagles Postgame Tail: Slime Roy, Bubble Screens & Case Keenum", timestamp: '00:14', seconds: 14 }},
      {{ id: 'sammy-c3', number: '03', title: "1976 Quarter Parity: Rejecting the .5 Hook & Hammering the Under", timestamp: '00:28', seconds: 28 }},
    ],
  }},
  {{
    id: 'track-04-startalk-kiln-collision',
    title: "StarTalk Collision Brief: Casino Variance, Fractal Breakdown & The 3,000K Kiln",
    shortTitle: "StarTalk: 3,000K Kiln Collision",
    subtitle: "0:42",
    audioSrc: "/audio/track_04_startalk_kiln_collision.mp3",
    coverArt: "/assets/wall_street_slang_cover.jpg",
    durationSeconds: 42,
    chapters: [
      {{ id: 'kiln-c1', number: '01', title: "[30:14] Casino Probability Blindness & Poisson Clumping vs. Real Anomalies", timestamp: '00:00', seconds: 0 }},
      {{ id: 'kiln-c2', number: '02', title: "[38:15] Why Fractals Fail Across Scales When Micro Rules Shift", timestamp: '00:15', seconds: 15 }},
      {{ id: 'kiln-c3', number: '03', title: "[53:20] The 3,000K Pottery Kiln & Thomas Crown Infrared Thermal Blindness", timestamp: '00:28', seconds: 28 }},
    ],
  }},
];

export const THESIS_CONCEPTS: any[] = [];
"""
    TRACKS_FILE.write_text(tracks_content, encoding="utf-8")
    print("[OK] Registered Track 05 ('4 AM Bleacher Morgue Mailbag') in apps/listen/src/data/tracks.ts.")


def update_sniper_bp_and_faas() -> None:
    bp_text = BP_FILE.read_text(encoding="utf-8")
    old_cat_line = 'item["advocate_handle"] = "Executive Brief: The 3,000K Kiln Collision" if vid == "BxpyAt5w54w" else "@SammyBoySmith_The_Savant"'
    new_cat_line = (
        'item["advocate_handle"] = "Charon, @SammyBoySmith_The_Savant & @barf" if vid == "bleacher_morgue_mailbag" '
        'else ("Executive Brief: The 3,000K Kiln Collision" if vid == "BxpyAt5w54w" else "@SammyBoySmith_The_Savant")'
    )
    if old_cat_line in bp_text:
        bp_text = bp_text.replace(old_cat_line, new_cat_line)
    BP_FILE.write_text(bp_text, encoding="utf-8")

    app_text = FAAS_APP.read_text(encoding="utf-8")
    old_cond = "{((currentResult as any).advocate_audio_url || currentResult.id === 'xHWbeRw680k' || currentResult.id === 'BxpyAt5w54w') && ("
    new_cond = "{((currentResult as any).advocate_audio_url || currentResult.id === 'xHWbeRw680k' || currentResult.id === 'BxpyAt5w54w' || currentResult.id === 'bleacher_morgue_mailbag') && ("
    if old_cond in app_text:
        app_text = app_text.replace(old_cond, new_cond)
    FAAS_APP.write_text(app_text, encoding="utf-8")
    print("[OK] Updated stream_sniper_bp.py and apps/faas/src/App.tsx for bleacher_morgue_mailbag.")


if __name__ == "__main__":
    update_tracks_ts()
    update_sniper_bp_and_faas()

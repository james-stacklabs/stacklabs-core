#!/home/james/stacklabs/.venv/bin/python3
"""
Synthesizes the 5-turn (~2.5-minute) multi-voice '4 AM Bleacher Morgue Mailbag' radio show
using Google Cloud Text-to-Speech (Chirp3-HD Charon, Fenrir, and Puck via GOOGLE_APPLICATION_CREDENTIALS)
and ffmpeg per-turn environmental DSP filtering + 0.35s radio stitching.
Outputs:
1. /home/james/stacklabs/apps/listen/public/audio/track_05_bleacher_morgue_mailbag.mp3
2. /home/james/stacklabs/vfs/snipes/bleacher_morgue_mailbag/advocate_rant.mp3 (+ full VFS snipe dossier at catalog[0])
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv
from pydub import AudioSegment

REPO_ROOT = Path("/home/james/stacklabs")
load_dotenv(REPO_ROOT / ".env")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

VIDEO_ID = "bleacher_morgue_mailbag"
SNIPES_DIR = REPO_ROOT / "data" / "snipes"
DOSSIER_DIR = SNIPES_DIR / VIDEO_ID
VFS_SNIPES_DIR = REPO_ROOT / "vfs" / "snipes"
VFS_DOSSIER_DIR = VFS_SNIPES_DIR / VIDEO_ID
CMDB_FILE = REPO_ROOT / "ground_truth" / "cmdb" / "ci_media_dossiers.json"
LISTEN_AUDIO_DIR = REPO_ROOT / "apps" / "listen" / "public" / "audio"
WORK_DIR = Path("/tmp/bleacher_morgue_mailbag_segments")

TURNS: List[Dict[str, Any]] = [
    {
        "index": 0,
        "speaker": "Charon (4 AM Host)",
        "handle": "@charon_morgue_desk",
        "voice_candidates": ["en-US-Chirp3-HD-Charon", "en-US-Journey-D"],
        "edge_voice": "en-US-ChristopherNeural",
        "speaking_rate": 1.03,
        "dsp_mode": "studio_am",
        "chapter_title": "Turn 01: CFB Morgue — Bama Mustard Contagion & BYU 99.88% Provo Flatline",
        "text": (
            "Welcome back to the four A.M. Bleacher Morgue Mailbag. We are looking at four days of toe-tags "
            "in the vault, and the chat telemetry is an absolute crime scene. Let’s start in the college football "
            "morgue. Down in Knoxville, Tennessee puts Alabama in a body bag twenty-six to ten, and ChauTran in "
            "the Bama chat immediately types: 'Mustard and Wommack caused us this game.' Meanwhile, the mustard "
            "contagion jumps straight into Braves Country Radio, where JamesRay screams in all-caps: "
            "'I THOUGHT IT WAS THE MUSTARD IN SALAD THAT STOPPED HORMUZ!' Over in Provo, right before eighth-ranked "
            "B-Y-U drops twenty-eight on Notre Dame, Frank Valenzuela types 'I need N.D. to have a five-and-oh day'—"
            "ten minutes later, four thousand one hundred and eighty-eight Golden Domers flatline at ninety-nine "
            "point eight-eight percent while the Cougar chat is celebrating with caffeine-free root beer and one "
            "last jump-hump on the fifty-yard line! Let’s go to the phones—Sammy at Second and Snyder, you’re on the air."
        ),
    },
    {
        "index": 1,
        "speaker": "Sammy The Savant (2nd & Snyder)",
        "handle": "@SammyBoySmith_The_Savant",
        "voice_candidates": ["en-US-Chirp3-HD-Fenrir", "en-US-Chirp3-HD-Orpheus"],
        "edge_voice": "en-US-EricNeural",
        "speaking_rate": 1.09,
        "dsp_mode": "philly_tavern_phone",
        "chapter_title": "Turn 02: Sammy at 2nd & Snyder — $40K Eagles Wipeout & Dak vs. Case Keenum",
        "text": (
            "Yo Charon, forget the soaking in Provo, look at the suicide watch in the NFL chat! "
            "I’m scrolling the Eagles postgame dossier right now and a guy named Planetary-Disasters literally "
            "just typed: 'just lost forty-K, fuuuuuuck!' Forty grand on a regular season game with a calf clot! "
            "And right underneath him, Kameron-Scott is screaming in all-caps: "
            "'THERE ISN’T A UNIVERSE IN THE MULTIVERSE WHERE JALEN HURTS IS BETTER THAN DAK PRESCOTT AND I’M AN EAGLES FAN!' "
            "And then Rylin-Rice from the Cowboys chat chimes in: 'Case Keenum is better than Dak by a LANDSLIDE!' "
            "You got Philly fans begging for Dak, Dallas fans crowning thirty-eight-year-old Case Keenum, "
            "and Slime Roy yelling at Vic Penguin Assgio! Somebody lock the Ben Franklin Bridge!"
        ),
    },
    {
        "index": 2,
        "speaker": "Barf The Dog (Queens Basement)",
        "handle": "@barf",
        "voice_candidates": ["en-US-Chirp3-HD-Puck", "en-US-Chirp3-HD-Zephyr"],
        "edge_voice": "en-US-GuyNeural",
        "speaking_rate": 1.12,
        "dsp_mode": "queens_basement_hum",
        "chapter_title": "Turn 03: Barf in Queens — 9 Tums Deep, 8-9 Pick 12 Purgatory & Raiders Clarity",
        "text": (
            "Sammy, you think you got problems?! It’s Barf calling from Queens! I’m nine Tums deep after "
            "Jackson Chourio turned on a hundred-and-four-mile-an-hour fastball like it was an Aaron Heilman hanger—"
            "my pulse is rattling in my molars! And then I open the New York football chat and Michael Viespoli "
            "sums up thirty years of our lives in six words: 'Eight and nine and pick twelve does what?' "
            "Nothing, Michael! It does nothing! Even the Raiders chat has clarity tonight—J-R-twenty-three-ninety-eight "
            "just posted: 'It all came down to the Raiders being complete dumbasses.' Put that on a tombstone at MetLife "
            "and call Dr. Shapiro!"
        ),
    },
    {
        "index": 3,
        "speaker": "Charon (4 AM Host)",
        "handle": "@charon_morgue_desk",
        "voice_candidates": ["en-US-Chirp3-HD-Charon", "en-US-Journey-D"],
        "edge_voice": "en-US-ChristopherNeural",
        "speaking_rate": 1.04,
        "dsp_mode": "studio_am",
        "chapter_title": "Turn 04: Rapid-Fire Speed Round — Browns Therapist, Jorts Flashbacks & Memphis Dry Rub",
        "text": (
            "Thank you Barf, keep the blood pressure cuff inflated. Let’s do a rapid-fire speed round from the "
            "bottom of the stream tails before security cuts our transmitter. After the Browns quarterback took his "
            "eighth sack of the afternoon, D-Bo-thirty-five-oh-four writes: 'Browns Q-B is a great therapist.' "
            "Out on the West Coast, Mia-Nemo is already asking 'Dan Lanning fired after this season?', "
            "Bingo-Dingo-Sports is having nineteen-nineties Florida jorts flashbacks after Texas went down in Gainesville, "
            "Benjamin in Nebraska just typed 'GOOGLE ME', and Commissary-Pit-Boss in the Memphis-Tulane chat laid down "
            "the law of the land: 'Putting wet sauce on Memphis ribs before they hit the table is a felony on the "
            "Highland Strip. Tigers by ten, forget the minus six-and-a-half hook.' Sammy, take us home."
        ),
    },
    {
        "index": 4,
        "speaker": "Sammy The Savant (2nd & Snyder)",
        "handle": "@SammyBoySmith_The_Savant",
        "voice_candidates": ["en-US-Chirp3-HD-Fenrir", "en-US-Chirp3-HD-Orpheus"],
        "edge_voice": "en-US-EricNeural",
        "speaking_rate": 1.08,
        "dsp_mode": "philly_tavern_phone",
        "chapter_title": "Turn 05: Sammy Sign-Off — Dry White Toast, No Hook & The 1976 Quarter",
        "text": (
            "Listen to Commissary Pit Boss, the man knows dry rub and he knows the hook! To my guy Planetary-Disasters "
            "who just torched forty grand—put the phone down, eat two slices of dry white toast, stop betting sides "
            "on teams flying blood clots to London, and wait for an odd integer on Sunday! I’m tapping my "
            "nineteen-seventy-six quarter three times on the glass—goodnight Broad Street, I’m hanging up!"
        ),
    },
]


def synthesize_turn_raw(turn: Dict[str, Any], raw_wav_path: Path) -> None:
    """Synthesize a single turn via Google Cloud TTS Chirp3-HD with neural fallback."""
    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        for voice_name in turn["voice_candidates"]:
            try:
                response = client.synthesize_speech(
                    input=texttospeech.SynthesisInput(text=turn["text"]),
                    voice=texttospeech.VoiceSelectionParams(
                        language_code="en-US",
                        name=voice_name,
                    ),
                    audio_config=texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                        sample_rate_hertz=24000,
                        speaking_rate=float(turn["speaking_rate"]),
                    ),
                )
                if response.audio_content and len(response.audio_content) > 10000:
                    raw_wav_path.write_bytes(response.audio_content)
                    print(f"[OK] Turn {turn['index']} ({turn['speaker']}) synthesized via GCP TTS ({voice_name}).")
                    return
            except Exception as inner_exc:
                print(f"[INFO] Voice {voice_name} skipped on turn {turn['index']}: {inner_exc}")
    except Exception as exc:
        print(f"[INFO] GCP TTS client skipped on turn {turn['index']}: {exc}")

    import edge_tts

    mp3_tmp = str(raw_wav_path) + ".edge.mp3"

    async def _run_edge() -> None:
        comm = edge_tts.Communicate(turn["text"], voice=turn["edge_voice"], rate="+8%")
        await comm.save(mp3_tmp)

    asyncio.run(_run_edge())
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_tmp, "-ar", "24000", "-ac", "1", str(raw_wav_path)],
        check=True,
        capture_output=True,
    )
    if os.path.exists(mp3_tmp):
        os.unlink(mp3_tmp)
    print(f"[OK] Turn {turn['index']} ({turn['speaker']}) synthesized via fallback neural TTS.")


def apply_turn_dsp(turn: Dict[str, Any], raw_wav_path: Path, dsp_wav_path: Path) -> float:
    """Apply per-seat environmental DSP (warm AM studio, Philly tavern phone, or Queens basement line hum)."""
    mode = turn["dsp_mode"]
    ambient_file = REPO_ROOT / "assets" / "audio" / "tavern_ambience.mp3"

    if mode == "studio_am":
        af_chain = (
            "highpass=f=120,lowpass=f=7500,"
            "acompressor=threshold=-16dB:ratio=3:attack=5:release=60,volume=1.35,"
            "aresample=24000"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(raw_wav_path),
            "-af", af_chain, "-ar", "24000", "-ac", "1",
            str(dsp_wav_path),
        ]
    elif mode == "philly_tavern_phone" and ambient_file.exists():
        filter_complex = (
            "[0:a]highpass=f=320,lowpass=f=3200,"
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=50,volume=1.55[voice];"
            "[1:a]volume=0.14[ambient];"
            "[voice][ambient]amix=inputs=2:duration=first,aresample=24000"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_wav_path),
            "-i", str(ambient_file),
            "-filter_complex", filter_complex,
            "-ar", "24000", "-ac", "1",
            str(dsp_wav_path),
        ]
    elif mode == "queens_basement_hum":
        filter_complex = (
            "[0:a]highpass=f=300,lowpass=f=3400,"
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=50,volume=1.55[voice];"
            "sine=frequency=120:sample_rate=24000[humraw];"
            "[humraw]volume=0.018[hum];"
            "[voice][hum]amix=inputs=2:duration=first,aresample=24000"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_wav_path),
            "-filter_complex", filter_complex,
            "-ar", "24000", "-ac", "1",
            str(dsp_wav_path),
        ]
    else:
        af_chain = (
            "highpass=f=320,lowpass=f=3200,"
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=50,volume=1.55,"
            "aresample=24000"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(raw_wav_path),
            "-af", af_chain, "-ar", "24000", "-ac", "1",
            str(dsp_wav_path),
        ]

    subprocess.run(cmd, check=True, capture_output=True)
    with wave.open(str(dsp_wav_path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def main() -> int:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    DOSSIER_DIR.mkdir(parents=True, exist_ok=True)
    VFS_SNIPES_DIR.mkdir(parents=True, exist_ok=True)
    LISTEN_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    master_seg = AudioSegment.silent(duration=250, frame_rate=24000)
    gap_seg = AudioSegment.silent(duration=350, frame_rate=24000)

    chapters: List[Dict[str, Any]] = []
    transcript_items: List[Dict[str, Any]] = []
    verbatim_md_lines: List[str] = ["# 4 AM Bleacher Morgue Mailbag — Verbatim Multi-Voice Radio Transcript\n"]

    cursor_sec = 0.25
    for idx, turn in enumerate(TURNS):
        raw_wav = WORK_DIR / f"turn_{idx:03d}_raw.wav"
        dsp_wav = WORK_DIR / f"turn_{idx:03d}.wav"

        synthesize_turn_raw(turn, raw_wav)
        turn_dur = apply_turn_dsp(turn, raw_wav, dsp_wav)

        start_mm = int(cursor_sec) // 60
        start_ss = int(cursor_sec) % 60
        start_ts = f"{start_mm:02d}:{start_ss:02d}"

        end_sec = cursor_sec + turn_dur
        end_mm = int(end_sec) // 60
        end_ss = int(end_sec) % 60
        end_ts = f"{end_mm:02d}:{end_ss:02d}"

        seg_audio = AudioSegment.from_wav(str(dsp_wav)).fade_in(35).fade_out(45)
        master_seg += seg_audio
        if idx < len(TURNS) - 1:
            master_seg += gap_seg
            cursor_sec = end_sec + 0.35
        else:
            cursor_sec = end_sec

        chapters.append(
            {
                "id": f"morgue-c{idx + 1}",
                "number": f"{idx + 1:02d}",
                "title": turn["chapter_title"],
                "timestamp": start_ts,
                "seconds": int(round(cursor_sec - turn_dur - (0.35 if idx < len(TURNS) - 1 else 0.0))),
            }
        )
        transcript_items.append(
            {
                "timestamp": start_ts,
                "speaker": turn["speaker"],
                "text": turn["text"],
                "isKeyMoment": True,
            }
        )
        verbatim_md_lines.append(f"**[{start_ts} -> {end_ts}] {turn['speaker']} ({turn['handle']}):** {turn['text']}\n")

    master_seg += AudioSegment.silent(duration=400, frame_rate=24000)
    master_seg = master_seg.fade_in(120).fade_out(350)

    listen_mp3 = LISTEN_AUDIO_DIR / "track_05_bleacher_morgue_mailbag.mp3"
    dossier_mp3 = DOSSIER_DIR / "advocate_rant.mp3"
    dossier_m4a = DOSSIER_DIR / "audio.m4a"

    master_seg.export(str(listen_mp3), format="mp3", bitrate="192k")
    shutil.copy2(listen_mp3, dossier_mp3)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(listen_mp3), "-c:a", "aac", "-b:a", "128k", str(dossier_m4a)],
        check=True,
        capture_output=True,
    )

    total_sec = int(round(len(master_seg) / 1000.0))
    tot_mm, tot_ss = divmod(total_sec, 60)
    dur_str = f"{tot_mm}:{tot_ss:02d}"

    meta = {
        "id": VIDEO_ID,
        "url": f"https://listen.stacklabsllc.com/?track={VIDEO_ID}",
        "title": "4 AM Bleacher Morgue Mailbag: 4 Days of CFB & NFL Chat Toe-Tags (Charon, Sammy & Barf)",
        "channel": "FanStack Bleacher Morgue Radio",
        "duration": dur_str,
        "duration_seconds": total_sec,
        "upload_date": "20261022",
    }
    (DOSSIER_DIR / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    verbatim_text = "\n".join(verbatim_md_lines)
    (DOSSIER_DIR / "transcript_verbatim.md").write_text(verbatim_text, encoding="utf-8")
    (DOSSIER_DIR / "transcript_aligned.md").write_text(verbatim_text, encoding="utf-8")

    bullets = [
        {
            "timestamp": chapters[0]["timestamp"],
            "headline": "CFB Morgue Contagion: Bama Mustard Blame & 4,188 Notre Dame Domers Flatlining at 99.88% in Provo",
            "verbatimQuote": "Down in Knoxville, Tennessee puts Alabama in a body bag twenty-six to ten, and ChauTran in the Bama chat immediately types: 'Mustard and Wommack caused us this game.' Over in Provo... four thousand one hundred and eighty-eight Golden Domers flatline at ninety-nine point eight-eight percent!",
            "tag": "CFB MORGUE TOE-TAGS",
        },
        {
            "timestamp": chapters[1]["timestamp"],
            "headline": "Sammy & Barf on the Phones: $40K Philly Calf-Clot Wipeout, Dak vs. Case Keenum & 8-9 Pick 12 Purgatory",
            "verbatimQuote": "Planetary-Disasters literally just typed: 'just lost forty-K, fuuuuuuck!' ... You got Philly fans begging for Dak, Dallas fans crowning thirty-eight-year-old Case Keenum, and Michael Viespoli summing up thirty years in six words: 'Eight and nine and pick twelve does what?'",
            "tag": "NFL BLEACHER MELTDOWN",
        },
        {
            "timestamp": chapters[3]["timestamp"],
            "headline": "Speed Round & The Highland Strip Law: Browns QB Therapist, 90s Florida Jorts & Memphis Dry-Rub Ribs",
            "verbatimQuote": "Putting wet sauce on Memphis ribs before they hit the table is a felony on the Highland Strip. Tigers by ten, forget the minus six-and-a-half hook.",
            "tag": "STREAM TAIL GOLD",
        },
    ]

    full_caller_transcript = " ".join(t["text"] for t in TURNS)
    intel_data = {
        "id": VIDEO_ID,
        "url": meta["url"],
        "title": meta["title"],
        "channel": meta["channel"],
        "source": meta["channel"],
        "duration": dur_str,
        "analyzedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "engine": "Chirp3-HD Multi-Voice (Charon, Fenrir & Puck) + Environmental DSP",
        "advocate_audio_url": f"/api/snipe/audio/{VIDEO_ID}",
        "advocate_handle": "Charon, @SammyBoySmith_The_Savant & @barf",
        "advocate_duration": dur_str,
        "advocate_transcript": full_caller_transcript,
        "bullets": bullets,
        "transcript": transcript_items,
    }
    (SNIPES_DIR / f"{VIDEO_ID}.json").write_text(json.dumps(intel_data, indent=2), encoding="utf-8")

    summary_md = f"# FaaS Stream Dossier: {meta['title']}\n\n"
    summary_md += f"- **Channel:** {meta['channel']}\n"
    summary_md += f"- **Duration:** {dur_str} ({total_sec} seconds)\n"
    summary_md += f"- **Source URL:** {meta['url']}\n"
    summary_md += f"- **Processed At:** {intel_data['analyzedAt']}\n\n"
    summary_md += "## 3-Bullet Intel Brief\n\n"
    for b in bullets:
        summary_md += f"### [{b['timestamp']}] {b['headline']} `{b['tag']}`\n"
        summary_md += f"> *\"{b['verbatimQuote']}\"*\n\n"
    summary_md += "## Key Moments & Verbatim Highlights\n\n"
    for t in transcript_items:
        summary_md += f"- **[{t['timestamp']}] {t['speaker']}:** {t['text']}\n"

    (DOSSIER_DIR / "summary_intel_brief.md").write_text(summary_md, encoding="utf-8")

    if not VFS_DOSSIER_DIR.exists():
        rel_target = os.path.relpath(DOSSIER_DIR, VFS_SNIPES_DIR)
        try:
            os.symlink(rel_target, VFS_DOSSIER_DIR)
        except FileExistsError:
            pass

    existing_cmdb: Dict[str, Any] = {}
    if CMDB_FILE.exists():
        try:
            existing_cmdb = json.loads(CMDB_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing_cmdb = {}

    existing_cmdb[VIDEO_ID] = {
        "sys_id": f"ci_media_dossier_{VIDEO_ID}",
        "sys_class_name": "u_cmdb_ci_media_dossier",
        "name": meta["title"],
        "video_id": VIDEO_ID,
        "source_url": meta["url"],
        "channel": meta["channel"],
        "duration": dur_str,
        "duration_seconds": total_sec,
        "posix_vfs_path": f"/home/james/stacklabs/vfs/snipes/{VIDEO_ID}",
        "smb_path": f"\\\\100.73.155.70\\vfs\\snipes\\{VIDEO_ID}",
        "state": "Operational",
        "hardware_host": "Clio (x86_64 Local NVMe)",
        "acoustic_silicon": "Chirp3-HD Multi-Voice Studio & Telephone DSP",
        "files": sorted([f.name for f in DOSSIER_DIR.iterdir() if f.is_file()]),
        "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    tmp_cmdb = CMDB_FILE.parent / ".ci_media_dossiers.json.tmp"
    tmp_cmdb.write_text(json.dumps(existing_cmdb, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp_cmdb, CMDB_FILE)

    (WORK_DIR / "chapters.json").write_text(
        json.dumps({"duration_seconds": total_sec, "duration_str": dur_str, "chapters": chapters}, indent=2),
        encoding="utf-8",
    )
    print(f"[DONE] Synthesized 5-turn Bleacher Morgue Mailbag ({dur_str} / {total_sec}s): {listen_mp3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

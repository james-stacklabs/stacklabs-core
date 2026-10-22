#!/home/james/stacklabs/.venv/bin/python3
"""
Synthesizes the 40-second South Philadelphia caller meltdown for @SammyBoySmith_The_Savant
reacting to Rich Eisen & Chris Brockman (xHWbeRw680k) and the Eagles Postgame stream tail.
Applies AM radio telephone/dive_bar DSP filtering and writes mastered MP3s to:
1. /home/james/stacklabs/vfs/snipes/xHWbeRw680k/advocate_rant.mp3
2. /home/james/stacklabs/apps/listen/public/audio/track_03_sammy_philly_meltdown.mp3
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path("/home/james/stacklabs")
load_dotenv(REPO_ROOT / ".env")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

VIDEO_ID = "xHWbeRw680k"
SNIPE_DIR = REPO_ROOT / "data" / "snipes" / VIDEO_ID
VFS_SNIPE_DIR = REPO_ROOT / "vfs" / "snipes" / VIDEO_ID
LISTEN_AUDIO_DIR = REPO_ROOT / "apps" / "listen" / "public" / "audio"

SAMMY_HANDLE = "@SammyBoySmith_The_Savant"
SAMMY_SCRIPT = (
    "Yo, it’s Sammy from Second and Snyder, turn the radio down! "
    "Are you listening to Rich Eisen right now?! "
    "First you fly Jalen Hurts across the Atlantic Ocean with a blood clot in his leg, "
    "and now Chris Brockman’s telling me to trade Saquon and hand the keys to Tanner McKee?! "
    "Look at the postgame chat, bro! You got Slime Roy screaming at 'Vic Penguin Assgio' "
    "about Makai Lemon bubble screens, Case Keenum carving us up like a Thanksgiving turkey, "
    "and guys begging for Jon Gruden! I’m sitting here eating dry white toast tapping my "
    "1976 quarter on three cracked phones—if you think I’m touching a side or a point-five hook "
    "with Tanner McKee under center, you’re out of your mind! Wait for an odd integer on the "
    "fourth Sunday and hammer the Under until the scoreboard breaks! I’m hanging up!"
)


def _save_pcm_wav(filename: str, pcm_bytes: bytes, rate: int = 24000) -> None:
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm_bytes)


def _try_gcp_chirp_tts(raw_wav_path: str) -> bool:
    """Synthesize vocal speech via Google Cloud Chirp3-HD Fenrir / Puck neural voices."""
    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        for voice_name in ("en-US-Chirp3-HD-Fenrir", "en-US-Chirp3-HD-Puck", "en-US-Journey-D"):
            try:
                response = client.synthesize_speech(
                    input=texttospeech.SynthesisInput(text=SAMMY_SCRIPT),
                    voice=texttospeech.VoiceSelectionParams(
                        language_code="en-US",
                        name=voice_name,
                    ),
                    audio_config=texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                        sample_rate_hertz=24000,
                        speaking_rate=1.08,
                    ),
                )
                if response.audio_content and len(response.audio_content) > 10000:
                    with open(raw_wav_path, "wb") as f:
                        f.write(response.audio_content)
                    print(f"[OK] Synthesized vocal track via Google Cloud TTS ({voice_name}).")
                    return True
            except Exception as inner_err:
                print(f"[INFO] Google Cloud TTS voice {voice_name} skipped: {inner_err}")
    except Exception as exc:
        print(f"[INFO] Google Cloud TTS skipped: {exc}")
    return False


def _try_gemini_tts(raw_wav_path: str) -> bool:
    """Attempt Gemini TTS synthesis with Fenrir voice and South Philly caller direction."""
    try:
        from core.broadcast_audio_engine import get_gemini_client
        from google.genai import types

        client = get_gemini_client()
        prompt = (
            f"# SPEAKER: {SAMMY_HANDLE}\n"
            "Accent: South Philadelphia Italian-American diner regular from 2nd and Snyder\n"
            "Emotion/Tone: Frantic, fast-talking, raspy 3:00 AM sports talk radio caller slamming the table\n\n"
            f"Transcript:\n{SAMMY_SCRIPT}\n"
        )
        for model_name in ("gemini-3.1-flash-tts-preview", "gemini-flash-latest"):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Fenrir")
                            )
                        ),
                    ),
                )
                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            data = part.inline_data.data
                            if isinstance(data, str):
                                data = base64.b64decode(data)
                            if len(data) > 10000:
                                _save_pcm_wav(raw_wav_path, data)
                                print(f"[OK] Synthesized vocal track via Gemini TTS ({model_name}, Fenrir).")
                                return True
            except Exception as inner_err:
                print(f"[INFO] Gemini TTS model {model_name} skipped: {inner_err}")
    except Exception as exc:
        print(f"[INFO] Gemini TTS client setup skipped: {exc}")
    return False


def _try_edge_neural_tts(raw_wav_path: str) -> bool:
    """Fallback to high-energy neural voice (en-US-GuyNeural / en-US-EricNeural) so output is real vocal speech."""
    try:
        import edge_tts

        mp3_tmp = raw_wav_path + ".edge.mp3"

        async def _run_edge() -> None:
            comm = edge_tts.Communicate(
                SAMMY_SCRIPT,
                voice="en-US-EricNeural",
                rate="+12%",
                pitch="-3Hz",
            )
            await comm.save(mp3_tmp)

        asyncio.run(_run_edge())
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_tmp, "-ar", "24000", "-ac", "1", raw_wav_path],
            check=True,
            capture_output=True,
        )
        if os.path.exists(mp3_tmp):
            os.unlink(mp3_tmp)
        print("[OK] Synthesized vocal track via Neural TTS (en-US-EricNeural +12%).")
        return True
    except Exception as exc:
        print(f"[WARN] Edge neural TTS failed: {exc}")
        return False


def apply_am_radio_caller_dsp(input_wav: str, output_mp3: str) -> float:
    """
    Applies authentic 300Hz-3200Hz AM radio telephone bandpass, dynamic broadcast compression,
    and subtle tavern background ambiance, exporting a 192k MP3.
    """
    ambient_file = REPO_ROOT / "assets" / "audio" / "tavern_ambience.mp3"
    os.makedirs(os.path.dirname(os.path.abspath(output_mp3)), exist_ok=True)

    if ambient_file.exists():
        filter_complex = (
            "[0:a]highpass=f=320,lowpass=f=3200,"
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=50,volume=1.55[voice];"
            "[1:a]volume=0.14[ambient];"
            "[voice][ambient]amix=inputs=2:duration=first,afade=t=in:st=0:d=0.25"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", input_wav,
            "-i", str(ambient_file),
            "-filter_complex", filter_complex,
            "-codec:a", "libmp3lame", "-b:a", "192k",
            output_mp3,
        ]
    else:
        af_chain = (
            "highpass=f=320,lowpass=f=3200,"
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=50,volume=1.55,"
            "afade=t=in:st=0:d=0.25"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", input_wav,
            "-af", af_chain,
            "-codec:a", "libmp3lame", "-b:a", "192k",
            output_mp3,
        ]

    subprocess.run(cmd, check=True, capture_output=True)

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", output_mp3],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(probe.stdout.strip() or "42.0")


def update_snipe_metadata(duration_sec: float) -> None:
    """Update data/snipes/xHWbeRw680k.json and metadata.json with advocate audio fields."""
    mins = int(duration_sec // 60)
    secs = int(round(duration_sec % 60))
    dur_str = f"{mins}:{secs:02d}"

    json_file = REPO_ROOT / "data" / "snipes" / f"{VIDEO_ID}.json"
    if json_file.exists():
        data = json.loads(json_file.read_text(encoding="utf-8"))
        data["advocate_audio_url"] = f"/api/snipe/audio/{VIDEO_ID}"
        data["advocate_handle"] = SAMMY_HANDLE
        data["advocate_duration"] = dur_str
        data["advocate_transcript"] = SAMMY_SCRIPT
        json_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    meta_file = SNIPE_DIR / "metadata.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta["advocate_audio_url"] = f"/api/snipe/audio/{VIDEO_ID}"
        meta["advocate_handle"] = SAMMY_HANDLE
        meta["advocate_duration"] = dur_str
        meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main() -> None:
    SNIPE_DIR.mkdir(parents=True, exist_ok=True)
    VFS_SNIPE_DIR.mkdir(parents=True, exist_ok=True)
    LISTEN_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        raw_wav = os.path.join(tmp, "sammy_raw.wav")
        ok = _try_gcp_chirp_tts(raw_wav)
        if not ok:
            ok = _try_gemini_tts(raw_wav)
        if not ok:
            ok = _try_edge_neural_tts(raw_wav)
        if not ok:
            raise RuntimeError("All TTS engines failed to synthesize Sammy audio.")

        target_snipe_mp3 = SNIPE_DIR / "advocate_rant.mp3"
        dur_sec = apply_am_radio_caller_dsp(raw_wav, str(target_snipe_mp3))

        target_vfs_mp3 = VFS_SNIPE_DIR / "advocate_rant.mp3"
        if not target_vfs_mp3.exists() or not os.path.samefile(target_snipe_mp3, target_vfs_mp3):
            shutil.copy2(target_snipe_mp3, target_vfs_mp3)

        target_listen_mp3 = LISTEN_AUDIO_DIR / "track_03_sammy_philly_meltdown.mp3"
        shutil.copy2(target_snipe_mp3, target_listen_mp3)

        update_snipe_metadata(dur_sec)
        print(
            f"[OK] Rendered Sammy Philly Meltdown ({dur_sec:.1f}s) -> "
            f"{target_snipe_mp3} ({target_snipe_mp3.stat().st_size} bytes) & {target_listen_mp3}"
        )


if __name__ == "__main__":
    main()

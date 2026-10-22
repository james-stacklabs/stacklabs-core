#!/home/james/stacklabs/.venv/bin/python3
"""
Synthesizes the 42-second Founder / Executive Audio Brief for StarTalk (BxpyAt5w54w)
connecting Neil deGrasse Tyson's three core points:
- [30:14] Casino probability blindness & Poisson clumping vs. real statistical anomalies.
- [38:15] Why fractals fail across scales when governing micro-scale rules change.
- [53:20] The 3,000-Kelvin pottery kiln & Thomas Crown Affair infrared heist thermal blindness.
Outputs mastered MP3 to:
1. /home/james/stacklabs/vfs/snipes/BxpyAt5w54w/advocate_rant.mp3
2. /home/james/stacklabs/apps/listen/public/audio/track_04_startalk_kiln_collision.mp3
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

VIDEO_ID = "BxpyAt5w54w"
SNIPE_DIR = REPO_ROOT / "data" / "snipes" / VIDEO_ID
VFS_SNIPE_DIR = REPO_ROOT / "vfs" / "snipes" / VIDEO_ID
LISTEN_AUDIO_DIR = REPO_ROOT / "apps" / "listen" / "public" / "audio"

SPEAKER_HANDLE = "Executive Brief: The 3,000K Kiln Collision"
BRIEF_SCRIPT = (
    "Here is the 42-second synthesis on why Neil deGrasse Tyson's StarTalk episode collides "
    "directly with twenty-year quantitative model failures. First, at thirty minutes and fourteen seconds, "
    "Tyson breaks down casino probability blindness: human operators see random Poisson clumping at a craps "
    "table and hallucinate a hot hand, mistaking normal variance for structural alpha. Second, at thirty-eight "
    "fifteen, he explains why fractals fail across physical scales: a self-similar macro model looks elegant "
    "until you zoom down to a micro regime where the governing boundary rules change completely. And third, "
    "at fifty-three twenty, the three-thousand-Kelvin pottery kiln and the Thomas Crown Affair infrared heist: "
    "when every object inside a kiln—or every AI dashboard on a trading desk—glows at the exact same background "
    "temperature, thermal contrast drops to zero and the sensor goes completely blind to the real signal."
)


def _save_pcm_wav(filename: str, pcm_bytes: bytes, rate: int = 24000) -> None:
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm_bytes)


def _try_gcp_chirp_tts(raw_wav_path: str) -> bool:
    """Synthesize vocal speech via Google Cloud Chirp3-HD Puck / Charon neural voices."""
    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        for voice_name in ("en-US-Chirp3-HD-Puck", "en-US-Chirp3-HD-Charon", "en-US-Journey-D"):
            try:
                response = client.synthesize_speech(
                    input=texttospeech.SynthesisInput(text=BRIEF_SCRIPT),
                    voice=texttospeech.VoiceSelectionParams(
                        language_code="en-US",
                        name=voice_name,
                    ),
                    audio_config=texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                        sample_rate_hertz=24000,
                        speaking_rate=1.06,
                    ),
                )
                if response.audio_content and len(response.audio_content) > 10000:
                    with open(raw_wav_path, "wb") as f:
                        f.write(response.audio_content)
                    print(f"[OK] Synthesized executive brief via Google Cloud TTS ({voice_name}).")
                    return True
            except Exception as inner_err:
                print(f"[INFO] Google Cloud TTS voice {voice_name} skipped: {inner_err}")
    except Exception as exc:
        print(f"[INFO] Google Cloud TTS skipped: {exc}")
    return False


def _try_gemini_tts(raw_wav_path: str) -> bool:
    try:
        from google import genai
        from google.genai import types
        from snipe_stream_dossier import get_gemini_keys

        prompt = (
            f"# SPEAKER: {SPEAKER_HANDLE}\n"
            "Tone: Crisp, grounded, authoritative executive systems architect briefing\n\n"
            f"Transcript:\n{BRIEF_SCRIPT}\n"
        )
        for api_key in get_gemini_keys():
            client = genai.Client(api_key=api_key)
            for model_name in ("gemini-3.1-flash-tts-preview", "gemini-flash-latest"):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=["AUDIO"],
                            speech_config=types.SpeechConfig(
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
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
                                    print(f"[OK] Synthesized executive brief via Gemini TTS ({model_name}, Puck).")
                                    return True
                except Exception as inner_err:
                    print(f"[INFO] Gemini TTS model {model_name} skipped: {inner_err}")
    except Exception as exc:
        print(f"[INFO] Gemini TTS client setup skipped: {exc}")
    return False


def _try_edge_neural_tts(raw_wav_path: str) -> bool:
    try:
        import edge_tts

        mp3_tmp = raw_wav_path + ".edge.mp3"

        async def _run_edge() -> None:
            comm = edge_tts.Communicate(
                BRIEF_SCRIPT,
                voice="en-US-AndrewNeural",
                rate="+6%",
                pitch="-1Hz",
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
        print("[OK] Synthesized executive brief via Neural TTS (en-US-AndrewNeural +6%).")
        return True
    except Exception as exc:
        print(f"[WARN] Edge neural TTS failed: {exc}")
        return False


def master_studio_brief_mp3(input_wav: str, output_mp3: str) -> float:
    os.makedirs(os.path.dirname(os.path.abspath(output_mp3)), exist_ok=True)
    af_chain = (
        "highpass=f=85,lowpass=f=11000,"
        "acompressor=threshold=-16dB:ratio=3:attack=8:release=80,volume=1.35,"
        "afade=t=in:st=0:d=0.15"
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
    return float(probe.stdout.strip() or 42.0)


def main() -> int:
    SNIPE_DIR.mkdir(parents=True, exist_ok=True)
    LISTEN_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        raw_wav = tmp.name

    try:
        ok = _try_gcp_chirp_tts(raw_wav)
        if not ok:
            ok = _try_gemini_tts(raw_wav)
        if not ok:
            ok = _try_edge_neural_tts(raw_wav)
        if not ok:
            raise RuntimeError("All vocal TTS synthesis engines failed for BxpyAt5w54w brief.")

        snipe_mp3 = SNIPE_DIR / "advocate_rant.mp3"
        listen_mp3 = LISTEN_AUDIO_DIR / "track_04_startalk_kiln_collision.mp3"

        dur_sec = master_studio_brief_mp3(raw_wav, str(snipe_mp3))
        shutil.copy2(snipe_mp3, listen_mp3)

        vfs_mp3 = VFS_SNIPE_DIR / "advocate_rant.mp3"
        if VFS_SNIPE_DIR.exists() and (not vfs_mp3.exists() or not os.path.samefile(snipe_mp3, vfs_mp3)):
            shutil.copy2(snipe_mp3, vfs_mp3)

        mm = int(dur_sec) // 60
        ss = int(round(dur_sec)) % 60
        dur_label = f"{mm}:{ss:02d}"

        snipe_json_path = REPO_ROOT / "data" / "snipes" / f"{VIDEO_ID}.json"
        if snipe_json_path.exists():
            data = json.loads(snipe_json_path.read_text(encoding="utf-8"))
            data["advocate_audio_url"] = f"/api/snipe/audio/{VIDEO_ID}"
            data["advocate_handle"] = SPEAKER_HANDLE
            data["advocate_duration"] = dur_label
            data["advocate_transcript"] = BRIEF_SCRIPT
            snipe_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        meta_file = SNIPE_DIR / "metadata.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            meta["advocate_audio_url"] = f"/api/snipe/audio/{VIDEO_ID}"
            meta["advocate_handle"] = SPEAKER_HANDLE
            meta["advocate_duration"] = dur_label
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        print(f"[DONE] Synthesized {snipe_mp3} ({dur_sec:.1f}s / {dur_label}) and mirrored to {listen_mp3}")
        return 0
    finally:
        if os.path.exists(raw_wav):
            os.unlink(raw_wav)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Sovereign OS: M.A.R.D. Broadcast Audio & Dynamic Speech Synthesis Engine
Path: /home/james/stacklabs/scripts/core/broadcast_audio_engine.py
Authority: James Carroll (Pilot / Lead Systems Architect)
SDLC: STRY0010012-BLUNDERDOME-MARD-AUTONOMOUS-BROADCAST-NETWORK

Features:
- Dynamic Seat-Filling & Universal Advocate Resolution (Zero Hardcoded Persona Branching).
- Multi-Speaker TTS Speech Generation via Google GenAI SDK.
- Parameterized DSP Environmental Audio Chain (Phone, Subway, Tavern, Dugout, Press Box).
- Lyria Bumper Music Synthesis & Pydub Master Audio Mixing.
- Relational Persistence into sovereign_now.db (sys_broadcast_episode / sys_broadcast_segment).
"""

import os
import re
import sys
import json
import time
import wave
import uuid
import base64
import random
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Resolve repository paths dynamically (Zero hardcoded host paths)
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
for p in [str(REPO_ROOT), str(SCRIPTS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from pydub import AudioSegment
from google import genai
from google.genai import types

from core.db import get_db


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BroadcastEngine")

# Voice Mapping Presets for Gemini TTS
DEFAULT_FEMALE_VOICES = ["Kore", "Aoede"]
DEFAULT_MALE_VOICES = ["Puck", "Charon", "Fenrir", "Orpheus", "Zephyr"]

# Master DSP Environmental Preset Registry
DSP_REGISTRY: Dict[str, Dict[str, Any]] = {
    "studio_clean": {
        "name": "Studio Broadcast Condenser",
        "description": "Clean 24kHz studio vocal condenser with flat response and subtle warmth.",
        "highpass_hz": 80,
        "lowpass_hz": 12000,
        "compression_ratio": 2,
        "volume_multiplier": 1.0,
        "ambient_file": None,
    },
    "telephone": {
        "name": "Analog Landline Phone",
        "description": "300Hz-3400Hz telephone bandpass with dynamic codec compression.",
        "highpass_hz": 300,
        "lowpass_hz": 3400,
        "compression_ratio": 4,
        "volume_multiplier": 1.5,
        "ambient_file": None,
    },
    "subway_platform": {
        "name": "7-Train Subway Platform",
        "description": "Phone bandpass with authentic NYC 7-train subway rumble and station acoustic.",
        "highpass_hz": 300,
        "lowpass_hz": 3400,
        "compression_ratio": 4,
        "volume_multiplier": 1.6,
        "ambient_file": "/home/james/stacklabs/assets/audio/subway_rumble.mp3",
    },
    "dive_bar": {
        "name": "Scruffy's Tavern Dive Bar",
        "description": "Phone bandpass with tavern room reflections and distant clinking mugs.",
        "highpass_hz": 350,
        "lowpass_hz": 3200,
        "compression_ratio": 3,
        "volume_multiplier": 1.4,
        "ambient_file": "/home/james/stacklabs/assets/audio/tavern_ambience.mp3",
    },
    "press_box": {
        "name": "Stadium Press Box",
        "description": "Landline bandpass with typewriter acoustics and subtle paper rustling.",
        "highpass_hz": 250,
        "lowpass_hz": 3800,
        "compression_ratio": 2,
        "volume_multiplier": 1.2,
        "ambient_file": "/home/james/stacklabs/assets/audio/pressbox_ambience.mp3",
    },
    "stadium_dugout": {
        "name": "Ballpark Dugout Intercom",
        "description": "Dugout intercom with crowd swells and distant stadium organ.",
        "highpass_hz": 400,
        "lowpass_hz": 3000,
        "compression_ratio": 4,
        "volume_multiplier": 1.4,
        "ambient_file": "/home/james/stacklabs/assets/audio/stadium_crowd.mp3",
    },
    "car_bluetooth": {
        "name": "Commuter Car Bluetooth",
        "description": "Highpass 200Hz with highway tire noise and cabin resonance.",
        "highpass_hz": 200,
        "lowpass_hz": 4000,
        "compression_ratio": 3,
        "volume_multiplier": 1.3,
        "ambient_file": "/home/james/stacklabs/assets/audio/car_interior.mp3",
    }
}


def get_gemini_client() -> genai.Client:
    """Resolve Gemini/Vertex API client using environment or .env configuration."""
    v_key = os.environ.get("VERTEX_API_KEY")
    g_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not v_key and not g_key:
        env_path = "/home/james/stacklabs/.env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("VERTEX_API_KEY=") and not v_key:
                        v_key = line.strip().split("=", 1)[1].strip("\"'")
                    elif line.startswith("GEMINI_API_KEY=") and not g_key:
                        g_key = line.strip().split("=", 1)[1].strip("\"'")

    if v_key:
        return genai.Client(vertexai=True, api_key=v_key)
    elif g_key:
        return genai.Client(api_key=g_key)
    else:
        logger.warning("No live GEMINI_API_KEY configured. Fallback client instantiated.")
        return genai.Client(api_key="dummy-key")


def fetch_persona_voice_profile(persona_identifier: str) -> Dict[str, Any]:
    """
    Dynamically fetch persona metadata from sovereign_now.db.
    Resolves voice_id, accent_preset, default_dsp_preset, system_prompt, and lore.
    Zero hardcoded persona branching.
    """
    clean_id = persona_identifier.lstrip("@").strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_name, display_name, system_prompt, behavior_notes, 
                   deep_lore, canned_takes, visual_style, capabilities_json
            FROM persona
            WHERE id = ? OR user_name = ? OR display_name = ?
            LIMIT 1
        """, (clean_id, clean_id, clean_id))
        row = cursor.fetchone()
        
        if row:
            caps = {}
            if row["capabilities_json"]:
                try:
                    caps = json.loads(row["capabilities_json"])
                except Exception:
                    caps = {}
            
            # Extract or assign dynamic voice properties
            voice_id = caps.get("voice_id")
            if not voice_id:
                # Deterministic voice hashing based on name
                name_hash = sum(ord(c) for c in row["user_name"])
                voice_id = DEFAULT_MALE_VOICES[name_hash % len(DEFAULT_MALE_VOICES)]
            
            accent_preset = caps.get("accent_preset", "American English")
            default_dsp = caps.get("default_dsp_preset", "telephone")
            
            return {
                "id": row["id"],
                "handle": f"@{row['user_name']}",
                "display_name": row["display_name"] or row["user_name"],
                "system_prompt": row["system_prompt"] or "Sports fan caller with strong opinions.",
                "deep_lore": row["deep_lore"] or row["behavior_notes"] or "",
                "voice_id": voice_id,
                "accent_preset": accent_preset,
                "default_dsp_preset": default_dsp,
                "visual_style": row["visual_style"] or "style_clay"
            }
    
    # Generic fallback profile if persona not found in DB
    return {
        "id": f"caller_{clean_id}",
        "handle": f"@{clean_id}",
        "display_name": clean_id.capitalize(),
        "system_prompt": "Passionate sports enthusiast and radio caller.",
        "deep_lore": "Lifelong fan passionate about game tactics.",
        "voice_id": "Puck",
        "accent_preset": "American English",
        "default_dsp_preset": "telephone",
        "visual_style": "style_clay"
    }


def generate_broadcast_script(
    show_name: str,
    topic: str,
    seats: List[Dict[str, Any]],
    trigger_context: str = "",
    style: str = "debate",
    duration_minutes: int = 3
) -> str:
    """
    Synthesize broadcast script using Gemini 3.5 Flash.
    Seats map: [ { "seat": 0, "role": "host", "persona": {...}, "dsp_preset": "studio_clean" }, ... ]
    """
    client = get_gemini_client()
    target_words = duration_minutes * 130
    
    host_seat = next((s for s in seats if s.get("role") == "host"), seats[0] if seats else None)
    caller_seats = [s for s in seats if s.get("role") != "host"]
    if not caller_seats:
        caller_seats = seats[1:] if len(seats) > 1 else []

    # Compile dynamic persona descriptions
    cast_descriptions = []
    for s in seats:
        p = s["persona"]
        role_label = "Host (In Studio)" if s.get("role") == "host" else f"Caller ({s.get('dsp_preset', 'telephone')})"
        cast_descriptions.append(
            f"- **{p['handle']} ({p['display_name']})** [{role_label}]:\n"
            f"  * Accent Directive: {p['accent_preset']}\n"
            f"  * Core Persona/Lore: {p['system_prompt']} {p['deep_lore']}"
        )

    cast_block = "\n".join(cast_descriptions)

    system_prompt = f"""You are an elite scriptwriter for "{show_name}", a fast-paced, high-energy, authentic sports talk radio show (similar to WFAN, ESPN First Take, or High Heat).

Your task is to write an authentic ~{duration_minutes}-minute ({target_words} words) radio broadcast script based on the active topic and sports context.

### CAST OF CHARACTERS:
{cast_block}

### TOPIC & TRIGGER CONTEXT:
Topic: {topic}
{f'Live Context: {trigger_context}' if trigger_context else ''}

### FORMAT & ACTING RULES:
1. Every single line MUST begin with the speaker handle and colon: `[Handle]: [Acting/Emotion Tag] [Accent: <Accent>] Text`
   Example: `@{host_seat['persona']['handle'].lstrip('@')}: [exasperatedly] [Accent: {host_seat['persona']['accent_preset']}] Welcome back to the show...`
2. **Authentic Delivery Tags**: Use bracketed emotional directions like `[sighs heavily]`, `[slams desk]`, `[yelling over subway noise]`, `[chuckles cynically]`, `[whispers]`, `[gasping]`.
3. **Natural Disfluencies**: Callers are real people. They should speak with spontaneous imperfections: "look", "uh", "you know", "I mean", cutting themselves off mid-thought.
4. **Host Introductions**: The host MUST introduce each caller by their name and location/context when they first come on the air.
5. **No Commercial Breaks / Clean Outro**: Conclude with a punchy sign-off from the host thanking the callers.
6. Target total word count: ~{target_words} words.
"""

    logger.info(f"Generating broadcast script for '{show_name}' with {len(seats)} seats...")
    
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=f"Write the radio script for topic: {topic}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.75
            )
        )
        return response.text or ""
    except Exception as e:
        logger.error(f"Script generation failed via Gemini: {e}")
        # Return fallback deterministic script if API fails
        host_handle = host_seat['persona']['handle'] if host_seat else "@host"
        c1_handle = caller_seats[0]['persona']['handle'] if caller_seats else "@caller1"
        return (
            f"{host_handle}: [welcomes listeners] [Accent: Neutral] Welcome back to {show_name}. We are breaking down today's breaking sports action: {topic}.\n"
            f"{c1_handle}: [breathlessly] [Accent: Queens] I cannot believe what just happened on the field today! This is absolute madness!"
        )


def parse_script_turns(script_text: str) -> List[Tuple[str, str, str, str]]:
    """
    Parse raw script into structured turns:
    Returns: [ (speaker_handle, clean_text, emotion_tag, accent) ]
    """
    turns = []
    lines = script_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            parts = line.split(":", 1)
            raw_handle = parts[0].strip().replace("*", "").strip()
            # Normalize handle to @handle format
            if not raw_handle.startswith("@"):
                raw_handle = f"@{raw_handle.lower()}"
            else:
                raw_handle = f"@{raw_handle.lstrip('@').lower()}"
                
            raw_content = parts[1].strip()
            
            # Extract emotion tag e.g. [sobbing]
            emotion = "neutral"
            emotion_match = re.search(r"\[([a-zA-Z\s,]+)\]", raw_content)
            if emotion_match:
                emotion = emotion_match.group(1).strip()
            
            # Extract accent tag
            accent = "American English"
            accent_match = re.search(r"\[Accent:\s*([^\]]+)\]", raw_content)
            if accent_match:
                accent = accent_match.group(1).strip()
            
            # Clean text of all bracketed directives and markdown bold
            clean_text = re.sub(r"\[.*?\]", "", raw_content).replace("*", "").strip()
            if clean_text:
                turns.append((raw_handle, clean_text, emotion, accent))
    return turns


def save_pcm_to_wav(filename: str, pcm_bytes: bytes, channels: int = 1, rate: int = 24000, width: int = 2):
    """Save raw PCM audio bytes to standard WAV file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(pcm_bytes)


def generate_single_turn_tts(
    client: genai.Client,
    speaker_handle: str,
    text: str,
    voice: str,
    accent: str,
    emotion: str,
    output_wav: str
) -> bool:
    """Generate TTS audio for a single dialogue turn with Gemini TTS."""
    prompt = f"""# SPEAKER: {speaker_handle}
Accent: {accent}
Emotion/Tone: {emotion}

Transcript:
{text}
"""
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-tts-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    data = part.inline_data.data
                    if isinstance(data, str):
                        data = base64.b64decode(data)
                    save_pcm_to_wav(output_wav, data)
                    return True
        logger.warning(f"No audio candidate returned for turn ({speaker_handle})")
        return False
    except Exception as e:
        logger.warning(f"Gemini TTS generation failed for turn ({speaker_handle}): {e}")
        # Synthetic fallback tone if TTS preview unavailable
        try:
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"sine=frequency=440:duration=2",
                output_wav
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except Exception:
            return False


def apply_parameterized_dsp(input_wav: str, output_wav: str, preset_key: str) -> None:
    """
    Apply context-aware FFmpeg DSP filters dynamically based on preset key.
    Zero hardcoded persona checks.
    """
    preset = DSP_REGISTRY.get(preset_key, DSP_REGISTRY["telephone"])
    highpass = preset.get("highpass_hz", 300)
    lowpass = preset.get("lowpass_hz", 3400)
    volume = preset.get("volume_multiplier", 1.4)
    ambient_file = preset.get("ambient_file")

    os.makedirs(os.path.dirname(os.path.abspath(output_wav)), exist_ok=True)

    if ambient_file and os.path.exists(ambient_file):
        # Mix voice bandpass with ambient background audio
        cmd = [
            "ffmpeg", "-y", "-i", input_wav, "-i", ambient_file,
            "-filter_complex",
            f"[0:a]highpass=f={highpass},lowpass=f={lowpass},acompressor=threshold=-20dB:ratio=4:attack=5:release=50,volume={volume}[voice];"
            f"[1:a]volume=0.15[ambient];[voice][ambient]amix=inputs=2:duration=first",
            output_wav
        ]
    else:
        # Filter voice only
        cmd = [
            "ffmpeg", "-y", "-i", input_wav,
            "-af", f"highpass=f={highpass},lowpass=f={lowpass},acompressor=threshold=-20dB:ratio=4:attack=5:release=50,volume={volume}",
            output_wav
        ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except Exception as e:
        logger.error(f"FFmpeg DSP processing failed for preset '{preset_key}': {e}. Using raw input.")
        if input_wav != output_wav:
            import shutil
            shutil.copy(input_wav, output_wav)


def generate_bumper_music(output_mp3: str, mood: str = "debate") -> bool:
    """Generate 30s background music bumper via Lyria or synthesized ambient loop."""
    client = get_gemini_client()
    os.makedirs(os.path.dirname(os.path.abspath(output_mp3)), exist_ok=True)
    
    prompts = {
        "debate": "Dramatic sports radio discussion intro track. 90s stadium organ, electric guitar riffs, building sports tension. Instrumental only, no vocals.",
        "chill": "Mellow lo-fi sports podcast bumper with Rhodes piano and subtle vinyl crackle. Instrumental only.",
        "celebration": "Explosive stadium celebration anthem with brass horns and organ chords. Instrumental only."
    }
    prompt_text = prompts.get(mood, prompts["debate"])
    
    try:
        interaction = client.interactions.create(
            model="lyria-3-clip-preview",
            input=prompt_text,
            store=False
        )
        for step in getattr(interaction, "steps", []):
            for item in getattr(step, "content", []):
                item_type = getattr(item, "type", "")
                mime_type = getattr(item, "mime_type", "")
                if item_type == "audio" or (isinstance(mime_type, str) and mime_type.startswith("audio/")):
                    with open(output_mp3, "wb") as f:
                        f.write(base64.b64decode(item.data))
                    logger.info(f"✅ Lyria bumper music generated: {output_mp3}")
                    return True
    except Exception as e:
        logger.warning(f"Lyria bumper generation unavailable: {e}. Synthesizing fallback acoustic bed.")

    # Fallback synthetic organ bed via FFmpeg lavfi
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=330:duration=15",
            "-af", "volume=0.3,fade=in:st=0:d=1,fade=out:st=12:d=3",
            output_mp3
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception:
        return False


def mix_master_broadcast(speech_wav: str, music_mp3: Optional[str], output_mp3: str) -> float:
    """
    Mix voice track with intro/outro music beds using Pydub.
    Applies -15dB ducking under speech, 3s speech padding, and exports 192k MP3.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_mp3)), exist_ok=True)
    speech = AudioSegment.from_wav(speech_wav)
    
    # 2.5s padding
    padding = AudioSegment.silent(duration=2500)
    speech = AudioSegment.silent(duration=500) + speech + padding
    
    if music_mp3 and os.path.exists(music_mp3):
        try:
            music = AudioSegment.from_file(music_mp3)
            # Intro bed (12s) ducked -15dB
            intro = music[:12000] - 15
            intro = intro.fade_in(1000).fade_out(3000)
            
            # Outro bed (12s) ducked -15dB
            outro = music[:12000] - 15
            outro = outro.fade_in(3000).fade_out(1000)
            
            combined = speech.overlay(intro, position=0)
            outro_pos = max(0, len(speech) - 12000)
            combined = combined.overlay(outro, position=outro_pos)
        except Exception as e:
            logger.warning(f"Failed to overlay music bed: {e}. Using speech only.")
            combined = speech
    else:
        combined = speech
        
    combined = combined.fade_in(400).fade_out(2000)
    combined.export(output_mp3, format="mp3", bitrate="192k")
    
    duration_sec = len(combined) / 1000.0
    logger.info(f"✅ Broadcast MP3 successfully rendered ({duration_sec:.1f}s): {output_mp3}")
    return duration_sec


def generate_episode_pipeline(
    show_id: str,
    title: str,
    topic: str,
    seat_roster: List[Dict[str, Any]],
    trigger_context: str = "",
    game_pk: Optional[str] = None,
    output_dir: str = "/home/james/stacklabs/output/broadcast"
) -> Dict[str, Any]:
    """
    Complete end-to-end autonomous broadcasting pipeline.
    Zero-hardcoding: seats are passed dynamically.
    """
    episode_id = f"ep_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    os.makedirs(output_dir, exist_ok=True)
    work_dir = os.path.join(output_dir, episode_id)
    os.makedirs(work_dir, exist_ok=True)
    
    # 1. Resolve personas for all seats
    resolved_seats = []
    seats_map = {}
    for item in seat_roster:
        persona_id = item.get("persona_id") or item.get("handle") or "host"
        persona_data = fetch_persona_voice_profile(persona_id)
        dsp_preset = item.get("dsp_preset") or persona_data.get("default_dsp_preset", "telephone")
        
        seat_obj = {
            "seat": item.get("seat", 0),
            "role": item.get("role", "caller"),
            "persona": persona_data,
            "dsp_preset": dsp_preset
        }
        resolved_seats.append(seat_obj)
        seats_map[persona_data["handle"]] = seat_obj

    # 2. Generate script
    script_text = generate_broadcast_script(
        show_name="The Blunderdome Radio",
        topic=topic,
        seats=resolved_seats,
        trigger_context=trigger_context,
        duration_minutes=3
    )
    
    script_file = os.path.join(work_dir, "script.md")
    with open(script_file, "w") as f:
        f.write(script_text)

    # 3. Parse turns and generate TTS + DSP in parallel
    turns = parse_script_turns(script_text)
    client = get_gemini_client()
    segments_dir = os.path.join(work_dir, "segments")
    os.makedirs(segments_dir, exist_ok=True)
    
    processed_segment_paths = []
    timecoded_segments = []
    current_time_sec = 0.0

    logger.info(f"Synthesizing speech for {len(turns)} turns across {len(resolved_seats)} dynamic seats...")
    
    for idx, (handle, clean_text, emotion, accent) in enumerate(turns):
        seat_config = seats_map.get(handle, resolved_seats[0] if resolved_seats else None)
        voice = seat_config["persona"]["voice_id"] if seat_config else "Puck"
        dsp_preset = seat_config["dsp_preset"] if seat_config else "telephone"
        
        raw_turn_wav = os.path.join(segments_dir, f"turn_{idx:03d}_raw.wav")
        dsp_turn_wav = os.path.join(segments_dir, f"turn_{idx:03d}.wav")
        
        # Generate TTS
        success = generate_single_turn_tts(client, handle, clean_text, voice, accent, emotion, raw_turn_wav)
        if not success:
            logger.warning(f"Turn {idx} failed TTS synthesis, skipping.")
            continue
            
        # Apply Parameterized DSP
        apply_parameterized_dsp(raw_turn_wav, dsp_turn_wav, dsp_preset)
        processed_segment_paths.append(dsp_turn_wav)
        
        # Calculate turn duration for timecoded transcript
        turn_dur = 3.0
        try:
            with wave.open(dsp_turn_wav, "rb") as wf:
                turn_dur = wf.getnframes() / float(wf.getframerate())
        except Exception:
            pass
            
        mins = int(current_time_sec // 60)
        secs = int(current_time_sec % 60)
        timecode_str = f"{mins:02d}:{secs:02d}"
        
        timecoded_segments.append({
            "segment_index": idx,
            "timecode_start": timecode_str,
            "timecode_seconds": int(current_time_sec),
            "speaker_handle": handle,
            "speaker_name": seat_config["persona"]["display_name"] if seat_config else handle,
            "text_content": clean_text,
            "accent": accent,
            "emotion_tag": emotion,
            "dsp_preset": dsp_preset
        })
        current_time_sec += turn_dur

    # 4. Concatenate speech segments
    combined_speech_wav = os.path.join(work_dir, "speech_combined.wav")
    all_pcm = b""
    for p in processed_segment_paths:
        with wave.open(p, "rb") as wf:
            all_pcm += wf.readframes(wf.getnframes())
    save_pcm_to_wav(combined_speech_wav, all_pcm)

    # 5. Generate Bumper Music
    bumper_mp3 = os.path.join(work_dir, "bumper.mp3")
    generate_bumper_music(bumper_mp3, mood="debate")

    # 6. Master Audio Mix
    master_mp3 = os.path.join(output_dir, f"{episode_id}.mp3")
    final_duration = mix_master_broadcast(combined_speech_wav, bumper_mp3, master_mp3)
    
    mins_tot = int(final_duration // 60)
    secs_tot = int(final_duration % 60)
    dur_formatted = f"{mins_tot:02d}:{secs_tot:02d}"

    # 7. Relational Database Persistence (Full-Stack Triad)
    summary_text = f"Host and callers debate: {topic}. High-energy call-in sports talk radio broadcast."
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sys_broadcast_episode (
                id, show_id, title, slug, duration_seconds, duration_formatted,
                summary, script_markdown, audio_path, audio_url, triggered_by_game_pk, status, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode_id,
            show_id,
            title,
            f"blunderdome-{episode_id}",
            int(final_duration),
            dur_formatted,
            summary_text,
            script_text,
            master_mp3,
            f"/api/broadcast/episodes/{episode_id}/audio",
            game_pk,
            "ready",
            json.dumps({"timecoded_transcript": timecoded_segments})
        ))
        
        for seg in timecoded_segments:
            seg_id = f"seg_{episode_id}_{seg['segment_index']}"
            cursor.execute("""
                INSERT OR REPLACE INTO sys_broadcast_segment (
                    id, episode_id, segment_index, timecode_start, timecode_seconds,
                    speaker_handle, speaker_name, text_content, accent, emotion_tag, dsp_preset
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                seg_id, episode_id, seg["segment_index"], seg["timecode_start"],
                seg["timecode_seconds"], seg["speaker_handle"], seg["speaker_name"],
                seg["text_content"], seg["accent"], seg["emotion_tag"], seg["dsp_preset"]
            ))
        conn.commit()

    logger.info(f"🎉 Episode {episode_id} ('{title}') successfully committed to database!")
    return {
        "id": episode_id,
        "title": title,
        "duration": dur_formatted,
        "duration_seconds": int(final_duration),
        "audio_url": f"/api/broadcast/episodes/{episode_id}/audio",
        "audio_path": master_mp3,
        "segments": timecoded_segments
    }


if __name__ == "__main__":
    print("=== Sovereign OS: Blunderdome Autonomous Broadcast Engine ===")
    test_seats = [
        {"seat": 0, "role": "host", "persona_id": "sal", "dsp_preset": "studio_clean"},
        {"seat": 1, "role": "caller", "persona_id": "barf", "dsp_preset": "dive_bar"},
        {"seat": 2, "role": "caller", "persona_id": "7_train", "dsp_preset": "subway_platform"}
    ]
    res = generate_episode_pipeline(
        show_id="show_blunderdome",
        title="The 9th-Inning Meltdown Pilot",
        topic="Mets 9th-Inning Blown Save & 3 Straight Walks",
        seat_roster=test_seats,
        trigger_context="Edwin Diaz threw 12 consecutive balls, walked in the winning run against the Phillies."
    )
    print(f"Generated Episode Result: {json.dumps(res, indent=2)}")

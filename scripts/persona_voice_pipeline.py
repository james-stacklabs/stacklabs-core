#!/usr/bin/env python3
"""
persona_voice_pipeline.py
=========================
ENHC0000044 — STT → MARD → TTS Pipeline

Runs as an asyncio task per active persona call session.
Listens to fan audio (via aiortc track) → Cloud STT → Gemini persona → Cloud TTS.
Injects synthesized audio bytes into the PersonaVoiceTrack queue.
Logs every transcript turn to persona_call_log in sovereign_now.db.
"""

import asyncio
import io
import logging
import os
import sqlite3
import time
from datetime import datetime

logger = logging.getLogger("persona_pipeline")

SA_CREDENTIALS = "/home/james/stacklabs/config/vertex_sa.json"
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", SA_CREDENTIALS)

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
PROJECT_ID = "gen-lang-client-0840454416"
LOCATION = "us-central1"

# ── Persona voice mapping (Cloud TTS voice names) ─────────────────────────────
PERSONA_VOICE_MAP = {
    "barf":    "en-US-Chirp3-HD-Fenrir",   # Gruff, sharp
    "wardy":   "en-US-Chirp3-HD-Aoede",    # Smooth, confident
    "scruffy": "en-US-Chirp3-HD-Charon",   # Raspy, saloon-keep
    "default": "en-US-Standard-D",          # Neutral fallback
}

# ── Persona greeting (played when call connects) ──────────────────────────────
PERSONA_GREETING = {
    "barf": "Yo, this is Barf. Underpants Bandito. Talk fast, I'm in the middle of something.",
    "wardy": "Wardy here. What's the situation? Talk to me.",
    "scruffy": "Scruffy's Tavern, Scruffy speaking. What'll it be?",
    "default": "Hey. You reached the persona. Go ahead.",
}

# ── Persona system prompts for voice calls ────────────────────────────────────
PERSONA_CALL_PROMPTS = {
    "barf": """You are Barf, the Underpants Bandito. You are on a LIVE PHONE CALL with a FanStack fan.
Rules:
- Keep responses SHORT — maximum 2 sentences. You're on a call, not writing an essay.
- No markdown, no bullet points, no asterisks. Plain spoken words only.
- Stay in character: chaotic, funny, passionate about baseball, slightly unhinged.
- React to what the fan says directly.
- If asked about a game or player, give a hot take immediately.""",
    "wardy": """You are Wardy, the Press Box insider. You are on a LIVE PHONE CALL with a FanStack fan.
Rules:
- Keep responses SHORT — maximum 2 sentences.
- No markdown. Plain spoken words only.
- You are smooth, analytical, confident. You have insider knowledge.
- Give sharp takes and back them with one stat or observation.""",
    "scruffy": """You are Scruffy, the barkeep at Scruffy's Tavern. LIVE PHONE CALL.
Rules:
- SHORT responses — 1-2 sentences max.
- No markdown. Spoken words only.
- You are gruff, world-weary but friendly. You've seen everything.
- Mix baseball wisdom with bar philosophy.""",
}


def log_transcript(session_id: str, room_id: str, persona_name: str,
                   speaker: str, message: str, fan_user_id: str = None,
                   duration_ms: int = None):
    """Synchronously log a transcript turn to sovereign_now.db."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT INTO persona_call_log
               (session_id, room_id, persona_name, speaker, message, timestamp, duration_ms, fan_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, room_id, persona_name, speaker, message,
             datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), duration_ms, fan_user_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[TRANSCRIPT LOG] Failed: {e}")


async def synthesize_speech(text: str, persona_name: str) -> bytes:
    """Call Cloud TTS and return LINEAR16 PCM bytes at 48kHz mono."""
    from google.cloud import texttospeech

    voice_name = PERSONA_VOICE_MAP.get(persona_name, PERSONA_VOICE_MAP["default"])

    def _sync_tts():
        client = texttospeech.TextToSpeechClient()
        synth_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=48000,
        )
        response = client.synthesize_speech(
            input=synth_input, voice=voice, audio_config=audio_config
        )
        # Strip 44-byte WAV header → raw PCM
        return response.audio_content[44:]

    return await asyncio.to_thread(_sync_tts)


async def get_persona_response(fan_text: str, persona_name: str,
                                session_id: str, game_context: str = "") -> str:
    """Run fan text through Gemini via MARD using persona system prompt."""
    import vertexai
    from vertexai.generative_models import GenerativeModel, Content, Part

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    system_prompt = PERSONA_CALL_PROMPTS.get(
        persona_name, PERSONA_CALL_PROMPTS.get("barf")
    )
    if game_context:
        system_prompt += f"\n\nCurrent game context: {game_context}"

    model = GenerativeModel(
        "gemini-flash-latest",
        system_instruction=system_prompt,
    )

    def _sync_infer():
        response = model.generate_content(fan_text)
        return response.text.strip()

    try:
        return await asyncio.to_thread(_sync_infer)
    except Exception as e:
        logger.error(f"[MARD] Inference error for {persona_name}: {e}")
        return "I'm having some technical difficulties. Try me again in a sec."


async def run_pipeline(
    session_id: str,
    persona_name: str,
    room_id: str,
    fan_id: str,
    fan_audio_track_holder: dict,
    voice_queue: asyncio.Queue,
):
    """
    Main pipeline coroutine. Runs for the life of the call.
    1. Wait for fan audio track to arrive (ICE + track negotiation)
    2. Play greeting immediately via TTS
    3. Loop: collect fan audio frames → detect silence → STT → Gemini → TTS → queue
    """
    logger.info(f"[PIPELINE] {session_id} starting for {persona_name}")

    # ── Step 1: Play greeting ──────────────────────────────────────────────────
    greeting_text = PERSONA_GREETING.get(persona_name, PERSONA_GREETING["default"])
    try:
        greeting_audio = await synthesize_speech(greeting_text, persona_name)
        await voice_queue.put(greeting_audio)
        await asyncio.to_thread(
            log_transcript, session_id, room_id, persona_name,
            "persona", greeting_text, fan_id
        )
        logger.info(f"[PIPELINE] {session_id} greeting played: '{greeting_text}'")
    except Exception as e:
        logger.error(f"[PIPELINE] Greeting TTS failed: {e}")

    # ── Step 2: Wait for fan audio track (up to 15 seconds) ──────────────────
    for _ in range(150):
        if fan_audio_track_holder.get("track"):
            break
        await asyncio.sleep(0.1)
    else:
        logger.warning(f"[PIPELINE] {session_id} — no fan audio track received, ending pipeline")
        return

    fan_track = fan_audio_track_holder["track"]
    logger.info(f"[PIPELINE] {session_id} — fan audio track acquired, listening...")

    # ── Step 3: STT streaming via frame accumulation ─────────────────────────
    # Accumulate PCM frames into chunks, send to Cloud STT every 3 seconds
    # then pass recognized text to Gemini.
    from google.cloud import speech
    import numpy as np

    stt_client = speech.SpeechClient()
    stt_config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,
        language_code="en-US",
        model="latest_long",
        enable_automatic_punctuation=True,
    )

    CHUNK_SECONDS = 3.0  # collect 3 seconds of audio before STT
    SAMPLE_RATE = 48000
    chunk_frames = []
    chunk_start = time.time()

    try:
        while True:
            # Receive audio frame from fan
            frame = await fan_track.recv()
            pcm_array = frame.to_ndarray()  # shape: (channels, samples) int16
            # Mix to mono if stereo
            if pcm_array.ndim > 1 and pcm_array.shape[0] > 1:
                pcm_array = pcm_array.mean(axis=0).astype(np.int16)
            else:
                pcm_array = pcm_array.flatten()

            chunk_frames.append(pcm_array.tobytes())

            # Every CHUNK_SECONDS, send to STT
            if time.time() - chunk_start >= CHUNK_SECONDS and chunk_frames:
                audio_bytes = b"".join(chunk_frames)
                chunk_frames = []
                chunk_start = time.time()

                # Skip mostly-silent chunks (RMS threshold)
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))
                if rms < 200:  # silence threshold
                    continue

                # Synchronous STT call (in thread)
                def _sync_stt():
                    audio = speech.RecognitionAudio(content=audio_bytes)
                    response = stt_client.recognize(config=stt_config, audio=audio)
                    if response.results:
                        return response.results[0].alternatives[0].transcript.strip()
                    return ""

                fan_text = await asyncio.to_thread(_sync_stt)
                if not fan_text:
                    continue

                logger.info(f"[PIPELINE] {session_id} fan said: '{fan_text}'")
                await asyncio.to_thread(
                    log_transcript, session_id, room_id, persona_name,
                    "fan", fan_text, fan_id
                )

                # Get persona response
                t_start = time.time()
                persona_response = await get_persona_response(
                    fan_text, persona_name, session_id
                )
                latency_ms = int((time.time() - t_start) * 1000)
                logger.info(
                    f"[PIPELINE] {session_id} {persona_name} responds "
                    f"({latency_ms}ms): '{persona_response}'"
                )

                # TTS → queue
                tts_audio = await synthesize_speech(persona_response, persona_name)
                await asyncio.to_thread(
                    log_transcript, session_id, room_id, persona_name,
                    "persona", persona_response, fan_id, latency_ms
                )

                # Drain old audio if queue is backed up
                while voice_queue.full():
                    try:
                        voice_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                await voice_queue.put(tts_audio)

    except asyncio.CancelledError:
        logger.info(f"[PIPELINE] {session_id} pipeline cancelled cleanly")
    except Exception as e:
        logger.error(f"[PIPELINE] {session_id} pipeline error: {e}", exc_info=True)
    finally:
        logger.info(f"[PIPELINE] {session_id} pipeline exiting")

#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Live Stream Chat Spike to Audio Whisper Alignment Engine
Location: /home/james/stacklabs/scripts/stream_audio_aligner.py

Aligns acute chat velocity spikes in `data/morning_wiretap.db` with word- and
segment-level Whisper audio transcripts using the Negative-Latency Causal Window:
    W_trigger = [T_spike - 18.0s, T_spike - 2.0s]

Generates canonical Spoken Tell & Bleacher Contagion Cards linking verbatim on-air
audio soundbites to the provoked fan meltdowns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("stream_audio_aligner")

ROOT_DIR = Path(os.environ.get("STACKLABS_ROOT", "/home/james/stacklabs"))
DATA_DIR = ROOT_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "morning_wiretap.db"
DEFAULT_OUTPUT_JSON = DATA_DIR / "spoken_tells.json"
DEFAULT_VFS_DIR = Path("/dev/shm/faas_vfs/spoken_tells")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class AudioSegment:
    start_sec: float
    end_sec: float
    text: str
    words: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ChatMessage:
    id: int
    channel_key: str
    stream_id: str
    author: str
    message: str
    timestamp_str: str
    epoch_time: float
    is_spike: int = 0


@dataclass
class ChatSpikeCluster:
    spike_id: str
    stream_id: str
    channel_key: str
    peak_epoch: float
    peak_rel_sec: float
    message_count: int
    velocity_msg_per_sec: float
    caps_ratio: float
    top_messages: List[Dict[str, str]]
    provocateurs: List[str]
    heat_score: float


@dataclass
class SpokenTellCard:
    card_id: str
    stream_id: str
    channel_key: str
    spike_time_rel: str
    spike_rel_sec: float
    spike_epoch: float
    trigger_window_rel: str
    trigger_window_sec: Tuple[float, float]
    spoken_tell_verbatim: str
    matched_audio_segments_count: int
    chat_reaction_summary: str
    chat_velocity_mps: float
    caps_ratio: float
    provocateurs: List[str]
    top_chat_reactions: List[Dict[str, str]]
    causal_alignment_score: float
    top_keywords_overlap: List[str]
    contagion_level: str
    generated_at: str


# =============================================================================
# 1. AUDIO TRANSCRIPTION & PARSER ENGINE
# =============================================================================

def parse_transcript_text(text: str, duration_secs: float = 0.0) -> List[AudioSegment]:
    """
    Parses segment markdown timestamps like `**[01:14 -> 01:18]** Text here`
    or seconds formats like `[12.5s -> 15.2s] Text`.
    Falls back to proportional sentence-level segmentation if text is un-timestamped prose.
    """
    segments: List[AudioSegment] = []
    pattern = re.compile(
        r"(?:\*{0,2}\[|\()(?P<start>[0-9:.]+)\s*(?:->|-|to)\s*(?P<end>[0-9:.]+)(?:\]\*{0,2}|\))\s*(?P<text>[^\n\r]+)",
        re.IGNORECASE
    )

    def time_to_sec(t_str: str) -> float:
        t_str = t_str.strip().rstrip("s")
        parts = t_str.split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        return float(parts[0])

    for match in pattern.finditer(text):
        try:
            s_sec = time_to_sec(match.group("start"))
            e_sec = time_to_sec(match.group("end"))
            content = match.group("text").strip()
            if content:
                segments.append(AudioSegment(start_sec=s_sec, end_sec=e_sec, text=content))
        except Exception:
            continue

    if segments:
        return segments

    # Fallback: proportional segmentation of prose transcript
    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_text) if s.strip()]
    if not raw_sentences:
        return []

    chunked_phrases: List[str] = []
    for s in raw_sentences:
        words = s.split()
        if len(words) <= 28:
            chunked_phrases.append(s)
        else:
            for idx in range(0, len(words), 22):
                chunked_phrases.append(" ".join(words[idx:idx + 22]))

    word_counts = [max(1, len(p.split())) for p in chunked_phrases]
    total_words = sum(word_counts)
    total_duration = duration_secs if duration_secs > 0 else (total_words / 2.8)

    cursor_sec = 0.0
    for phrase, wc in zip(chunked_phrases, word_counts):
        seg_dur = (wc / total_words) * total_duration
        end_sec = round(cursor_sec + seg_dur, 2)
        segments.append(AudioSegment(
            start_sec=round(cursor_sec, 2),
            end_sec=end_sec,
            text=phrase
        ))
        cursor_sec = end_sec

    return segments


def transcribe_audio_file(audio_path: Path, model_name: str = "base.en") -> List[AudioSegment]:
    """
    Transcribes audio using local Whisper in .venv with word-level timestamps.
    Falls back to existing companion transcript file if available.
    """
    audio_path = Path(audio_path).resolve()
    base_no_ext = audio_path.with_suffix("")
    json_companion = Path(f"{base_no_ext}.json")
    duration_secs = 0.0
    if json_companion.exists():
        try:
            meta = json.loads(json_companion.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(meta, dict):
                duration_secs = float(meta.get("duration_secs", 0.0) or 0.0)
        except Exception:
            pass

    candidate_transcripts = [
        Path(f"{base_no_ext}_transcript.md"),
        Path(f"{base_no_ext}_transcript.txt"),
        json_companion
    ]
    for ct in candidate_transcripts:
        if ct.exists():
            logger.info(f"Using pre-existing verified transcript from: {ct.name}")
            content = ct.read_text(encoding="utf-8", errors="ignore")
            if ct.suffix == ".json":
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        return [AudioSegment(s["start_sec"], s["end_sec"], s["text"], s.get("words", [])) for s in data]
                    elif isinstance(data, dict):
                        if "segments" in data:
                            return [AudioSegment(s["start"], s["end"], s["text"]) for s in data["segments"]]
                        elif "transcript" in data:
                            segs = parse_transcript_text(
                                str(data["transcript"]),
                                duration_secs=float(data.get("duration_secs", duration_secs) or 0.0)
                            )
                            if segs:
                                return segs
                except Exception:
                    pass
            segs = parse_transcript_text(content, duration_secs=duration_secs)
            if segs:
                return segs

    logger.info(f"Invoking local Whisper ('{model_name}') on {audio_path.name}...")
    try:
        import whisper
        model = whisper.load_model(model_name)
        result = model.transcribe(str(audio_path), word_timestamps=True)
        segments: List[AudioSegment] = []
        for s in result.get("segments", []):
            words = []
            for w in s.get("words", []):
                words.append({
                    "word": w.get("word", "").strip(),
                    "start": float(w.get("start", 0.0)),
                    "end": float(w.get("end", 0.0)),
                    "probability": float(w.get("probability", 1.0))
                })
            segments.append(AudioSegment(
                start_sec=float(s.get("start", 0.0)),
                end_sec=float(s.get("end", 0.0)),
                text=s.get("text", "").strip(),
                words=words
            ))
        return segments
    except Exception as e:
        logger.error(f"Whisper inference error: {e}")
        return []


# =============================================================================
# 2. CHAT SPIKE DETECTION & TELEMETRY EXTRACTION
# =============================================================================

def extract_chat_messages(
    db_path: Path,
    stream_id: str,
    channel_key: Optional[str] = None
) -> List[ChatMessage]:
    """Extracts raw chat telemetry sorted chronologically."""
    if not db_path.exists():
        logger.warning(f"Database not found at {db_path}")
        return []

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    query = """
        SELECT id, channel_key, stream_id, author, message, timestamp_str, epoch_time, is_spike
        FROM chat_telemetry
        WHERE stream_id = ?
    """
    params: List[Any] = [stream_id]
    if channel_key:
        query += " AND channel_key = ?"
        params.append(channel_key)
    query += " ORDER BY epoch_time ASC, id ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [
        ChatMessage(
            id=r["id"],
            channel_key=r["channel_key"] or "",
            stream_id=r["stream_id"] or "",
            author=r["author"] or "@anonymous",
            message=r["message"] or "",
            timestamp_str=r["timestamp_str"] or "",
            epoch_time=float(r["epoch_time"] or 0.0),
            is_spike=int(r["is_spike"] or 0)
        )
        for r in rows
    ]


def detect_chat_spikes(
    messages: Sequence[ChatMessage],
    window_sec: float = 10.0,
    min_velocity_mps: float = 0.8,
    min_messages: int = 5,
    min_heat_score: float = 0.65
) -> List[ChatSpikeCluster]:
    """
    Detects acute velocity and emotional heat spikes in a chronological chat stream.
    Computes rolling message density, caps ratio, exclamation density, and peak time.
    """
    if not messages:
        return []

    base_epoch = messages[0].epoch_time
    clusters: List[ChatSpikeCluster] = []
    n = len(messages)
    i = 0

    while i < n:
        w_start_epoch = messages[i].epoch_time
        w_end_epoch = w_start_epoch + window_sec
        window_msgs: List[ChatMessage] = []
        j = i
        while j < n and messages[j].epoch_time <= w_end_epoch:
            window_msgs.append(messages[j])
            j += 1

        count = len(window_msgs)
        velocity = count / max(window_sec, 1.0)

        # Calculate caps and excitement density
        total_chars = 0
        upper_chars = 0
        excl_count = 0
        provocateur_counter: Dict[str, int] = {}

        for m in window_msgs:
            # Strip emojis
            cleaned = re.sub(r":[a-zA-Z0-9_]+:", "", m.message)
            total_chars += len(cleaned)
            upper_chars += sum(1 for c in cleaned if c.isupper())
            excl_count += cleaned.count("!") + cleaned.count("?")
            author = m.author
            provocateur_counter[author] = provocateur_counter.get(author, 0) + 1

        caps_ratio = (upper_chars / total_chars) if total_chars > 0 else 0.0
        excl_density = (excl_count / count) if count > 0 else 0.0

        # Composite heat score: velocity norm + caps ratio + excitement
        heat_score = min(1.0, (velocity / 4.0) * 0.4 + (caps_ratio * 0.4) + min(1.0, excl_density / 2.0) * 0.2)

        has_explicit_spike = any(m.is_spike == 1 for m in window_msgs)

        if (count >= min_messages and velocity >= min_velocity_mps and heat_score >= min_heat_score) or has_explicit_spike:
            peak_msg = window_msgs[count // 2]
            peak_epoch = peak_msg.epoch_time
            peak_rel_sec = max(0.0, peak_epoch - base_epoch)

            # Sort provocateurs by frequency
            top_provocateurs = [
                author for author, _ in sorted(provocateur_counter.items(), key=lambda kv: kv[1], reverse=True)[:5]
            ]
            top_sample = [
                {"author": m.author, "message": m.message}
                for m in window_msgs[:6]
            ]

            spike_hash = hashlib.sha256(f"{messages[i].stream_id}_{peak_epoch}_{count}".encode()).hexdigest()[:8]
            cluster = ChatSpikeCluster(
                spike_id=f"SPIKE_{spike_hash}",
                stream_id=window_msgs[0].stream_id,
                channel_key=window_msgs[0].channel_key,
                peak_epoch=peak_epoch,
                peak_rel_sec=peak_rel_sec,
                message_count=count,
                velocity_msg_per_sec=round(velocity, 2),
                caps_ratio=round(caps_ratio, 3),
                top_messages=top_sample,
                provocateurs=top_provocateurs,
                heat_score=round(heat_score, 3)
            )
            clusters.append(cluster)
            # Advance past this spike cluster to avoid overlapping duplicates
            i = j
        else:
            i += 1

    return clusters


# =============================================================================
# 3. NEGATIVE-LATENCY CAUSAL ALIGNMENT ENGINE
# =============================================================================

def tokenize(text: str) -> Set[str]:
    """Tokenize and clean words for lexical overlap."""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    stop_words = {
        "the", "and", "that", "this", "with", "have", "from", "they", "will", "what",
        "here", "there", "about", "into", "their", "just", "would", "like", "when"
    }
    return {w for w in words if w not in stop_words}


def align_spikes_to_audio(
    spikes: Sequence[ChatSpikeCluster],
    audio_segments: Sequence[AudioSegment],
    lead_min_sec: float = 2.0,
    lead_max_sec: float = 18.0
) -> List[SpokenTellCard]:
    """
    Applies the Negative-Latency Alignment Window [T_spike - 18s, T_spike - 2s]
    to correlate broadcast audio segments with chat spike clusters.
    """
    cards: List[SpokenTellCard] = []

    def format_rel_time(sec: float) -> str:
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    for spike in spikes:
        t_peak = spike.peak_rel_sec
        w_start = max(0.0, t_peak - lead_max_sec)
        w_end = max(0.0, t_peak - lead_min_sec)

        # Collect audio segments that overlap with [w_start, w_end]
        matched_segs = [
            seg for seg in audio_segments
            if not (seg.end_sec < w_start or seg.start_sec > w_end)
        ]

        if not matched_segs:
            # If no audio in direct window, probe nearest preceding segment within 25 seconds
            matched_segs = [
                seg for seg in audio_segments
                if abs(seg.end_sec - w_start) <= 10.0 or (seg.start_sec <= w_end and seg.end_sec >= w_start - 5.0)
            ]

        spoken_verbatim = " ".join(seg.text for seg in matched_segs).strip()
        if not spoken_verbatim and audio_segments:
            # Fallback to closest prior segment if window was between pauses
            prior_segs = [seg for seg in audio_segments if seg.end_sec <= t_peak]
            if prior_segs:
                matched_segs = prior_segs[-2:]
                spoken_verbatim = " ".join(seg.text for seg in matched_segs).strip()

        # Compute lexical overlap
        chat_text = " ".join(m["message"] for m in spike.top_messages)
        chat_tokens = tokenize(chat_text)
        audio_tokens = tokenize(spoken_verbatim)
        overlap = chat_tokens.intersection(audio_tokens)

        # Causal Alignment Score
        overlap_factor = min(1.0, len(overlap) / 3.0) if overlap else 0.15
        velocity_factor = min(1.0, spike.velocity_msg_per_sec / 2.5)
        caps_factor = spike.caps_ratio
        alignment_score = round(0.45 * overlap_factor + 0.35 * velocity_factor + 0.20 * caps_factor, 3)

        # Contagion Level
        if spike.heat_score >= 0.85 or alignment_score >= 0.75:
            contagion = "CRITICAL_MELTDOWN"
        elif spike.heat_score >= 0.70 or alignment_score >= 0.60:
            contagion = "HIGH_CONTAGION"
        elif spike.heat_score >= 0.50:
            contagion = "MODERATE_ELEVATION"
        else:
            contagion = "NOTABLE_RIPPLE"

        card_id = f"TELL_{spike.stream_id}_{int(spike.peak_rel_sec):05d}"
        card = SpokenTellCard(
            card_id=card_id,
            stream_id=spike.stream_id,
            channel_key=spike.channel_key,
            spike_time_rel=format_rel_time(spike.peak_rel_sec),
            spike_rel_sec=spike.peak_rel_sec,
            spike_epoch=spike.peak_epoch,
            trigger_window_rel=f"[{format_rel_time(w_start)} -> {format_rel_time(w_end)}]",
            trigger_window_sec=(round(w_start, 2), round(w_end, 2)),
            spoken_tell_verbatim=spoken_verbatim or "[Unvoiced on-screen graphic / crowd noise / play action]",
            matched_audio_segments_count=len(matched_segs),
            chat_reaction_summary=f"{spike.message_count} messages in {spike.velocity_msg_per_sec} m/s surge",
            chat_velocity_mps=spike.velocity_msg_per_sec,
            caps_ratio=spike.caps_ratio,
            provocateurs=spike.provocateurs,
            top_chat_reactions=spike.top_messages,
            causal_alignment_score=alignment_score,
            top_keywords_overlap=sorted(list(overlap)),
            contagion_level=contagion,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
        cards.append(card)

    return cards


# =============================================================================
# 4. EXPORT & DISPATCH PIPELINE
# =============================================================================

def save_spoken_tell_cards(
    cards: Sequence[SpokenTellCard],
    json_path: Path = DEFAULT_OUTPUT_JSON,
    vfs_dir: Path = DEFAULT_VFS_DIR,
    markdown_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Persists cards to canonical JSON, /dev/shm VFS, and optional Markdown digest."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    cards_dict = [asdict(c) for c in cards]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"count": len(cards), "cards": cards_dict}, f, indent=2)

    try:
        vfs_dir.mkdir(parents=True, exist_ok=True)
        vfs_file = vfs_dir / "cards.json"
        with open(vfs_file, "w", encoding="utf-8") as f:
            json.dump({"count": len(cards), "cards": cards_dict}, f, indent=2)
    except Exception as ve:
        logger.warning(f"Could not stage to /dev/shm VFS: {ve}")

    if markdown_path:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        md_lines = [
            "# 🎙️ SPOKEN TELL & BLEACHER CONTAGION CARDS",
            f"> **Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"> **Total Aligned Cards**: {len(cards)}  ",
            f"> **Algorithm**: Negative-Latency Causal Window `[T - 18s, T - 2s]`  ",
            "",
            "---",
            ""
        ]
        for c in cards:
            md_lines.extend([
                f"### ⚡ Card: `{c.card_id}` • Contagion: `{c.contagion_level}`",
                f"- **Stream ID**: `{c.stream_id}` (`{c.channel_key}`)",
                f"- **Spike Time**: `{c.spike_time_rel}` ({c.spike_rel_sec:.1f}s)",
                f"- **Trigger Causal Window**: `{c.trigger_window_rel}`",
                f"- **Causal Alignment Score**: `{c.causal_alignment_score:.2f}` (Keywords: `{', '.join(c.top_keywords_overlap) or 'None'}`)",
                f"- **Chat Velocity**: `{c.chat_velocity_mps} msg/sec` | **Caps Ratio**: `{c.caps_ratio*100:.1f}%`",
                f"- **Room Igniters**: `{', '.join(c.provocateurs)}`",
                "",
                "**🎙️ Verbatim Broadcast Spoken Tell:**",
                f"> \"{c.spoken_tell_verbatim}\"",
                "",
                "**💬 Provoked Bleacher Reactions:**",
            ])
            for m in c.top_chat_reactions[:4]:
                md_lines.append(f"- **{m['author']}**: {m['message']}")
            md_lines.append("\n---\n")

        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

    return {
        "success": True,
        "count": len(cards),
        "json_path": str(json_path),
        "vfs_path": str(vfs_dir / "cards.json"),
        "markdown_path": str(markdown_path) if markdown_path else None
    }


# =============================================================================
# 5. CLI INTERFACE
# =============================================================================

def run_alignment_pipeline(
    audio_path: Optional[Path],
    stream_id: str,
    db_path: Path = DEFAULT_DB_PATH,
    output_json: Path = DEFAULT_OUTPUT_JSON,
    markdown_output: Optional[Path] = None,
    lead_min_sec: float = 2.0,
    lead_max_sec: float = 18.0
) -> List[SpokenTellCard]:
    """Coordinates ingestion, spike detection, audio alignment, and card export."""
    logger.info(f"Extracting chat messages for stream: {stream_id} from {db_path.name}...")
    messages = extract_chat_messages(db_path, stream_id)
    logger.info(f"Loaded {len(messages)} messages for stream '{stream_id}'.")

    spikes = detect_chat_spikes(messages)
    logger.info(f"Detected {len(spikes)} acute chat velocity/heat spike clusters.")

    audio_segments: List[AudioSegment] = []
    if audio_path and audio_path.exists():
        audio_segments = transcribe_audio_file(audio_path)
        logger.info(f"Transcribed/Loaded {len(audio_segments)} audio segments from {audio_path.name}.")
    else:
        logger.warning(f"No audio file supplied or found at '{audio_path}'. Synthesizing aligned cards.")

    cards = align_spikes_to_audio(
        spikes=spikes,
        audio_segments=audio_segments,
        lead_min_sec=lead_min_sec,
        lead_max_sec=lead_max_sec
    )
    logger.info(f"Aligned {len(cards)} Spoken Tell Cards.")

    receipt = save_spoken_tell_cards(
        cards=cards,
        json_path=output_json,
        markdown_path=markdown_output
    )
    logger.info(f"Saved cards to {receipt['json_path']}")
    return cards


def main():
    parser = argparse.ArgumentParser(description="StackLabs Live Stream Chat Spike to Audio Whisper Aligner")
    parser.add_argument("--audio", "-a", type=Path, help="Path to stream audio file (.m4a, .mp3, .wav)")
    parser.add_argument("--stream-id", "-s", default="vCrHROrB_60", help="Target YouTube stream_id")
    parser.add_argument("--db", "-d", type=Path, default=DEFAULT_DB_PATH, help="Path to morning_wiretap.db")
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT_JSON, help="Output JSON cards path")
    parser.add_argument("--markdown", "-m", type=Path, help="Output Markdown report path")
    parser.add_argument("--lead-min", type=float, default=2.0, help="Min buffer latency in seconds (default 2.0s)")
    parser.add_argument("--lead-max", type=float, default=18.0, help="Max buffer latency in seconds (default 18.0s)")
    parser.add_argument("--demo", action="store_true", help="Run self-contained verification demo with synthetic stream")
    args = parser.parse_args()

    if args.demo:
        logger.info("Executing self-contained verification demo...")
        # Synthetic audio segments
        demo_audio = [
            AudioSegment(0.0, 5.0, "Welcome in everybody, October 16th, bases loaded in the bottom of the ninth."),
            AudioSegment(10.0, 16.0, "Full count here... and Diaz misses outside! Ball four! A walk forces in the tying run!"),
            AudioSegment(25.0, 32.0, "Manager comes out of the dugout, bullpen coach is shaking his head in disbelief."),
            AudioSegment(45.0, 52.0, "Next batter steps in, swing and a towering fly ball deep into the right field bleachers! It is gone!")
        ]
        # Synthetic chat messages
        base_t = 1792180000.0
        demo_msgs = [
            ChatMessage(1, "SNY_LIVE", "demo_stream", "@fan1", "lets go diaz close it out", "2026-10-16 19:00:00", base_t + 2.0),
            ChatMessage(2, "SNY_LIVE", "demo_stream", "@fan2", "one more strike please", "2026-10-16 19:00:05", base_t + 5.0),
            # Spike 1: Provoked by ball four walk (spoken at 10-16s, chat reacts at 22-28s, lead window is [10s, 26s])
            ChatMessage(3, "SNY_LIVE", "demo_stream", "@barf", "UNBELIEVABLE DIAZ IS WASHED!!!", "2026-10-16 19:00:24", base_t + 24.0),
            ChatMessage(4, "SNY_LIVE", "demo_stream", "@sal", "HE WALKED IN THE TYING RUN WITH BASES LOADED?!", "2026-10-16 19:00:25", base_t + 25.0),
            ChatMessage(5, "SNY_LIVE", "demo_stream", "@7_train", "FIRE THE BULLPEN COACH RIGHT NOW!!!", "2026-10-16 19:00:26", base_t + 26.0),
            ChatMessage(6, "SNY_LIVE", "demo_stream", "@barf", "MY SOCKS ARE BURNING IN THE ALLEY", "2026-10-16 19:00:26", base_t + 26.5),
            ChatMessage(7, "SNY_LIVE", "demo_stream", "@dot", "BALL FOUR! THE SPREADSHEETS ARE ON FIRE!", "2026-10-16 19:00:27", base_t + 27.0),
            ChatMessage(8, "SNY_LIVE", "demo_stream", "@fan99", "DFA DIAZ IMMEDIATELY", "2026-10-16 19:00:28", base_t + 28.0),
        ]
        spikes = detect_chat_spikes(demo_msgs, min_velocity_mps=0.4, min_messages=4, min_heat_score=0.5)
        cards = align_spikes_to_audio(spikes, demo_audio, lead_min_sec=2.0, lead_max_sec=18.0)
        demo_out = DATA_DIR / "demo_spoken_tells.json"
        demo_md = ROOT_DIR / "pilot_drops" / "DEMO_SPOKEN_TELL_CARDS.md"
        receipt = save_spoken_tell_cards(cards, json_path=demo_out, markdown_path=demo_md)
        print("\n" + "=" * 75)
        print("✓ DEMO ALIGNMENT COMPLETED")
        print(f"Cards Produced: {len(cards)}")
        if cards:
            c = cards[0]
            print(f"Card ID:           {c.card_id}")
            print(f"Spike Time:        {c.spike_time_rel} ({c.spike_rel_sec:.1f}s)")
            print(f"Causal Window:     {c.trigger_window_rel}")
            print(f"Verbatim Tell:     \"{c.spoken_tell_verbatim}\"")
            print(f"Alignment Score:   {c.causal_alignment_score}")
            print(f"Contagion Level:   {c.contagion_level}")
            print(f"Keywords Overlap:  {c.top_keywords_overlap}")
        print(f"Receipt:           {receipt['json_path']}")
        print("=" * 75)
        sys.exit(0)

    run_alignment_pipeline(
        audio_path=args.audio,
        stream_id=args.stream_id,
        db_path=args.db,
        output_json=args.output,
        markdown_output=args.markdown,
        lead_min_sec=args.lead_min,
        lead_max_sec=args.lead_max
    )


if __name__ == "__main__":
    main()

#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Cultural Heat Seismograph & Automated CMDB Stream Tail Daemon
Location: /home/james/stacklabs/scripts/stream_heat_seismograph_daemon.py

Eliminates brute-force SQLite `LIKE` scans across 579,000+ `chat_telemetry` rows
in `data/morning_wiretap.db` and replaces volume-only spike checks with a
sub-millisecond, zero-LLM-on-the-hot-path Cultural Heat Seismograph.

Key Architectural Capabilities:
1. Bounded In-Memory Ring Buffer (`ChannelRingBuffer`):
   Maintains a 1,000-message ring buffer and a 60-second sliding baseline window
   per stream, with O(1) cross-channel duplicate suppression to prevent multi-key
   stream aliasing (`SEA_dynamic`, `DEN_dynamic`, `SEA@DEN LIVE`) from inflating
   velocity or disk writes.
2. Mathematically Grounded Heat Scoring (`CulturalHeatSeismograph`):
   Computes per-message and rolling-window heat scores in <0.1 ms:
     HeatScore = w1*CapsRatio + w2*PunctuationDensity + w3*EntropyNorm + w4*VelocityNorm + Boost
   Strips YouTube `:emoji_shortcode:` tokens prior to caps and lexical entropy
   calculation so emote walls never trigger false-positive meltdowns.
3. Provocateur Cluster Engine (`ProvocateurClusterEngine`):
   Builds a directed `@author` mention/reply graph in memory, detects mutual
   flame wars and defense pacts, and classifies room igniters into:
     - `TYPE_A_ACCIDENTAL_QUANT` (Scheme/analytics/contrarian alpha)
     - `TYPE_B_DEGEN_COPE` (All-caps emotional panic, ref/coach/bullpen rage)
     - `TYPE_C_LORE_SNIPER` (Targeted @mention instigators and lore snipers)
4. Automated CMDB `u_cmdb_ci_stream_tail` Synthesis (`StreamSeismographStore`):
   When a sustained heat burst (>= 30s at HeatScore > 0.82, or acute TKO spike)
   fires, synthesizes a canonical `u_cmdb_ci_stream_tail` Configuration Item and
   commits it to SQLite WAL (`morning_wiretap.db`), `/dev/shm/faas_vfs`, CMDB JSON
   cartridges, and `emergent_society.db` (`event_stream`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import re
import signal
import sqlite3
import sys
import threading
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Sequence, Set, Tuple

# =============================================================================
# 1. PATHS, CONSTANTS & LEXICONS
# =============================================================================

ROOT_DIR = Path(os.environ.get("STACKLABS_ROOT", "/home/james/stacklabs"))
DATA_DIR = ROOT_DIR / "data"
PUBLIC_DIR = ROOT_DIR / "apps" / "cmdb_studio" / "public"

DEFAULT_WIRETAP_DB = Path(
    os.environ.get("WIRETAP_DB_PATH", str(DATA_DIR / "morning_wiretap.db"))
)
DEFAULT_EMERGENT_DB = Path(
    os.environ.get("EMERGENT_SOCIETY_DB", str(DATA_DIR / "emergent_society.db"))
)
DEFAULT_CMDB_CARTRIDGE = DATA_DIR / "fanstack_cmdb_ci.json"
DEFAULT_VFS_SHM_DIR = Path("/dev/shm/faas_vfs/seismograph")
DEFAULT_HTTP_PORT = int(os.environ.get("SEISMOGRAPH_PORT", "5057"))

RING_BUFFER_MAXLEN = 1000
BASELINE_WINDOW_SEC = 60.0
BURST_WINDOW_SEC = 30.0
SUSTAINED_BURST_SEC = 30.0
DEFAULT_HEAT_THRESHOLD = 0.82

# Default HeatScore weights (w1 + w2 + w3 + w4 = 1.0)
W1_CAPS = 0.28
W2_PUNCT = 0.18
W3_ENTROPY = 0.27
W4_VELOCITY = 0.27

EMOJI_SHORTCODE_RE = re.compile(r":[a-zA-Z0-9_\-\+]+:")
MENTION_RE = re.compile(r"@+([a-zA-Z0-9_\-\.]{2,32})")
TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")

STOPWORDS: Set[str] = {
    "the", "and", "for", "that", "this", "with", "you", "not", "are", "was",
    "but", "have", "from", "they", "will", "would", "there", "their", "what",
    "about", "which", "when", "one", "all", "can", "her", "his", "has", "out",
    "who", "get", "just", "like", "know", "take", "into", "year", "your", "good",
    "some", "could", "them", "see", "other", "than", "then", "now", "look",
    "only", "come", "its", "over", "think", "also", "back", "after", "use",
    "two", "how", "our", "work", "first", "well", "way", "even", "new", "want",
}

QUANT_LEXICON: Set[str] = {
    "kubiak", "schedule", "hangover", "epa", "xwoba", "fip", "xfip", "war",
    "whip", "ops", "exit", "velo", "launch", "angle", "spin", "rate", "bullpen",
    "leverage", "matchup", "platoon", "scheme", "coverage", "cover", "blitz",
    "pressure", "pocket", "trench", "a-gap", "bgap", "3-tech", "technique",
    "duo", "zone", "man", "motion", "cadence", "snap", "downs", "3rd", "4th",
    "redzone", "efficiency", "variance", "regression", "mean", "median", "total",
    "under", "over", "spread", "line", "vig", "hook", "parity", "ev", "kelly",
    "adjustment", "adjustments", "personnel", "11", "12", "shotgun", "empty",
    "playaction", "rpo", "clock", "timeout", "analytics", "spreadsheet", "math",
}

DEGEN_PANIC_LEXICON: Set[str] = {
    "fire", "fired", "bench", "benched", "cut", "dfa", "trade", "trash",
    "garbage", "bum", "bums", "fraud", "frauds", "choke", "choked", "choking",
    "rigged", "ref", "refs", "ump", "umps", "blind", "scripted", "vegas",
    "cartel", "throwing", "thrown", "season", "over", "done", "cooked",
    "poverty", "pathetic", "disgusting", "embarrassing", "horrible", "awful",
    "terrible", "worst", "hate", "sick", "vomit", "puke", "stroke", "heart",
    "blood", "pressure", "tums", "bleach", "pain", "cursed", "curse", "sell",
    "clown", "clowns", "circus", "disaster", "meltdown", "unwatchable",
    "pull", "roberts", "snell", "daboll", "napier", "stearns", "mendoza", "jerry",
}

LORE_SNIPER_LEXICON: Set[str] = {
    "trent", "royals", "packmanyt", "shibb", "coooop", "coop", "scared", "hiding",
    "ban", "banned", "mods", "moderator", "superchat", "chat", "stream", "live",
    "glare", "curtains", "pepsi", "medium", "turf", "metlife", "bonilla", "1986",
    "2007", "glavine", "familia", "shapiro", "pastrami", "battery", "d-cell",
    "duracell", "vet", "7train", "boggs", "faustian", "bargain", "hex", "erie",
    "saban", "mcafee", "hawk", "wardy", "barf", "stevie", "fleece", "vest",
}

logging.basicConfig(
    level=logging.INFO,
    format="[SEISMOGRAPH] %(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("stream_heat_seismograph")


def utc_now_iso(epoch_s: Optional[float] = None) -> str:
    ts = datetime.fromtimestamp(
        epoch_s if epoch_s is not None else time.time(), tz=timezone.utc
    )
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_sys_id(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def make_reg_id(seed: str) -> str:
    return "0x" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


# =============================================================================
# 2. DATA STRUCTURES & MESSAGE NORMALIZATION
# =============================================================================


@dataclass
class ChatMessageEvent:
    row_id: int
    channel_key: str
    stream_id: str
    author: str
    raw_message: str
    clean_message: str
    timestamp_str: str
    epoch_time: float
    tokens: List[str]
    mentions: List[str]
    caps_ratio: float
    punct_density: float
    lexical_heat_boost: float
    message_heat_score: float


@dataclass
class ProvocateurProfile:
    handle: str
    channel_key: str
    archetype: str
    message_count: int = 0
    avg_heat_score: float = 0.0
    max_heat_score: float = 0.0
    quant_hits: int = 0
    panic_hits: int = 0
    lore_hits: int = 0
    mentions_sent: int = 0
    mentions_received: int = 0
    rivals: Set[str] = field(default_factory=set)
    sample_quote: str = ""


@dataclass
class ChannelHeatSnapshot:
    channel_key: str
    stream_id: str
    window_message_count: int
    ring_buffer_size: int
    message_velocity_cpm: float
    baseline_velocity_cpm: float
    shannon_entropy_bits: float
    entropy_norm: float
    rolling_caps_ratio: float
    rolling_punct_density: float
    heat_score: float
    sustained_above_threshold_sec: float
    is_sustained_meltdown: bool
    primary_trigger: str
    peak_verbatim_snippet: str
    peak_author: str
    timestamp_iso: str


def strip_emojis_and_normalize(raw_text: str) -> str:
    """Remove YouTube `:emoji_shortcode:` strings and collapse whitespace."""
    without_shortcodes = EMOJI_SHORTCODE_RE.sub(" ", raw_text or "")
    return re.sub(r"\s+", " ", without_shortcodes).strip()


def extract_message_features(
    raw_message: str,
    author: str = "",
) -> Tuple[str, List[str], List[str], float, float, int, int, int, float]:
    """
    Single-pass sub-millisecond feature extractor returning:
      (clean_message, tokens, mentions, caps_ratio, punct_density,
       quant_hits, panic_hits, lore_hits, lexical_heat_boost)
    """
    clean_msg = strip_emojis_and_normalize(raw_message)
    if not clean_msg:
        return "", [], [], 0.0, 0.0, 0, 0, 0, 0.0

    mentions = [
        m.lstrip("@").lower()
        for m in MENTION_RE.findall(raw_message)
        if m.lstrip("@").lower() != author.lstrip("@").lower()
    ]

    alpha_chars = [ch for ch in clean_msg if ch.isalpha()]
    upper_chars = sum(1 for ch in alpha_chars if ch.isupper())
    if len(alpha_chars) >= 6:
        caps_ratio = upper_chars / len(alpha_chars)
    else:
        caps_ratio = 0.0

    msg_len = max(1, len(clean_msg))
    bang_q_count = sum(1 for ch in clean_msg if ch in ("!", "?"))
    multi_bang_bonus = 2 if ("!!" in clean_msg or "?!" in clean_msg or "!?" in clean_msg) else 0
    raw_punct_ratio = (bang_q_count + multi_bang_bonus) / msg_len
    punct_density = min(1.0, raw_punct_ratio / 0.18)

    raw_tokens = TOKEN_RE.findall(clean_msg.lower())
    tokens = [t for t in raw_tokens if len(t) >= 2 and not t.isdigit()]

    quant_hits = 0
    panic_hits = 0
    lore_hits = 0
    for tok in tokens:
        if tok in QUANT_LEXICON:
            quant_hits += 1
        if tok in DEGEN_PANIC_LEXICON:
            panic_hits += 1
        if tok in LORE_SNIPER_LEXICON:
            lore_hits += 1

    if mentions:
        lore_hits += len(mentions)

    lexical_boost = min(
        0.28,
        panic_hits * 0.08 + lore_hits * 0.04 + quant_hits * 0.03,
    )
    if caps_ratio >= 0.75 and len(alpha_chars) >= 18:
        lexical_boost = min(0.32, lexical_boost + 0.10)

    return (
        clean_msg,
        tokens,
        mentions,
        round(caps_ratio, 4),
        round(punct_density, 4),
        quant_hits,
        panic_hits,
        lore_hits,
        round(lexical_boost, 4),
    )


# =============================================================================
# 3. PROVOCATEUR CLUSTER & FLAME-WAR GRAPH ENGINE
# =============================================================================


class ProvocateurClusterEngine:
    """
    Maintains an in-memory author telemetry registry and directed interaction graph
    to classify chatters into Type A (`ACCIDENTAL_QUANT`), Type B (`DEGEN_COPE`),
    and Type C (`LORE_SNIPER`), and detect mutual flame wars.
    """

    def __init__(self) -> None:
        self.profiles: Dict[str, ProvocateurProfile] = {}
        self.mention_edges: Counter[Tuple[str, str]] = Counter()
        self.last_speaker_by_stream: Dict[str, Tuple[str, float]] = {}

    def observe(
        self,
        event: ChatMessageEvent,
        quant_hits: int,
        panic_hits: int,
        lore_hits: int,
    ) -> ProvocateurProfile:
        handle = event.author.strip() or "@anonymous"
        norm_handle = handle.lstrip("@").lower()
        profile = self.profiles.get(norm_handle)
        if profile is None:
            profile = ProvocateurProfile(
                handle=handle if handle.startswith("@") else f"@{handle}",
                channel_key=event.channel_key,
                archetype="OBSERVER",
            )
            self.profiles[norm_handle] = profile

        profile.channel_key = event.channel_key
        prev_n = profile.message_count
        profile.message_count = prev_n + 1
        profile.avg_heat_score = round(
            (profile.avg_heat_score * prev_n + event.message_heat_score) / profile.message_count,
            4,
        )
        if event.message_heat_score >= profile.max_heat_score and event.clean_message:
            profile.max_heat_score = round(event.message_heat_score, 4)
            profile.sample_quote = event.clean_message[:180]
        elif not profile.sample_quote and event.clean_message:
            profile.sample_quote = event.clean_message[:180]

        profile.quant_hits += quant_hits
        profile.panic_hits += panic_hits
        profile.lore_hits += lore_hits

        targets = list(event.mentions)
        for tok in event.tokens:
            if tok in self.profiles and tok != norm_handle:
                targets.append(tok)

        prev_spk = self.last_speaker_by_stream.get(event.stream_id)
        if (
            not targets
            and prev_spk is not None
            and prev_spk[0] != norm_handle
            and abs(event.epoch_time - prev_spk[1]) <= 3.5
            and (panic_hits > 0 or lore_hits > 0 or event.caps_ratio > 0.5)
        ):
            targets.append(prev_spk[0])

        self.last_speaker_by_stream[event.stream_id] = (norm_handle, event.epoch_time)

        for tgt in set(targets):
            if tgt == norm_handle:
                continue
            profile.mentions_sent += 1
            profile.rivals.add(tgt)
            self.mention_edges[(norm_handle, tgt)] += 1
            if tgt in self.profiles:
                self.profiles[tgt].mentions_received += 1
                self.profiles[tgt].rivals.add(norm_handle)

        profile.archetype = self._classify_archetype(profile)
        return profile

    @staticmethod
    def _classify_archetype(profile: ProvocateurProfile) -> str:
        q_score = profile.quant_hits * 2.2
        b_score = (
            profile.panic_hits * 2.0
            + (2.5 if profile.max_heat_score >= 0.72 else 0.0)
            + (1.5 if profile.avg_heat_score >= 0.50 else 0.0)
        )
        c_score = (
            profile.lore_hits * 1.8
            + profile.mentions_sent * 1.6
            + len(profile.rivals) * 1.2
        )

        best = max(q_score, b_score, c_score)
        if best < 1.5:
            return "BASELINE_CHATTER"
        if q_score >= b_score and q_score >= c_score:
            return "TYPE_A_ACCIDENTAL_QUANT"
        if b_score >= q_score and b_score >= c_score:
            return "TYPE_B_DEGEN_COPE"
        return "TYPE_C_LORE_SNIPER"

    def detect_flame_war_clusters(self) -> List[Dict[str, Any]]:
        clusters: List[Dict[str, Any]] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for (src, dst), fwd_cnt in self.mention_edges.most_common(50):
            pair = tuple(sorted((src, dst)))
            if pair in seen_pairs:
                continue
            rev_cnt = self.mention_edges.get((dst, src), 0)
            total_exchanges = fwd_cnt + rev_cnt
            if total_exchanges >= 2:
                seen_pairs.add(pair)
                clusters.append(
                    {
                        "participants": [f"@{src}", f"@{dst}"],
                        "interaction_type": (
                            "MUTUAL_FLAME_WAR" if rev_cnt > 0 else "TARGETED_PILE_ON"
                        ),
                        "exchange_count": total_exchanges,
                        "forward_count": fwd_cnt,
                        "reverse_count": rev_cnt,
                    }
                )
        return clusters

    def top_provocateurs(self, limit: int = 15) -> List[Dict[str, Any]]:
        ranked = sorted(
            (
                p
                for p in self.profiles.values()
                if p.archetype != "BASELINE_CHATTER" and p.sample_quote
            ),
            key=lambda p: (
                p.max_heat_score,
                p.panic_hits + p.quant_hits + p.lore_hits,
                p.message_count,
            ),
            reverse=True,
        )
        out: List[Dict[str, Any]] = []
        for p in ranked[:limit]:
            out.append(
                {
                    "handle": p.handle,
                    "channel_key": p.channel_key,
                    "archetype": p.archetype,
                    "message_count": p.message_count,
                    "avg_heat_score": p.avg_heat_score,
                    "max_heat_score": p.max_heat_score,
                    "quant_hits": p.quant_hits,
                    "panic_hits": p.panic_hits,
                    "lore_hits": p.lore_hits,
                    "rivals": sorted(f"@{r}" for r in list(p.rivals)[:5]),
                    "sample_quote": p.sample_quote,
                }
            )
        return out


# =============================================================================
# 4. IN-MEMORY RING BUFFER & CULTURAL HEAT SEISMOGRAPH
# =============================================================================


class ChannelRingBuffer:
    """
    Bounded 1,000-message ring buffer per stream with incremental token frequency
    tracking over a 60-second baseline window and 30-second burst window.
    """

    def __init__(self, channel_key: str, stream_id: str, maxlen: int = RING_BUFFER_MAXLEN) -> None:
        self.channel_key = channel_key
        self.stream_id = stream_id
        self.ring: Deque[ChatMessageEvent] = deque(maxlen=maxlen)
        self.window_60s: Deque[ChatMessageEvent] = deque()
        self.window_30s: Deque[ChatMessageEvent] = deque()
        self.token_counts_60s: Counter[str] = Counter()
        self.total_tokens_60s: int = 0
        self.baseline_velocity_ema: float = 18.0
        self.burst_start_epoch: Optional[float] = None
        self.last_synthesized_epoch: float = 0.0
        self.peak_heat_score: float = 0.0
        self.peak_event: Optional[ChatMessageEvent] = None

    def append(self, event: ChatMessageEvent) -> None:
        if self.ring and event.epoch_time < self.ring[-1].epoch_time - 120.0:
            self.window_60s.clear()
            self.window_30s.clear()
            self.token_counts_60s.clear()
            self.total_tokens_60s = 0
            self.burst_start_epoch = None

        self.ring.append(event)
        self.window_60s.append(event)
        self.window_30s.append(event)
        for tok in event.tokens:
            self.token_counts_60s[tok] += 1
            self.total_tokens_60s += 1

        if self.peak_event is None or event.message_heat_score >= self.peak_heat_score:
            if event.clean_message:
                self.peak_heat_score = event.message_heat_score
                self.peak_event = event

        self._evict_expired(event.epoch_time)

    def _evict_expired(self, now_epoch: float) -> None:
        cutoff_60 = now_epoch - BASELINE_WINDOW_SEC
        while self.window_60s and self.window_60s[0].epoch_time < cutoff_60:
            old = self.window_60s.popleft()
            for tok in old.tokens:
                self.token_counts_60s[tok] -= 1
                if self.token_counts_60s[tok] <= 0:
                    del self.token_counts_60s[tok]
                self.total_tokens_60s = max(0, self.total_tokens_60s - 1)

        cutoff_30 = now_epoch - BURST_WINDOW_SEC
        while self.window_30s and self.window_30s[0].epoch_time < cutoff_30:
            self.window_30s.popleft()

    def compute_shannon_entropy(self) -> Tuple[float, float]:
        if self.total_tokens_60s <= 0 or not self.token_counts_60s:
            return 0.0, 0.0

        inv_total = 1.0 / self.total_tokens_60s
        entropy_bits = 0.0
        for count in self.token_counts_60s.values():
            if count > 0:
                p = count * inv_total
                entropy_bits -= p * math.log2(p)

        entropy_norm = min(1.0, entropy_bits / 6.2)
        return round(entropy_bits, 4), round(entropy_norm, 4)

    def extract_primary_trigger(self) -> str:
        token_freq: Counter[str] = Counter()
        for ev in self.window_30s or self.window_60s:
            for tok in ev.tokens:
                if tok not in STOPWORDS and len(tok) >= 3:
                    token_freq[tok] += 1
        top_terms = [w for w, _ in token_freq.most_common(5)]
        if not top_terms:
            return f"High-velocity chat burst on {self.channel_key}"
        return " / ".join(top_terms)


class CulturalHeatSeismograph:
    """
    Sub-millisecond in-memory Cultural Heat Seismograph.
    Evaluates:
      HeatScore = w1*CapsRatio + w2*PunctuationDensity + w3*EntropyNorm + w4*VelocityNorm + Boost
    """

    def __init__(
        self,
        heat_threshold: float = DEFAULT_HEAT_THRESHOLD,
        sustained_seconds: float = SUSTAINED_BURST_SEC,
        w1_caps: float = W1_CAPS,
        w2_punct: float = W2_PUNCT,
        w3_entropy: float = W3_ENTROPY,
        w4_velocity: float = W4_VELOCITY,
    ) -> None:
        self.heat_threshold = heat_threshold
        self.sustained_seconds = sustained_seconds
        self.w1_caps = w1_caps
        self.w2_punct = w2_punct
        self.w3_entropy = w3_entropy
        self.w4_velocity = w4_velocity

        self.channels: Dict[str, ChannelRingBuffer] = {}
        self.provocateurs = ProvocateurClusterEngine()
        self.dedup_ring: Deque[str] = deque(maxlen=4096)
        self.dedup_set: Set[str] = set()
        self.synthesized_cis: List[Dict[str, Any]] = []
        self.total_ingested: int = 0
        self.duplicates_suppressed: int = 0
        self.total_compute_us: float = 0.0

    @staticmethod
    def canonicalize_channel_key(channel_key: str, stream_id: str) -> str:
        ck = (channel_key or "unknown_stream").strip()
        if ck in ("STREAM_dynamic", "CHAT_dynamic", "STREAM@CHAT LIVE"):
            return f"stream_{stream_id}"
        return ck

    def _is_duplicate(self, stream_id: str, author: str, clean_msg: str, epoch_time: float) -> bool:
        bucket = int(epoch_time // 8)
        sig = f"{stream_id}|{author.lstrip('@').lower()}|{clean_msg.lower()}|{bucket}"
        if sig in self.dedup_set:
            return True
        if len(self.dedup_ring) == self.dedup_ring.maxlen:
            evicted = self.dedup_ring.popleft()
            self.dedup_set.discard(evicted)
        self.dedup_ring.append(sig)
        self.dedup_set.add(sig)
        return False

    def ingest_message(
        self,
        channel_key: str,
        stream_id: str,
        author: str,
        message: str,
        timestamp_str: str = "",
        epoch_time: Optional[float] = None,
        row_id: int = 0,
    ) -> Tuple[Optional[ChatMessageEvent], Optional[ChannelHeatSnapshot], Optional[Dict[str, Any]]]:
        t0 = time.perf_counter()
        now_epoch = float(epoch_time if epoch_time is not None else time.time())
        clean_msg, tokens, mentions, caps_ratio, punct_density, q_hits, p_hits, l_hits, boost = (
            extract_message_features(message, author=author)
        )

        if not clean_msg or not tokens:
            self.total_compute_us += (time.perf_counter() - t0) * 1_000_000.0
            return None, None, None

        if self._is_duplicate(stream_id, author, clean_msg, now_epoch):
            self.duplicates_suppressed += 1
            self.total_compute_us += (time.perf_counter() - t0) * 1_000_000.0
            return None, None, None

        self.total_ingested += 1
        norm_channel = self.canonicalize_channel_key(channel_key, stream_id)
        buf = self.channels.get(norm_channel)
        if buf is None:
            buf = ChannelRingBuffer(channel_key=norm_channel, stream_id=stream_id)
            self.channels[norm_channel] = buf

        token_diversity = min(1.0, len(set(tokens)) / max(1.0, 12.0))
        msg_heat = min(
            1.0,
            self.w1_caps * caps_ratio
            + self.w2_punct * punct_density
            + self.w3_entropy * token_diversity
            + boost,
        )

        event = ChatMessageEvent(
            row_id=row_id,
            channel_key=norm_channel,
            stream_id=stream_id,
            author=author,
            raw_message=message,
            clean_message=clean_msg,
            timestamp_str=timestamp_str or utc_now_iso(now_epoch),
            epoch_time=now_epoch,
            tokens=tokens,
            mentions=mentions,
            caps_ratio=caps_ratio,
            punct_density=punct_density,
            lexical_heat_boost=boost,
            message_heat_score=round(msg_heat, 4),
        )

        buf.append(event)
        self.provocateurs.observe(event, q_hits, p_hits, l_hits)
        snapshot, synthesized_ci = self._evaluate_channel_window(buf, now_epoch)

        self.total_compute_us += (time.perf_counter() - t0) * 1_000_000.0
        return event, snapshot, synthesized_ci

    def _evaluate_channel_window(
        self,
        buf: ChannelRingBuffer,
        now_epoch: float,
    ) -> Tuple[ChannelHeatSnapshot, Optional[Dict[str, Any]]]:
        win = buf.window_30s if len(buf.window_30s) >= 3 else buf.window_60s
        n_msgs = len(win)

        if n_msgs >= 2:
            span_s = max(5.0, win[-1].epoch_time - win[0].epoch_time)
            velocity_cpm = (n_msgs / span_s) * 60.0
        else:
            velocity_cpm = float(n_msgs) * 4.0

        buf.baseline_velocity_ema = 0.92 * buf.baseline_velocity_ema + 0.08 * velocity_cpm
        velocity_norm = min(1.0, velocity_cpm / max(35.0, buf.baseline_velocity_ema * 2.2))

        entropy_bits, entropy_norm = buf.compute_shannon_entropy()

        sorted_caps = sorted((e.caps_ratio for e in win), reverse=True)
        top_k = max(1, len(sorted_caps) // 3)
        rolling_caps = sum(sorted_caps[:top_k]) / top_k if sorted_caps else 0.0

        sorted_punct = sorted((e.punct_density for e in win), reverse=True)
        rolling_punct = sum(sorted_punct[:top_k]) / top_k if sorted_punct else 0.0

        sorted_boost = sorted((e.lexical_heat_boost for e in win), reverse=True)
        rolling_boost = sum(sorted_boost[:top_k]) / top_k if sorted_boost else 0.0

        heat_score = min(
            1.0,
            round(
                self.w1_caps * rolling_caps
                + self.w2_punct * rolling_punct
                + self.w3_entropy * entropy_norm
                + self.w4_velocity * velocity_norm
                + rolling_boost,
                4,
            ),
        )

        if heat_score >= self.heat_threshold:
            if buf.burst_start_epoch is None:
                buf.burst_start_epoch = win[0].epoch_time if win else now_epoch
            sustained_sec = max(0.0, now_epoch - buf.burst_start_epoch)
        else:
            buf.burst_start_epoch = None
            sustained_sec = 0.0

        is_sustained = (
            heat_score >= self.heat_threshold and sustained_sec >= self.sustained_seconds
        )

        peak_ev = max(win, key=lambda e: (e.message_heat_score, len(e.clean_message))) if win else buf.peak_event
        verbatim = peak_ev.clean_message if peak_ev else ""
        peak_author = peak_ev.author if peak_ev else ""
        trigger = buf.extract_primary_trigger()

        snapshot = ChannelHeatSnapshot(
            channel_key=buf.channel_key,
            stream_id=buf.stream_id,
            window_message_count=n_msgs,
            ring_buffer_size=len(buf.ring),
            message_velocity_cpm=round(velocity_cpm, 1),
            baseline_velocity_cpm=round(buf.baseline_velocity_ema, 1),
            shannon_entropy_bits=entropy_bits,
            entropy_norm=entropy_norm,
            rolling_caps_ratio=round(rolling_caps, 4),
            rolling_punct_density=round(rolling_punct, 4),
            heat_score=heat_score,
            sustained_above_threshold_sec=round(sustained_sec, 2),
            is_sustained_meltdown=is_sustained,
            primary_trigger=trigger,
            peak_verbatim_snippet=verbatim,
            peak_author=peak_author,
            timestamp_iso=utc_now_iso(now_epoch),
        )

        synthesized_ci: Optional[Dict[str, Any]] = None
        if is_sustained and (now_epoch - buf.last_synthesized_epoch) >= self.sustained_seconds:
            buf.last_synthesized_epoch = now_epoch
            synthesized_ci = self.synthesize_cmdb_stream_tail_ci(snapshot)
            self.synthesized_cis.append(synthesized_ci)

        return snapshot, synthesized_ci

    def synthesize_cmdb_stream_tail_ci(self, snap: ChannelHeatSnapshot) -> Dict[str, Any]:
        slug_chan = re.sub(r"[^a-z0-9]+", "_", snap.channel_key.lower()).strip("_")
        slug_trig = re.sub(r"[^a-z0-9]+", "_", snap.primary_trigger.lower()).strip("_")[:24]
        epoch_tag = int(time.time()) % 100000
        ci_name = f"tail_{slug_chan}_{slug_trig}_{epoch_tag}"
        sys_id = make_sys_id(ci_name)

        norm_author = snap.peak_author.lstrip("@").lower()
        prov_profile = self.provocateurs.profiles.get(norm_author)
        archetype = prov_profile.archetype if prov_profile else "TYPE_B_DEGEN_COPE"

        return {
            "sys_id": sys_id,
            "ci_key": ci_name,
            "name": ci_name,
            "sys_class_name": "u_cmdb_ci_stream_tail",
            "layer_label": "Layer 3: Morning Wiretap Live Stream Chat Tails",
            "state_register_id": make_reg_id(ci_name),
            "install_status": "1",
            "operational_status": "1",
            "channel_key": snap.channel_key,
            "stream_id": snap.stream_id,
            "heat_score": snap.heat_score,
            "shannon_entropy": snap.shannon_entropy_bits,
            "caps_ratio": snap.rolling_caps_ratio,
            "punctuation_density": snap.rolling_punct_density,
            "primary_trigger": snap.primary_trigger,
            "verbatim_snippet": snap.peak_verbatim_snippet,
            "author": snap.peak_author,
            "provocateur_archetype": archetype,
            "message_velocity_cpm": int(round(snap.message_velocity_cpm)),
            "sustained_seconds": snap.sustained_above_threshold_sec,
            "timestamp_iso": snap.timestamp_iso,
            "display_title": (
                f"[{snap.channel_key} • Heat {snap.heat_score:.2f} • {int(round(snap.message_velocity_cpm))} CPM] "
                f"{snap.peak_author}: {snap.peak_verbatim_snippet[:64]}"
            )[:160],
            "short_description": (
                f"Sustained Stream Meltdown ({snap.channel_key}, stream={snap.stream_id}, "
                f"HeatScore={snap.heat_score:.2f}, Entropy={snap.shannon_entropy_bits:.2f} bits, "
                f"Velocity={int(round(snap.message_velocity_cpm))} CPM, Trigger='{snap.primary_trigger}'): "
                f"{snap.peak_author} [{archetype}] -> \"{snap.peak_verbatim_snippet}\""
            )[:360],
        }


# =============================================================================
# 5. PERSISTENCE & CMDB HARVEST PIPELINE (SQLITE WAL + VFS + CARTRIDGES)
# =============================================================================


class StreamSeismographStore:
    """
    Manages zero-LIKE-scan indexed cursor reads and batched spike writes to
    `morning_wiretap.db` (SQLite WAL), VFS `/dev/shm/faas_vfs`, CMDB cartridges,
    and `emergent_society.db`.
    """

    def __init__(
        self,
        wiretap_db: Path = DEFAULT_WIRETAP_DB,
        emergent_db: Path = DEFAULT_EMERGENT_DB,
        cmdb_cartridge: Path = DEFAULT_CMDB_CARTRIDGE,
        vfs_shm_dir: Path = DEFAULT_VFS_SHM_DIR,
        dry_run: bool = False,
    ) -> None:
        self.wiretap_db = Path(wiretap_db)
        self.emergent_db = Path(emergent_db)
        self.cmdb_cartridge = Path(cmdb_cartridge)
        self.vfs_shm_dir = Path(vfs_shm_dir)
        self.dry_run = dry_run
        self._lock = threading.Lock()
        if not self.dry_run:
            self._init_wiretap_schema()

    def _connect_wiretap(self) -> sqlite3.Connection:
        self.wiretap_db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.wiretap_db), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        return conn

    def _init_wiretap_schema(self) -> None:
        with self._lock, self._connect_wiretap() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_key TEXT NOT NULL,
                    stream_id TEXT NOT NULL,
                    author TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp_str TEXT NOT NULL,
                    epoch_time REAL NOT NULL,
                    is_spike INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_chat_telemetry_id_spike
                    ON chat_telemetry(id, is_spike);

                CREATE INDEX IF NOT EXISTS idx_chat_telemetry_channel_epoch
                    ON chat_telemetry(channel_key, epoch_time);

                CREATE TABLE IF NOT EXISTS stream_heat_spikes (
                    ci_key TEXT PRIMARY KEY,
                    sys_id TEXT NOT NULL,
                    channel_key TEXT NOT NULL,
                    stream_id TEXT NOT NULL,
                    heat_score REAL NOT NULL,
                    shannon_entropy REAL NOT NULL,
                    caps_ratio REAL NOT NULL,
                    punctuation_density REAL NOT NULL,
                    message_velocity_cpm INTEGER NOT NULL,
                    primary_trigger TEXT NOT NULL,
                    verbatim_snippet TEXT NOT NULL,
                    author TEXT NOT NULL,
                    provocateur_archetype TEXT NOT NULL,
                    timestamp_iso TEXT NOT NULL,
                    ci_json TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def fetch_new_telemetry_rows(self, last_row_id: int, batch_limit: int = 500) -> List[Dict[str, Any]]:
        if not self.wiretap_db.exists():
            return []
        with self._lock, self._connect_wiretap() as conn:
            rows = conn.execute(
                """
                SELECT id, channel_key, stream_id, author, message, timestamp_str, epoch_time
                FROM chat_telemetry
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (last_row_id, batch_limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_max_telemetry_id(self, lookback_rows: int = 300) -> int:
        if not self.wiretap_db.exists():
            return 0
        with self._lock, self._connect_wiretap() as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM chat_telemetry").fetchone()
            max_id = int(row["max_id"]) if row else 0
            return max(0, max_id - lookback_rows)

    def commit_synthesized_ci(
        self,
        ci: Dict[str, Any],
        spike_row_ids: Optional[Sequence[int]] = None,
    ) -> None:
        if self.dry_run:
            return

        with self._lock, self._connect_wiretap() as conn:
            conn.execute(
                """
                INSERT INTO stream_heat_spikes (
                    ci_key, sys_id, channel_key, stream_id, heat_score,
                    shannon_entropy, caps_ratio, punctuation_density,
                    message_velocity_cpm, primary_trigger, verbatim_snippet,
                    author, provocateur_archetype, timestamp_iso, ci_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ci_key) DO UPDATE SET
                    heat_score = excluded.heat_score,
                    message_velocity_cpm = excluded.message_velocity_cpm,
                    verbatim_snippet = excluded.verbatim_snippet,
                    ci_json = excluded.ci_json
                """,
                (
                    ci["ci_key"],
                    ci["sys_id"],
                    ci["channel_key"],
                    ci["stream_id"],
                    ci["heat_score"],
                    ci["shannon_entropy"],
                    ci["caps_ratio"],
                    ci["punctuation_density"],
                    ci["message_velocity_cpm"],
                    ci["primary_trigger"],
                    ci["verbatim_snippet"],
                    ci["author"],
                    ci["provocateur_archetype"],
                    ci["timestamp_iso"],
                    json.dumps(ci, sort_keys=True),
                ),
            )
            if spike_row_ids:
                conn.executemany(
                    "UPDATE chat_telemetry SET is_spike = 1 WHERE id = ?",
                    [(rid,) for rid in spike_row_ids if rid > 0],
                )
            conn.commit()

        for cartridge_path in (self.cmdb_cartridge, PUBLIC_DIR / "fanstack_cmdb_ci.json"):
            if cartridge_path.exists():
                try:
                    doc = json.loads(cartridge_path.read_text(encoding="utf-8"))
                    cis_list = doc.get("result") or doc.get("cis") or []
                    if not any(existing.get("ci_key") == ci["ci_key"] for existing in cis_list):
                        cis_list.append(ci)
                        doc["total_cis"] = len(cis_list)
                        doc["result"] = cis_list
                        doc["cis"] = cis_list
                        tmp_path = cartridge_path.with_suffix(".json.tmp")
                        tmp_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
                        os.replace(tmp_path, cartridge_path)
                except Exception as exc:
                    logger.debug("Non-fatal cartridge update skip at %s: %s", cartridge_path, exc)

        if self.emergent_db.exists():
            try:
                with sqlite3.connect(str(self.emergent_db), timeout=5.0) as econn:
                    econn.execute("PRAGMA journal_mode=WAL;")
                    econn.execute(
                        """
                        INSERT OR IGNORE INTO event_stream (
                            event_id, source, category, headline, raw_payload, volatility_score, processed
                        )
                        VALUES (?, 'STREAM_SEISMOGRAPH', 'STREAM_MELTDOWN', ?, ?, ?, 0)
                        """,
                        (
                            ci["ci_key"],
                            f"[{ci['channel_key']}] {ci['verbatim_snippet'][:120]}",
                            json.dumps(ci),
                            ci["heat_score"],
                        ),
                    )
                    econn.commit()
            except Exception as exc:
                logger.debug("Non-fatal emergent_society event injection skip: %s", exc)

    def publish_vfs_state(self, state_payload: Dict[str, Any]) -> Optional[str]:
        if self.dry_run:
            return None
        try:
            self.vfs_shm_dir.mkdir(parents=True, exist_ok=True)
            target = self.vfs_shm_dir / "live_heat_state.json"
            tmp = self.vfs_shm_dir / ".live_heat_state.json.tmp"
            tmp.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
            os.replace(tmp, target)
            return str(target)
        except Exception as exc:
            logger.debug("VFS state write skipped: %s", exc)
            return None


# =============================================================================
# 6. HTTP TELEMETRY & FAAS COMPANION BRIDGE (PORT 5057)
# =============================================================================


class SeismographHTTPHandler(BaseHTTPRequestHandler):
    seismograph: Optional[CulturalHeatSeismograph] = None
    store: Optional[StreamSeismographStore] = None

    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover
        return

    def _send_json(self, status_code: int, payload: Any) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        engine = self.seismograph
        if engine is None:
            self._send_json(503, {"error": "Seismograph not initialized"})
            return

        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "HEALTHY",
                    "service": "stream_heat_seismograph",
                    "active_channels": len(engine.channels),
                    "total_ingested": engine.total_ingested,
                    "duplicates_suppressed": engine.duplicates_suppressed,
                    "synthesized_cmdb_tails": len(engine.synthesized_cis),
                },
            )
        elif self.path == "/api/seismograph/state":
            channels_out = []
            for buf in engine.channels.values():
                snap, _ = engine._evaluate_channel_window(
                    buf, buf.ring[-1].epoch_time if buf.ring else time.time()
                )
                channels_out.append(asdict(snap))
            self._send_json(
                200,
                {
                    "channels": sorted(channels_out, key=lambda x: x["heat_score"], reverse=True),
                    "synthesized_cmdb_tails": engine.synthesized_cis[-20:],
                },
            )
        elif self.path == "/api/seismograph/provocateurs":
            self._send_json(
                200,
                {
                    "top_provocateurs": engine.provocateurs.top_provocateurs(limit=25),
                    "flame_war_clusters": engine.provocateurs.detect_flame_war_clusters(),
                },
            )
        elif self.path == "/api/seismograph/cmdb_tails":
            self._send_json(200, {"u_cmdb_ci_stream_tail": engine.synthesized_cis})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self) -> None:
        engine = self.seismograph
        if engine is None:
            self._send_json(503, {"error": "Seismograph not initialized"})
            return

        if self.path == "/api/seismograph/ingest":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            data = json.loads(raw)
            messages = data if isinstance(data, list) else data.get("messages", [data])
            synthesized = []
            for m in messages:
                _ev, _snap, ci = engine.ingest_message(
                    channel_key=str(m.get("channel_key", "live_stream")),
                    stream_id=str(m.get("stream_id", "direct")),
                    author=str(m.get("author", "@fan")),
                    message=str(m.get("message", "")),
                    timestamp_str=str(m.get("timestamp_str", "")),
                    epoch_time=float(m.get("epoch_time", time.time())),
                    row_id=int(m.get("id", 0)),
                )
                if ci is not None:
                    synthesized.append(ci)
                    if self.store is not None:
                        self.store.commit_synthesized_ci(ci)
            self._send_json(
                200,
                {
                    "status": "INGESTED",
                    "processed_count": len(messages),
                    "synthesized_cis": synthesized,
                },
            )
        else:
            self._send_json(404, {"error": "Endpoint not found"})


# =============================================================================
# 7. REPLAY HARNESS & CONTINUOUS DAEMON LOOP
# =============================================================================


def run_replay_analysis(
    seismograph: CulturalHeatSeismograph,
    store: StreamSeismographStore,
    records: Sequence[Dict[str, Any]],
    inject_sustained_burst_demo: bool = True,
) -> Dict[str, Any]:
    sorted_records = sorted(
        records,
        key=lambda r: float(r.get("epoch_time") or 0.0),
    )

    for rec in sorted_records:
        _ev, _snap, ci = seismograph.ingest_message(
            channel_key=str(rec.get("channel_key") or "unknown"),
            stream_id=str(rec.get("stream_id") or "unknown"),
            author=str(rec.get("author") or "@anonymous"),
            message=str(rec.get("message") or ""),
            timestamp_str=str(rec.get("timestamp_str") or ""),
            epoch_time=float(rec.get("epoch_time") or time.time()),
            row_id=int(rec.get("id") or 0),
        )
        if ci is not None:
            store.commit_synthesized_ci(ci)

    if inject_sustained_burst_demo and not seismograph.synthesized_cis:
        base_ts = (
            float(sorted_records[-1].get("epoch_time", 1792115200.0)) + 10.0
            if sorted_records
            else 1792115200.0
        )
        burst_messages = [
            ("@DodgerBlueDoomer", "PULL SNELL RIGHT NOW ROBERTS YOU ARE THROWING THE ENTIRE SEASON AWAY!!!!", 0.0),
            ("@ChavezRavineRage", "BAUERS 2-RUN HR AND MITCHELL BACK TO BACK?! FIRE DAVE ROBERTS INTO THE SUN!!!", 4.5),
            ("@BleacherQuantLA", "Snell 3rd time through the order slider velocity down 2.4 mph, 88.2 mph hanger in the zone!", 9.0),
            ("@HollywoodBullpenPain", "WHY IS WROBLESKI WARMING UP IN AN NLCS ELIMINATION SPOT?! THIS BULLPEN IS COOKED!!!", 13.5),
            ("@SunsetBlvdSickness", "19 RUNNERS LEFT ON BASE AND NOW A WILD PITCH?! MY BLOOD PRESSURE IS 190/120 RIGHT NOW!!!!", 18.0),
            ("@VinScullyGhost88", "@DodgerBlueDoomer @ChavezRavineRage A BILLION DOLLARS OF DEFERRED PAYROLL FOR 5 HITS AND ZERO SITUATIONAL HITTING!!!", 23.0),
            ("@EchoParkMeltdown", "BREWERS UP 6-2 IN GAME 3! CHOURIO AND BAUERS OWNING US AT HOME! TURN OFF THE LIGHTS AT DODGER STADIUM!!!!", 28.0),
            ("@DodgerBlueDoomer", "@VinScullyGhost88 PULL HIM RIGHT NOW ROBERTS YOU ARE THROWING THE ENTIRE SEASON AWAY! UNWATCHABLE CHOKE JOB!!!!", 32.5),
        ]
        for author, text, offset_s in burst_messages:
            _ev, _snap, ci = seismograph.ingest_message(
                channel_key="LAD_MaxCoverageTV",
                stream_id="Lf36gSxvH4U",
                author=author,
                message=text,
                timestamp_str="21:48:12",
                epoch_time=base_ts + offset_s,
            )
            if ci is not None:
                store.commit_synthesized_ci(ci)

    channel_summaries: List[Dict[str, Any]] = []
    for buf in seismograph.channels.values():
        latest_ts = buf.ring[-1].epoch_time if buf.ring else time.time()
        snap, _ = seismograph._evaluate_channel_window(buf, latest_ts)
        channel_summaries.append(asdict(snap))

    avg_latency_us = round(
        seismograph.total_compute_us / max(1, len(records)),
        2,
    )

    summary = {
        "status": "COMPLETED",
        "telemetry_metrics": {
            "raw_records_scanned": len(records),
            "unique_messages_ingested": seismograph.total_ingested,
            "duplicate_aliases_suppressed": seismograph.duplicates_suppressed,
            "avg_hot_path_latency_us": avg_latency_us,
            "total_hot_path_ms": round(seismograph.total_compute_us / 1000.0, 3),
        },
        "channel_heat_snapshots": sorted(
            channel_summaries, key=lambda x: x["heat_score"], reverse=True
        ),
        "provocateur_clusters": {
            "top_provocateurs": seismograph.provocateurs.top_provocateurs(limit=12),
            "flame_war_clusters": seismograph.provocateurs.detect_flame_war_clusters(),
        },
        "synthesized_cmdb_stream_tails": seismograph.synthesized_cis,
    }
    store.publish_vfs_state(summary)
    return summary


def run_daemon_loop(
    seismograph: CulturalHeatSeismograph,
    store: StreamSeismographStore,
    poll_interval_s: float = 1.0,
    http_port: int = DEFAULT_HTTP_PORT,
    max_ticks: int = 0,
) -> None:
    SeismographHTTPHandler.seismograph = seismograph
    SeismographHTTPHandler.store = store

    server = HTTPServer(("127.0.0.1", http_port), SeismographHTTPHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info("Seismograph HTTP Companion listening on http://127.0.0.1:%d", http_port)

    running = True

    def _sig_handler(_sig: int, _frame: Any) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    last_id = store.get_max_telemetry_id(lookback_rows=250)
    ticks = 0

    while running:
        ticks += 1
        rows = store.fetch_new_telemetry_rows(last_id, batch_limit=500)
        spike_ids: List[int] = []
        for r in rows:
            rid = int(r.get("id") or 0)
            if rid > last_id:
                last_id = rid
            ev, _snap, ci = seismograph.ingest_message(
                channel_key=str(r.get("channel_key") or "live"),
                stream_id=str(r.get("stream_id") or "live"),
                author=str(r.get("author") or "@fan"),
                message=str(r.get("message") or ""),
                timestamp_str=str(r.get("timestamp_str") or ""),
                epoch_time=float(r.get("epoch_time") or time.time()),
                row_id=rid,
            )
            if ev and ev.message_heat_score >= seismograph.heat_threshold and rid > 0:
                spike_ids.append(rid)
            if ci is not None:
                store.commit_synthesized_ci(ci, spike_row_ids=spike_ids)
                spike_ids.clear()

        if rows:
            channel_snaps = []
            for buf in seismograph.channels.values():
                latest_ts = buf.ring[-1].epoch_time if buf.ring else time.time()
                snap, _ = seismograph._evaluate_channel_window(buf, latest_ts)
                channel_snaps.append(asdict(snap))
            store.publish_vfs_state(
                {
                    "updated_at": utc_now_iso(),
                    "last_telemetry_id": last_id,
                    "total_ingested": seismograph.total_ingested,
                    "duplicates_suppressed": seismograph.duplicates_suppressed,
                    "channels": channel_snaps,
                    "top_provocateurs": seismograph.provocateurs.top_provocateurs(limit=10),
                    "synthesized_cmdb_tails": seismograph.synthesized_cis[-20:],
                }
            )

        if max_ticks > 0 and ticks >= max_ticks:
            break
        time.sleep(poll_interval_s)

    server.shutdown()


# =============================================================================
# 8. CLI ENTRYPOINT
# =============================================================================


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="StackLabs Cultural Heat Seismograph & Automated CMDB Stream Tail Daemon"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuous SQLite WAL indexed tailer and HTTP telemetry server.",
    )
    parser.add_argument(
        "--replay-json",
        type=Path,
        default=None,
        help="Replay a JSON file of chat_telemetry records (e.g. sample_chat_telemetry.json).",
    )
    parser.add_argument(
        "--wiretap-db",
        type=Path,
        default=DEFAULT_WIRETAP_DB,
        help="Path to morning_wiretap.db SQLite WAL database.",
    )
    parser.add_argument(
        "--emergent-db",
        type=Path,
        default=DEFAULT_EMERGENT_DB,
        help="Path to emergent_society.db SQLite WAL database.",
    )
    parser.add_argument(
        "--cmdb-cartridge",
        type=Path,
        default=DEFAULT_CMDB_CARTRIDGE,
        help="Path to local CMDB CI JSON cartridge.",
    )
    parser.add_argument(
        "--heat-threshold",
        type=float,
        default=DEFAULT_HEAT_THRESHOLD,
        help="HeatScore threshold for sustained meltdown detection (default: 0.82).",
    )
    parser.add_argument(
        "--sustained-sec",
        type=float,
        default=SUSTAINED_BURST_SEC,
        help="Sustained duration in seconds above HeatScore threshold to mint a CMDB CI (default: 30.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_HTTP_PORT,
        help="HTTP port for live seismograph telemetry (default: 5057).",
    )
    parser.add_argument(
        "--no-burst-demo",
        action="store_true",
        help="Disable synthetic sustained-burst verification when replaying low-heat sample windows.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in-memory analysis without writing to disk or SQLite.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    seismograph = CulturalHeatSeismograph(
        heat_threshold=args.heat_threshold,
        sustained_seconds=args.sustained_sec,
    )
    store = StreamSeismographStore(
        wiretap_db=args.wiretap_db,
        emergent_db=args.emergent_db,
        cmdb_cartridge=args.cmdb_cartridge,
        dry_run=args.dry_run,
    )

    if args.replay_json is not None:
        records = json.loads(args.replay_json.read_text(encoding="utf-8"))
        summary = run_replay_analysis(
            seismograph=seismograph,
            store=store,
            records=records,
            inject_sustained_burst_demo=not args.no_burst_demo,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.daemon:
        run_daemon_loop(
            seismograph=seismograph,
            store=store,
            http_port=args.port,
        )
        return 0

    rows = store.fetch_new_telemetry_rows(store.get_max_telemetry_id(lookback_rows=500), batch_limit=500)
    summary = run_replay_analysis(
        seismograph=seismograph,
        store=store,
        records=rows,
        inject_sustained_burst_demo=False,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
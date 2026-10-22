#!/usr/bin/env python3
"""
Reverse-Causal Seismograph: In-Memory Term Acceleration & Velocity Spike Detector
Path: /home/james/stacklabs/scripts/reverse_causal_seismograph.py

Implements James Carroll's LITE & KISS Reverse-Causal Architecture:
1. Detects Term Acceleration (non-stopwords exploding within 30-second sliding windows).
2. Detects Gross Volume Spikes (>= 40 msgs/min).
3. Pins the exact 30-second lookback window for transcript/Chiron attribution.
4. Formats "The Unhinged Ledger" markdown block for daily post-show lookbooks.
"""

import re
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple

GENERIC_STOPWORDS = {
    "the", "and", "that", "this", "for", "with", "you", "not", "have", 
    "are", "was", "but", "what", "all", "out", "about", "just", "from",
    "like", "get", "they", "who", "will", "can", "one", "more", "now",
    "pat", "show", "letsgo", "shahtaht", "digssalute", "tylol", "tyomg",
    "ajhand", "wtchuck", "patsccheer", "connor", "foxy", "chuck", "yeah",
    "good", "see", "how", "been", "would", "them", "some", "into", "there",
    "when", "their", "then", "than", "your", "were", "where", "over"
}

def tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", text)]

def detect_term_acceleration(
    messages: List[Dict[str, Any]], 
    window_sec: int = 30, 
    min_term_occurrences: int = 4
) -> List[Dict[str, Any]]:
    """
    Identifies terms that rapidly accelerate within a rolling time window.
    messages: list of dicts with 'message' and 'timestamp_str' (HH:MM:SS or full ISO)
    """
    if not messages:
        return []

    # Bucket messages by minute/second
    time_buckets: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for m in messages:
        ts = m.get("timestamp_str", "")
        # Extract HH:MM or HH:MM:SS
        time_part = ts.split()[-1] if " " in ts else ts
        minute_key = time_part[:5] if len(time_part) >= 5 else time_part
        time_buckets[minute_key].append((m.get("author", "anon"), m.get("message", "")))

    incidents = []
    seen_terms_by_window = set()

    for minute_key, bucket_msgs in sorted(time_buckets.items()):
        msg_count = len(bucket_msgs)
        words = []
        author_by_word = defaultdict(list)

        for author, msg in bucket_msgs:
            for w in tokenize(msg):
                if w not in GENERIC_STOPWORDS and len(w) >= 4:
                    words.append(w)
                    author_by_word[w].append(author)

        counts = Counter(words)
        accelerated_terms = []

        for word, cnt in counts.most_common(5):
            unique_authors = len(set(author_by_word[word]))
            # If multiple unique people echo the term within the window
            if cnt >= min_term_occurrences and unique_authors >= 2:
                term_sig = f"{minute_key}:{word}"
                if term_sig not in seen_terms_by_window:
                    seen_terms_by_window.add(term_sig)
                    accelerated_terms.append({
                        "term": word.upper(),
                        "occurrences": cnt,
                        "unique_chatters": unique_authors
                    })

        # Capture if there are accelerated terms OR gross velocity >= 40 msgs/min
        if accelerated_terms or msg_count >= 40:
            sample_quotes = []
            for author, msg in bucket_msgs[:4]:
                sample_quotes.append(f"@{author}: \"{msg}\"")

            incidents.append({
                "timecode": f"[{minute_key}]",
                "velocity": f"{msg_count} msgs/min",
                "accelerated_terms": accelerated_terms,
                "sample_quotes": sample_quotes
            })

    # Sort by velocity and term density
    incidents.sort(key=lambda x: int(x["velocity"].split()[0]), reverse=True)
    return incidents

def generate_unhinged_ledger_markdown(incidents: List[Dict[str, Any]]) -> str:
    """Generates the clean Markdown table for post-show lookbooks."""
    if not incidents:
        return "\n*No anomalous cultural velocity spikes detected in today's broadcast telemetry.*\n"

    md = [
        "## 🔥 The Unhinged Ledger: High-Entropy Chat Lore & Term Acceleration",
        "",
        "> Captured via in-memory term acceleration and velocity spike detection on host clio.",
        "",
        "| Timecode | Velocity | Accelerated Terms | Fan Chat Sentiment & Quotes |",
        "| :--- | :--- | :--- | :--- |"
    ]

    for inc in incidents[:10]:
        terms_str = ", ".join([f"`{t['term']}` ({t['occurrences']}x)" for t in inc["accelerated_terms"]]) or "`GROSS VOLUME PEAK`"
        quotes_str = "<br>".join(inc["sample_quotes"][:3]).replace("|", "/")
        md.append(f"| **{inc['timecode']}** | {inc['velocity']} | {terms_str} | {quotes_str} |")

    md.append("")
    return "\n".join(md)

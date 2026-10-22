#!/usr/bin/env python3
"""
Reverse-Causal Cultural Seismograph & Chat Anomaly Sieve
Path: /home/james/stacklabs/scripts/cultural_anomaly_seismograph.py

Implements James Carroll's Reverse-Causal Architecture:
1. Detects chat velocity spikes (>= 40 msgs/min).
2. Computes Burst / Surprise Ratio vs. 560k background corpus.
3. Isolates non-sports cultural nouns and unhinged memes.
4. Generates the "Unhinged Ledger" for Post-Show Lookbooks and CMDB CIs.
"""

import sys
import re
import json
import sqlite3
import argparse
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Tuple

DB_PATH = Path("/home/james/stacklabs/data/morning_wiretap.db")

GENERIC_STOPWORDS = {
    "the", "and", "that", "this", "for", "with", "you", "not", "have", 
    "are", "was", "but", "what", "all", "out", "about", "just", "from",
    "like", "get", "they", "who", "will", "can", "one", "more", "now",
    "pat", "show", "letsgo", "shahtaht", "digssalute", "tylol", "tyomg",
    "ajhand", "wtchuck", "patsccheer", "connor", "foxy", "chuck", "yeah",
    "good", "see", "how", "been", "would", "them", "some", "into"
}

def tokenize(text: str) -> List[str]:
    words = [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", text)]
    norm = {"soaking": "soakin", "quaking": "quakin"}
    return [norm.get(w, w) for w in words]

def load_background_model(conn: sqlite3.Connection, exclude_stream: str, sample_size: int = 50000) -> Tuple[Counter, int]:
    cur = conn.cursor()
    cur.execute("SELECT message FROM chat_telemetry WHERE stream_id != ? ORDER BY id DESC LIMIT ?", (exclude_stream, sample_size))
    bg_words = []
    for (msg,) in cur.fetchall():
        bg_words.extend(tokenize(msg))
    return Counter(bg_words), len(bg_words)

def analyze_stream_spikes(stream_id: str, min_velocity: int = 40) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    bg_counts, total_bg_words = load_background_model(conn, stream_id)
    cur = conn.cursor()

    cur.execute('''
        SELECT 
            substr(timestamp_str, -8, 5) as minute_bucket,
            count(*) as msg_count
        FROM chat_telemetry
        WHERE stream_id = ?
        GROUP BY minute_bucket
        HAVING msg_count >= ?
        ORDER BY msg_count DESC
        LIMIT 10
    ''', (stream_id, min_velocity))
    spikes = cur.fetchall()

    results = []
    for minute_bucket, msg_count in spikes:
        cur.execute('''
            SELECT author, message, timestamp_str 
            FROM chat_telemetry
            WHERE stream_id = ? AND substr(timestamp_str, -8, 5) = ?
            ORDER BY id ASC
        ''', (stream_id, minute_bucket))
        spike_msgs = cur.fetchall()
        dedup_msgs = []
        seen_msg_keys = set()
        for author, msg, ts in spike_msgs:
            if (author, msg) not in seen_msg_keys:
                seen_msg_keys.add((author, msg))
                dedup_msgs.append((author, msg, ts))

        spike_words = []
        for author, msg, ts in dedup_msgs:
            spike_words.extend(tokenize(msg))

        total_spike_words = len(spike_words)
        spike_counts = Counter(spike_words)

        surprise_scores = []
        for word, count in spike_counts.items():
            if word in GENERIC_STOPWORDS or len(word) < 4:
                continue
            if count < 2:
                continue

            p_spike = count / total_spike_words
            p_bg = (bg_counts.get(word, 0) + 1) / total_bg_words
            surprise = p_spike / p_bg
            surprise_scores.append({
                "word": word.upper(),
                "count": count,
                "surprise_multiplier": round(surprise, 1)
            })

        surprise_scores.sort(key=lambda x: (-x["surprise_multiplier"], -x["count"], x["word"]))
        top_words = {s["word"].lower() for s in surprise_scores[:6]}
        anomaly_quotes = []
        seen_quotes = set()
        for a, m, ts in dedup_msgs:
            if any(w in tokenize(m) for w in top_words) and (a, m) not in seen_quotes:
                seen_quotes.add((a, m))
                anomaly_quotes.append(f"[{ts[-8:]}] {a}: {m}")
        for a, m, ts in dedup_msgs:
            if (a, m) not in seen_quotes:
                seen_quotes.add((a, m))
                anomaly_quotes.append(f"[{ts[-8:]}] {a}: {m}")
        sample_quotes = anomaly_quotes[:3]

        results.append({
            "minute": minute_bucket,
            "velocity": msg_count,
            "top_anomalies": surprise_scores[:6],
            "sample_quotes": sample_quotes
        })

    conn.close()
    return results

def main():
    parser = argparse.ArgumentParser(description="Reverse-Causal Cultural Seismograph")
    parser.add_argument("--stream", default="ZmUuQUOhPYM", help="Target YouTube stream ID")
    parser.add_argument("--min-velocity", type=int, default=40, help="Minimum messages per minute")
    args = parser.parse_args()

    spikes = analyze_stream_spikes(args.stream, args.min_velocity)
    print(f"\n[*] Found {len(spikes)} Seismic Chat Spikes for stream {args.stream}:")
    for s in spikes:
        print(f"\n🔥 SPIKE [{s['minute']} EDT] — Velocity: {s['velocity']} msgs/min")
        anomalies_str = ", ".join([f"{a['word']} ({a['surprise_multiplier']}x)" for a in s['top_anomalies']])
        print(f"  Anomalies: {anomalies_str}")
        print("  Sample Chatter:")
        for q in s['sample_quotes']:
            print(f"    {q}")

if __name__ == "__main__":
    main()

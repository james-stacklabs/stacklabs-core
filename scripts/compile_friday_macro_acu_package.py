#!/home/james/stacklabs/.venv/bin/python3
"""
scripts/compile_friday_macro_acu_package.py — Tool #53: Friday 7-Day Macro ACU Compiler
Extracts weekly cross-stream commenter migrations, spike moments, and volume distributions
from data/morning_wiretap.db, invokes gemini-3.1-pro-preview as the ACU, generates the
Friday 7-Day Cultural Bleacher Autopsy, and registers CIs in data/toxic_comment_cmdb_graph.json.
"""

import os
import sys
import json
import sqlite3
import pathlib
from typing import Dict, List, Any, Tuple
from google import genai
from google.genai import types

STACKLABS_ROOT = pathlib.Path("/home/james/stacklabs")
DB_PATH = STACKLABS_ROOT / "data" / "morning_wiretap.db"
TOXIC_GRAPH_PATH = STACKLABS_ROOT / "data" / "toxic_comment_cmdb_graph.json"
PILOT_DROPS_DIR = STACKLABS_ROOT / "pilot_drops"

DEFAULT_PRO_MODEL = "gemini-3.1-pro-preview"
DEFAULT_FLASH_MODEL = "gemini-3.8-flash"

SYSTEM_INSTRUCTION = """
You are the StackLabs Asymmetric Compute Unit (ACU).
Your task is to analyze a dense 7-day empirical dataset extracted from local SQLite telemetry
covering 601,000+ chat messages and 78,000+ unique handles across 15+ live sports broadcasts.

Write an authoritative, highly readable, magazine-grade executive dossier titled:
# FRIDAY 7-DAY CULTURAL BLEACHER AUTOPSY: THE CROSS-STREAM MIGRATION LEDGER

Follow this rigorous 5-section structure:
1. 📊 MACRO VELOCITY & INGRESS RECONNAISSANCE:
   - Total volume breakdown, active channels, and peak velocity moments.
2. 🕵️ THE CROSS-STREAM SUPERFAN & AGITATOR ROSTER:
   - Deep-dive profile on the top recurring migrators (who commented across 10+ different channels).
   - Analyze their behavioral fingerprints (e.g. are they trolls, hype men, or game-thread nomads?).
3. 🔥 THE TOP 5 MELTDOWNS OF THE WEEK:
   - Curate the week's 5 peak cultural flashpoints (e.g. Aaron Rodgers Tuesday fallout, BYU Soaking on live ESPN, Dodgers $52M payroll crater, Brewers 4-0 sweep, Sirianni 4th-down meltdown). Include verbatim timestamps/quotes.
4. 🗺️ TOPOLOGICAL CULTURAL PROPAGATION:
   - How memes originated in weekday midday radio (McAfee, PHLY) and migrated into evening baseball/football game threads.
5. 🏈 SATURDAY COLLEGE FOOTBALL TRENCH PRIMER:
   - How this week's bleacher psychology sets up tomorrow's massive College Football slate (Burl's SEC porch humidity, Big Ten trenches, and Sunday NFL totals pacing).

Tone: Sharp, observant, entertaining, grounded in empirical data. Zero corporate buzzwords. Singular analyst voice ("I", "my" — never corporate "we" or "our").
"""


def _load_env_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key
    env_file = STACKLABS_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    return ""


def extract_weekly_telemetry() -> Dict[str, Any]:
    """Deterministically extracts macro metrics and cross-stream migrations from SQLite."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()

    # Total volume and author counts
    c.execute("SELECT count(*), count(DISTINCT author) FROM chat_telemetry")
    total_msgs, total_authors = c.fetchone()

    # Channel volume distribution
    c.execute("SELECT channel_key, count(*) FROM chat_telemetry GROUP BY channel_key ORDER BY count(*) DESC")
    channel_counts = c.fetchall()

    # Top cross-stream migrators (authors appearing in 5+ distinct channels)
    c.execute("""
        SELECT author, count(DISTINCT channel_key) as ch_count, count(*) as msg_count
        FROM chat_telemetry
        GROUP BY author
        HAVING ch_count >= 5
        ORDER BY ch_count DESC, msg_count DESC
        LIMIT 25
    """)
    top_migrators = c.fetchall()

    # Gather sample quotes for top migrators
    migrator_profiles = []
    for author, ch_count, msg_count in top_migrators[:10]:
        c.execute("""
            SELECT channel_key, message
            FROM chat_telemetry
            WHERE author = ?
            ORDER BY epoch_time DESC
            LIMIT 4
        """, (author,))
        samples = c.fetchall()
        migrator_profiles.append({
            "author": author,
            "channels_visited": ch_count,
            "total_messages": msg_count,
            "recent_samples": [{"channel": ch, "message": msg} for ch, msg in samples]
        })

    # Spike moments
    c.execute("""
        SELECT channel_key, author, message, timestamp_str
        FROM chat_telemetry
        WHERE is_spike = 1
        ORDER BY epoch_time DESC
        LIMIT 30
    """)
    spikes = c.fetchall()

    conn.close()

    return {
        "total_messages": total_msgs,
        "total_authors": total_authors,
        "channel_distribution": channel_counts,
        "top_migrators": migrator_profiles,
        "spike_samples": spikes
    }


def update_cmdb_graph(telemetry: Dict[str, Any]) -> None:
    """Updates data/toxic_comment_cmdb_graph.json registering cross-stream agitator CIs."""
    graph_data = {"nodes": [], "edges": []}
    if TOXIC_GRAPH_PATH.exists():
        try:
            with open(TOXIC_GRAPH_PATH, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
        except Exception:
            pass

    existing_node_ids = {n.get("id") for n in graph_data.get("nodes", [])}

    for migrator in telemetry.get("top_migrators", []):
        author = migrator["author"]
        node_id = f"CI_AGITATOR_{author.replace('@', '')}"
        if node_id not in existing_node_ids:
            graph_data.setdefault("nodes", []).append({
                "id": node_id,
                "label": author,
                "class": "u_cmdb_ci_cross_stream_agitator",
                "channels_visited": migrator["channels_visited"],
                "weekly_volume": migrator["total_messages"],
                "status": "CLASSIFIED_ACTIVE"
            })
            existing_node_ids.add(node_id)

    with open(TOXIC_GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)
    print(f"[+] Updated CMDB graph with {len(existing_node_ids)} total nodes: {TOXIC_GRAPH_PATH}")


def run_acu_synthesis(telemetry: Dict[str, Any]) -> str:
    """Sends structured telemetry to gemini-3.1-pro-preview (or gemini-3.8-flash fallback)."""
    api_key = _load_env_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable missing.")

    client = genai.Client(api_key=api_key)

    payload_json = json.dumps(telemetry, indent=2)
    prompt = f"""
Here is the 7-day empirical telemetry payload extracted from Clio's SQLite database on Friday, October 16, 2026:

```json
{payload_json}
```

Execute the full 5-section Friday 7-Day Cultural Bleacher Autopsy. Ground every observation in the empirical data above.
"""

    print(f"[*] Invoking ACU reasoning model ({DEFAULT_PRO_MODEL})...")
    try:
        response = client.models.generate_content(
            model=DEFAULT_PRO_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
        return response.text
    except Exception as e:
        print(f"[-] Pro model error ({e}), falling back to {DEFAULT_FLASH_MODEL}...")
        response = client.models.generate_content(
            model=DEFAULT_FLASH_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
        return response.text


def main():
    print("[*] Extracting 7-day macro telemetry from morning_wiretap.db...")
    telemetry = extract_weekly_telemetry()
    print(f"[+] Total Messages: {telemetry['total_messages']:,}")
    print(f"[+] Total Authors: {telemetry['total_authors']:,}")
    print(f"[+] Top Migrators Extracted: {len(telemetry['top_migrators'])}")

    print("[*] Running ACU LLM synthesis...")
    report_md = run_acu_synthesis(telemetry)

    out_file = PILOT_DROPS_DIR / "FRIDAY_7D_CULTURAL_BLEACHER_AUTOPSY_2026_10_16.md"
    out_file.write_text(report_md, encoding="utf-8")
    print(f"[✅] Dossier generated: {out_file} ({len(report_md)} bytes)")

    print("[*] Updating ServiceNow CMDB configuration items...")
    update_cmdb_graph(telemetry)
    print("[✅] Friday 7-Day ACU Synthesis complete.")


if __name__ == "__main__":
    main()

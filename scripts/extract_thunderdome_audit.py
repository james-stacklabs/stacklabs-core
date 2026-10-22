#!/usr/bin/env python3
"""
StackLabs ACU - ThunderDome 7-Day Contagion & Bleacher Router Extractor
Enforces Argon Law 3 (WAL mode, emoji regex stripping, zero unindexed LIKE scans)
and locks snapshot denominators across all report sections.
"""
import json
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = Path("/home/james/stacklabs/data/morning_wiretap.db")
OUT_JSON = Path("/dev/shm/faas_vfs/thunderdome_contagion_audit.json")

# Pre-compiled Argon Law 3 regexes
EMOJI_SHORTCODE_RE = re.compile(r":[a-zA-Z0-9_+-]+:")
WHITESPACE_RE = re.compile(r"\s+")
GREETING_NOISE_RE = re.compile(
    r"\b(hi|hello|hey|gm|gn|good morning|good night|stay well|hope everything is ok|birthday|kepi|mrmemo|choualor)\b",
    re.IGNORECASE,
)
SPORTS_HEAT_RE = re.compile(
    r"\b(rodgers|jets|sirianni|eagles|cashman|boone|yankees|dodgers|brewers|soaking|byu|fire|fraud|bum|choke|refs|rigged|contract|bench|trade|playoffs|mvp|qb|bullpen|offense|defense|coach)\b",
    re.IGNORECASE,
)

CHANNEL_METADATA = {
    "radio_mcafee": ("The Pat McAfee Show (ThunderDome)", "Primary National Noon Narrative Router"),
    "NYY_TalkinYanks": ("Talkin' Yanks (Jomboy Media)", "AL East Evening Bleacher Tribunal"),
    "radio_phly": ("PHLY Sports Philadelphia", "NFC East / NL East High-Heat Node"),
    "DET_WoodwardSports": ("Woodward Sports Detroit", "NFC North Midday/Afternoon Hub"),
    "TEN_dynamic": ("Tennessee / SEC Live Wire", "AFC South & SEC Game-Tail Aggregator"),
    "CIN_dynamic": ("Cincinnati / AFC North Wire", "AFC North Live Game-Tail Hub"),
    "TB_dynamic": ("Tampa Bay / NFC South Wire", "NFC South Live Game-Tail Hub"),
    "LV_dynamic": ("Las Vegas / AFC West Wire", "West Coast Afternoon Migration Hub"),
    "IND_dynamic": ("Indianapolis / AFC South Wire", "Local Indy / ThunderDome Spillover Node"),
    "PHI_ValhallaSports": ("Valhalla Sports (Philly Watch Party)", "Multi-Sport Live Watch-Party Hub"),
    "NL_dynamic": ("NL Postseason Live Wire", "MLB October Postseason Contagion Node"),
}


def clean_message(raw_text: str) -> str:
    if not raw_text:
        return ""
    stripped = EMOJI_SHORTCODE_RE.sub("", raw_text)
    return WHITESPACE_RE.sub(" ", stripped).strip()


def score_sports_quote(msg: str) -> float:
    cleaned = clean_message(msg)
    length = len(cleaned)
    if length < 28 or length > 140:
        return -100.0
    if GREETING_NOISE_RE.search(cleaned):
        return -50.0

    alpha_chars = [c for c in cleaned if c.isalpha()]
    if len(alpha_chars) < 15:
        return -50.0

    caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    heat_hits = len(SPORTS_HEAT_RE.findall(cleaned))
    exclamations = min(cleaned.count("!") + cleaned.count("?"), 4)

    # Reward sports vocabulary + punchy length + controlled caps heat
    return (heat_hits * 18.0) + (length * 0.25) + (caps_ratio * 15.0) + (exclamations * 3.0)


def run_extraction() -> dict:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("PRAGMA temp_store=MEMORY;")

    # 1. detect text & timestamp columns dynamically from schema
    c.execute("PRAGMA table_info(chat_telemetry)")
    cols = [row[1] for row in c.fetchall()]
    msg_col = "message" if "message" in cols else ("text" if "text" in cols else "body")
    id_col = "id" if "id" in cols else "rowid"

    # 2. Lock snapshot ceiling so KPI and Header never drift
    c.execute(f"SELECT MAX({id_col}), COUNT(*), COUNT(DISTINCT author) FROM chat_telemetry")
    max_id, total_events, unique_handles = c.fetchone()

    # 3. Get the exact set of handles who stepped foot in radio_mcafee
    c.execute(
        f"""
        SELECT DISTINCT author
        FROM chat_telemetry
        WHERE {id_col} <= ? AND channel_key = 'radio_mcafee' AND author IS NOT NULL
        """,
        (max_id,),
    )
    mcafee_veterans = {row[0] for row in c.fetchall()}

    # 4. Section 1: Broadcast Node Topology + Unique Handles + McAfee Overlap
    c.execute(
        f"""
        SELECT
            channel_key,
            COUNT(*) AS msg_volume,
            COUNT(DISTINCT author) AS unique_chatters,
            SUM(CASE WHEN channel_key != 'radio_mcafee' AND author IN (
                SELECT DISTINCT author FROM chat_telemetry WHERE {id_col} <= ? AND channel_key = 'radio_mcafee'
            ) THEN 1 ELSE 0 END) AS mcafee_crossover_msgs
        FROM chat_telemetry
        WHERE {id_col} <= ?
        GROUP BY channel_key
        ORDER BY msg_volume DESC
        LIMIT 10
        """,
        (max_id, max_id),
    )
    topology_rows = []
    for ch_key, vol, uniq, crossover in c.fetchall():
        display_name, role = CHANNEL_METADATA.get(
            ch_key, (ch_key, "Regional Live Broadcast & Bleacher Node")
        )
        topology_rows.append(
            {
                "broadcast_node": display_name,
                "system_key": ch_key,
                "volume_7d": vol,
                "unique_handles": uniq,
                "mcafee_crossover_msgs": crossover if ch_key != "radio_mcafee" else vol,
                "ecosystem_role": role,
            }
        )

    # 5. Section 2: True ThunderDome Super-Spreaders (Anchored in radio_mcafee + >= 3 channels)
    c.execute(
        f"""
        SELECT
            author,
            COUNT(DISTINCT channel_key) AS breadth,
            COUNT(*) AS total_msgs,
            SUM(CASE WHEN channel_key = 'radio_mcafee' THEN 1 ELSE 0 END) AS mcafee_msgs
        FROM chat_telemetry
        WHERE {id_col} <= ?
          AND author IS NOT NULL
          AND author IN (
              SELECT DISTINCT author FROM chat_telemetry
              WHERE {id_col} <= ? AND channel_key = 'radio_mcafee'
          )
        GROUP BY author
        HAVING breadth >= 3 AND mcafee_msgs >= 3
        ORDER BY breadth DESC, total_msgs DESC
        LIMIT 12
        """,
        (max_id, max_id),
    )
    candidates = c.fetchall()

    super_spreaders = []
    for author, breadth, total_msgs, mcafee_msgs in candidates:
        # Per-channel slice breakdown (always putting radio_mcafee first, then top 4 external targets)
        c.execute(
            f"""
            SELECT channel_key, COUNT(*) AS cnt
            FROM chat_telemetry
            WHERE {id_col} <= ? AND author = ?
            GROUP BY channel_key
            ORDER BY CASE WHEN channel_key = 'radio_mcafee' THEN 0 ELSE 1 END, cnt DESC
            LIMIT 5
            """,
            (max_id, author),
        )
        slices = [f"{ch} ({cnt})" for ch, cnt in c.fetchall()]

        # Pull up to 150 recent messages for this handle and select highest-entropy sports quote
        c.execute(
            f"""
            SELECT {msg_col}, channel_key
            FROM chat_telemetry
            WHERE {id_col} <= ? AND author = ?
            ORDER BY {id_col} DESC
            LIMIT 150
            """,
            (max_id, author),
        )
        best_quote = ""
        best_quote_ch = ""
        best_score = -999.0
        for raw_msg, ch in c.fetchall():
            sc = score_sports_quote(str(raw_msg))
            if sc > best_score:
                best_score = sc
                best_quote = clean_message(str(raw_msg))
                best_quote_ch = ch

        super_spreaders.append(
            {
                "router_handle": author,
                "breadth": f"{breadth} channels",
                "volume": total_msgs,
                "mcafee_volume": mcafee_msgs,
                "top_ingress_slices": ", ".join(slices),
                "sample_verbatim_quote": f'"{best_quote}" [{best_quote_ch}]',
            }
        )

    conn.close()

    payload = {
        "locked_max_id": max_id,
        "total_ingest_events": total_events,
        "unique_handles": unique_handles,
        "thunderdome_veteran_handles": len(mcafee_veterans),
        "network_topology": topology_rows,
        "super_spreaders": super_spreaders[:10],
    }

    # Atomic write per Argon Law 6
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = OUT_JSON.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, OUT_JSON)
    return payload


if __name__ == "__main__":
    data = run_extraction()
    print(f"LOCKED TOTAL EVENTS: {data['total_ingest_events']:,} | UNIQUE HANDLES: {data['unique_handles']:,}")
    print(f"THUNDERDOME VETERANS: {data['thunderdome_veteran_handles']:,}")
    print("\n--- TOP 10 THUNDERDOME SUPER-SPREADERS ---")
    for row in data["super_spreaders"]:
        print(f"{row['router_handle']:24s} | {row['breadth']:11s} | {row['volume']:4d} msgs | {row['top_ingress_slices']}")
        print(f"   -> QUOTE: {row['sample_verbatim_quote']}")

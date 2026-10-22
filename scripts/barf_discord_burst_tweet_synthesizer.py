#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs @BarfFanStack Dynamic Discord Burst Tweet Synthesizer & Gateway Dispatcher
Path: /home/james/stacklabs/scripts/barf_discord_burst_tweet_synthesizer.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Host: Clio (clio / Dedicated Linux Host / 100.96.77.20)
Active Gemini Model Invariant: gemini-3.8-flash (Strict October 2026 Production Standard)
Governing Standards: Invariant 0, 15, 21, 32 (Law of "I"), 35 (.venv), 38, 50, Argon Laws 1-9
"""

import argparse
import dataclasses
import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

REPO_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(REPO_ROOT))

from scripts.cfb_slate_omni_resolver import get_wal_connection, sync_lexicon_to_sqlite
from scripts.discord_stream_tailer import (
    atomic_write_json,
    compute_merkle_sha256,
    ensure_wiretap_discord_schemas,
    load_dotenv_file,
)

ENV_PATH = REPO_ROOT / ".env"
load_dotenv_file(ENV_PATH)

DB_PATH = Path(
    os.getenv(
        "STACKLABS_WIRETAP_DB",
        str(REPO_ROOT / "data" / "morning_wiretap.db"),
    )
)
VFS_TELEMETRY_DIR = Path("/dev/shm/vfs/telemetry")
BARF_LATEST_STORM_VFS_PATH = VFS_TELEMETRY_DIR / "barf_latest_tweet_storm.json"

MAX_TWEET_CHARS = 280
FINAL_TWEET_SAFE_CEILING = 268

PROGRAM_SOCIAL_TAXONOMY: Dict[str, Dict[str, str]] = {
    "BYU": {"handle": "@BYUFootball", "hashtags": "#BYUFootball #GoCougs"},
    "TEX": {"handle": "@TexasFootball", "hashtags": "#HookEm #TexasLonghorns"},
    "TENN": {"handle": "@Vol_Football", "hashtags": "#GBO #Vols"},
    "MISS": {"handle": "@OleMissFB", "hashtags": "#HottyToddy #OleMiss"},
    "AUB": {"handle": "@AuburnFootball", "hashtags": "#WarEagle #Auburn"},
    "LSU": {"handle": "@LSUfootball", "hashtags": "#GeauxTigers #LSU"},
    "TAMU": {"handle": "@AggieFootball", "hashtags": "#GigEm #TexAgs"},
    "MICH": {"handle": "@UMichFootball", "hashtags": "#GoBlue #Michigan"},
    "FLA": {"handle": "@GatorsFB", "hashtags": "#GoGators #TheSwamp"},
    "UGA": {"handle": "@GeorgiaFootball", "hashtags": "#GoDawgs #DawgNation"},
    "OSU": {"handle": "@OhioStateFB", "hashtags": "#GoBucks #BuckeyeNation"},
    "IU": {"handle": "@IndianaFootball", "hashtags": "#9WINDIANA #Hoosiers"},
    "ND": {"handle": "@NDFootball", "hashtags": "#GoIrish #NotreDame"},
    "ALA": {"handle": "@AlabamaFTBL", "hashtags": "#RollTide #Bama"},
    "ORE": {"handle": "@oregonfootball", "hashtags": "#GoDucks #ScoDucks"},
    "PSU": {"handle": "@PennStateFball", "hashtags": "#WeAre #PennState"},
    "PHI": {"handle": "@Eagles", "hashtags": "#FlyEaglesFly #Eagles"},
    "NYG": {"handle": "@Giants", "hashtags": "#TogetherBlue #NYGiants"},
    "DAL": {"handle": "@dallascowboys", "hashtags": "#CowboysNation #DallasCowboys"},
    "NYM": {"handle": "@Mets", "hashtags": "#LGM #Mets"},
}


@dataclasses.dataclass(frozen=True)
class VerifiedTweetBlock:
    part_number: int
    total_parts: int
    text: str
    char_count: int
    headroom_chars: int

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class BarfTweetStormReceipt:
    storm_id: str
    source_alert_id: str
    channel_key: str
    shibboleth_id: str
    team_abbrev: str
    program_name: str
    z_score: float
    velocity_mps: float
    hit_count: int
    window_messages: int
    blood_pressure: str
    pastrami_lbs: float
    tums_chewed: int
    dr_shapiro_status: str
    discord_blast: str
    tweets: List[VerifiedTweetBlock]
    content_sha256: str
    dispatched_to_discord: bool
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "storm_id": self.storm_id,
            "source_alert_id": self.source_alert_id,
            "channel_key": self.channel_key,
            "shibboleth_id": self.shibboleth_id,
            "team_abbrev": self.team_abbrev,
            "program_name": self.program_name,
            "z_score": self.z_score,
            "velocity_mps": self.velocity_mps,
            "hit_count": self.hit_count,
            "window_messages": self.window_messages,
            "blood_pressure": self.blood_pressure,
            "pastrami_lbs": self.pastrami_lbs,
            "tums_chewed": self.tums_chewed,
            "dr_shapiro_status": self.dr_shapiro_status,
            "discord_blast": self.discord_blast,
            "tweets": [t.to_dict() for t in self.tweets],
            "content_sha256": self.content_sha256,
            "dispatched_to_discord": self.dispatched_to_discord,
            "created_at": self.created_at,
        }


def ensure_barf_tables(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS barf_tweet_storms (
                storm_id TEXT PRIMARY KEY,
                source_alert_id TEXT NOT NULL,
                channel_key TEXT NOT NULL,
                shibboleth_id TEXT NOT NULL,
                team_abbrev TEXT NOT NULL,
                z_score REAL NOT NULL,
                velocity_mps REAL NOT NULL,
                blood_pressure TEXT,
                tums_chewed INTEGER,
                discord_blast TEXT,
                tweets_json TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                dispatched_to_discord INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_barf_storms_created
            ON barf_tweet_storms(created_at DESC);
            """
        )


def compute_barf_biometrics(z_score: float, velocity_mps: float) -> Tuple[str, float, int, str]:
    systolic = int(140 + min(65, z_score * 11))
    diastolic = int(90 + min(35, velocity_mps * 7))
    bp_str = f"{systolic}/{diastolic}"
    pastrami_lbs = round(1.2 + (z_score * 0.35), 2)
    tums_cnt = int(3 + round(velocity_mps * 2.5))
    shapiro_options = [
        "Dr. Shapiro frantically paging me from Queens Blvd",
        "Dr. Shapiro screaming into his phone on the Grand Central Parkway",
        "Dr. Shapiro ordering an ambulance to my basement right now",
        "Dr. Shapiro refusing to write any more Lipitor refills",
    ]
    shapiro_idx = int(z_score + velocity_mps) % len(shapiro_options)
    return bp_str, pastrami_lbs, tums_cnt, shapiro_options[shapiro_idx]


def clamp_tweet_body(prefix: str, body: str, suffix: str = "", ceiling: int = MAX_TWEET_CHARS) -> str:
    body_clean = re.sub(r"\s+", " ", body).strip()
    prefix_clean = prefix.strip()
    suffix_clean = suffix.strip()

    if prefix_clean and body_clean.startswith(prefix_clean):
        body_clean = body_clean[len(prefix_clean):].strip()

    fixed_len = len(prefix_clean) + (1 if prefix_clean else 0) + (1 if suffix_clean else 0) + len(suffix_clean)
    available = ceiling - fixed_len

    if len(body_clean) > available:
        cutoff = max(10, available - 3)
        body_clean = body_clean[:cutoff].rstrip() + "..."

    parts = [p for p in [prefix_clean, body_clean, suffix_clean] if p]
    return " ".join(parts)


def generate_barf_llm_storm(
    team_abbrev: str,
    program_name: str,
    channel_key: str,
    shib_id: str,
    ngram_token: str,
    ground_truth: str,
    false_pos: str,
    peak_quote: str,
    peak_author: str,
    z_score: float,
    velocity_mps: float,
    hit_count: int,
    window_msgs: int,
    bp_str: str,
    pastrami_lbs: float,
    tums_cnt: int,
    shapiro_status: str,
) -> Optional[Dict[str, str]]:
    candidate_keys = [
        os.getenv("GEMINI_FREE_KEY_1"),
        os.getenv("GEMINI_CLOUD_CONSOLE_KEY"),
        os.getenv("VERTEX_API_KEY"),
        os.getenv("GEMINI_API_KEY"),
    ]
    valid_keys = [k for k in candidate_keys if k]
    if not valid_keys:
        return None

    system_instruction = (
        "You are Barf the Dog (@BarfFanStack), an unhinged, neurotic, pastrami-inhaling "
        "New York Mets diehard fan broadcasting from a Queens basement. You are a savage, "
        "culturally literate savant who exposes Wall Street hedge fund algorithms for failing to understand "
        "authentic college football subcultural slang. You speak in fast, hilarious, raw Queens banter, "
        "referencing your medical status, your pastrami consumption, and Dr. Shapiro. "
        "You MUST output valid, pure JSON without markdown backticks."
    )

    prompt = f"""Generate Barf's reaction to this live Discord lexical anomaly burst.
Metrics:
- Team: {team_abbrev} ({program_name})
- Game / Channel: {channel_key}
- Shibboleth: {shib_id}
- Burst Phrase: "{ngram_token}"
- Stat Spike: +{z_score:.2f} sigma, {velocity_mps:.2f} msgs/sec ({hit_count} hits in {window_msgs} msgs)
- Bleacher Ground Truth: {ground_truth}
- Wall Street Algo Mistake: {false_pos}
- Discord Quote by @{peak_author}: "{peak_quote}"
- Biometrics: BP {bp_str}, {pastrami_lbs} lbs pastrami eaten, {tums_cnt} Tums chewed, Shapiro note: {shapiro_status}

Requirements:
Return a JSON object with exactly these 5 keys:
1. "tweet_1": Part 1/4. Visceral basement shock, statistical spike, and quoting @{peak_author}. Under 240 characters (do not include "(1/4)" prefix, it will be prepended automatically).
2. "tweet_2": Part 2/4. Tearing apart the suit-and-tie Wall Street quants for thinking "{ngram_token}" was {false_pos.lower()}, decoding the real ground truth. Under 240 characters.
3. "tweet_3": Part 3/4. Barf's emotional/tactical meltdown, blood pressure ({bp_str}), Tums count ({tums_cnt}), and Dr. Shapiro. Under 240 characters.
4. "tweet_4": Part 4/4. Final verdict. Must leave room for tags. Under 180 characters.
5. "discord_blast": Direct punchy 1-2 sentence message Barf screams directly into the Discord chat. Under 280 characters.
"""

    last_err: Optional[Exception] = None
    for api_key in valid_keys:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    response_mime_type="application/json",
                ),
            )
            if response and response.text:
                cleaned = response.text.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                return json.loads(cleaned)
        except Exception as exc:
            last_err = exc
            continue

    if last_err is not None:
        print(f"[BARF-SYNTHESIZER] Note: LLM synthesis fallback triggered ({last_err})", file=sys.stderr)
    return None


def synthesize_fallback_tweets(
    team_abbrev: str,
    program_name: str,
    channel_key: str,
    ngram_token: str,
    ground_truth: str,
    false_pos: str,
    peak_quote: str,
    peak_author: str,
    z_score: float,
    velocity_mps: float,
    hit_count: int,
    window_msgs: int,
    bp_str: str,
    pastrami_lbs: float,
    tums_cnt: int,
    shapiro_status: str,
    barf_angle: str,
    primary_board: str,
) -> Dict[str, str]:
    gt_clause = ground_truth.split(",")[0].strip().rstrip(".")
    fp_clause = false_pos.split(",")[0].strip().lower().rstrip(".")
    quote_short = peak_quote if len(peak_quote) <= 75 else peak_quote[:72].rstrip() + "..."

    t1_body = (
        f"Spilled my Cel-Ray over {pastrami_lbs} lbs of pastrami in Queens! "
        f"{program_name} Discord ({channel_key}) erupted at +{z_score:.2f}σ ({velocity_mps:.2f} msgs/s, "
        f"{hit_count}/{window_msgs} hits) on \"{ngram_token}\". @{peak_author}: \"{quote_short}\""
    )
    t2_body = (
        f"Wall Street quants think \"{ngram_token}\" on {primary_board} is {fp_clause}. "
        f"Clueless suits! Bleacher reality: {gt_clause}."
    )
    t3_body = (
        f"{barf_angle} BP is {bp_str}, I'm {tums_cnt} Tums deep, and "
        f"{shapiro_status}."
    )
    t4_body = (
        f"Pull the main breaker in {team_abbrev} country before {primary_board} "
        f"melts the rack. Certified +{z_score:.1f}σ sicko pandemonium."
    )
    blast = (
        f"🚨 BARF ALERT: +{z_score:.1f}σ lexical spike on '{ngram_token}'! "
        f"Wall Street bots are lost, my BP is {bp_str}, and {primary_board} is off the rails."
    )
    return {
        "tweet_1": t1_body,
        "tweet_2": t2_body,
        "tweet_3": t3_body,
        "tweet_4": t4_body,
        "discord_blast": blast,
    }


def synthesize_barf_storm(
    alert_row: Dict[str, Any],
    conn: sqlite3.Connection,
    dispatch_discord: bool = False,
    target_channel_id: Optional[str] = None,
    dry_run: bool = False,
) -> BarfTweetStormReceipt:
    shib_id = str(alert_row.get("shibboleth_id") or "UNKNOWN_SHIBBOLETH")
    channel_key = str(alert_row.get("channel_key") or "UNKNOWN_GAME")
    ngram_token = str(alert_row.get("ngram_or_token") or "unknown_slang")
    peak_quote = str(alert_row.get("peak_quote") or "no quote recorded")
    peak_author = str(alert_row.get("peak_author") or "anonymous_fan")
    z_score = float(alert_row.get("z_score") or 4.5)
    velocity_mps = float(alert_row.get("velocity_mps") or 2.0)
    hit_count = int(alert_row.get("hit_count") or 5)
    window_msgs = int(alert_row.get("window_messages") or 30)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM cfb_subcultural_lexicon
        WHERE shibboleth_id = ?
        LIMIT 1;
        """,
        (shib_id,),
    )
    lex_res = cur.fetchone()
    lex_row = dict(lex_res) if lex_res else {}

    team_abbrev = str(lex_row.get("team_abbrev") or alert_row.get("team_abbrev") or "CFB").upper()
    program_name = str(lex_row.get("program_name") or f"{team_abbrev} Football")
    primary_board = str(
        lex_row.get("primary_board")
        or lex_row.get("primary_fan_board")
        or f"{team_abbrev} Game Thread"
    )
    ground_truth = str(
        lex_row.get("subcultural_ground_truth")
        or lex_row.get("bleacher_ground_truth")
        or f"Subcultural meaning for {ngram_token}"
    )
    false_pos = str(
        lex_row.get("static_nlp_false_positive")
        or lex_row.get("wall_street_false_positive")
        or f"Literal semantic error for {ngram_token}"
    )
    barf_angle = str(
        lex_row.get("barf_ammunition_angle") or f"{program_name} has lost all composure."
    )

    bp_str, pastrami_lbs, tums_cnt, shapiro_status = compute_barf_biometrics(z_score, velocity_mps)
    tax = PROGRAM_SOCIAL_TAXONOMY.get(
        team_abbrev,
        {"handle": f"@{team_abbrev}Football", "hashtags": f"#{team_abbrev} #CFB"},
    )
    game_hashtag = f"#{channel_key.replace('_', 'vs')}"

    llm_output = generate_barf_llm_storm(
        team_abbrev=team_abbrev,
        program_name=program_name,
        channel_key=channel_key,
        shib_id=shib_id,
        ngram_token=ngram_token,
        ground_truth=ground_truth,
        false_pos=false_pos,
        peak_quote=peak_quote,
        peak_author=peak_author,
        z_score=z_score,
        velocity_mps=velocity_mps,
        hit_count=hit_count,
        window_msgs=window_msgs,
        bp_str=bp_str,
        pastrami_lbs=pastrami_lbs,
        tums_cnt=tums_cnt,
        shapiro_status=shapiro_status,
    )

    if not llm_output:
        llm_output = synthesize_fallback_tweets(
            team_abbrev=team_abbrev,
            program_name=program_name,
            channel_key=channel_key,
            ngram_token=ngram_token,
            ground_truth=ground_truth,
            false_pos=false_pos,
            peak_quote=peak_quote,
            peak_author=peak_author,
            z_score=z_score,
            velocity_mps=velocity_mps,
            hit_count=hit_count,
            window_msgs=window_msgs,
            bp_str=bp_str,
            pastrami_lbs=pastrami_lbs,
            tums_cnt=tums_cnt,
            shapiro_status=shapiro_status,
            barf_angle=barf_angle,
            primary_board=primary_board,
        )

    t1_text = clamp_tweet_body("(1/4)", llm_output.get("tweet_1", ""), ceiling=MAX_TWEET_CHARS)
    t2_text = clamp_tweet_body("(2/4)", llm_output.get("tweet_2", ""), ceiling=MAX_TWEET_CHARS)
    t3_text = clamp_tweet_body("(3/4)", llm_output.get("tweet_3", ""), ceiling=MAX_TWEET_CHARS)

    closing_tags = f"{tax['handle']} {tax['hashtags']} {game_hashtag} @TheWardyNYM"
    t4_text = clamp_tweet_body(
        "(4/4)",
        llm_output.get("tweet_4", ""),
        suffix=closing_tags,
        ceiling=FINAL_TWEET_SAFE_CEILING,
    )
    discord_blast = str(llm_output.get("discord_blast") or t1_text)[:300]

    raw_tweets = [t1_text, t2_text, t3_text, t4_text]
    verified_blocks: List[VerifiedTweetBlock] = []
    for idx, txt in enumerate(raw_tweets, start=1):
        char_len = len(txt)
        if char_len > MAX_TWEET_CHARS:
            raise AssertionError(f"Tweet ({idx}/4) exceeded 280 chars: {char_len}")
        if idx == 4 and "@TheWardyNYM" not in txt:
            raise AssertionError("Tweet (4/4) missing mandatory @TheWardyNYM tag")
        verified_blocks.append(
            VerifiedTweetBlock(
                part_number=idx,
                total_parts=4,
                text=txt,
                char_count=char_len,
                headroom_chars=MAX_TWEET_CHARS - char_len,
            )
        )

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    merkle_digest = compute_merkle_sha256(
        {
            "source_alert_id": str(alert_row.get("alert_id") or "seed_alert"),
            "channel_key": channel_key,
            "shibboleth_id": shib_id,
            "tweets": [b.text for b in verified_blocks],
        }
    )
    storm_id = f"barf-storm-{team_abbrev.lower()}-{merkle_digest[:12]}"

    dispatched = False
    if dispatch_discord and not dry_run:
        chan = target_channel_id or str(alert_row.get("channel_id") or "")
        dispatched = dispatch_message_to_discord(chan, discord_blast)

    receipt = BarfTweetStormReceipt(
        storm_id=storm_id,
        source_alert_id=str(alert_row.get("alert_id") or "seed_alert"),
        channel_key=channel_key,
        shibboleth_id=shib_id,
        team_abbrev=team_abbrev,
        program_name=program_name,
        z_score=z_score,
        velocity_mps=velocity_mps,
        hit_count=hit_count,
        window_messages=window_msgs,
        blood_pressure=bp_str,
        pastrami_lbs=pastrami_lbs,
        tums_chewed=tums_cnt,
        dr_shapiro_status=shapiro_status,
        discord_blast=discord_blast,
        tweets=verified_blocks,
        content_sha256=merkle_digest,
        dispatched_to_discord=dispatched,
        created_at=now_iso,
    )

    atomic_write_json(BARF_LATEST_STORM_VFS_PATH, receipt.to_dict())

    if not dry_run:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO barf_tweet_storms (
                    storm_id, source_alert_id, channel_key, shibboleth_id, team_abbrev,
                    z_score, velocity_mps, blood_pressure, tums_chewed, discord_blast,
                    tweets_json, content_sha256, dispatched_to_discord, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    receipt.storm_id,
                    receipt.source_alert_id,
                    receipt.channel_key,
                    receipt.shibboleth_id,
                    receipt.team_abbrev,
                    receipt.z_score,
                    receipt.velocity_mps,
                    receipt.blood_pressure,
                    receipt.tums_chewed,
                    receipt.discord_blast,
                    json.dumps([t.to_dict() for t in receipt.tweets]),
                    receipt.content_sha256,
                    1 if receipt.dispatched_to_discord else 0,
                    receipt.created_at,
                ),
            )

    return receipt


def dispatch_message_to_discord(channel_id: str, message_text: str) -> bool:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        try:
            resp = requests.post(webhook_url, json={"content": message_text, "username": "LFGM_Barf"}, timeout=5.0)
            return resp.status_code in (200, 204)
        except Exception as exc:
            print(f"[BARF-DISPATCH] Webhook send failed: {exc}", file=sys.stderr)

    user_token = os.getenv("DISCORD_USER_TOKEN")
    if user_token and channel_id:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {
            "Authorization": user_token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }
        try:
            resp = requests.post(url, headers=headers, json={"content": message_text}, timeout=5.0)
            return resp.status_code in (200, 201)
        except Exception as exc:
            print(f"[BARF-DISPATCH] Gateway REST send failed: {exc}", file=sys.stderr)

    return False


def seed_canonical_burst_if_empty(conn: sqlite3.Connection) -> Dict[str, Any]:
    ensure_wiretap_discord_schemas(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM discord_burst_alerts
        ORDER BY epoch_time DESC
        LIMIT 1;
        """
    )
    row = cur.fetchone()
    if row:
        return dict(row)

    now_epoch = time.time()
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seed = {
        "alert_id": f"burst-byu_soaking_quaking-{int(now_epoch * 1000)}",
        "channel_id": "1296543210987654321",
        "stream_id": "discord_nd_byu_live",
        "channel_key": "ND_BYU",
        "shibboleth_id": "BYU_SOAKING_QUAKING",
        "team_abbrev": "BYU",
        "ngram_or_token": "quaking, soaking",
        "z_score": 5.0,
        "z_score_threshold": 4.5,
        "velocity_mps": 2.45,
        "hit_count": 8,
        "window_messages": 35,
        "window_seconds": 60.0,
        "peak_quote": "soaking and quaking in Helaman Halls after that touchdown #2!",
        "peak_author": "HonorCodeWatcher2",
        "epoch_time": now_epoch,
        "timestamp_str": now_str,
        "created_at": now_str,
    }
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO discord_burst_alerts (
                alert_id, channel_id, stream_id, channel_key, shibboleth_id,
                team_abbrev, ngram_or_token, z_score, z_score_threshold,
                velocity_mps, hit_count, window_messages, window_seconds,
                peak_quote, peak_author, epoch_time, content_sha256, timestamp_str
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                seed["alert_id"],
                seed["channel_id"],
                seed["stream_id"],
                seed["channel_key"],
                seed["shibboleth_id"],
                seed["team_abbrev"],
                seed["ngram_or_token"],
                seed["z_score"],
                seed["z_score_threshold"],
                seed["velocity_mps"],
                seed["hit_count"],
                seed["window_messages"],
                seed["window_seconds"],
                seed["peak_quote"],
                seed["peak_author"],
                seed["epoch_time"],
                compute_merkle_sha256(seed),
                seed["timestamp_str"],
            ),
        )
    return seed


def main() -> None:
    parser = argparse.ArgumentParser(description="StackLabs Barf Tweet Storm Synthesizer")
    parser.add_argument("--alert-id", help="Specific alert_id to synthesize from")
    parser.add_argument("--dispatch", action="store_true", help="Dispatch blast to Discord")
    parser.add_argument("--channel-id", help="Explicit Discord channel ID to dispatch to")
    parser.add_argument("--dry-run", action="store_true", help="Synthesize without DB writes")
    args = parser.parse_args()

    conn = get_wal_connection(DB_PATH)
    ensure_wiretap_discord_schemas(conn)
    sync_lexicon_to_sqlite(conn)
    ensure_barf_tables(conn)

    if args.alert_id:
        cur = conn.cursor()
        cur.execute("SELECT * FROM discord_burst_alerts WHERE alert_id = ? LIMIT 1;", (args.alert_id,))
        row = cur.fetchone()
        alert_row = dict(row) if row else seed_canonical_burst_if_empty(conn)
    else:
        alert_row = seed_canonical_burst_if_empty(conn)

    receipt = synthesize_barf_storm(
        alert_row=alert_row,
        conn=conn,
        dispatch_discord=args.dispatch,
        target_channel_id=args.channel_id,
        dry_run=args.dry_run,
    )

    print(f"[BARF-SYNTHESIZER] SUCCESS: Storm ID: {receipt.storm_id}")
    print(f"[BARF-SYNTHESIZER] Shibboleth: {receipt.shibboleth_id} (+{receipt.z_score:.1f}σ)")
    print(f"[BARF-SYNTHESIZER] Discord Blast: {receipt.discord_blast}")
    for t in receipt.tweets:
        print(f"  [{t.part_number}/4] ({t.char_count} chars): {t.text}")


if __name__ == "__main__":
    main()

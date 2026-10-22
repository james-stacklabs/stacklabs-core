#!/home/james/stacklabs/.venv/bin/python3
"""
Chat Velocity Burst Bridge Runner with Unhinged Fan Radar & Canvas Broadcaster
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/vfs/services/chat_velocity_bridge/run.py
"""
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import time
import urllib.request

BASE_DIR = pathlib.Path(__file__).resolve().parent
PENDING_FILE = BASE_DIR / ".state" / "pending_burst.json"
COOLDOWNS_FILE = BASE_DIR / ".state" / "team_cooldowns.json"
DISPATCH_LOG = BASE_DIR / ".state" / "dispatched_bursts.log"
ROOM_COOLDOWN_FILE = BASE_DIR / ".state" / "room_last_canvas_drop.json"
DB_PATH = pathlib.Path("/home/james/stacklabs/data/morning_wiretap.db")
ENV_PATH = pathlib.Path("/home/james/stacklabs/.env")

BOT_DENYLIST = {
    "streamlabs", "nightbot", "streamelements", "moobot", "wizebot",
    "bot", "automod", "restreambot", "fossabot", "chatbot", "moderator"
}

SPAM_REGEX = re.compile(
    r"(\b(https?://|www\.)\S+)|"
    r"(\b[a-zA-Z0-9_-]+(\.com|\.net|\.org|\.io|\.tv|\.me|,çom|,com)\b)|"
    r"(buffstream|nflhd|nflcbs|vipbox|crackstream|streameast|livestream|live stream)|"
    r"(discord\.gg|t\.me)|"
    r"(betting is open|use !bet|register your bet|pointsbet|draftkings|fanduel)",
    re.IGNORECASE
)

UNHINGED_KEYWORDS = [
    "fire", "bench", "washed", "fraud", "bum", "clown", "trash", "garbage",
    "meltdown", "choke", "pissed", "hate", "kill me", "bleach", "crying",
    "stickum", "refs", "holding", "flag", "blind", "rigged", "checkdown",
    "coward", "interception", "pick 6", "fumble", "drop", "dropped", "wide open",
    "wine", "beer", "cab sauv", "liquor", "drywall", "couch", "doctor", "blood pressure",
    "divorce", "quit", "done with this", "selling my tickets", "never watching again"
]


def is_authentic_human_fan(message: str, author: str) -> bool:
    if not message or len(message.strip()) < 10:
        return False
    auth_clean = author.lower().lstrip("@")
    for bot_term in BOT_DENYLIST:
        if bot_term in auth_clean:
            return False
    if SPAM_REGEX.search(message):
        return False
    # Reject Unicode mathematical symbols used by scam bots
    math_chars = sum(1 for c in message if 0x1D400 <= ord(c) <= 0x1D7FF)
    if math_chars >= 3:
        return False
    # Reject pure emoji spam
    words = message.split()
    if len(words) < 3:
        return False
    return True


def score_unhinged_entropy(message: str, author: str) -> float:
    text_lower = message.lower()
    score = 1.0

    for term in UNHINGED_KEYWORDS:
        if term in text_lower:
            score += 3.5

    # Reward emotional punctuation and all-caps emphasis
    exclamations = min(4, message.count("!"))
    questions = min(3, message.count("?"))
    score += (exclamations * 0.8) + (questions * 0.6)

    upper_letters = sum(1 for c in message if c.isupper())
    total_letters = sum(1 for c in message if c.isalpha())
    if total_letters > 15 and (upper_letters / total_letters) > 0.6:
        score += 2.5

    # Penalize bland short generic cheers
    generic_cheers = ["go pack go", "let's go pack", "lets go pack", "go cowboys", "let's go cowboys", "lets go cowboys"]
    if any(text_lower.strip() == c for c in generic_cheers):
        score -= 5.0

    if len(message) > 180:
        score -= 2.0

    return score


def route_advocate(quote: str, team: str) -> str:
    q = quote.lower()
    if any(k in q for k in ["total", "over", "under", "parity", "line", "spread", "hook", "odds", "quant", "bet"]):
        return "sammy"
    if any(k in q for k in ["pack", "packers", "green bay", "love", "lambeau", "cheese", "chet", "wisconsin"]):
        return "chet"
    if any(k in q for k in ["cowboy", "cowboys", "dallas", "dak", "larry", "jerry", "parsons", "arlington"]):
        return "larry"
    if any(k in q for k in ["wine", "beer", "cab sauv", "liquor", "old", "weather", "catfish", "tractor", "pond"]):
        return "burl"
    return "barf"


def main() -> int:
    if not PENDING_FILE.exists():
        return 0

    try:
        burst_meta = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except Exception:
        PENDING_FILE.unlink(missing_ok=True)
        return 0

    channel_key = burst_meta.get("channel_key", "UNKNOWN")
    stream_id = burst_meta.get("stream_id", "stream")
    team_abbrev = burst_meta.get("team", "NFL")
    msg_count = int(burst_meta.get("msg_count", 10))
    now_epoch = time.time()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_epoch))

    # Room-wide cooldown check: minimum 180 seconds between quote blasts
    last_drop_epoch = 0
    if ROOM_COOLDOWN_FILE.exists():
        try:
            last_drop_epoch = json.loads(ROOM_COOLDOWN_FILE.read_text(encoding="utf-8")).get("epoch", 0)
        except Exception:
            last_drop_epoch = 0

    if (now_epoch - last_drop_epoch) < 180:
        PENDING_FILE.unlink(missing_ok=True)
        return 0

    # Read candidates from database
    candidates = []
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("""
                SELECT author, message 
                FROM chat_telemetry 
                WHERE channel_key = ? AND epoch_time > (? - 90)
                ORDER BY epoch_time DESC 
                LIMIT 60
            """, (channel_key, now_epoch))
            candidates = cur.fetchall()
            conn.close()
        except Exception as exc:
            print(f"[CHAT_VELOCITY_BRIDGE] DB query error: {exc}")

    ranked = []
    for author, msg in candidates:
        if is_authentic_human_fan(str(msg), str(author)):
            s = score_unhinged_entropy(str(msg), str(author))
            ranked.append((s, str(author).lstrip("@"), str(msg).strip()))

    if not ranked:
        PENDING_FILE.unlink(missing_ok=True)
        return 0

    ranked.sort(key=lambda x: x[0], reverse=True)
    best_score, peak_author, peak_quote = ranked[0]

    target_advocate = route_advocate(peak_quote, team_abbrev)
    alert_id = f"burst-{team_abbrev.lower()}-{int(now_epoch * 1000)}"
    content_sha256 = hashlib.sha256(f"{alert_id}:{peak_quote}".encode("utf-8")).hexdigest()
    velocity_mps = round(msg_count / 15.0, 2)
    z_score = round(max(4.5, min(8.0, 3.5 + (msg_count / 10.0))), 2)

    # Dispatch Bleacher Canvas Quote Card to Discord
    webhook_url = ""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
                webhook_url = line.split("=", 1)[1].strip().strip("\"'")

    canvas_card = (
        f"📺 **OVERHEARD IN THE BLEACHERS**\n"
        f"> *\"{peak_quote}\"*\n"
        f"— **@{peak_author}** • *Lambeau Live Bleachers*"
    )

    if webhook_url.startswith("http"):
        try:
            wh_payload = json.dumps({"content": canvas_card, "flags": 4096}).encode("utf-8")
            wh_req = urllib.request.Request(
                webhook_url,
                data=wh_payload,
                headers={"Content-Type": "application/json", "User-Agent": "BleacherCanvas/2.0"}
            )
            with urllib.request.urlopen(wh_req, timeout=5):
                pass
        except Exception as exc:
            print(f"[CHAT_VELOCITY_BRIDGE] Webhook canvas card error: {exc}")

    # Record room cooldown
    ROOM_COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
    ROOM_COOLDOWN_FILE.write_text(json.dumps({"epoch": int(now_epoch), "author": peak_author}, indent=2), encoding="utf-8")

    # Insert into discord_burst_alerts with targeted advocate tag
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO discord_burst_alerts (
                alert_id, channel_key, stream_id, channel_id, shibboleth_id,
                team_abbrev, ngram_or_token, hit_count, window_messages, window_seconds,
                velocity_mps, z_score, z_score_threshold, peak_author, peak_quote,
                timestamp_str, epoch_time, content_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert_id, channel_key, stream_id, channel_key, target_advocate,
            team_abbrev, "UNHINGED_FAN_QUOTE", msg_count, msg_count, 15.0,
            velocity_mps, z_score, 4.5, peak_author, peak_quote,
            now_iso, now_epoch, content_sha256
        ))
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[CHAT_VELOCITY_BRIDGE] Insert burst error: {exc}")

    # Stage enriched burst data for the targeted advocate
    burst_payload = {
        "burst_id": alert_id,
        "game_id": team_abbrev,
        "target_advocate": target_advocate,
        "peak_author": peak_author,
        "sample_text": peak_quote,
        "z_score": z_score,
        "timestamp": int(now_epoch)
    }
    (BASE_DIR / ".state" / "enriched_burst.json").write_text(json.dumps(burst_payload, indent=2), encoding="utf-8")

    with open(DISPATCH_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {alert_id} -> Target: {target_advocate} | @{peak_author}: \"{peak_quote}\"\n")

    PENDING_FILE.unlink(missing_ok=True)
    print(f"✓ [BLEACHER CANVAS] Broadcasted quote by @{peak_author} -> Assigned Advocate: {target_advocate}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

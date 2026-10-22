#!/usr/bin/env python3
"""
weedstack_content_poller.py
Polls enabled content sources for WEEDSTACK_SIM_001 and queues events.
Runs as a background daemon alongside fanstack_relay.py.
"""
import sqlite3, uuid, time, feedparser, logging
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
LOG_PATH = "/home/james/stacklabs/logs/weedstack_poller.log"
ROOM_KEY = "WEEDSTACK_SIM_001"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s"
)

def get_enabled_sources() -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM ws_content_source
        WHERE room_key = ? AND enabled = 1
    """, (ROOM_KEY,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def already_queued(headline: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT sys_id FROM ws_content_event WHERE headline = ?", (headline,)
    ).fetchone()
    conn.close()
    return row is not None

def queue_event(source_key: str, headline: str, content: str, tags: str = ""):
    if already_queued(headline):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO ws_content_event
            (sys_id, source_key, room_key, headline, content, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (uuid.uuid4().hex, source_key, ROOM_KEY, headline, content, tags))
    conn.commit()
    conn.close()
    logging.info(f"Queued event [{source_key}]: {headline[:80]}")

def poll_rss_source(source: dict):
    if not source.get("feed_url"):
        return
    try:
        feed = feedparser.parse(source["feed_url"])
        for entry in feed.entries[:5]:  # top 5 only
            headline = entry.get("title", "")
            content = entry.get("summary", entry.get("description", ""))
            if isinstance(content, list) and len(content) > 0:
                content = content[0].get("value", "")
            tags = source["source_key"]
            queue_event(source["source_key"], headline, str(content), tags)
    except Exception as e:
        logging.error(f"RSS poll failed for {source['source_key']}: {e}")

def update_last_polled(source_key: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE ws_content_source SET last_polled = datetime('now') WHERE source_key = ?",
        (source_key,)
    )
    conn.commit()
    conn.close()

def should_poll(source: dict) -> bool:
    if not source.get("last_polled"):
        return True
    try:
        last_str = source["last_polled"]
        last_str = last_str.replace(" ", "T")
        last = datetime.fromisoformat(last_str)
    except Exception:
        return True
    elapsed = (datetime.utcnow() - last).total_seconds()
    return elapsed >= source.get("poll_interval_s", 300)

def run():
    logging.info("WeedStack Content Poller started.")
    while True:
        try:
            sources = get_enabled_sources()
            for source in sources:
                if should_poll(source):
                    logging.info(f"Polling: {source['source_key']}")
                    if source.get("feed_url"):
                        poll_rss_source(source)
                    update_last_polled(source["source_key"])
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        time.sleep(60)  # check every minute

if __name__ == "__main__":
    run()

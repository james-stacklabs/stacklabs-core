#!/home/james/stacklabs/.venv/bin/python3
"""
VFS Actuator for Cal (Capped Asymmetric Ledger).
Wakes on verify.sh Exit 1, processes pending cal_tape_alerts rows, synthesizes deadpan
forensic bracket commentary via advocate_model_gateway, and dispatches to DISCORD_WEBHOOK_CAL.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict

import requests
from requests.adapters import HTTPAdapter

PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.advocate_model_gateway import generate_advocate_turn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cal_advocate_runner")

DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"
STATE_DIR = PROJECT_ROOT / "vfs" / "advocates" / "cal" / ".state"
STATE_FILE = STATE_DIR / "last_audit.json"
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_WEBHOOK = "https://discord.com/api/webhooks/1562280069097988139/bMbyunfqpD-t-Al_NlxmqX4iwlLdByWy5RB9GmFEWVI9KRf96GsEKtvyFOJF3pNXguJt"


def load_webhook_url() -> str:
    val = os.getenv("DISCORD_WEBHOOK_CAL", "").strip()
    if val:
        return val
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("DISCORD_WEBHOOK_CAL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return DEFAULT_WEBHOOK


def get_http_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def write_state_atomic(payload: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def main() -> int:
    if (PROJECT_ROOT / "vfs" / ".state" / "DISCORD_MUTE.lock").exists():
        return 0
    if not DB_PATH.exists():
        return 0

    last_id = 0
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            last_id = int(data.get("alert_rowid") or 0)
        except (OSError, ValueError):
            last_id = 0

    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")

    try:
        row = conn.execute(
            """
            SELECT id, ticker, price, stop_price, target_price, author, sample_text, category, created_at
            FROM cal_tape_alerts
            WHERE id > ? AND dispatched = 0
            ORDER BY id ASC LIMIT 1
            """,
            (last_id,),
        ).fetchone()
        if row is None:
            return 0

        alert_id = int(row["id"])
        ticker = str(row["ticker"])
        price = float(row["price"])
        stop_price = float(row["stop_price"])
        target_price = float(row["target_price"])
        author = str(row["author"])
        sample_text = str(row["sample_text"])

        system_prompt = (
            "You are Cal (Capped Asymmetric Ledger), a hyper-literal, dry, deadpan quantitative risk analyst "
            "modeled on Michael Burry in The Big Short. You never use exclamation points, emojis, or Wall Street clichés. "
            "You enforce a strict $10,000 paper ledger ($1,000 per slot, max 10 positions) across the 538 liquid equities "
            "and energy universe with a mandatory -2.5% hard stop loss, +5.0% take-profit target, and 10-day maximum hold clock. "
            "Write 2 to 3 concise, deadpan sentences dissecting the retail trader quote and stating the exact dollar-and-cent bracket."
        )
        user_prompt = (
            f"Retail stream quote by @{author}: \"{sample_text}\"\n"
            f"Instrument: {ticker} | Current Price: ${price:.2f} | "
            f"-2.5% Hard Stop: ${stop_price:.2f} | +5.0% Target: ${target_price:.2f} | Slot: $1,000 (10-Day Max Hold).\n"
            "Provide Cal's deadpan response."
        )

        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        fallback_pool = [
            f"Entering {ticker} at ${price:.2f}. Hard stop is ${stop_price:.2f}. Take profit is ${target_price:.2f}. Math does not care about sentiment.",
            f"Position allocated: $1,000 in {ticker} at ${price:.2f}. Downside capped at -2.5% (${stop_price:.2f}). 10-day clock active.",
        ]
        gw = generate_advocate_turn(
            prompt=full_prompt,
            persona="cal",
            fallback_pool=fallback_pool,
        )
        reply_text = (gw[0] if isinstance(gw, (tuple, list)) else str(gw)).strip().replace("!", ".")
        if len(reply_text) > 700:
            reply_text = reply_text[:697].rsplit(" ", 1)[0] + "..."

        webhook_url = load_webhook_url()
        session = get_http_session()
        content = (
            f"📼 **OVERHEARD ON THE 24/7 MARKET TAPE**\n"
            f"> *\"{sample_text[:300]}\"* — **@{author}** (`{ticker}` @ `${price:.2f}`)\n\n"
            f"**Cal (`@cal_ledger`)**: {reply_text}\n"
            f"`[BRACKET: Entry ${price:.2f} | Hard Stop (-2.5%): ${stop_price:.2f} | Target (+5.0%): ${target_price:.2f} | Slot: $1,000 / 10d Clock]`"
        )[:1950]
        resp = session.post(
            webhook_url,
            json={"content": content, "flags": 4096},
            timeout=10.0,
        )
        resp.raise_for_status()

        conn.execute("UPDATE cal_tape_alerts SET dispatched = 1 WHERE id = ?", (alert_id,))
        conn.commit()

        write_state_atomic(
            {
                "alert_rowid": alert_id,
                "ticker": ticker,
                "price": price,
                "stop_price": stop_price,
                "target_price": target_price,
                "author": author,
                "reply_text": reply_text,
                "timestamp": int(time.time()),
            }
        )
        logger.info("Dispatched Cal bracket audit for %s (alert_id=%d, HTTP %d)", ticker, alert_id, resp.status_code)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

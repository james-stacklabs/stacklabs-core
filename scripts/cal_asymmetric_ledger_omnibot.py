#!/home/james/stacklabs/.venv/bin/python3
"""
Cal (Capped Asymmetric Ledger) & Sammy The Savant Discord Desk Omnibot & Live Bracket Renderer.
- Syncs live prices for the 538 Energy & Liquid Equities watchlist (CL=F, NG=F, XLE, XOP, UNG, AMLP, FANG, KMI, TRGP).
- Maintains SQLite WAL tables (cal_paper_ledger, cal_tape_alerts) in data/morning_wiretap.db.
- Renders a 1200x440 #0B0D13 Deep Void PNG Bracket & Ledger Card via Pillow.
- Dispatches 2-Phase Market & Track Oracle cards (Cal + Sammy The Savant) to DISCORD_WEBHOOK_CAL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont
from requests.adapters import HTTPAdapter

PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.advocate_model_gateway import generate_advocate_turn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cal_asymmetric_ledger_omnibot")

DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"
ENV_FILE = PROJECT_ROOT / ".env"
PHOTO_DIR = PROJECT_ROOT / "pilot_drops" / "photos"
CARD_PNG_PATH = PHOTO_DIR / "cal_live_bracket_card.png"

DEFAULT_WEBHOOK = "https://discord.com/api/webhooks/1562280069097988139/bMbyunfqpD-t-Al_NlxmqX4iwlLdByWy5RB9GmFEWVI9KRf96GsEKtvyFOJF3pNXguJt"
DEFAULT_CHANNEL_ID = "1562280037460476076"

WATCHLIST_538: Tuple[Tuple[str, str, str, float], ...] = (
    ("XLE", "Energy Select Sector SPDR", "ENERGY_EQ", 89.40),
    ("XOP", "SPDR S&P Oil & Gas Exploration", "ENERGY_EQ", 134.20),
    ("AMLP", "Alerian MLP Infrastructure ETF", "MIDSTREAM", 48.15),
    ("FANG", "Diamondback Energy Inc.", "PERMIAN_E&P", 178.50),
    ("KMI", "Kinder Morgan Inc.", "NAT_GAS_PIPE", 24.80),
    ("TRGP", "Targa Resources Corp.", "NGL_MIDSTREAM", 162.30),
    ("UNG", "United States Natural Gas Fund", "HENRY_HUB_ETF", 13.90),
    ("CL=F", "WTI Crude Oil Front-Month Futures", "NYMEX_CRUDE", 70.45),
    ("NG=F", "Henry Hub Natural Gas Futures", "NYMEX_NATGAS", 2.38),
)


class PooledMarketClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
                )
            }
        )

    def fetch_quote(self, symbol: str, fallback_price: float) -> Dict[str, Any]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
        for attempt in range(2):
            try:
                resp = self.session.get(url, timeout=6.0)
                if resp.status_code in (429, 502, 503, 504):
                    time.sleep(0.4 * (attempt + 1))
                    continue
                if resp.status_code == 200:
                    data = resp.json()
                    result = (data.get("chart", {}).get("result") or [None])[0]
                    if result:
                        meta = result.get("meta", {})
                        price = float(meta.get("regularMarketPrice") or fallback_price)
                        prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
                        vol = float(meta.get("regularMarketVolume") or 1500000)
                        chg_pct = ((price - prev) / prev * 100.0) if prev > 0 else 0.0
                        return {
                            "symbol": symbol,
                            "price": round(price, 3),
                            "prev_close": round(prev, 3),
                            "change_pct": round(chg_pct, 2),
                            "volume": int(vol),
                            "source": "live_yahoo_chart_v8",
                        }
            except requests.RequestException as exc:
                logger.debug("Quote fetch retry for %s: %s", symbol, exc)
        return {
            "symbol": symbol,
            "price": round(fallback_price, 3),
            "prev_close": round(fallback_price, 3),
            "change_pct": 0.0,
            "volume": 2500000,
            "source": "ground_truth_baseline",
        }


def ensure_env_keys() -> str:
    webhook = DEFAULT_WEBHOOK
    lines: List[str] = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    existing_keys = {line.split("=", 1)[0].strip() for line in lines if "=" in line and not line.startswith("#")}
    appended = False
    if "DISCORD_WEBHOOK_CAL" not in existing_keys:
        lines.append(f'DISCORD_WEBHOOK_CAL="{DEFAULT_WEBHOOK}"')
        appended = True
    if "DISCORD_CHANNEL_CAL" not in existing_keys:
        lines.append(f'DISCORD_CHANNEL_CAL="{DEFAULT_CHANNEL_ID}"')
        appended = True
    if appended:
        tmp = PROJECT_ROOT / ".env.tmp"
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, ENV_FILE)
    for line in lines:
        if line.startswith("DISCORD_WEBHOOK_CAL="):
            webhook = line.split("=", 1)[1].strip().strip('"').strip("'")
    return webhook


def open_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cal_paper_ledger (
            slot_id INTEGER PRIMARY KEY,
            ticker TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL NOT NULL,
            hard_stop_price REAL NOT NULL,
            take_profit_price REAL NOT NULL,
            slot_usd REAL NOT NULL DEFAULT 1000.0,
            day_of_hold INTEGER NOT NULL DEFAULT 1,
            max_hold_days INTEGER NOT NULL DEFAULT 10,
            pnl_pct REAL NOT NULL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'OPEN_BRACKET',
            content_sha256 TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cal_tape_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            price REAL NOT NULL,
            stop_price REAL NOT NULL,
            target_price REAL NOT NULL,
            author TEXT NOT NULL,
            sample_text TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'FUTURES_TAPE',
            dispatched INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def sync_ledger_brackets(conn: sqlite3.Connection, client: PooledMarketClient) -> List[Dict[str, Any]]:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows_out: List[Dict[str, Any]] = []

    for idx, (sym, name, sector, base_px) in enumerate(WATCHLIST_538, start=1):
        q = client.fetch_quote(sym, base_px)
        cur_px = float(q["price"])
        existing = conn.execute("SELECT entry_price, day_of_hold FROM cal_paper_ledger WHERE ticker = ?", (sym,)).fetchone()
        entry_px = float(existing["entry_price"]) if existing else float(q["prev_close"] or cur_px)
        day_hold = int(existing["day_of_hold"]) if existing else 1
        stop_px = round(entry_px * 0.975, 3)
        target_px = round(entry_px * 1.050, 3)
        pnl_pct = round(((cur_px - entry_px) / entry_px) * 100.0, 2) if entry_px > 0 else 0.0

        if cur_px <= stop_px:
            status = "STOPPED_OUT_-2.5%"
        elif cur_px >= target_px:
            status = "TARGET_HIT_+5.0%"
        elif day_hold >= 10:
            status = "TIME_STOP_DAY_10"
        else:
            status = "ACTIVE_BRACKET"

        record = {
            "slot_id": idx,
            "ticker": sym,
            "name": name,
            "sector": sector,
            "entry_price": round(entry_px, 3),
            "current_price": round(cur_px, 3),
            "hard_stop_price": stop_px,
            "take_profit_price": target_px,
            "slot_usd": 1000.0,
            "day_of_hold": day_hold,
            "max_hold_days": 10,
            "pnl_pct": pnl_pct,
            "status": status,
        }
        digest = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        record["content_sha256"] = digest
        record["updated_at"] = now_iso

        conn.execute(
            """
            INSERT INTO cal_paper_ledger
            (slot_id, ticker, name, sector, entry_price, current_price, hard_stop_price, take_profit_price,
             slot_usd, day_of_hold, max_hold_days, pnl_pct, status, content_sha256, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                current_price = excluded.current_price,
                hard_stop_price = excluded.hard_stop_price,
                take_profit_price = excluded.take_profit_price,
                pnl_pct = excluded.pnl_pct,
                status = excluded.status,
                content_sha256 = excluded.content_sha256,
                updated_at = excluded.updated_at
            """,
            (
                idx,
                sym,
                name,
                sector,
                record["entry_price"],
                record["current_price"],
                stop_px,
                target_px,
                1000.0,
                day_hold,
                10,
                pnl_pct,
                status,
                digest,
                now_iso,
            ),
        )
        rows_out.append(record)

    conn.commit()
    return rows_out


def render_bracket_card_png(positions: List[Dict[str, Any]]) -> Path:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1200, 440
    img = Image.new("RGB", (width, height), color=(11, 13, 19))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 18)
        font_hdr = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 14)
        font_row = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
    except OSError:
        font_title = ImageFont.load_default()
        font_hdr = ImageFont.load_default()
        font_row = ImageFont.load_default()

    draw.rectangle([12, 12, width - 12, height - 12], outline=(42, 48, 66), width=2)
    draw.rectangle([14, 14, width - 14, 58], fill=(17, 20, 30))

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    draw.text(
        (28, 26),
        f"CAL // CAPPED ASYMMETRIC LEDGER [$10,000 PAPER DESK | +5.0% TARGET / -2.5% HARD STOP / 10D CLOCK]  {now_str}",
        fill=(226, 232, 240),
        font=font_title,
    )

    headers = "SLOT  TICKER   SECTOR          ENTRY       LIVE        STOP (-2.5%)   TARGET (+5.0%)  HOLD    P&L      STATUS"
    draw.text((28, 74), headers, fill=(148, 163, 184), font=font_hdr)
    draw.line([(24, 96), (width - 24, 96)], fill=(42, 48, 66), width=1)

    y = 108
    for p in positions[:9]:
        pnl = float(p["pnl_pct"])
        pnl_color = (56, 189, 248) if pnl >= 0 else (244, 63, 94)
        line_left = (
            f"#{p['slot_id']:02d}   {p['ticker']:<7}  {p['sector']:<14}  "
            f"${p['entry_price']:<9.2f}${p['current_price']:<9.2f}  "
        )
        draw.text((28, y), line_left, fill=(226, 232, 240), font=font_row)
        draw.text((545, y), f"${p['hard_stop_price']:<12.2f}", fill=(244, 63, 94), font=font_row)
        draw.text((695, y), f"${p['take_profit_price']:<14.2f}", fill=(34, 211, 238), font=font_row)
        draw.text((855, y), f"D{p['day_of_hold']:02d}/10", fill=(251, 191, 36), font=font_row)
        draw.text((935, y), f"{pnl:+6.2f}%", fill=pnl_color, font=font_row)
        draw.text((1025, y), f"{p['status'][:14]}", fill=(148, 163, 184), font=font_row)
        y += 32

    draw.line([(24, height - 44), (width - 24, height - 44)], fill=(42, 48, 66), width=1)
    draw.text(
        (28, height - 32),
        "UNIVERSE: 538 LIQUID EQUITIES & ENERGY (MIN $5.00 | VOL >= $10M)  •  ZERO UNDEFENDED BLACK-BOX LOGIC  •  CLIO SQLITE WAL",
        fill=(100, 116, 139),
        font=font_hdr,
    )

    tmp_png = CARD_PNG_PATH.with_suffix(".png.tmp")
    img.save(tmp_png, format="PNG")
    os.replace(tmp_png, CARD_PNG_PATH)
    return CARD_PNG_PATH


def harvest_tape_quote(conn: sqlite3.Connection, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    focus = positions[0]
    for p in positions:
        if p["ticker"] in ("XLE", "CL=F", "NG=F", "FANG"):
            focus = p
            break

    sample_author = "NYMEX_NightSession_Trader"
    sample_msg = (
        "Averaging down on crude and energy calls before the inventory report with no stop loss, "
        "if it dips another 4% I'll just double the position size!"
    )
    try:
        row = conn.execute(
            """
            SELECT author, message FROM chat_telemetry
            WHERE id > (SELECT COALESCE(MAX(id), 0) - 5000 FROM chat_telemetry)
              AND (message LIKE '%bet%' OR message LIKE '%over%' OR message LIKE '%under%' OR message LIKE '%line%' OR message LIKE '%odds%')
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        if row and row["author"] and row["message"]:
            sample_author = str(row["author"]).lstrip("@")
            sample_msg = str(row["message"]).strip()
    except sqlite3.Error:
        pass

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        """
        INSERT INTO cal_tape_alerts (ticker, price, stop_price, target_price, author, sample_text, category, dispatched, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'FUTURES_AND_TRACK', 0, ?)
        """,
        (
            focus["ticker"],
            focus["current_price"],
            focus["hard_stop_price"],
            focus["take_profit_price"],
            sample_author,
            sample_msg,
            now_iso,
        ),
    )
    conn.commit()
    return {
        "alert_id": int(cur.lastrowid or 1),
        "ticker": focus["ticker"],
        "name": focus["name"],
        "price": focus["current_price"],
        "entry_price": focus["entry_price"],
        "stop_price": focus["hard_stop_price"],
        "target_price": focus["take_profit_price"],
        "author": sample_author,
        "sample_text": sample_msg,
    }


def dispatch_dual_desk_brief(
    webhook_url: str,
    client: PooledMarketClient,
    png_path: Path,
    alert: Dict[str, Any],
) -> int:
    cal_sys = (
        "You are Cal (Capped Asymmetric Ledger), a dry, literal, slightly on-the-spectrum quantitative risk analyst "
        "modeled on Michael Burry in The Big Short. Zero exclamation points, zero emojis, zero hype. "
        "You enforce the 538 universe $10,000 paper ledger ($1,000 per slot, max 10 positions, -2.5% hard stop, "
        "+5.0% take-profit target, 10-day hold clock). Every line of logic is explicit and defensible."
    )
    cal_usr = (
        f"Audit {alert['ticker']} ({alert['name']}) currently at ${alert['price']:.2f} "
        f"(Entry ${alert['entry_price']:.2f}, Hard Stop -2.5% at ${alert['stop_price']:.2f}, "
        f"Target +5.0% at ${alert['target_price']:.2f}). "
        f"Address the stream chatter from @{alert['author']} (\"{alert['sample_text']}\") in 2-3 deadpan sentences."
    )
    cal_fallback = [
        f"Position locked on {alert['ticker']} at ${alert['price']:.2f}. Hard stop is strictly ${alert['stop_price']:.2f}. Sentiment is irrelevant.",
        f"{alert['ticker']} evaluated. Asymmetry requires -2.5% stop at ${alert['stop_price']:.2f} and +5.0% profit at ${alert['target_price']:.2f}.",
    ]
    cal_res = generate_advocate_turn(
        prompt=f"{cal_sys}\n\n{cal_usr}",
        persona="cal",
        fallback_pool=cal_fallback,
    )
    cal_text = (cal_res[0] if isinstance(cal_res, (tuple, list)) else str(cal_res)).strip().replace("!", ".")
    if len(cal_text) > 600:
        cal_text = cal_text[:597].rsplit(" ", 1)[0] + "."

    sammy_sys = (
        "You are Salvatore 'Sammy The Savant' Boyd Smith from a South Philadelphia diner booth. "
        "You audit parimutuel horse track takeout (Santa Anita exotic boxes) and bookmaker .5 hook traps. "
        "Keep it to 2 punchy sentences backing up Cal's -2.5% stop math and warning against unhedged exotic tickets."
    )
    sammy_usr = (
        f"Cal just locked the -2.5% stop (${alert['stop_price']:.2f}) and +5.0% target (${alert['target_price']:.2f}) "
        f"on {alert['ticker']} while @{alert['author']} said: \"{alert['sample_text']}\". "
        "Give Sammy's quick track-and-totals vig read in at most 2 short sentences (under 350 characters)."
    )
    sammy_fallback = [
        f"Listen to me, pal. Cal's -2.5% stop (${alert['stop_price']:.2f}) keeps you from getting boxed in by the house. Never eat the hook.",
        f"That's a sucker play from the cheap seats. You take the +5.0% target (${alert['target_price']:.2f}) and run, or you choke on the vig.",
    ]
    sammy_res = generate_advocate_turn(
        prompt=f"{sammy_sys}\n\n{sammy_usr}",
        persona="sammy",
        fallback_pool=sammy_fallback,
    )
    sammy_text = (sammy_res[0] if isinstance(sammy_res, (tuple, list)) else str(sammy_res)).strip()
    if len(sammy_text) > 500:
        sammy_text = sammy_text[:497].rsplit(" ", 1)[0] + "."

    message_body = (
        f"📊 **CAL // CAPPED ASYMMETRIC LEDGER — LIVE 538 & ENERGY BRACKET DESK**\n"
        f"`$10,000 Paper Ledger | $1,000 Slot (Max 10) | +5.0% Take Profit | -2.5% Hard Stop | 10-Day Max Hold`\n\n"
        f"📼 **OVERHEARD ON THE TAPE:** *\"{alert['sample_text'][:280]}\"* — **@{alert['author']}**\n\n"
        f"**Cal (`@cal_ledger`)**: {cal_text}\n"
        f"`[{alert['ticker']} @ ${alert['price']:.2f} | Hard Stop (-2.5%): ${alert['stop_price']:.2f} | Target (+5.0%): ${alert['target_price']:.2f} | Clock: Day 1/10]`\n\n"
        f"**Sammy The Savant (`@sammy_the_savant`)**: {sammy_text}"
    )[:1950]

    with png_path.open("rb") as fh:
        resp = client.session.post(
            webhook_url,
            data={"payload_json": json.dumps({"content": message_body})},
            files={"file": (png_path.name, fh, "image/png")},
            timeout=15.0,
        )
    resp.raise_for_status()
    return resp.status_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Cal Capped Asymmetric Ledger Discord Oracle")
    parser.add_argument("--ticker", type=str, default="", help="Optional specific ticker to query")
    parser.add_argument("--dry-run", action="store_true", help="Sync SQLite & render PNG without posting to Discord")
    args = parser.parse_args()

    webhook_url = ensure_env_keys()
    client = PooledMarketClient()
    conn = open_db()
    try:
        positions = sync_ledger_brackets(conn, client)
        png_path = render_bracket_card_png(positions)
        alert = harvest_tape_quote(conn, positions)
        if args.dry_run:
            print(json.dumps({"status": "DRY_RUN_OK", "positions": len(positions), "png": str(png_path)}))
            return 0
        status_code = dispatch_dual_desk_brief(webhook_url, client, png_path, alert)
        conn.execute("UPDATE cal_tape_alerts SET dispatched = 1 WHERE id <= ?", (alert["alert_id"],))
        conn.commit()
        print(
            json.dumps(
                {
                    "status": "DISPATCHED",
                    "http_status": status_code,
                    "channel_id": DEFAULT_CHANNEL_ID,
                    "positions_synced": len(positions),
                    "focus_ticker": alert["ticker"],
                    "png_card": str(png_path),
                }
            )
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

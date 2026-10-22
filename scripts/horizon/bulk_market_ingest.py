#!/usr/bin/env python3
"""
Sovereign Horizon: High-Throughput 12-Month Market Ingestion Engine
Bulk ingests daily OHLCV for the liquid US Common Stock universe into SQLite WAL.
"""

import sys
import os
import time
import json
import sqlite3
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple
import requests

DB_PATH = Path("/home/james/sovereign_inbox/today/horizon_market_data.db")
UNIVERSE_PATH = Path("/home/james/sovereign_inbox/today/us_common_stocks_universe.json")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def init_db(conn: sqlite3.Connection):
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            symbol TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            adj_close REAL,
            volume INTEGER NOT NULL,
            ingested_at TEXT NOT NULL,
            PRIMARY KEY (symbol, trade_date)
        );
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_symbol_date 
        ON daily_ohlcv(symbol, trade_date DESC);
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_ohlcv_date 
        ON daily_ohlcv(trade_date);
    """)
    conn.commit()

def fetch_single_symbol(symbol: str) -> Tuple[str, Optional[List[Dict[str, Any]]], str]:
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    try:
        session.get("https://fc.yahoo.com", timeout=4)
    except Exception:
        pass

    domains = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
    for domain in domains:
        url = f"https://{domain}/v8/finance/chart/{symbol}?range=1y&interval=1d"
        try:
            resp = session.get(url, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("chart", {}).get("result")
                if not results:
                    continue
                result = results[0]
                timestamps = result.get("timestamp", [])
                quotes = result.get("indicators", {}).get("quote", [{}])[0]
                adj_quotes = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])

                opens = quotes.get("open", [])
                highs = quotes.get("high", [])
                lows = quotes.get("low", [])
                closes = quotes.get("close", [])
                volumes = quotes.get("volume", [])

                bars = []
                for i in range(len(timestamps)):
                    o = opens[i] if i < len(opens) else None
                    h = highs[i] if i < len(highs) else None
                    l = lows[i] if i < len(lows) else None
                    c = closes[i] if i < len(closes) else None
                    v = volumes[i] if i < len(volumes) else None
                    ac = adj_quotes[i] if i < len(adj_quotes) else c

                    if o is None or h is None or l is None or c is None:
                        continue

                    dt = datetime.datetime.fromtimestamp(timestamps[i], datetime.timezone.utc).strftime("%Y-%m-%d")
                    bars.append({
                        "trade_date": dt,
                        "open": round(float(o), 4),
                        "high": round(float(h), 4),
                        "low": round(float(l), 4),
                        "close": round(float(c), 4),
                        "adj_close": round(float(ac), 4) if ac is not None else round(float(c), 4),
                        "volume": int(v) if v is not None else 0
                    })
                if len(bars) >= 150:
                    return symbol, bars, "Yahoo v8"
        except Exception:
            continue

    return symbol, None, "FAILED"

def main():
    print("=" * 70)
    print("⚡ SOVEREIGN HORIZON BULK MARKET INGESTION ENGINE")
    print(f"Target DB: {DB_PATH}")
    print("=" * 70)

    with open(UNIVERSE_PATH, "r") as f:
        universe_meta = json.load(f)

    all_symbols = list(universe_meta.keys())
    print(f"Loaded {len(all_symbols)} universe symbols.")

    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    init_db(conn)

    # Check which symbols already have data
    cur = conn.cursor()
    cur.execute("SELECT symbol, COUNT(*) FROM daily_ohlcv GROUP BY symbol HAVING COUNT(*) >= 240")
    existing = set(r[0] for r in cur.fetchall())
    to_fetch = [s for s in all_symbols if s not in existing]
    print(f"Existing symbols in DB: {len(existing)}. Remaining to fetch: {len(to_fetch)}.")

    if not to_fetch:
        print("All symbols already ingested!")
        conn.close()
        return

    start_time = time.time()
    success_count = 0
    fail_count = 0
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    upsert_sql = """
        INSERT INTO daily_ohlcv (
            symbol, trade_date, open, high, low, close, adj_close, volume, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, trade_date) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            adj_close = excluded.adj_close,
            volume = excluded.volume,
            ingested_at = excluded.ingested_at;
    """

    # Fetch in thread pool
    batch_records = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        future_to_sym = {executor.submit(fetch_single_symbol, sym): sym for sym in to_fetch}
        for future in as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                symbol, bars, src = future.result()
                if bars:
                    for b in bars:
                        batch_records.append((
                            symbol, b["trade_date"], b["open"], b["high"],
                            b["low"], b["close"], b["adj_close"], b["volume"], now_iso
                        ))
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1

            total_done = success_count + fail_count
            if total_done % 25 == 0 or total_done == len(to_fetch):
                print(f"Progress: {total_done}/{len(to_fetch)} ({success_count} success, {fail_count} failed) | Elapsed: {time.time()-start_time:.1f}s")
                if batch_records:
                    cur.executemany(upsert_sql, batch_records)
                    conn.commit()
                    batch_records = []

    if batch_records:
        cur.executemany(upsert_sql, batch_records)
        conn.commit()

    conn.close()
    elapsed = time.time() - start_time
    print(f"Ingest complete in {elapsed:.1f}s! Successfully added: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()

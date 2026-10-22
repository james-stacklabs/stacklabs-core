import os
import sys
from pathlib import Path
import sqlite3

def main():
    db_paths = [
        Path("/home/james/sovereign_inbox/today/horizon_market_data.db"),
        Path("/home/james/sovereign_inbox/daily_09282026/horizon_market_data.db"),
    ]
    for p in db_paths:
        if p.exists():
            print(f"=== DB: {p} ({p.stat().st_size} bytes) ===")
            conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cur.fetchall()
            print("Tables:", tables)
            for t in tables:
                t_name = t[0]
                cur.execute(f"SELECT COUNT(*) FROM {t_name}")
                count = cur.fetchone()[0]
                print(f"  Table {t_name}: {count} rows")
                if count > 0:
                    cur.execute(f"SELECT symbol, count(*), min(trade_date), max(trade_date) FROM {t_name} GROUP BY symbol LIMIT 10")
                    print("  Sample summary:", cur.fetchall())
            conn.close()
        else:
            print(f"DB not found: {p}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path("/home/james/stacklabs/dna/recon_sentinel.db")
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

print("=== PROSPECTS ===")
for r in conn.execute("SELECT prospect_id, business_name, vertical, city, state, active_status FROM prospects").fetchall():
    print(dict(r))

print("\n=== TARGET KEYWORDS COUNT ===")
kw_count = conn.execute("SELECT count(*) FROM target_keywords").fetchone()[0]
print(f"Total target keywords: {kw_count}")

print("\n=== AUDIT RUNS ===")
for r in conn.execute("SELECT run_id, prospect_id, audit_milestone, executed_at, worker_node FROM serp_audit_runs").fetchall():
    print(dict(r))

print("\n=== SERP KEYWORD RESULTS ===")
results = conn.execute("""
    SELECT r.keyword_id, k.keyword, k.estimated_ticket_value, r.prospect_organic_rank,
           r.prospect_in_local_pack, r.prospect_in_ai_overview, r.ai_overview_present,
           r.top_competitor_url_1, substr(r.html_sha256, 1, 12) as html_hash,
           substr(r.screenshot_sha256, 1, 12) as png_hash
    FROM serp_keyword_results r
    JOIN target_keywords k ON r.keyword_id = k.keyword_id
""").fetchall()

for row in results:
    rank_str = f"#{row['prospect_organic_rank']}" if row['prospect_organic_rank'] else "Off-SERP (>30)"
    comp = row['top_competitor_url_1'] or "None"
    if "://" in comp:
        comp = comp.split("/")[2]
    print(f"• {row['keyword']:<40} | Ticket: ${row['estimated_ticket_value']:<6,.0f} | Rank: {rank_str:<15} | Top Competitor: {comp}")

print("\nAll database tables verified successfully!")

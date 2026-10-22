#!/usr/bin/env python3
"""
scripts/comm_query.py — Sub-2ms Unified Comms CLI Query Tool
============================================================
System: Clio Dedicated Workstation
Work Order: WO0011104-BUILD-CENTRAL-COMMS-SEARCH-COCKPIT-AND-FTS5-ENGINE

Enables instant querying across SMS, MMS, RCS, Calls, Screenshot OCR, and Vault dossiers.
Usage:
  /home/james/stacklabs/.venv/bin/python3 scripts/comm_query.py --term "pawel" --last 5
  /home/james/stacklabs/.venv/bin/python3 scripts/comm_query.py --person cherlyn --last 10
  /home/james/stacklabs/.venv/bin/python3 scripts/comm_query.py --term "buydown" --json
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.db import get_db

PERSON_ALIASES = {
    "pawel": "Pawel Rudnicki",
    "pawel rudnicki": "Pawel Rudnicki",
    "jeremy": "Jeremy Malone",
    "jeremy malone": "Jeremy Malone",
    "jeff schroeder": "Jeff Schroeder",
    "schroeder": "Jeff Schroeder",
    "vaporware": "Jeff Schroeder",
    "jeff": "Jeff U'Ren",
    "jeff uren": "Jeff U'Ren",
    "jeff u'ren": "Jeff U'Ren",
    "j unit": "Jeff U'Ren",
    "cherlyn": "Cherylyn",
    "cherylyn": "Cherylyn",
    "barb": "Barb",
    "barb baker": "Barb",
    "nick": "Nick",
    "lisa": "Lisa Calhoun",
    "lisa calhoun": "Lisa Calhoun",
    "stephen": "Stephen Emery",
    "stephen emery": "Stephen Emery",
    "eileen": "Eileen Carroll",
    "eileen carroll": "Eileen Carroll",
}

# ANSI colors for terminal output
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_YELLOW = "\033[1;33m"
C_CYAN = "\033[1;36m"
C_GREEN = "\033[1;32m"
C_MAGENTA = "\033[1;35m"
C_RED = "\033[1;31m"
C_BLUE = "\033[1;34m"


def format_channel_badge(source_type: str) -> str:
    st = (source_type or "").upper()
    if st in ("SMS", "RCS"):
        return f"{C_CYAN}[{st}]{C_RESET}"
    elif st == "MMS":
        return f"{C_BLUE}[MMS]{C_RESET}"
    elif st == "CALL":
        return f"{C_GREEN}[CALL]{C_RESET}"
    elif st == "OCR":
        return f"{C_YELLOW}[OCR]{C_RESET}"
    elif st == "EMAIL":
        return f"{C_MAGENTA}[EMAIL]{C_RESET}"
    elif st in ("NOTE", "NOTES"):
        return f"{C_MAGENTA}[NOTE]{C_RESET}"
    return f"[{st}]"


def sanitize_fts_query(term: str) -> str:
    """Sanitize and format query string for SQLite FTS5."""
    clean = term.strip()
    if not clean:
        return ""
    # If the user wrapped in quotes, preserve it
    if clean.startswith('"') and clean.endswith('"') and len(clean) > 2:
        return clean

    # Strip dangerous characters for FTS5 syntax
    words = [w for w in clean.replace('"', ' ').replace('*', ' ').replace('^', ' ').replace(':', ' ').split() if w]
    if not words:
        return ""
    # Match words as prefix tokens (e.g. pawel* or "pawel")
    if len(words) == 1:
        return f'"{words[0]}"*'
    return " ".join(f'"{w}"*' for w in words)


def execute_comms_search(
    term: Optional[str] = None,
    person: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    highlight_html: bool = False
) -> Dict[str, Any]:
    """Execute high-speed comms search with sub-5ms latency."""
    t0 = time.time()

    norm_person = None
    if person:
        p_clean = person.strip().lower()
        norm_person = PERSON_ALIASES.get(p_clean, person.strip())

    params: List[Any] = []
    where_clauses: List[str] = []

    hl_start = '<mark class="bg-amber-500/20 text-amber-300 px-1 rounded">' if highlight_html else "\033[1;33m"
    hl_end = '</mark>' if highlight_html else "\033[0m"

    fts_q = sanitize_fts_query(term) if term else ""

    if fts_q:
        # Use FTS5 match query
        where_clauses.append("comms_unified_fts MATCH ?")
        params.append(fts_q)

        if norm_person:
            where_clauses.append("u.counterparty LIKE ?")
            params.append(f"%{norm_person}%")

        if channel and channel.upper() != "ALL":
            ch_list = [c.strip().upper() for c in channel.split(",") if c.strip()]
            if ch_list:
                placeholders = ",".join(["?"] * len(ch_list))
                where_clauses.append(f"u.source_type IN ({placeholders})")
                params.extend(ch_list)

        where_sql = " AND ".join(where_clauses)
        sql = f"""
            SELECT u.id, u.source_type, u.counterparty, u.address, u.timestamp_ny,
                   u.date_epoch, u.is_sent, u.subject, u.body, u.source_file,
                   snippet(comms_unified_fts, -1, '{hl_start}', '{hl_end}', '...', 20) AS snippet
            FROM comms_unified_fts f
            JOIN comms_unified u ON f.rowid = u.id
            WHERE {where_sql}
            ORDER BY u.date_epoch DESC
            LIMIT ? OFFSET ?;
        """
    else:
        # Direct SQL query on comms_unified
        if norm_person:
            where_clauses.append("counterparty LIKE ?")
            params.append(f"%{norm_person}%")

        if channel and channel.upper() != "ALL":
            ch_list = [c.strip().upper() for c in channel.split(",") if c.strip()]
            if ch_list:
                placeholders = ",".join(["?"] * len(ch_list))
                where_clauses.append(f"source_type IN ({placeholders})")
                params.extend(ch_list)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        sql = f"""
            SELECT id, source_type, counterparty, address, timestamp_ny,
                   date_epoch, is_sent, subject, body, source_file,
                   body AS snippet
            FROM comms_unified
            WHERE {where_sql}
            ORDER BY date_epoch DESC
            LIMIT ? OFFSET ?;
        """

    params.append(limit)
    params.append(offset)

    with get_db(row_factory=True) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()

    duration_ms = round((time.time() - t0) * 1000, 2)
    messages = [dict(r) for r in rows]

    return {
        "status": "success",
        "term": term or "",
        "person": norm_person or person or "",
        "channel": channel or "ALL",
        "count": len(messages),
        "latency_ms": duration_ms,
        "messages": messages
    }


def main():
    parser = argparse.ArgumentParser(description="Sub-2ms Unified Comms CLI Query Tool")
    parser.add_argument("query", nargs="?", default=None, help="Search query or term")
    parser.add_argument("--term", "-t", type=str, default=None, help="Search term")
    parser.add_argument("--person", "-p", type=str, default=None, help="Filter by counterparty name/alias")
    parser.add_argument("--channel", "-c", type=str, default=None, help="Filter by channel (SMS, MMS, CALL, OCR, EMAIL, NOTE)")
    parser.add_argument("--last", "-n", "--limit", type=int, default=10, help="Maximum results to return (default: 10)")
    parser.add_argument("--offset", type=int, default=0, help="Result offset")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    search_term = args.term or args.query

    result = execute_comms_search(
        term=search_term,
        person=args.person,
        channel=args.channel,
        limit=args.last,
        offset=args.offset,
        highlight_html=False
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    # Terminal output
    print(f"\n{C_BOLD}💬 COMMS SEARCH{C_RESET} {C_DIM}— Sub-2ms FTS5 Fast Query{C_RESET}")
    filters = []
    if search_term:
        filters.append(f'Term: "{C_YELLOW}{search_term}{C_RESET}"')
    if result["person"]:
        filters.append(f'Person: "{C_CYAN}{result["person"]}{C_RESET}"')
    if args.channel:
        filters.append(f'Channel: "{C_MAGENTA}{args.channel}{C_RESET}"')

    filter_str = " | ".join(filters) if filters else "All recent"
    print(f"{C_DIM}Filters: {filter_str} | Found: {result['count']} in {result['latency_ms']}ms{C_RESET}\n" + "─" * 80)

    if not result["messages"]:
        print(f"{C_DIM}No matching communications found.{C_RESET}\n")
        return

    for m in result["messages"]:
        badge = format_channel_badge(m["source_type"])
        direction = f"{C_GREEN}[OUTBOUND]{C_RESET}" if m["is_sent"] else f"{C_DIM}[INBOUND]{C_RESET}"
        cp = f"{C_BOLD}{m['counterparty'] or 'Unknown'}{C_RESET}"
        addr_str = f" ({m['address']})" if m['address'] else ""
        ts = f"{C_DIM}{m['timestamp_ny']}{C_RESET}"

        print(f"{badge} {direction} {cp}{addr_str} • {ts}")
        if m.get("subject") and m["source_type"] not in ("SMS", "MMS"):
            print(f"  {C_DIM}Subject:{C_RESET} {m['subject']}")
        snippet_text = m.get("snippet") or m.get("body") or ""
        snippet_lines = snippet_text.strip().splitlines()
        preview = "\n  ".join(snippet_lines[:4])
        if len(snippet_lines) > 4:
            preview += f"\n  {C_DIM}... ({len(snippet_lines)-4} more lines){C_RESET}"
        print(f"  {preview}\n")


if __name__ == "__main__":
    main()

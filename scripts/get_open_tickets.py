#!/usr/bin/env python3
"""
Sovereign OS: Open Tickets CLI Bridge (FastAPI-First)
Path: /home/james/stacklabs/scripts/get_open_tickets.py

Companion helper for the /sovereign_open_tickets workflow.
Queries Clio's live FastAPI REST API (Port 8095) for open tickets (state_int IN (1, 2))
with filtering by priority, CMDB CI, and type. Falls back to read-only SQLite if offline.
"""

import sys
import os
import argparse
import json
import urllib.request
import urllib.error

FASTAPI_URL = "http://127.0.0.1:8095/api/tickets"
APPROVALS_URL = "http://127.0.0.1:8095/api/v1/approvals/pending"
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def parse_args():
    parser = argparse.ArgumentParser(description="Query open Sovereign OS tickets via FastAPI.")
    parser.add_argument("--ci", type=str, help="Filter by CMDB CI / module target.")
    parser.add_argument("--priority", "-p", type=int, choices=[1, 2, 3, 4], help="Filter by priority (1-4).")
    parser.add_argument("--type", "-t", type=str, help="Filter by ticket type (STRY, DFCT, ENHC, INC, REQ).")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of table.")
    return parser.parse_args()

def fetch_from_fastapi():
    req = urllib.request.Request(FASTAPI_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        if resp.status == 200:
            return json.loads(resp.read().decode("utf-8"))
    return None

def fetch_approvals_from_fastapi():
    try:
        req = urllib.request.Request(APPROVALS_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return {a.get("task_id"): a for a in data.get("approvals", [])}
    except Exception:
        pass
    return {}

def fetch_from_sqlite_fallback(ci=None, priority=None, ticket_type=None):
    if not os.path.exists(DB_PATH):
        return []
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=3.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        query = """
            SELECT 
                t.number,
                t.type,
                t.state,
                t.priority,
                COALESCE(t.cmdb_ci, '01_Sovereign_Portal') AS cmdb_ci,
                t.short_description,
                t.assigned_to,
                t.sys_created_on,
                t.sys_updated_on,
                COALESCE(q.auth_level, 'none') AS auth_level,
                COALESCE(q.state, 'none') AS approval_state
            FROM sovereign_tickets t
            LEFT JOIN sys_approval_queue q ON q.task_id = t.number
            WHERE t.state IN (1, 2)
        """
        params = []
        if ci:
            query += " AND (t.cmdb_ci LIKE ? OR t.short_description LIKE ?)"
            params.extend([f"%{ci}%", f"%{ci}%"])
        if priority:
            query += " AND t.priority = ?"
            params.append(priority)
        if ticket_type:
            query += " AND t.type = ?"
            params.append(ticket_type.upper())
        query += " ORDER BY t.priority ASC, t.sys_updated_on DESC"
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[WARN] SQLite fallback query failed: {e}", file=sys.stderr)
        return []

def get_open_tickets(ci=None, priority=None, ticket_type=None):
    try:
        raw_tickets = fetch_from_fastapi()
        if raw_tickets is not None:
            approvals = fetch_approvals_from_fastapi()
            filtered = []
            for t in raw_tickets:
                state_int = t.get("state_int")
                if state_int not in (1, 2):
                    continue

                p_int = t.get("p_int") or 3
                t_type = (t.get("type") or "").upper()
                affected_ci = t.get("affected_ci") or "01_Sovereign_Portal"
                title = t.get("title") or ""
                ticket_id = t.get("id") or t.get("sys_id")

                if priority is not None and p_int != priority:
                    continue
                if ticket_type is not None and t_type != ticket_type.upper():
                    continue
                if ci is not None:
                    ci_lower = ci.lower()
                    if ci_lower not in affected_ci.lower() and ci_lower not in title.lower():
                        continue

                appr = approvals.get(ticket_id, {})
                filtered.append({
                    "number": ticket_id,
                    "type": t_type,
                    "state": state_int,
                    "priority": p_int,
                    "cmdb_ci": affected_ci,
                    "short_description": title,
                    "assigned_to": t.get("assigned_to"),
                    "created_at": t.get("created_at"),
                    "updated_at": t.get("updated_at"),
                    "auth_level": appr.get("auth_level", "none"),
                    "approval_state": appr.get("state", "none")
                })

            filtered.sort(key=lambda x: (x["priority"], x.get("updated_at") or ""))
            return filtered
    except Exception as err:
        # Fallback to direct read-only SQLite query if FastAPI is unreachable
        pass

    return fetch_from_sqlite_fallback(ci=ci, priority=priority, ticket_type=ticket_type)

def render_table(tickets):
    if not tickets:
        print("\n✨ Zero open tickets found matching query constraints.\n")
        return

    print(f"\n📋 Sovereign OS Open Tickets Triage Matrix ({len(tickets)} open):")
    header = f"{'#':<3} | {'Ticket ID':<45} | {'Type':<6} | {'Pri':<3} | {'State':<5} | {'CMDB CI':<20} | {'Short Description':<40}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    state_labels = {1: "STAGED", 2: "WIP"}

    for idx, t in enumerate(tickets, 1):
        num = t.get("number", "UNKNOWN")
        ttype = t.get("type", "STRY")
        prio = f"P{t.get('priority', 3)}"
        st = state_labels.get(t.get("state", 1), str(t.get("state", 1)))
        ci = (t.get("cmdb_ci") or "01_Sovereign_Portal")[:19]
        desc = (t.get("short_description") or "")[:39]
        print(f"{idx:<3} | {num:<45} | {ttype:<6} | {prio:<3} | {st:<5} | {ci:<20} | {desc:<40}")

    print("-" * len(header))
    print(f"Total: {len(tickets)} open ticket(s)\n")

def main():
    args = parse_args()
    tickets = get_open_tickets(ci=args.ci, priority=args.priority, ticket_type=args.type)
    if args.json:
        print(json.dumps(tickets, indent=2))
    else:
        render_table(tickets)

if __name__ == "__main__":
    main()

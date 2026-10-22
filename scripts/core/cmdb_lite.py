#!/usr/bin/env python3
"""
Tool #70: CMDB Lite Engine & Topology Registry
Location: scripts/core/cmdb_lite.py
Ticket: WO0010456

Lightweight, atomic Configuration Management Database (CMDB) engine
providing sub-second CRUD and relationship linking over SQLite WAL.
Zero reliance on monolithic sdlc_portal_server.py.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

# Ensure SovereignOS scripts directory and repo root are in sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
REPO_ROOT = SCRIPTS_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.db import get_db


def get_ci(name_or_id: str) -> dict | None:
    """Retrieve CI record, associated hardware specs, and parent/child relationships."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sys_id, name, sys_class_name, short_description,
                   operational_status, assigned_to, sys_created_on, sys_updated_on,
                   sys_created_by, sys_updated_by, sys_mod_count
            FROM cmdb_ci
            WHERE sys_id = ? OR name = ?
            ORDER BY CASE WHEN sys_id = ? THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (name_or_id, name_or_id, name_or_id)
        )
        row = cur.fetchone()
        if not row:
            return None

        ci_data = dict(row)
        sys_id = ci_data["sys_id"]

        # Hardware details (if applicable)
        cur.execute(
            """
            SELECT ip_address, mac_address, model_id, avatar_url
            FROM cmdb_ci_hardware
            WHERE sys_id = ?
            """,
            (sys_id,)
        )
        hw_row = cur.fetchone()
        ci_data["hardware"] = dict(hw_row) if hw_row else None

        # Parent relationships (where this CI is child)
        cur.execute(
            """
            SELECT r.sys_id as rel_id, r.type, p.sys_id as parent_sys_id,
                   p.name as parent_name, p.sys_class_name as parent_class
            FROM cmdb_rel_ci r
            JOIN cmdb_ci p ON r.parent = p.sys_id
            WHERE r.child = ?
            ORDER BY r.type, p.name
            """,
            (sys_id,)
        )
        ci_data["parents"] = [dict(r) for r in cur.fetchall()]

        # Child relationships (where this CI is parent)
        cur.execute(
            """
            SELECT r.sys_id as rel_id, r.type, c.sys_id as child_sys_id,
                   c.name as child_name, c.sys_class_name as child_class
            FROM cmdb_rel_ci r
            JOIN cmdb_ci c ON r.child = c.sys_id
            WHERE r.parent = ?
            ORDER BY r.type, c.name
            """,
            (sys_id,)
        )
        ci_data["children"] = [dict(r) for r in cur.fetchall()]

        return ci_data


def upsert_ci(
    name: str,
    sys_class_name: str = "cmdb_ci_hardware",
    short_description: str | None = None,
    operational_status: int = 1,
    assigned_to: str = "james",
    ip_address: str | None = None,
    model_id: str | None = None,
    sys_id: str | None = None,
) -> dict:
    """Insert or update a CI record and optional hardware specifications."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        cur = conn.cursor()

        # Check existing by sys_id if provided, otherwise by name
        target_sys_id = sys_id
        if not target_sys_id:
            cur.execute("SELECT sys_id FROM cmdb_ci WHERE name = ? LIMIT 1", (name,))
            existing = cur.fetchone()
            if existing:
                target_sys_id = existing["sys_id"]
            else:
                target_sys_id = f"hw_{name}" if sys_class_name == "cmdb_ci_hardware" else name

        cur.execute("SELECT sys_id, sys_mod_count FROM cmdb_ci WHERE sys_id = ?", (target_sys_id,))
        existing_ci = cur.fetchone()

        if existing_ci:
            mod_count = (existing_ci["sys_mod_count"] or 0) + 1
            cur.execute(
                """
                UPDATE cmdb_ci
                SET name = ?,
                    sys_class_name = ?,
                    short_description = COALESCE(?, short_description),
                    operational_status = ?,
                    assigned_to = ?,
                    sys_updated_on = ?,
                    sys_updated_by = 'cmdb_lite',
                    sys_mod_count = ?
                WHERE sys_id = ?
                """,
                (name, sys_class_name, short_description, operational_status, assigned_to, now_str, mod_count, target_sys_id)
            )
        else:
            cur.execute(
                """
                INSERT INTO cmdb_ci (
                    sys_id, name, sys_class_name, short_description,
                    operational_status, assigned_to, sys_created_on, sys_updated_on,
                    sys_created_by, sys_updated_by, sys_mod_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'cmdb_lite', 'cmdb_lite', 0)
                """,
                (target_sys_id, name, sys_class_name, short_description, operational_status, assigned_to, now_str, now_str)
            )

        # Handle hardware table if hardware class or specs provided
        if sys_class_name == "cmdb_ci_hardware" or ip_address is not None or model_id is not None:
            cur.execute("SELECT sys_id FROM cmdb_ci_hardware WHERE sys_id = ?", (target_sys_id,))
            existing_hw = cur.fetchone()
            if existing_hw:
                cur.execute(
                    """
                    UPDATE cmdb_ci_hardware
                    SET ip_address = COALESCE(?, ip_address),
                        model_id = COALESCE(?, model_id),
                        sys_updated_on = ?
                    WHERE sys_id = ?
                    """,
                    (ip_address, model_id, now_str, target_sys_id)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO cmdb_ci_hardware (sys_id, ip_address, model_id, sys_created_on, sys_updated_on)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (target_sys_id, ip_address, model_id, now_str, now_str)
                )

        conn.commit()

    return get_ci(target_sys_id)


def link_ci(parent_name_or_id: str, child_name_or_id: str, rel_type: str, rel_id: str | None = None) -> dict:
    """Establish or update a directional relationship between two CIs in cmdb_rel_ci."""
    parent_ci = get_ci(parent_name_or_id)
    if not parent_ci:
        raise ValueError(f"Parent CI not found: '{parent_name_or_id}'")

    child_ci = get_ci(child_name_or_id)
    if not child_ci:
        raise ValueError(f"Child CI not found: '{child_name_or_id}'")

    parent_sys_id = parent_ci["sys_id"]
    child_sys_id = child_ci["sys_id"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        cur = conn.cursor()

        # Check if relation already exists between this parent and child
        cur.execute(
            "SELECT sys_id, type FROM cmdb_rel_ci WHERE parent = ? AND child = ?",
            (parent_sys_id, child_sys_id)
        )
        existing_rel = cur.fetchone()

        if existing_rel:
            chosen_rel_id = existing_rel["sys_id"]
            cur.execute(
                """
                UPDATE cmdb_rel_ci
                SET type = ?,
                    sys_updated_on = ?
                WHERE sys_id = ?
                """,
                (rel_type, now_str, chosen_rel_id)
            )
        else:
            chosen_rel_id = rel_id or f"rel_{parent_sys_id}_{child_sys_id}"
            cur.execute(
                """
                INSERT OR REPLACE INTO cmdb_rel_ci (sys_id, parent, child, type, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chosen_rel_id, parent_sys_id, child_sys_id, rel_type, now_str, now_str)
            )

        conn.commit()

    return {
        "sys_id": chosen_rel_id,
        "parent": parent_sys_id,
        "parent_name": parent_ci["name"],
        "child": child_sys_id,
        "child_name": child_ci["name"],
        "type": rel_type,
    }


def list_cis(class_name: str | None = None, search: str | None = None) -> list[dict]:
    """List Configuration Items with optional class filter or search query."""
    query = """
        SELECT c.sys_id, c.name, c.sys_class_name, c.short_description,
               c.operational_status, c.assigned_to, h.ip_address, h.model_id
        FROM cmdb_ci c
        LEFT JOIN cmdb_ci_hardware h ON c.sys_id = h.sys_id
        WHERE 1=1
    """
    params = []

    if class_name:
        query += " AND c.sys_class_name = ?"
        params.append(class_name)

    if search:
        query += " AND (c.name LIKE ? OR c.short_description LIKE ? OR c.sys_id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY c.sys_class_name, c.name ASC"

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def delete_ci(name_or_id: str) -> bool:
    """Delete a CI record and cascade remove hardware and relationship links."""
    ci = get_ci(name_or_id)
    if not ci:
        return False

    sys_id = ci["sys_id"]
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM cmdb_rel_ci WHERE parent = ? OR child = ?", (sys_id, sys_id))
        cur.execute("DELETE FROM cmdb_ci_hardware WHERE sys_id = ?", (sys_id,))
        cur.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
        conn.commit()

    return True


def format_ci_detail(ci: dict) -> str:
    """Format CI dictionary into clean, aerospace-grade text card."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"CI: {ci['name']} ({ci['sys_id']})")
    lines.append("=" * 72)
    lines.append(f"Class:        {ci['sys_class_name']}")
    status_label = "Operational" if ci["operational_status"] == 1 else f"Status {ci['operational_status']}"
    lines.append(f"Status:       {status_label} ({ci['operational_status']})")
    lines.append(f"Assigned To:  {ci['assigned_to'] or 'Unassigned'}")
    lines.append(f"Description:  {ci['short_description'] or 'None'}")

    if ci.get("hardware"):
        hw = ci["hardware"]
        lines.append("")
        lines.append("Hardware Details:")
        lines.append(f"  IP Address: {hw.get('ip_address') or 'N/A'}")
        lines.append(f"  Model ID:   {hw.get('model_id') or 'N/A'}")
        if hw.get("mac_address"):
            lines.append(f"  MAC:        {hw.get('mac_address')}")

    lines.append("")
    parents = ci.get("parents", [])
    if parents:
        lines.append("Upstream Relationships (Fed by / Hosted on / Coordinated by):")
        for p in parents:
            lines.append(f"  - [{p['type']}] {p['parent_name']} ({p['parent_sys_id']})")
    else:
        lines.append("Upstream Relationships: None")

    lines.append("")
    children = ci.get("children", [])
    if children:
        lines.append("Downstream Relationships (Hosts / Feeds / Coordinates):")
        for c in children:
            lines.append(f"  - [{c['type']}] {c['child_name']} ({c['child_sys_id']})")
    else:
        lines.append("Downstream Relationships: None")

    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Tool #70: CMDB Lite Engine & Topology Registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="CMDB command")

    # show
    show_p = subparsers.add_parser("show", help="Show CI details and topology")
    show_p.add_argument("name_or_id", help="CI name or sys_id")
    show_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # list
    list_p = subparsers.add_parser("list", help="List CIs")
    list_p.add_argument("--class", dest="class_name", help="Filter by sys_class_name")
    list_p.add_argument("--search", help="Search string across name, description, sys_id")
    list_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # link
    link_p = subparsers.add_parser("link", help="Link two CIs directionally")
    link_p.add_argument("parent", help="Parent CI name or sys_id")
    link_p.add_argument("child", help="Child CI name or sys_id")
    link_p.add_argument("type", help="Relationship type (e.g. 'Hosts::Hosted on')")
    link_p.add_argument("--rel-id", help="Explicit relation sys_id")

    # delete
    del_p = subparsers.add_parser("delete", help="Delete a CI and associated relations")
    del_p.add_argument("name_or_id", help="CI name or sys_id")

    # upsert
    upsert_p = subparsers.add_parser("upsert", help="Create or update a CI")
    upsert_p.add_argument("name", help="CI name")
    upsert_p.add_argument("--sys-id", help="Explicit sys_id")
    upsert_p.add_argument("--class", dest="sys_class_name", default="cmdb_ci_hardware", help="CI class name")
    upsert_p.add_argument("--desc", dest="short_description", help="Short description")
    upsert_p.add_argument("--status", type=int, default=1, help="Operational status integer")
    upsert_p.add_argument("--assigned", default="james", help="Assigned to user")
    upsert_p.add_argument("--ip", dest="ip_address", help="Hardware IP address")
    upsert_p.add_argument("--model", dest="model_id", help="Hardware model identifier")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "show":
        ci = get_ci(args.name_or_id)
        if not ci:
            print(f"Error: CI '{args.name_or_id}' not found.", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(ci, indent=2))
        else:
            print(format_ci_detail(ci))

    elif args.command == "list":
        items = list_cis(class_name=args.class_name, search=args.search)
        if args.json:
            print(json.dumps(items, indent=2))
        else:
            print(f"Found {len(items)} Configuration Items:")
            print(f"{'SYS_ID':<28} {'NAME':<32} {'CLASS':<24} {'IP':<16} {'STATUS'}")
            print("-" * 110)
            for item in items:
                ip = item.get("ip_address") or "-"
                print(f"{item['sys_id']:<28} {item['name']:<32} {item['sys_class_name']:<24} {ip:<16} {item['operational_status']}")

    elif args.command == "link":
        try:
            res = link_ci(args.parent, args.child, args.type, rel_id=args.rel_id)
            print(f"Successfully linked: {res['parent_name']} --[{res['type']}]--> {res['child_name']} ({res['sys_id']})")
        except Exception as e:
            print(f"Error linking CIs: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "delete":
        if delete_ci(args.name_or_id):
            print(f"Successfully deleted CI '{args.name_or_id}'.")
        else:
            print(f"Error: CI '{args.name_or_id}' not found.", file=sys.stderr)
            sys.exit(1)

    elif args.command == "upsert":
        ci = upsert_ci(
            name=args.name,
            sys_class_name=args.sys_class_name,
            short_description=args.short_description,
            operational_status=args.status,
            assigned_to=args.assigned,
            ip_address=args.ip_address,
            model_id=args.model_id,
            sys_id=args.sys_id,
        )
        print(f"Successfully upserted CI: {ci['name']} ({ci['sys_id']})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import sys
import sqlite3
import argparse
import subprocess
import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
REPO_PATH = "/home/james/stacklabs"

def parse_db_time(ts_str):
    if not ts_str:
        return None
    # Replace 'T' with space
    ts_str = ts_str.replace('T', ' ')
    # Truncate fractional seconds
    if '.' in ts_str:
        ts_str = ts_str.split('.')[0]
    ts_str = ts_str.strip()
    try:
        return datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def parse_git_time(git_date_str):
    if not git_date_str:
        return None
    try:
        # standard ISO format, e.g. 2026-06-09T20:09:14+00:00
        # Convert to UTC and strip tz
        dt = datetime.datetime.fromisoformat(git_date_str)
        if dt.tzinfo:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        # Fallback manual split
        try:
            date_part = git_date_str.split("+")[0].split("-")
            # if format is like 2026-06-09T20:09:14
            t_part = date_part[2].split("T")
            year = int(date_part[0])
            month = int(date_part[1])
            day = int(t_part[0])
            hms = t_part[1].split(":")
            hour = int(hms[0])
            minute = int(hms[1])
            second = int(hms[2])
            return datetime.datetime(year, month, day, hour, minute, second)
        except Exception:
            return None

def pct_change(curr, prev):
    if prev == 0:
        if curr == 0:
            return "0.0%"
        else:
            return "N/A"
    change = ((curr - prev) / prev) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"

def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Productivity Reporter")
    parser.add_argument("--output", help="Path to save the generated markdown report")
    args = parser.parse_args()

    # Define time windows (UTC naive)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    w1_start = now - datetime.timedelta(hours=48)
    w2_start = now - datetime.timedelta(hours=120)  # 48h + 72h = 120h

    print(f"📊 Analyzing productivity metrics...")
    print(f"   Current UTC Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Last 48 Hours: {w1_start.strftime('%Y-%m-%d %H:%M:%S')} to {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Previous 72 Hours: {w2_start.strftime('%Y-%m-%d %H:%M:%S')} to {w1_start.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Query SQLite Database for Tickets
    tickets_created_w1 = []
    tickets_created_w2 = []
    tickets_resolved_w1 = []
    tickets_resolved_w2 = []

    if os.path.exists(DB_PATH):
        try:
            con = sqlite3.connect(DB_PATH)
            cur = con.cursor()
            cur.execute("SELECT number, type, short_description, state, sys_created_on, sys_updated_on FROM sovereign_tickets")
            rows = cur.fetchall()
            con.close()

            for row in rows:
                number, t_type, short_desc, state, created_str, updated_str = row
                
                created_dt = parse_db_time(created_str)
                updated_dt = parse_db_time(updated_str)

                ticket_info = {
                    "number": number,
                    "type": t_type,
                    "description": short_desc,
                    "state": state,
                    "created_on": created_dt,
                    "updated_on": updated_dt
                }

                # Check Created
                if created_dt:
                    if w1_start <= created_dt <= now:
                        tickets_created_w1.append(ticket_info)
                    elif w2_start <= created_dt < w1_start:
                        tickets_created_w2.append(ticket_info)

                # Check Resolved (State 4 = Resolved, State 5 = Closed)
                if updated_dt and state in (4, 5):
                    if w1_start <= updated_dt <= now:
                        tickets_resolved_w1.append(ticket_info)
                    elif w2_start <= updated_dt < w1_start:
                        tickets_resolved_w2.append(ticket_info)
        except Exception as e:
            print(f"⚠️ Error reading SQLite database: {e}")
    else:
        print(f"⚠️ Database not found at {DB_PATH}. Skipping ticket counts.")

    # 2. Get Git Commits in Repositories
    commits_w1 = []
    commits_w2 = []

    if os.path.exists(REPO_PATH):
        try:
            # Run git log in repo
            cmd = ["git", "log", "--date=iso-strict", "--pretty=format:%ad|%h|%an|%s"]
            res = subprocess.run(cmd, cwd=REPO_PATH, capture_output=True, text=True, check=True)
            lines = res.stdout.strip().split("\n")

            for line in lines:
                if not line or "|" not in line:
                    continue
                parts = line.split("|", 3)
                if len(parts) < 4:
                    continue
                git_time_str, commit_hash, author, message = parts
                commit_dt = parse_git_time(git_time_str)

                commit_info = {
                    "hash": commit_hash,
                    "author": author,
                    "message": message,
                    "date": commit_dt
                }

                if commit_dt:
                    if w1_start <= commit_dt <= now:
                        commits_w1.append(commit_info)
                    elif w2_start <= commit_dt < w1_start:
                        commits_w2.append(commit_info)
        except Exception as e:
            print(f"⚠️ Error running git log: {e}")
    else:
        print(f"⚠️ Repository path not found at {REPO_PATH}. Skipping commit counts.")

    # Calculate percentages
    commits_pct = pct_change(len(commits_w1), len(commits_w2))
    tickets_created_pct = pct_change(len(tickets_created_w1), len(tickets_created_w2))
    tickets_resolved_pct = pct_change(len(tickets_resolved_w1), len(tickets_resolved_w2))

    # Format detailed lists
    commits_list_md = ""
    if commits_w1:
        for c in commits_w1:
            commits_list_md += f"- `{c['hash']}`: {c['message']} (by {c['author']})\n"
    else:
        commits_list_md = "_No commits recorded in this window._\n"

    tickets_created_list_md = ""
    if tickets_created_w1:
        for t in tickets_created_w1:
            tickets_created_list_md += f"- **[{t['type']}]** `{t['number']}`: {t['description']}\n"
    else:
        tickets_created_list_md = "_No tickets created in this window._\n"

    tickets_resolved_list_md = ""
    if tickets_resolved_w1:
        for t in tickets_resolved_w1:
            tickets_resolved_list_md += f"- **[{t['type']}]** `{t['number']}`: {t['description']}\n"
    else:
        tickets_resolved_list_md = "_No tickets resolved in this window._\n"

    report_md = f"""# Sovereign OS Productivity Report

This report compares project velocity over the last 48 hours to the previous 72 hours.

## 📊 Performance Comparison Matrix

| Metric | Last 48 Hours | Previous 72 Hours | Velocity Change |
| :--- | :---: | :---: | :---: |
| **Git Commits** | {len(commits_w1)} | {len(commits_w2)} | `{commits_pct}` |
| **Tickets Created** | {len(tickets_created_w1)} | {len(tickets_created_w2)} | `{tickets_created_pct}` |
| **Tickets Resolved** | {len(tickets_resolved_w1)} | {len(tickets_resolved_w2)} | `{tickets_resolved_pct}` |

---

## 🔍 Activity Log (Last 48 Hours)

### 🛠️ Commits Pushed
{commits_list_md}

### 📋 Tickets Created
{tickets_created_list_md}

### ✅ Tickets Resolved/Closed
{tickets_resolved_list_md}
"""

    if args.output:
        try:
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            with open(args.output, "w") as f:
                f.write(report_md)
            print(f"💾 Report saved successfully to: {args.output}")
        except Exception as e:
            print(f"❌ Failed to write report file: {e}")

    # Output to stdout always
    print("\n" + "="*60)
    print("PRODUCIVITY REPORT OUTPUT:")
    print("="*60)
    print(report_md)

if __name__ == "__main__":
    main()

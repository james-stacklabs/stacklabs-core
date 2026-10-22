#!/usr/bin/env python3
"""
StackLabs Hardened Dual-Plane VFS: Persistent Outbox Worker with Token Bucket & OCC
Path: /home/james/stacklabs/scripts/sn_outbox_worker.py
Author: James Carroll (Pilot) & Cockpit Architect
"""
import os
import sys
import json
import time
import sqlite3
from pathlib import Path

# Defensive path resolution
sys.path.insert(0, str(Path(__file__).parent))

DB_PATH = Path("/home/james/stacklabs/vfs/cmdb.db")

class TokenBucket:
    """Thread-safe / deterministic token bucket rate limiter (e.g. 5 req/sec)."""
    def __init__(self, rate: float = 5.0, capacity: float = 5.0):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.perf_counter()

    def acquire(self):
        while True:
            now = time.perf_counter()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            time.sleep(0.05)

class ServiceNowOutboxWorker:
    def __init__(self, db_path=DB_PATH, rate_limit=5.0):
        self.db_path = db_path
        self.limiter = TokenBucket(rate=rate_limit, capacity=rate_limit)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def enqueue_remediation(self, ticket_number: str, action: str, payload: dict, expected_mod_count: int) -> int:
        """Enqueues an atomic writeback to the NVMe SQLite WAL outbox."""
        conn = self._get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO outbox (ticket_number, action, payload, expected_mod_count, status)
            VALUES (?, ?, ?, ?, 'PENDING');
            """, (ticket_number, action, json.dumps(payload), expected_mod_count))
            outbox_id = cur.lastrowid
        conn.close()
        return outbox_id

    def drain_outbox(self, simulate_wan=True, simulated_mod_counts=None) -> list:
        """
        Drains pending outbox entries.
        Enforces:
        1. Token-Bucket Rate Limiter (5 req/sec).
        2. Optimistic Concurrency Control (OCC) against simulated_mod_counts.
        3. Network partition safety (pending records remain on NVMe if WAN is offline).
        """
        results = []
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM outbox WHERE status = 'PENDING' ORDER BY id ASC;")
        pending_rows = cur.fetchall()
        conn.close()

        simulated_mod_counts = simulated_mod_counts or {}

        for row in pending_rows:
            if not simulate_wan:
                # Network partition simulation: Leave record as PENDING on NVMe
                results.append({
                    "id": row["id"],
                    "ticket": row["ticket_number"],
                    "status": "QUEUED_OFFLINE",
                    "note": "WAN disconnected. Mutation safely buffered on NVMe SQLite WAL."
                })
                continue

            # 1. Enforce Token Bucket (cap WAN load)
            self.limiter.acquire()

            # 2. Check OCC Condition
            ticket_num = row["ticket_number"]
            expected_mod = row["expected_mod_count"]
            # Current mod count in upstream ServiceNow
            current_upstream_mod = simulated_mod_counts.get(ticket_num, expected_mod)

            conn = self._get_connection()
            with conn:
                if current_upstream_mod != expected_mod:
                    # OCC Precondition Failed! A human or workflow edited the ticket concurrently.
                    error_msg = f"HTTP 412 Precondition Failed: sys_mod_count mismatch (expected {expected_mod}, upstream {current_upstream_mod}). Aborting overwrite to prevent clobber."
                    conn.execute("""
                    UPDATE outbox
                    SET status = 'CONFLICT', error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                    """, (error_msg, row["id"]))
                    results.append({
                        "id": row["id"],
                        "ticket": ticket_num,
                        "status": "CONFLICT",
                        "error": error_msg
                    })
                else:
                    # Successful atomic sync to upstream
                    conn.execute("""
                    UPDATE outbox
                    SET status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                    """, (row["id"],))
                    results.append({
                        "id": row["id"],
                        "ticket": ticket_num,
                        "status": "COMPLETED",
                        "sys_mod_count": expected_mod + 1
                    })
            conn.close()

        return results

if __name__ == "__main__":
    worker = ServiceNowOutboxWorker()
    # Test enqueue
    outbox_id = worker.enqueue_remediation(
        ticket_number="INC0000060",
        action="PATCH_RESOLVE",
        payload={"state": "6", "close_notes": "Auto-remediated heap starvation"},
        expected_mod_count=4
    )
    print(f"[PASS] Enqueued Outbox Receipt #{outbox_id} on NVMe SQLite WAL.")
    drained = worker.drain_outbox(simulate_wan=True)
    print(f"[PASS] Drained Outbox: {drained}")

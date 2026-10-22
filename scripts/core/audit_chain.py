#!/usr/bin/env python3
"""
Sovereign OS: Cryptographic Merkle Audit Chain Module
Path: /home/james/stacklabs/scripts/core/audit_chain.py
Specification: SOW-040 (Sovereign Merkle Audit Chain & Adversarial Review Gate)
Ticket: WO0010312

Hardware-grade append-only Merkle hash chain in SQLite, protected by database-level
immutability triggers preventing UPDATE and DELETE operations.
Provides deterministic SHA-256 preimages with recursive canonical JSON serialization.
"""

import os
import sys
import json
import time
import hmac
import hashlib
import sqlite3
import argparse
from typing import Dict, Any, Optional, List, Tuple, Union

# Genesis sentinel: 64 zero hex characters matching SHA-256 digest length
GENESIS_PREV_HASH: str = "0" * 64

# Domain separation tag to prevent cross-protocol preimage collisions
HASH_DOMAIN: str = "sovereign/audit-log-chain/v1"

# Maximum payload size in bytes (64 KB) to prevent dumping large blobs into audit log
MAX_PAYLOAD_BYTES: int = 64 * 1024

DEFAULT_DB_PATH: str = "/home/james/stacklabs/dna/sovereign_now.db"
if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists("/home/james/stacklabs/data/sovereign_now.db"):
    DEFAULT_DB_PATH = "/home/james/stacklabs/data/sovereign_now.db"

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS audit_log_chain (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  signature TEXT,
  signature_alg TEXT,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_chain_event_type ON audit_log_chain(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_chain_created_at ON audit_log_chain(created_at DESC);

CREATE TRIGGER IF NOT EXISTS audit_log_chain_no_update
  BEFORE UPDATE ON audit_log_chain
  FOR EACH ROW
  BEGIN
    SELECT RAISE(ABORT, 'audit_log_chain is append-only: UPDATE forbidden');
  END;

CREATE TRIGGER IF NOT EXISTS audit_log_chain_no_delete
  BEFORE DELETE ON audit_log_chain
  FOR EACH ROW
  BEGIN
    SELECT RAISE(ABORT, 'audit_log_chain is append-only: DELETE forbidden');
  END;
"""


class AuditPayloadTooLargeError(ValueError):
    """Raised when an audit payload exceeds MAX_PAYLOAD_BYTES."""
    pass


class AuditChainImmutabilityError(RuntimeError):
    """Raised when an attempt is made to mutate or delete audit chain entries."""
    pass


def canonical_json_stringify(value: Any) -> str:
    """
    Recursively sorts dictionary keys and formats without whitespace separators
    to guarantee deterministic serialization across runtimes (Python/Node.js).
    """
    def _normalize(val: Any) -> Any:
        if val is None or isinstance(val, (int, float, str, bool)):
            return val
        if isinstance(val, (list, tuple)):
            return [_normalize(item) for item in val]
        if isinstance(val, dict):
            return {str(k): _normalize(v) for k, v in sorted(val.items(), key=lambda x: str(x[0]))}
        if isinstance(val, (bytes, bytearray)):
            return val.hex()
        if hasattr(val, "isoformat"):
            return val.isoformat()
        return str(val)

    normalized = _normalize(value)
    return json.dumps(normalized, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def compute_entry_hash(prev_hash: str, created_at_ms: int, event_type: str, canonical_payload: str) -> str:
    """
    Computes the SHA-256 digest over the canonical domain-separated preimage:
    <HASH_DOMAIN>\n<prev_hash>\n<created_at_ms>\n<event_type>\n<canonical_payload>
    """
    preimage = f"{HASH_DOMAIN}\n{prev_hash}\n{created_at_ms}\n{event_type}\n{canonical_payload}"
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


class SovereignAuditChain:
    """
    Tamper-evident Merkle hash chain backed by SQLite with append-only database triggers.
    """

    def __init__(self, db_path: Optional[str] = None, signature_key: Optional[Union[str, bytes]] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.signature_key: Optional[bytes] = None
        if signature_key:
            if isinstance(signature_key, str):
                self.signature_key = signature_key.encode("utf-8")
            else:
                self.signature_key = bytes(signature_key)
            if len(self.signature_key) < 32:
                raise ValueError(f"Audit signature key must be at least 32 bytes (got {len(self.signature_key)})")

        self._init_db()

    def _get_connection(self, timeout: float = 30.0) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=timeout)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes table and immutability triggers if not present."""
        conn = self._get_connection()
        try:
            conn.executescript(SCHEMA_DDL)
            conn.commit()
        finally:
            conn.close()

    def append(self, event_type: str, payload: Dict[str, Any], signature_key: Optional[Union[str, bytes]] = None) -> Dict[str, Any]:
        """
        Atomically appends an audit event to the hash chain inside an immediate transaction.
        Returns {'seq': int, 'hash': str}.
        """
        if not event_type or not isinstance(event_type, str):
            raise ValueError("event_type must be a non-empty string")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary")

        canonical_payload = canonical_json_stringify(payload)
        payload_bytes_len = len(canonical_payload.encode("utf-8"))
        if payload_bytes_len > MAX_PAYLOAD_BYTES:
            raise AuditPayloadTooLargeError(
                f"Audit payload too large: {payload_bytes_len} bytes (max {MAX_PAYLOAD_BYTES}). "
                "Log a reference (id, path) instead of full content."
            )

        signing_key = self.signature_key
        if signature_key is not None:
            if isinstance(signature_key, str):
                signing_key = signature_key.encode("utf-8")
            else:
                signing_key = bytes(signature_key)
            if len(signing_key) < 32:
                raise ValueError("Supplied signature_key must be at least 32 bytes")

        conn = self._get_connection()
        try:
            # Begin immediate transaction to prevent concurrent race conditions
            conn.execute("BEGIN IMMEDIATE;")
            cur = conn.cursor()
            cur.execute("SELECT hash FROM audit_log_chain ORDER BY seq DESC LIMIT 1;")
            row = cur.fetchone()
            prev_hash = row["hash"] if row else GENESIS_PREV_HASH

            created_at_ms = int(time.time() * 1000)
            entry_hash = compute_entry_hash(prev_hash, created_at_ms, event_type, canonical_payload)

            signature = None
            signature_alg = None
            if signing_key:
                signature = hmac.new(signing_key, entry_hash.encode("utf-8"), hashlib.sha256).hexdigest()
                signature_alg = "HMAC-SHA256"

            cur.execute(
                """
                INSERT INTO audit_log_chain (
                    prev_hash, hash, event_type, payload_json, signature, signature_alg, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (prev_hash, entry_hash, event_type, canonical_payload, signature, signature_alg, created_at_ms)
            )
            seq = cur.lastrowid
            conn.commit()
            return {"seq": seq, "hash": entry_hash}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def verify(self, from_seq: int = 1, to_seq: Optional[int] = None) -> Dict[str, Any]:
        """
        Verifies the cryptographic integrity of the chain within the specified sequence range.
        Returns:
            {
                "valid": bool,
                "broken_at": int | None,
                "reason": str | None,
                "entries_checked": int
            }
        """
        conn = self._get_connection()
        try:
            # Establish the expected prev_hash for the first entry in range
            if from_seq <= 1:
                expected_prev = GENESIS_PREV_HASH
            else:
                cur = conn.cursor()
                cur.execute("SELECT hash FROM audit_log_chain WHERE seq = ?;", (from_seq - 1,))
                anchor = cur.fetchone()
                if not anchor:
                    return {
                        "valid": False,
                        "broken_at": from_seq,
                        "reason": f"Anchor entry seq={from_seq - 1} not found",
                        "entries_checked": 0
                    }
                expected_prev = anchor["hash"]

            query = "SELECT seq, prev_hash, hash, event_type, payload_json, signature, signature_alg, created_at FROM audit_log_chain WHERE seq >= ?"
            params: List[Any] = [from_seq]
            if to_seq is not None:
                query += " AND seq <= ?"
                params.append(to_seq)
            query += " ORDER BY seq ASC;"

            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            entries_checked = 0
            for row in rows:
                seq = row["seq"]
                stored_prev = row["prev_hash"]
                stored_hash = row["hash"]
                event_type = row["event_type"]
                payload_json = row["payload_json"]
                created_at_ms = row["created_at"]
                signature = row["signature"]
                signature_alg = row["signature_alg"]

                # 1. Linkage verification
                if stored_prev != expected_prev:
                    return {
                        "valid": False,
                        "broken_at": seq,
                        "reason": f"prev_hash mismatch at seq={seq}: chain linkage broken",
                        "entries_checked": entries_checked
                    }

                # 2. JSON validity check
                try:
                    payload = json.loads(payload_json)
                except Exception as e:
                    return {
                        "valid": False,
                        "broken_at": seq,
                        "reason": f"payload_json corrupt at seq={seq}: {e}",
                        "entries_checked": entries_checked
                    }

                # 3. Recomputed hash verification
                canonical_payload = canonical_json_stringify(payload)
                recomputed_hash = compute_entry_hash(stored_prev, created_at_ms, event_type, canonical_payload)
                if recomputed_hash != stored_hash:
                    return {
                        "valid": False,
                        "broken_at": seq,
                        "reason": f"hash mismatch at seq={seq}: entry content altered or tampered",
                        "entries_checked": entries_checked
                    }

                # 4. Signature verification (if key is configured on chain)
                if self.signature_key:
                    if not signature or signature_alg != "HMAC-SHA256":
                        return {
                            "valid": False,
                            "broken_at": seq,
                            "reason": f"missing or unsupported signature at seq={seq} (expected HMAC-SHA256)",
                            "entries_checked": entries_checked
                        }
                    expected_sig = hmac.new(self.signature_key, stored_hash.encode("utf-8"), hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(signature, expected_sig):
                        return {
                            "valid": False,
                            "broken_at": seq,
                            "reason": f"signature mismatch at seq={seq}: signature key changed or forged",
                            "entries_checked": entries_checked
                        }

                expected_prev = stored_hash
                entries_checked += 1

            return {
                "valid": True,
                "broken_at": None,
                "reason": None,
                "entries_checked": entries_checked
            }
        finally:
            conn.close()

    def latest(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent audit chain entry or None if empty."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT seq, prev_hash, hash, event_type, payload_json, signature, signature_alg, created_at
                FROM audit_log_chain ORDER BY seq DESC LIMIT 1;
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "seq": row["seq"],
                "prev_hash": row["prev_hash"],
                "hash": row["hash"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "signature": row["signature"],
                "signature_alg": row["signature_alg"],
                "created_at": row["created_at"]
            }
        finally:
            conn.close()

    def count(self) -> int:
        """Returns total number of records in the audit chain."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS total FROM audit_log_chain;")
            row = cur.fetchone()
            return int(row["total"]) if row else 0
        finally:
            conn.close()

    def get_entries(self, from_seq: int = 1, to_seq: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns ordered audit chain entries within range."""
        conn = self._get_connection()
        try:
            query = """
                SELECT seq, prev_hash, hash, event_type, payload_json, signature, signature_alg, created_at
                FROM audit_log_chain WHERE seq >= ?
            """
            params: List[Any] = [from_seq]
            if to_seq is not None:
                query += " AND seq <= ?"
                params.append(to_seq)
            query += " ORDER BY seq ASC LIMIT ?;"
            params.append(limit)

            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    "seq": r["seq"],
                    "prev_hash": r["prev_hash"],
                    "hash": r["hash"],
                    "event_type": r["event_type"],
                    "payload": json.loads(r["payload_json"]),
                    "signature": r["signature"],
                    "signature_alg": r["signature_alg"],
                    "created_at": r["created_at"]
                })
            return results
        finally:
            conn.close()


def run_self_test(db_path: Optional[str] = None) -> bool:
    """Runs rigorous test suite verifying append, verify, and trigger immutability."""
    import tempfile
    test_db = db_path or tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    print(f"🔒 [TEST] Running SovereignAuditChain verification tests against: {test_db}")

    try:
        chain = SovereignAuditChain(db_path=test_db)

        # 1. Test Genesis Append
        res1 = chain.append("test.genesis", {"test_key": "val1", "count": 1})
        print(f"  ✓ Appended entry seq={res1['seq']}, hash={res1['hash'][:16]}...")
        assert res1["seq"] == 1, "Expected seq=1 for first entry"

        # 2. Test Second Append
        res2 = chain.append("test.step2", {"author": "clio", "action": "forge"})
        print(f"  ✓ Appended entry seq={res2['seq']}, hash={res2['hash'][:16]}...")
        assert res2["seq"] == 2, "Expected seq=2"

        # 3. Test Verification
        v_res = chain.verify()
        print(f"  ✓ Chain verify passed: {v_res}")
        assert v_res["valid"] is True, f"Expected valid chain, got: {v_res}"
        assert v_res["entries_checked"] == 2, "Expected 2 checked entries"

        # 4. Test Trigger Immutability: UPDATE ABORT
        conn = chain._get_connection()
        update_blocked = False
        try:
            conn.execute("UPDATE audit_log_chain SET event_type = 'tampered' WHERE seq = 1;")
            conn.commit()
        except sqlite3.DatabaseError as e:
            update_blocked = True
            print(f"  ✓ SQLite Trigger blocked UPDATE as expected: {e}")
        finally:
            conn.close()
        assert update_blocked, "CRITICAL: Trigger failed to abort UPDATE operation on audit_log_chain!"

        # 5. Test Trigger Immutability: DELETE ABORT
        conn = chain._get_connection()
        delete_blocked = False
        try:
            conn.execute("DELETE FROM audit_log_chain WHERE seq = 1;")
            conn.commit()
        except sqlite3.DatabaseError as e:
            delete_blocked = True
            print(f"  ✓ SQLite Trigger blocked DELETE as expected: {e}")
        finally:
            conn.close()
        assert delete_blocked, "CRITICAL: Trigger failed to abort DELETE operation on audit_log_chain!"

        # 6. Test Payload Size Limit
        oversized = {"big_data": "x" * (MAX_PAYLOAD_BYTES + 1024)}
        size_blocked = False
        try:
            chain.append("test.oversize", oversized)
        except AuditPayloadTooLargeError as e:
            size_blocked = True
            print(f"  ✓ Max payload check caught oversized entry: {e}")
        assert size_blocked, "CRITICAL: MAX_PAYLOAD_BYTES check failed!"

        print("🎉 [TEST] All SovereignAuditChain self-tests passed with 100% compliance!")
        return True
    finally:
        if not db_path and os.path.exists(test_db):
            try:
                os.remove(test_db)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Merkle Audit Chain CLI")
    parser.add_argument("--verify", action="store_true", help="Verify cryptographic integrity of the audit chain")
    parser.add_argument("--test", "--tamper-test", action="store_true", dest="test", help="Run comprehensive test suite against temporary database")
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database file")
    parser.add_argument("--latest", action="store_true", help="Print latest audit entry")
    parser.add_argument("--count", action="store_true", help="Print total count of audit records")
    args = parser.parse_args()

    if args.test:
        success = run_self_test(args.db)
        sys.exit(0 if success else 1)

    chain = SovereignAuditChain(db_path=args.db)

    if args.latest:
        entry = chain.latest()
        if entry:
            print(json.dumps(entry, indent=2))
        else:
            print("Chain is empty (no entries).")
        sys.exit(0)

    if args.count:
        print(f"Total audit entries: {chain.count()}")
        sys.exit(0)

    if args.verify or len(sys.argv) == 1:
        res = chain.verify()
        print(f"Audit Chain Verification Status: {'VALID ✓' if res['valid'] else 'COMPROMISED ✗'}")
        print(f"  Entries Checked: {res['entries_checked']}")
        if not res["valid"]:
            print(f"  Broken at Seq:   {res['broken_at']}")
            print(f"  Reason:          {res['reason']}")
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()

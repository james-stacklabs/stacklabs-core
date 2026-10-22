#!/usr/bin/env python3
"""
Sovereign OS: Dataset Quarantine Ingress Validator (Tool #51)
Path: /home/james/stacklabs/scripts/ops/dataset_quarantine_validator.py
Catalog ID: Tool #51

Automated zero-privilege staging buffer and schema linter for external builder
client database drops, SQL dumps, CSV rosters, and JSON feeds.

Validates:
1. SQLite PRAGMA integrity_check
2. SQLite PRAGMA foreign_key_check (orphaned relational records)
3. Primary Key integrity (scans for missing PKs or NULL primary key records)
4. ISO-8601 timestamp compliance across all datetime/timestamp columns
5. CSV/JSON parse integrity and primary key non-null enforcement
6. Generates structured JSON audit manifest (quarantine_audit_manifest.json)
"""

import os
import sys
import json
import sqlite3
import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

ISO8601_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$'
)

TIMESTAMP_COL_KEYWORDS = (
    'time', 'timestamp', 'date', 'created', 'updated', 'sys_created_on',
    'sys_updated_on', 'created_at', 'updated_at', 'datetime'
)

ID_COL_KEYWORDS = (
    'id', 'uuid', 'pk', 'sys_id', 'ticket_id', 'game_pk', 'node_id', 'user_id'
)


class QuarantineValidator:
    def __init__(self, target_path: str, output_report: Optional[str] = None, sample_limit: int = 5000, verbose: bool = False):
        self.target_path = Path(target_path).resolve()
        self.output_report = Path(output_report).resolve() if output_report else Path("quarantine_audit_manifest.json")
        self.sample_limit = sample_limit
        self.verbose = verbose
        self.report: Dict[str, Any] = {
            "validator": "Dataset Quarantine Ingress Validator (Tool #51)",
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "target_file": str(self.target_path),
            "file_size_bytes": 0,
            "file_type": "unknown",
            "overall_status": "UNKNOWN",
            "summary": {
                "tables_or_entities_audited": 0,
                "integrity_status": "NOT_RUN",
                "foreign_key_violations_count": 0,
                "null_primary_keys_count": 0,
                "timestamp_violations_count": 0,
                "missing_pk_tables": []
            },
            "checks": {},
            "clean_migration_requirements": []
        }

    def run(self) -> int:
        if not self.target_path.exists():
            print(f"[ERROR] Target file does not exist: {self.target_path}", file=sys.stderr)
            self.report["overall_status"] = "FAILED"
            self.report["clean_migration_requirements"].append(f"Target file not found: {self.target_path}")
            self._save_report()
            return 1

        self.report["file_size_bytes"] = self.target_path.stat().st_size
        suffix = self.target_path.suffix.lower()

        if suffix in ('.db', '.sqlite', '.sqlite3'):
            self.report["file_type"] = "sqlite"
            success = self._validate_sqlite(self.target_path)
        elif suffix == '.sql':
            self.report["file_type"] = "sql_dump"
            success = self._validate_sql_dump(self.target_path)
        elif suffix == '.csv':
            self.report["file_type"] = "csv"
            success = self._validate_csv(self.target_path)
        elif suffix == '.json':
            self.report["file_type"] = "json"
            success = self._validate_json(self.target_path)
        else:
            # Attempt SQLite probe first
            if self._is_sqlite_file(self.target_path):
                self.report["file_type"] = "sqlite"
                success = self._validate_sqlite(self.target_path)
            else:
                self.report["file_type"] = "unsupported"
                print(f"[ERROR] Unsupported file extension for quarantine validation: {suffix}", file=sys.stderr)
                self.report["overall_status"] = "FAILED"
                self.report["clean_migration_requirements"].append("Unsupported file format. Provide .db, .sqlite, .sql, .csv, or .json.")
                self._save_report()
                return 1

        self.report["overall_status"] = "PASSED" if success else "FAILED"
        self._print_terminal_summary()
        self._save_report()
        return 0 if success else 1

    def _is_sqlite_file(self, path: Path) -> bool:
        try:
            with open(path, 'rb') as f:
                header = f.read(16)
                return header.startswith(b'SQLite format 3\x00')
        except Exception:
            return False

    def _validate_sqlite(self, db_path: Path) -> bool:
        all_passed = True
        conn = None
        try:
            # Read-only URI mode to prevent db write locks
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1. Integrity check
            try:
                cursor.execute("PRAGMA integrity_check;")
                integrity_rows = cursor.fetchall()
                integrity_results = [r[0] for r in integrity_rows]
                integrity_passed = (len(integrity_results) == 1 and integrity_results[0].lower() == 'ok')
                self.report["checks"]["integrity_check"] = {
                    "passed": integrity_passed,
                    "details": integrity_results
                }
                self.report["summary"]["integrity_status"] = "OK" if integrity_passed else "CORRUPTED"
                if not integrity_passed:
                    all_passed = False
                    self.report["clean_migration_requirements"].append("Database failed PRAGMA integrity_check; restore from clean backup.")
            except Exception as e:
                self.report["checks"]["integrity_check"] = {"passed": False, "error": str(e)}
                self.report["summary"]["integrity_status"] = "ERROR"
                all_passed = False

            # 2. Foreign key check
            try:
                cursor.execute("PRAGMA foreign_key_check;")
                fk_rows = cursor.fetchall()
                fk_violations = []
                for r in fk_rows:
                    fk_violations.append({
                        "table": r[0],
                        "rowid": r[1],
                        "parent_table": r[2],
                        "fkid": r[3]
                    })
                fk_passed = len(fk_violations) == 0
                self.report["checks"]["foreign_key_check"] = {
                    "passed": fk_passed,
                    "violations_count": len(fk_violations),
                    "violations": fk_violations[:50]
                }
                self.report["summary"]["foreign_key_violations_count"] = len(fk_violations)
                if not fk_passed:
                    all_passed = False
                    self.report["clean_migration_requirements"].append(f"Foreign key violations detected ({len(fk_violations)} orphaned records). Clean or cascade foreign key references.")
            except Exception as e:
                self.report["checks"]["foreign_key_check"] = {"passed": False, "error": str(e)}
                all_passed = False

            # 3. Table schema, Primary Keys, and Timestamp checks
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [r[0] for r in cursor.fetchall()]
            self.report["summary"]["tables_or_entities_audited"] = len(tables)

            pk_audit: Dict[str, Any] = {"tables": {}}
            ts_audit: Dict[str, Any] = {"columns_checked": 0, "violations": []}
            total_null_pks = 0
            total_ts_violations = 0
            missing_pk_tables = []

            for tbl in tables:
                cursor.execute(f"PRAGMA table_info('{tbl}');")
                cols = cursor.fetchall()

                pk_cols = [c['name'] for c in cols if c['pk'] > 0]
                if not pk_cols:
                    missing_pk_tables.append(tbl)
                    pk_audit["tables"][tbl] = {"has_pk": False, "pk_columns": [], "null_pk_count": 0}
                else:
                    null_count_for_tbl = 0
                    for pk_col in pk_cols:
                        safe_pk = pk_col.replace('"', '""')
                        safe_tbl = tbl.replace('"', '""')
                        cursor.execute(f'SELECT COUNT(*) FROM "{safe_tbl}" WHERE "{safe_pk}" IS NULL;')
                        cnt = cursor.fetchone()[0]
                        null_count_for_tbl += cnt

                    total_null_pks += null_count_for_tbl
                    pk_audit["tables"][tbl] = {
                        "has_pk": True,
                        "pk_columns": pk_cols,
                        "null_pk_count": null_count_for_tbl
                    }

                # Timestamp verification
                ts_cols = [
                    c['name'] for c in cols
                    if any(kw in c['name'].lower() for kw in TIMESTAMP_COL_KEYWORDS)
                ]
                safe_tbl = tbl.replace('"', '""')
                for col in ts_cols:
                    safe_col = col.replace('"', '""')
                    ts_audit["columns_checked"] += 1
                    limit_clause = f"LIMIT {self.sample_limit}" if self.sample_limit > 0 else ""
                    cursor.execute(f'SELECT rowid, "{safe_col}" FROM "{safe_tbl}" WHERE "{safe_col}" IS NOT NULL AND "{safe_col}" != \'\' {limit_clause};')
                    sample_rows = cursor.fetchall()
                    for s_row in sample_rows:
                        val = str(s_row[1]).strip()
                        if val and not ISO8601_PATTERN.match(val):
                            total_ts_violations += 1
                            if len(ts_audit["violations"]) < 50:
                                ts_audit["violations"].append({
                                    "table": tbl,
                                    "column": col,
                                    "rowid": s_row[0],
                                    "invalid_value": val[:100]
                                })

            self.report["summary"]["null_primary_keys_count"] = total_null_pks
            self.report["summary"]["missing_pk_tables"] = missing_pk_tables
            self.report["summary"]["timestamp_violations_count"] = total_ts_violations

            pk_passed = (total_null_pks == 0)
            if not pk_passed:
                all_passed = False
                self.report["clean_migration_requirements"].append(f"Detected {total_null_pks} records with NULL primary keys.")

            if missing_pk_tables:
                self.report["clean_migration_requirements"].append(f"Tables missing formal PRIMARY KEY: {', '.join(missing_pk_tables[:10])}")

            ts_passed = (total_ts_violations == 0)
            if not ts_passed:
                all_passed = False
                self.report["clean_migration_requirements"].append(f"Detected {total_ts_violations} non-ISO8601 timestamp values. Normalize timestamps to YYYY-MM-DDTHH:MM:SSZ.")

            self.report["checks"]["primary_key_audit"] = {
                "passed": pk_passed,
                "null_primary_keys": total_null_pks,
                "missing_pk_tables": missing_pk_tables,
                "details": pk_audit
            }
            self.report["checks"]["timestamp_audit"] = {
                "passed": ts_passed,
                "violations_count": total_ts_violations,
                "sample_violations": ts_audit["violations"]
            }

        except Exception as e:
            print(f"[ERROR] SQLite validation exception: {e}", file=sys.stderr)
            self.report["checks"]["sqlite_error"] = str(e)
            all_passed = False
        finally:
            if conn:
                conn.close()

        return all_passed

    def _validate_sql_dump(self, sql_path: Path) -> bool:
        """Execute SQL dump into an in-memory SQLite DB and run validation."""
        temp_conn = None
        try:
            temp_conn = sqlite3.connect(":memory:")
            with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
                sql_content = f.read()
            temp_conn.executescript(sql_content)

            # Dump into temporary db file and run standard validation
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
                tmp_db_path = Path(tmp_file.name)

            file_conn = sqlite3.connect(tmp_db_path)
            temp_conn.backup(file_conn)
            file_conn.close()
            temp_conn.close()

            result = self._validate_sqlite(tmp_db_path)
            try:
                tmp_db_path.unlink()
            except Exception:
                pass
            return result
        except Exception as e:
            self.report["checks"]["sql_dump_error"] = str(e)
            self.report["clean_migration_requirements"].append(f"SQL execution error during quarantine parsing: {e}")
            return False

    def _validate_csv(self, csv_path: Path) -> bool:
        all_passed = True
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    has_header = csv.Sniffer().has_header(sample)
                except Exception:
                    dialect = csv.excel
                    has_header = True

                reader = csv.DictReader(f, dialect=dialect) if has_header else None
                if not reader or not reader.fieldnames:
                    self.report["checks"]["csv_error"] = "CSV lacks parseable header row."
                    self.report["clean_migration_requirements"].append("Add standard header row with column definitions to CSV.")
                    return False

                fieldnames = reader.fieldnames
                self.report["summary"]["tables_or_entities_audited"] = 1
                id_cols = [c for c in fieldnames if c and any(kw == c.lower() or c.lower().endswith(f"_{kw}") for kw in ID_COL_KEYWORDS)]
                ts_cols = [c for c in fieldnames if c and any(kw in c.lower() for kw in TIMESTAMP_COL_KEYWORDS)]

                null_id_count = 0
                ts_violations = 0
                row_count = 0

                for row_idx, row in enumerate(reader, start=1):
                    row_count += 1
                    for id_col in id_cols:
                        if not row.get(id_col) or not str(row[id_col]).strip():
                            null_id_count += 1
                    for ts_col in ts_cols:
                        val = str(row.get(ts_col) or "").strip()
                        if val and not ISO8601_PATTERN.match(val):
                            ts_violations += 1

                self.report["summary"]["null_primary_keys_count"] = null_id_count
                self.report["summary"]["timestamp_violations_count"] = ts_violations
                self.report["checks"]["csv_audit"] = {
                    "total_rows": row_count,
                    "columns": fieldnames,
                    "id_columns_identified": id_cols,
                    "timestamp_columns_identified": ts_cols,
                    "null_id_count": null_id_count,
                    "timestamp_violations": ts_violations
                }

                if null_id_count > 0:
                    all_passed = False
                    self.report["clean_migration_requirements"].append(f"Detected {null_id_count} CSV rows with empty/null ID field.")
                if ts_violations > 0:
                    all_passed = False
                    self.report["clean_migration_requirements"].append(f"Detected {ts_violations} CSV timestamp values not matching ISO-8601.")

                return all_passed
        except Exception as e:
            self.report["checks"]["csv_error"] = str(e)
            return False

    def _validate_json(self, json_path: Path) -> bool:
        all_passed = True
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            records = []
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                # Inspect values if list of records, or treat dict as single record
                if "records" in data and isinstance(data["records"], list):
                    records = data["records"]
                elif "data" in data and isinstance(data["data"], list):
                    records = data["data"]
                else:
                    records = [data]

            self.report["summary"]["tables_or_entities_audited"] = 1
            null_id_count = 0
            ts_violations = 0

            for rec in records:
                if isinstance(rec, dict):
                    for k, v in rec.items():
                        k_lower = k.lower()
                        if any(kw == k_lower or k_lower.endswith(f"_{kw}") for kw in ID_COL_KEYWORDS):
                            if v is None or (isinstance(v, str) and not v.strip()):
                                null_id_count += 1
                        if any(kw in k_lower for kw in TIMESTAMP_COL_KEYWORDS):
                            if isinstance(v, str) and v.strip() and not ISO8601_PATTERN.match(v.strip()):
                                ts_violations += 1

            self.report["summary"]["null_primary_keys_count"] = null_id_count
            self.report["summary"]["timestamp_violations_count"] = ts_violations
            self.report["checks"]["json_audit"] = {
                "total_records": len(records),
                "null_id_count": null_id_count,
                "timestamp_violations": ts_violations
            }

            if null_id_count > 0:
                all_passed = False
                self.report["clean_migration_requirements"].append(f"Detected {null_id_count} JSON entities with null primary keys.")
            if ts_violations > 0:
                all_passed = False
                self.report["clean_migration_requirements"].append(f"Detected {ts_violations} non-ISO8601 timestamps in JSON records.")

            return all_passed
        except Exception as e:
            self.report["checks"]["json_error"] = str(e)
            return False

    def _print_terminal_summary(self) -> None:
        status = self.report["overall_status"]
        status_color = "\033[92m" if status == "PASSED" else "\033[91m"
        reset = "\033[0m"

        print("=" * 78)
        print(f"🛡️  SOVEREIGN DATASET QUARANTINE INGRESS AUDIT — TOOL #51")
        print("=" * 78)
        print(f"Target:       {self.report['target_file']}")
        print(f"Format:       {self.report['file_type'].upper()} ({self.report['file_size_bytes']} bytes)")
        print(f"Status:       {status_color}{status}{reset}")
        print("-" * 78)
        print(f"Integrity Check:          {self.report['summary']['integrity_status']}")
        print(f"Entities/Tables Audited:  {self.report['summary']['tables_or_entities_audited']}")
        print(f"Foreign Key Violations:   {self.report['summary']['foreign_key_violations_count']}")
        print(f"NULL Primary Keys:        {self.report['summary']['null_primary_keys_count']}")
        print(f"ISO-8601 TS Violations:   {self.report['summary']['timestamp_violations_count']}")
        if self.report["summary"]["missing_pk_tables"]:
            print(f"Tables Missing PK:        {len(self.report['summary']['missing_pk_tables'])}")
        print("-" * 78)

        if self.report["clean_migration_requirements"]:
            print("🚨 CLEAN MIGRATION REMEDIATION REQUIREMENTS:")
            for req in self.report["clean_migration_requirements"]:
                print(f"  • {req}")
            print("-" * 78)

        print(f"Audit Manifest saved to: {self.output_report}")
        print("=" * 78)

    def _save_report(self) -> None:
        try:
            self.output_report.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_report, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to write quarantine manifest report: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Dataset Quarantine Ingress Validator (Tool #51): Zero-privilege schema & integrity linter."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to external database, SQL dump, CSV, or JSON file to validate."
    )
    parser.add_argument(
        "--output-report", "-o",
        default="quarantine_audit_manifest.json",
        help="Path where structured JSON audit manifest will be saved (default: quarantine_audit_manifest.json)."
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5000,
        help="Row sampling limit per table for ISO-8601 timestamp audits (default: 5000, 0 = check all rows)."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output logging."
    )

    args = parser.parse_args()
    validator = QuarantineValidator(
        target_path=args.input,
        output_report=args.output_report,
        sample_limit=args.sample_limit,
        verbose=args.verbose
    )
    sys.exit(validator.run())


if __name__ == "__main__":
    main()

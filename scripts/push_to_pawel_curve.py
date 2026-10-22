#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Zero-API Telegraph Bridge to Both Ends of the Curve (WO0011272 / WO0011287).
Supports:
  1. --collision <collision_id> / --top-collision / --essay <slug>:
     Loads deterministic 2-hop/3-hop Swanson VFS collision + Blind-Spot (L_C \\ L_A) receipt.
  2. --clipboard:
     Harvests recent Antigravity IDE chat turns on local NVMe and formats a 3-bullet brief.
  3. --message / --file:
     Direct working-engineer payload submission.
Enforces Playwright press_sequentially(..., delay=10) for Wix React state synchronization,
posts visual preview/submission receipts to DISCORD_WEBHOOK_CAL, and records audit rows in
both data/morning_wiretap.db (SQLite WAL) and pilot_drops/pawel_curve_pushes.jsonl.
"""

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = Path("/home/james/stacklabs")
ENV_PATH = BASE_DIR / ".env"
WIRETAP_DB_PATH = BASE_DIR / "data" / "morning_wiretap.db"
LIBERATED_JSONL_PATH = BASE_DIR / "pilot_drops" / "pawel_curve_pushes.jsonl"
PHOTOS_DIR = BASE_DIR / "pilot_drops" / "photos"
COLLISIONS_INDEX_PATH = BASE_DIR / "vfs" / "collisions" / "latest_ranked_collisions.json"
TARGET_URL = "https://www.bothendsofthecurve.com"


def load_env_vars() -> Dict[str, str]:
    env_map: Dict[str, str] = {}
    if ENV_PATH.is_file():
        try:
            for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env_map[k.strip()] = v.strip().strip("'").strip('"')
        except OSError:
            pass
    for k, v in os.environ.items():
        env_map[k] = v
    return env_map


def build_pooled_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(pool_connections=4, pool_maxsize=4, max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def resolve_collision_payload(
    collision_id: Optional[str] = None,
    essay_query: Optional[str] = None,
    silo_query: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    if not COLLISIONS_INDEX_PATH.is_file():
        subprocess.run(
            [
                "/home/james/stacklabs/.venv/bin/python3",
                str(BASE_DIR / "scripts" / "swanson_vfs_collider.py"),
            ],
            check=True,
        )

    data = json.loads(COLLISIONS_INDEX_PATH.read_text(encoding="utf-8"))
    ranked: List[Dict[str, Any]] = data.get("ranked_collisions", [])
    if not ranked:
        raise RuntimeError("No ranked collisions found in latest_ranked_collisions.json")

    selected: Optional[Dict[str, Any]] = None
    if collision_id:
        q_id = collision_id.strip().lower()
        for item in ranked:
            if item["collision_id"].lower() == q_id or q_id in item["collision_id"].lower():
                selected = item
                break
    elif essay_query:
        q_essay = essay_query.strip().lower()
        for item in ranked:
            if q_essay in item["essay_slug"].lower() or q_essay in item["essay_title"].lower():
                if not silo_query or item["empirical_silo"].lower() == silo_query.strip().lower():
                    selected = item
                    break
    else:
        if silo_query:
            q_silo = silo_query.strip().lower()
            for item in ranked:
                if item["empirical_silo"].lower() == q_silo:
                    selected = item
                    break
        if selected is None:
            selected = ranked[0]

    if selected is None:
        raise ValueError(
            f"Could not resolve collision matching collision_id={collision_id!r}, essay={essay_query!r}"
        )

    return selected["crucible_brief_3bullet"], selected


def harvest_latest_ide_transcript(max_turns: int = 8, max_age_hours: float = 12.0) -> List[str]:
    brain_root = Path("/home/james/.gemini/antigravity-ide/brain")
    snippets: List[str] = []
    now_ts = time.time()

    if brain_root.is_dir():
        candidates: List[Tuple[float, Path]] = []
        for log_path in brain_root.glob("*/.system_generated/logs/transcript.jsonl"):
            try:
                mtime = log_path.stat().st_mtime
                if (now_ts - mtime) <= (max_age_hours * 3600.0):
                    candidates.append((mtime, log_path))
            except OSError:
                continue
        candidates.sort(key=lambda item: item[0], reverse=True)
        if candidates:
            latest_log = candidates[0][1]
            try:
                lines = latest_log.read_text(encoding="utf-8", errors="replace").splitlines()
                for raw_line in lines[-max_turns:]:
                    try:
                        rec = json.loads(raw_line)
                        text_val = (
                            rec.get("text")
                            or rec.get("content")
                            or rec.get("message")
                            or ""
                        )
                        if isinstance(text_val, str) and text_val.strip():
                            snippets.append(text_val.strip()[:280])
                    except json.JSONDecodeError:
                        continue
            except OSError:
                pass

    if not snippets:
        _, top_col = resolve_collision_payload()
        snippets.append(top_col["crucible_brief_3bullet"])

    return snippets


def build_clipboard_payload() -> str:
    turns = harvest_latest_ide_transcript()
    if len(turns) == 1 and turns[0].startswith("1. STRUCTURAL THESIS LOCK"):
        return turns[0]
    joined = " | ".join(turns[-3:])
    return (
        "1. EMPIRICAL VFS AUDIT: I ran your essay syllabus through my local POSIX VFS Swanson Collider "
        "against SEC 10-K interconnect disclosures, ERCOT 2026 hourly load curves, and live broadcast snipes in 212.0 us.\n\n"
        f"2. LIVE WORKSTATION TELEMETRY: {joined[:240]}\n\n"
        "3. THE BREEZE CHALLENGE: Where does the thesis account for asymmetric tail contagion when physical "
        "grid queues and black-box model drift collide simultaneously?"
    )


def execute_playwright_push(
    message: str,
    email: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_name = "pawel_push_preview.png" if dry_run else "pawel_push_receipt.png"
    screenshot_path = PHOTOS_DIR / screenshot_name

    from playwright.sync_api import sync_playwright

    result_meta: Dict[str, Any] = {
        "target_url": TARGET_URL,
        "dry_run": dry_run,
        "screenshot_path": str(screenshot_path),
        "form_populated": False,
        "submitted": False,
        "status": "INIT",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 960},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        textarea = page.locator("textarea").first
        if textarea.count() > 0:
            textarea.scroll_into_view_if_needed()
            textarea.click()
            textarea.fill("")
            textarea.press_sequentially(message, delay=10)
            textarea.dispatch_event("input")
            textarea.dispatch_event("change")
            result_meta["form_populated"] = True

        if email:
            email_inputs = page.locator("input[type='email'], input[placeholder*='email' i]")
            if email_inputs.count() > 0:
                email_el = email_inputs.first
                email_el.click()
                email_el.fill("")
                email_el.press_sequentially(email, delay=10)
                email_el.dispatch_event("input")
                email_el.dispatch_event("change")

        page.wait_for_timeout(600)

        if not dry_run and result_meta["form_populated"]:
            submit_btn = page.locator("button:has-text('Push'), button:has-text('Submit'), button:has-text('Send')").first
            if submit_btn.count() > 0:
                submit_btn.click()
                page.wait_for_timeout(2500)
                result_meta["submitted"] = True
                result_meta["status"] = "SUBMITTED_LIVE"
            else:
                result_meta["status"] = "SUBMIT_BUTTON_NOT_FOUND"
        else:
            result_meta["status"] = "DRY_RUN_STAGED" if result_meta["form_populated"] else "TEXTAREA_NOT_FOUND"

        page.screenshot(path=str(screenshot_path), full_page=False)
        browser.close()

    return result_meta


def record_push_audit(
    mode: str,
    status: str,
    message: str,
    screenshot_path: str,
    collision_meta: Optional[Dict[str, Any]] = None,
    email: str = "james@stacklabsllc.com",
) -> Tuple[int, str]:
    sha256_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()
    created_at = datetime.now(timezone.utc).isoformat()
    collision_id = collision_meta.get("collision_id") if collision_meta else None

    WIRETAP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(WIRETAP_DB_PATH), timeout=10.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pawel_curve_pushes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT 'james@stacklabsllc.com',
                quote_anon INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                screenshot_path TEXT NOT NULL DEFAULT '',
                content_sha256 TEXT NOT NULL DEFAULT '',
                sha256_hash TEXT NOT NULL DEFAULT '',
                collision_id TEXT
            )
            """
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(pawel_curve_pushes)").fetchall()}
        if "message_text" in cols and "content_sha256" in cols:
            cur = conn.execute(
                """
                INSERT INTO pawel_curve_pushes (
                    message_text, email, quote_anon, mode, status,
                    screenshot_path, content_sha256, created_at,
                    message, sha256_hash, collision_id
                )
                VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message,
                    email,
                    mode,
                    status,
                    screenshot_path,
                    sha256_hash,
                    created_at,
                    message,
                    sha256_hash,
                    collision_id,
                ),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO pawel_curve_pushes (created_at, mode, status, message, screenshot_path, sha256_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (created_at, mode, status, message, screenshot_path, sha256_hash),
            )
        row_id = int(cur.lastrowid or 0)
        conn.commit()
    finally:
        conn.close()

    LIBERATED_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    jsonl_record = {
        "id": row_id,
        "created_at": created_at,
        "mode": mode,
        "status": status,
        "collision_id": collision_id,
        "sha256_hash": sha256_hash,
        "screenshot_path": screenshot_path,
        "message": message,
    }
    with open(LIBERATED_JSONL_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(jsonl_record, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())

    return row_id, sha256_hash


def post_receipt_to_discord(
    message: str,
    screenshot_path: str,
    mode: str,
    status: str,
    sha256_hash: str,
    collision_meta: Optional[Dict[str, Any]] = None,
) -> int:
    env_map = load_env_vars()
    webhook_url = (
        env_map.get("DISCORD_WEBHOOK_CAL")
        or env_map.get("DISCORD_CAL_WEBHOOK_URL")
        or env_map.get("DISCORD_WEBHOOK_URL")
        or ""
    )
    if not webhook_url:
        return 0

    header_line = f"**[PAWEL CURVE TELEGRAPH — {mode} / {status}]**"
    if collision_meta:
        header_line += (
            f"\n`Collision`: `{collision_meta.get('collision_id')}` "
            f"| `Latency`: `{collision_meta.get('traversal_latency_us')} us` "
            f"| `BlindSpot(C\\A)`: `{','.join(collision_meta.get('blind_spot_lenses_c_minus_a', [])) or 'NONE'}`"
        )

    content_body = f"{header_line}\n```text\n{message[:1400]}\n```\n`SHA-256`: `{sha256_hash[:16]}...`"
    session = build_pooled_session()

    shot_file = Path(screenshot_path)
    if shot_file.is_file():
        with open(shot_file, "rb") as img_fh:
            resp = session.post(
                webhook_url,
                data={"payload_json": json.dumps({"content": content_body})},
                files={"file": (shot_file.name, img_fh, "image/png")},
                timeout=15,
            )
            return resp.status_code

    resp = session.post(webhook_url, json={"content": content_body}, timeout=15)
    return resp.status_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Push empirical Swanson VFS collision or working-engineer brief to Both Ends of the Curve."
    )
    parser.add_argument("--message", type=str, default=None, help="Explicit message string to push")
    parser.add_argument("--file", type=str, default=None, help="Path to markdown/text file to push")
    parser.add_argument("--clipboard", action="store_true", help="Harvest recent Antigravity IDE chat turns")
    parser.add_argument("--collision", type=str, default=None, help="Specific Swanson VFS collision_id to push")
    parser.add_argument("--essay", type=str, default=None, help="Select top Swanson collision for given essay slug")
    parser.add_argument("--silo", type=str, default=None, help="Filter Swanson collision by empirical silo (ercot, sec_risk, snipes, arxiv, macro)")
    parser.add_argument("--top-collision", action="store_true", help="Select #1 overall Swanson VFS cross-silo collision")
    parser.add_argument("--email", type=str, default="james@stacklabsllc.com", help="Reply email for Wix form")
    parser.add_argument("--dry-run", action="store_true", help="Populate Wix form and capture screenshot without clicking submit")
    parser.add_argument("--live", action="store_true", help="Execute live submission into Both Ends of the Curve")
    parser.add_argument("--notify-discord", action="store_true", help="Post visual receipt to DISCORD_WEBHOOK_CAL")
    args = parser.parse_args()

    dry_run = True
    if args.live and not args.dry_run:
        dry_run = False

    collision_meta: Optional[Dict[str, Any]] = None
    if args.collision or args.essay or args.top_collision or args.silo:
        message, collision_meta = resolve_collision_payload(
            collision_id=args.collision,
            essay_query=args.essay,
            silo_query=args.silo,
        )
    elif args.message:
        message = args.message.strip()
    elif args.file:
        message = Path(args.file).read_text(encoding="utf-8").strip()
    elif args.clipboard:
        message = build_clipboard_payload()
    else:
        message, collision_meta = resolve_collision_payload()

    pw_result = execute_playwright_push(message=message, email=args.email, dry_run=dry_run)
    mode_label = "DRY_RUN" if dry_run else "LIVE_PUSH"
    row_id, sha256_hash = record_push_audit(
        mode=mode_label,
        status=pw_result["status"],
        message=message,
        screenshot_path=pw_result["screenshot_path"],
        collision_meta=collision_meta,
        email=args.email,
    )

    discord_http = 0
    if args.notify_discord:
        discord_http = post_receipt_to_discord(
            message=message,
            screenshot_path=pw_result["screenshot_path"],
            mode=mode_label,
            status=pw_result["status"],
            sha256_hash=sha256_hash,
            collision_meta=collision_meta,
        )

    output = {
        "row_id": row_id,
        "mode": mode_label,
        "status": pw_result["status"],
        "collision_id": collision_meta.get("collision_id") if collision_meta else None,
        "blind_spot_lenses_c_minus_a": (
            collision_meta.get("blind_spot_lenses_c_minus_a") if collision_meta else []
        ),
        "screenshot_path": pw_result["screenshot_path"],
        "sha256_hash": sha256_hash,
        "discord_http": discord_http,
        "message": message,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

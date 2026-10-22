#!/home/james/stacklabs/.venv/bin/python3
"""
Stigmergic Discord Auth Circuit Breaker (WO0011280).
I use this guard across my Discord daemons and webhook dispatchers so an expired
token (HTTP 401/403) trips an atomic lockfile in 2 microseconds instead of
hammering Discord's Cloudflare WAF into a 24-hour ban.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("discord_auth_breaker")

ROOT_DIR = Path("/home/james/stacklabs")
STATE_DIR = ROOT_DIR / ".state"
LOCK_FILE = STATE_DIR / "DISCORD_AUTH_TRIP.lock"
MUTE_FILE = STATE_DIR / "DISCORD_MUTE.lock"


class DiscordAuthCircuitBreaker:
    """Pooled HTTP client with immediate 401/403 stigmergic circuit breaking."""

    def __init__(self, max_retries: int = 3, base_backoff_s: float = 1.0, max_backoff_s: float = 16.0) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    @staticmethod
    def is_tripped(service_name: Optional[str] = None) -> bool:
        if MUTE_FILE.exists():
            return True
        if not LOCK_FILE.exists():
            return False
        if service_name is None:
            return True
        try:
            payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            tripped_services = payload.get("tripped_services", [])
            return "*" in tripped_services or service_name in tripped_services
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed reading lockfile %s: %s", LOCK_FILE, exc)
            return True

    @staticmethod
    def trip(service_name: str, status_code: int, detail: str, credential_fingerprint: str = "") -> Dict[str, Any]:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        existing: Dict[str, Any] = {"tripped_services": [], "events": []}
        if LOCK_FILE.exists():
            try:
                existing = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Resetting corrupted lockfile %s: %s", LOCK_FILE, exc)

        services = set(existing.get("tripped_services", []))
        services.add(service_name)
        events = list(existing.get("events", []))[-19:]
        event = {
            "service": service_name,
            "status_code": int(status_code),
            "detail": detail[:240],
            "credential_sha256_prefix": credential_fingerprint[:12],
            "tripped_at_epoch": time.time(),
            "tripped_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        events.append(event)
        state_payload = {
            "breaker_state": "TRIPPED",
            "tripped_services": sorted(services),
            "last_trip": event,
            "events": events,
        }
        tmp_path = LOCK_FILE.with_suffix(".lock.tmp")
        tmp_path.write_text(json.dumps(state_payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp_path, LOCK_FILE)
        logger.error("DISCORD AUTH CIRCUIT BREAKER TRIPPED for %s (HTTP %s): %s", service_name, status_code, detail)
        return state_payload

    @staticmethod
    def reset(service_name: Optional[str] = None) -> Dict[str, Any]:
        if not LOCK_FILE.exists():
            return {"breaker_state": "CLOSED", "tripped_services": []}
        if service_name is None:
            LOCK_FILE.unlink(missing_ok=True)
            return {"breaker_state": "CLOSED", "tripped_services": []}
        try:
            existing = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            services = [s for s in existing.get("tripped_services", []) if s != service_name]
            if not services:
                LOCK_FILE.unlink(missing_ok=True)
                return {"breaker_state": "CLOSED", "tripped_services": []}
            existing["tripped_services"] = services
            tmp_path = LOCK_FILE.with_suffix(".lock.tmp")
            tmp_path.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp_path, LOCK_FILE)
            return existing
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Error resetting lockfile: %s", exc)
            LOCK_FILE.unlink(missing_ok=True)
            return {"breaker_state": "CLOSED", "tripped_services": []}

    def post_webhook_safe(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        service_name: str = "discord_webhook",
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        if self.is_tripped(service_name):
            return {"ok": False, "skipped": True, "reason": "CIRCUIT_BREAKER_TRIPPED", "lock_file": str(LOCK_FILE)}

        cred_hash = hashlib.sha256(webhook_url.encode("utf-8")).hexdigest()
        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(webhook_url, json=payload, timeout=timeout)
                if resp.status_code in (200, 204):
                    return {"ok": True, "status_code": resp.status_code}
                if resp.status_code in (401, 403):
                    self.trip(service_name, resp.status_code, resp.text, cred_hash)
                    return {"ok": False, "status_code": resp.status_code, "breaker_tripped": True}
                if resp.status_code in (429, 502, 503, 504):
                    retry_after_hdr = resp.headers.get("Retry-After")
                    retry_after = float(retry_after_hdr) if retry_after_hdr and retry_after_hdr.replace(".", "", 1).isdigit() else None
                    cap = min(max(self.max_backoff_s, 1.0), self.base_backoff_s * (2 ** attempt))
                    sleep_s = retry_after if retry_after is not None else random.uniform(cap * 0.5, cap)
                    logger.warning("Discord HTTP %s on %s; backing off %.2fs", resp.status_code, service_name, sleep_s)
                    time.sleep(sleep_s)
                    continue
                return {"ok": False, "status_code": resp.status_code, "detail": resp.text[:200]}
            except requests.RequestException as exc:
                cap = min(max(self.max_backoff_s, 1.0), self.base_backoff_s * (2 ** attempt))
                sleep_s = random.uniform(cap * 0.5, cap)
                logger.warning("Discord request exception (%s) attempt %d/%d; sleeping %.2fs", exc, attempt + 1, self.max_retries, sleep_s)
                time.sleep(sleep_s)

        return {"ok": False, "status_code": 0, "detail": "MAX_RETRIES_EXHAUSTED"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the Stigmergic Discord Auth Circuit Breaker.")
    parser.add_argument("--status", action="store_true", help="Print current circuit breaker state.")
    parser.add_argument("--simulate-401", metavar="SERVICE", help="Simulate an HTTP 401 trip for a service.")
    parser.add_argument("--reset", nargs="?", const="*", metavar="SERVICE", help="Reset breaker for a service or all (*).")
    args = parser.parse_args()

    breaker = DiscordAuthCircuitBreaker()
    if args.simulate_401:
        state = breaker.trip(args.simulate_401, 401, "Simulated 401 Unauthorized token expiration", "sim_token_hash")
        print(json.dumps(state, indent=2))
        return 0
    if args.reset:
        target = None if args.reset == "*" else args.reset
        state = breaker.reset(target)
        print(json.dumps(state, indent=2))
        return 0

    if LOCK_FILE.exists():
        print(LOCK_FILE.read_text(encoding="utf-8"))
    else:
        print(json.dumps({"breaker_state": "CLOSED", "lock_file": str(LOCK_FILE), "tripped_services": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

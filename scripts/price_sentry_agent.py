#!/usr/bin/env python3
"""
Sovereign Price Shield — Lightweight Edge Sentry Agent
=======================================================
Runs on RAM-constrained Tailscale edge nodes (Pi Zero 2 W: hobbes, grogu-1).
Zero pip dependencies beyond stdlib + python3-requests (apt-installed).

Listens on port 8710. Accepts scrape jobs from clio orchestrator via POST /scrape.
Returns price telemetry JSON from this node's unique public ISP IP.

Deploy:
    scp scripts/price_sentry_agent.py <node>:/home/<user>/price_sentry_agent.py
    ssh <node> "sudo cp /etc/systemd/system/price-sentry.service <path>"
    ssh <node> "sudo systemctl enable --now price-sentry"
"""

import json
import logging
import os
import re
import socket
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SENTRY_PORT = int(os.environ.get("SENTRY_PORT", "8710"))
SENTRY_SECRET = os.environ.get("SENTRY_SECRET", "sovereign-sentry-v1")
REQUEST_TIMEOUT = int(os.environ.get("SENTRY_TIMEOUT", "25"))
NODE_NAME = socket.gethostname()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] price-sentry %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("price_sentry")

# ---------------------------------------------------------------------------
# UA Profile Definitions (mirrors price_shield_engine.py profiles)
# ---------------------------------------------------------------------------
PROFILES: dict[str, dict[str, Any]] = {
    "baseline_desktop": {
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "accept_language": "en-US,en;q=0.9",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "sec_ch_ua": '"Chromium";v="128", "Not;A Brand";v="24", "Google Chrome";v="128"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Linux"',
    },
    "flagship_mobile": {
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
            "Mobile/15E148 Safari/604.1"
        ),
        "accept_language": "en-US,en;q=0.9",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "sec_ch_ua": '"Safari";v="18"',
        "sec_ch_ua_mobile": "?1",
        "sec_ch_ua_platform": '"iOS"',
    },
    "budget_android": {
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 14; SM-A155F Build/UP1A.231005.007) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 "
            "Mobile Safari/537.36"
        ),
        "accept_language": "en-US,en;q=0.8",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "sec_ch_ua": '"Chromium";v="128", "Android WebView";v="128"',
        "sec_ch_ua_mobile": "?1",
        "sec_ch_ua_platform": '"Android"',
    },
}

# Tracker beacon domains intercepted (logged in response, not blocked at network level)
TRACKER_SIGNATURES = [
    "bloomreach.com", "liveramp.com", "connect.facebook.net",
    "criteo.com", "doubleclick.net", "clarity.ms", "hotjar.com",
    "mastercard.us", "addthis.com", "quantserve.com",
    "scorecardresearch.com", "taboola.com", "outbrain.com",
]

# Surveillance query params to strip for clean URL
SURVEILLANCE_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "irclickid", "affiliate_id",
    "tracking_id", "session_id", "ref", "referrer", "clickid",
    "_ga", "_gid", "mc_cid", "mc_eid",
}

# ---------------------------------------------------------------------------
# Price extraction helpers
# ---------------------------------------------------------------------------
PRICE_RE = re.compile(
    r"""(?:
        "price"\s*:\s*"?([\d,]+\.?\d*)"?   # JSON-LD "price": "49.99"
        |itemprop="price"\s+content="([\d,.]+)"   # microdata
        |content="([\d,.]+)"\s+itemprop="price"
        |<meta[^>]+property="product:price:amount"[^>]+content="([\d,.]+)"
        |<meta[^>]+property="og:price:amount"[^>]+content="([\d,.]+)"
    )""",
    re.IGNORECASE | re.VERBOSE,
)

DOM_PRICE_RE = re.compile(
    r'\$\s*([\d,]+\.\d{2})\b',
)


def _parse_price(raw: str) -> float | None:
    """Normalize a raw price string to float."""
    try:
        return float(raw.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def extract_price_from_html(html: str) -> float | None:
    """
    Multi-strategy price extraction:
    1. JSON-LD schema.org/Product offers.price
    2. OpenGraph / meta product:price:amount
    3. Microdata itemprop=price
    4. DOM regex fallback ($XX.XX pattern — lowest-confidence)
    """
    for m in PRICE_RE.finditer(html):
        for group in m.groups():
            if group:
                price = _parse_price(group)
                if price and 0.01 < price < 100_000:
                    return price

    # DOM fallback — take the median of all dollar-formatted prices found
    dom_prices = [
        p for raw in DOM_PRICE_RE.findall(html)
        if (p := _parse_price(raw)) and 0.01 < p < 100_000
    ]
    if dom_prices:
        dom_prices.sort()
        return dom_prices[len(dom_prices) // 2]

    return None


def detect_trackers(html: str) -> list[str]:
    """Identify surveillance beacon domains present in page source."""
    found = []
    html_lower = html.lower()
    for sig in TRACKER_SIGNATURES:
        if sig in html_lower:
            found.append(sig)
    return found


def clean_url(url: str) -> str:
    """Strip surveillance parameters and append clean checkout flags."""
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    cleaned_qs = {k: v for k, v in qs.items() if k.lower() not in SURVEILLANCE_PARAMS}
    cleaned_qs["clean_guest"] = ["1"]
    cleaned_qs["untracked"] = ["true"]
    new_query = urllib.parse.urlencode(cleaned_qs, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))


# ---------------------------------------------------------------------------
# Core scrape function
# ---------------------------------------------------------------------------
def scrape_profile(url: str, profile_key: str) -> dict[str, Any]:
    """
    Fetch URL with the given UA profile and extract price telemetry.
    Returns structured result dict compatible with PriceShieldEngine format.
    """
    if not REQUESTS_OK:
        return {"error": "requests library not available", "profile": profile_key}

    profile = PROFILES.get(profile_key)
    if not profile:
        return {"error": f"unknown profile: {profile_key}", "profile": profile_key}

    session = requests.Session()
    retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    headers = {
        "User-Agent": profile["user_agent"],
        "Accept": profile["accept"],
        "Accept-Language": profile["accept_language"],
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Ch-Ua": profile.get("sec_ch_ua", ""),
        "Sec-Ch-Ua-Mobile": profile.get("sec_ch_ua_mobile", "?0"),
        "Sec-Ch-Ua-Platform": profile.get("sec_ch_ua_platform", '"Linux"'),
    }

    result: dict[str, Any] = {
        "profile": profile_key,
        "url": url,
        "node": NODE_NAME,
        "price": None,
        "currency": "USD",
        "blocked_trackers": [],
        "clean_url": clean_url(url),
        "http_status": None,
        "error": None,
        "extraction_method": None,
    }

    try:
        resp = session.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        result["http_status"] = resp.status_code
        result["final_url"] = resp.url

        if resp.status_code == 200:
            html = resp.text
            price = extract_price_from_html(html)
            result["price"] = price
            result["blocked_trackers"] = detect_trackers(html)
            if price:
                result["extraction_method"] = "html_parse"
        else:
            result["error"] = f"HTTP {resp.status_code}"

    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"connection_error: {e}"
    except Exception as e:
        result["error"] = f"unexpected: {e}"
        logger.exception("Scrape error for profile %s on %s", profile_key, url)

    finally:
        session.close()

    return result


# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------
class SentryHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler — no framework deps, pure stdlib."""

    server_version = "PriceSentry/1.0"
    sys_version = ""  # suppress Python version header

    def log_message(self, fmt, *args):  # noqa: D102
        logger.info(fmt, *args)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Sentry-Node", NODE_NAME)
        self.end_headers()
        self.wfile.write(body)

    def _check_auth(self) -> bool:
        auth = self.headers.get("X-Sentry-Secret", "")
        return auth == SENTRY_SECRET

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {
                "status": "online",
                "node": NODE_NAME,
                "requests_available": REQUESTS_OK,
                "profiles": list(PROFILES.keys()),
            })
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/scrape":
            self._send_json(404, {"error": "not found"})
            return

        if not self._check_auth():
            self._send_json(403, {"error": "forbidden"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError):
            self._send_json(400, {"error": "invalid JSON"})
            return

        url = body.get("url", "").strip()
        profiles = body.get("profiles", list(PROFILES.keys()))

        if not url:
            self._send_json(400, {"error": "url is required"})
            return

        logger.info("Scrape job: url=%s profiles=%s", url, profiles)

        results = {}
        for profile_key in profiles:
            if profile_key in PROFILES:
                results[profile_key] = scrape_profile(url, profile_key)
            else:
                results[profile_key] = {"error": f"unknown profile: {profile_key}"}

        self._send_json(200, {
            "node": NODE_NAME,
            "url": url,
            "results": results,
        })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    if not REQUESTS_OK:
        logger.error(
            "python3-requests not available. Install with: sudo apt install python3-requests"
        )

    logger.info("Sovereign Price Sentry starting on port %d (node: %s)", SENTRY_PORT, NODE_NAME)
    server = HTTPServer(("0.0.0.0", SENTRY_PORT), SentryHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Sentry shutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

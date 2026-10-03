#!/usr/bin/env python3
"""
parity_check.py -- READ-ONLY comparison of the live server vs staging v2.

    python3 parity_check.py                       # 8088 (live) vs 8089 (v2)
    python3 parity_check.py --a 8088 --b 8089

GET requests ONLY. It never sends POST, so it cannot trigger kill_runner,
uploads (which rclone to your Drive), sync/execute, approvals, work-order
staging, or predict trades -- all of which act on state shared with the live
server. Exit code 0 = parity, 1 = differences.

Compares: HTTP status, content-type, and
  * HTML/static bodies  -> must be byte-identical
  * JSON bodies         -> must have the same key structure (values like
                           timestamps/vitals legitimately differ between two calls)
"""
import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request

# (path, kind)   kind: "exact" = body must match, "shape" = JSON key structure must match
GETS = [
    ("/", "exact"),
    ("/cockpit", "exact"),
    ("/sync", "exact"),
    ("/pulse", "exact"),
    ("/api/pulse", "shape"),
    ("/api/drops", "shape"),
    ("/api/sync/envelopes", "shape"),
    ("/api/sync/staged", "shape"),
    ("/api/cockpit/queue", "shape"),
    ("/api/cockpit/approvals", "shape"),
    ("/api/cockpit/cmdb_lite", "shape"),
    ("/api/cockpit/alpha_trader_stats", "shape"),
    ("/api/horizon/evidence/DOC_SEC_INDENTURE?start=142&end=401", "exact"),
    ("/api/horizon/evidence/DOC_LEGAL_1889?start=179&end=335", "exact"),
    ("/api/horizon/evidence/DOC_EMERGENCY_TOURNIQUET?start=375&end=519", "exact"),
    ("/api/horizon/evidence/DOES_NOT_EXIST", "exact"),   # 404 path must match too
    ("/api/market/ohlcv/AAPL", "shape"),
    ("/api/market/ohlcv/NOPE", "shape"),
    ("/api/predict/state", "shape"),
]


def fetch(port, path):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()
    except Exception as e:  # connection refused etc.
        return None, "", str(e).encode()


def shape(x):
    if isinstance(x, dict):
        return {k: shape(v) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [shape(x[0])] if x else []
    return type(x).__name__ if x is not None else "null"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=8088, help="live")
    ap.add_argument("--b", type=int, default=8089, help="staging v2")
    args = ap.parse_args()

    failures = 0
    for path, kind in GETS:
        sa, ta, ba = fetch(args.a, path)
        sb, tb, bb = fetch(args.b, path)
        ok, why = True, ""
        if sa is None or sb is None:
            ok, why = False, f"unreachable (live={sa}, v2={sb})"
        elif sa != sb:
            ok, why = False, f"status {sa} vs {sb}"
        elif ta.split(";")[0] != tb.split(";")[0]:
            ok, why = False, f"content-type {ta!r} vs {tb!r}"
        elif kind == "exact" and ba != bb:
            ok, why = False, f"body differs ({hashlib.sha256(ba).hexdigest()[:10]} vs {hashlib.sha256(bb).hexdigest()[:10]})"
        elif kind == "shape" and "json" in ta:
            try:
                if shape(json.loads(ba)) != shape(json.loads(bb)):
                    ok, why = False, "JSON key structure differs"
            except Exception as e:
                ok, why = False, f"unparseable JSON: {e}"
        print(f"{'PASS' if ok else 'FAIL'}  {sa or '---'}  {path}" + ("" if ok else f"   <- {why}"))
        failures += not ok

    print(f"\n{len(GETS) - failures}/{len(GETS)} routes at parity")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011216: DualStreamSplitView Discord Burst & Supervisor UI
Path: /home/james/stacklabs/scripts/verify_wo0011216_faas_discord_ui.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
"""

import glob
import re
import sys
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
TSX_PATH = REPO_ROOT / "apps" / "faas" / "src" / "components" / "DualStreamSplitView.tsx"
DIST_ASSETS_DIR = REPO_ROOT / "apps" / "faas" / "dist" / "assets"

EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "]+",
    flags=re.UNICODE,
)


def verify_tsx_source_invariants() -> None:
    assert TSX_PATH.exists(), f"Missing {TSX_PATH}"
    src = TSX_PATH.read_text(encoding="utf-8")

    # 1. Required API endpoints and UI telemetry markers
    required_tokens = [
        "/api/faas/lexicon/bursts",
        "/api/faas/lexicon/discord_bursts",
        "/api/faas/lexicon/discord_status",
        "/api/faas/lexicon/drilldown",
        "velocity_mps",
        "DISCORD VELOCITY:",
        "DISCORD GATEWAY BURST",
        "UnifiedViewNav",
        "#0B0D13",
    ]
    for token in required_tokens:
        assert token in src, f"Missing required token in DualStreamSplitView.tsx: {token}"

    # 2. Gandalf UI Craft & OPSEC checks (zero emojis, zero hardcoded UGA_BAMA fallback, zero leaked filesystem terms)
    assert not EMOJI_RE.search(src), "Banned Unicode emoji detected in DualStreamSplitView.tsx"
    assert "UGA_BAMA" not in src, "Banned hardcoded UGA_BAMA fallback detected"
    assert "/dev/shm" not in src and "SQLite WAL" not in src, "Banned internal storage term leaked into UI TSX"
    print("[PASS] 1/2 DualStreamSplitView.tsx source invariants & Gandalf UI Craft verified.")


def verify_production_bundle() -> None:
    js_files = sorted(glob.glob(str(DIST_ASSETS_DIR / "index-*.js")))
    assert js_files, f"No compiled index-*.js bundle found in {DIST_ASSETS_DIR}"
    bundle_text = "\n".join(Path(p).read_text(encoding="utf-8", errors="ignore") for p in js_files)
    for expected in [
        "/api/faas/lexicon/discord_bursts",
        "/api/faas/lexicon/discord_status",
        "DISCORD VELOCITY:",
        "DISCORD GATEWAY BURST",
    ]:
        assert expected in bundle_text, f"Compiled production bundle missing token: {expected}"
    print("[PASS] 2/2 Compiled Vite production bundle verified in apps/faas/dist/assets/.")


def main() -> None:
    verify_tsx_source_invariants()
    verify_production_bundle()
    print("\n=== ALL WO0011216 DISCORD SHIBBOLETH INSPECTOR UI CHECKS PASSED ===")


if __name__ == "__main__":
    main()

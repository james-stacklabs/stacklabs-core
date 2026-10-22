#!/usr/bin/env python3
"""
Sovereign OS: ATF Headless Playwright Visual Digital Twin Verification Harness
Path: /home/james/stacklabs/scripts/atf_visual_twin_audit.py
Symlink: /home/james/scripts/atf_visual_twin_audit.py

Mandate:
1. Automated, headless verification of UI layout geometry and visual stability.
2. Hard bounding box assertions (e.g. element height <= 145px) preventing vertical bloat.
3. Viewport scroll spill assertions (zero unexpected horizontal or vertical document scroll).
4. Visual snapshot pixel mismatch comparison (delta <= 5.0% threshold).
5. Automatic generation of failure diff artifacts in /home/james/evidence/visual_audits/diff_<TIMESTAMP>.png.
6. Execution logging to /home/james/logs/aggie_pipeline.log.
"""

import sys
import os

# Invariant 35: Re-exec with canonical venv if not already active
VENV_PYTHON = "/home/james/stacklabs/.venv/bin/python3"
if sys.executable != VENV_PYTHON and os.path.exists(VENV_PYTHON):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

DEFAULT_CONTRACTS_DIR = Path("/home/james/contracts/visual_twins")
DEFAULT_BASELINE_DIR = Path("/home/james/evidence/visual_twins")
DEFAULT_EVIDENCE_DIR = Path("/home/james/evidence/visual_audits")
DEFAULT_LOG_FILE = Path("/home/james/logs/aggie_pipeline.log")


def compare_visual_snapshots(
    baseline_path: Path,
    current_shot_path: Path,
    diff_output_path: Optional[Path] = None,
    color_tolerance: int = 15
) -> Tuple[float, int, int]:
    """
    Compare baseline image with current image using NumPy vectorization.
    Returns: (delta_percentage, mismatched_pixels, total_pixels)
    """
    img_base = Image.open(baseline_path).convert("RGBA")
    img_curr = Image.open(current_shot_path).convert("RGBA")

    w1, h1 = img_base.size
    w2, h2 = img_curr.size
    max_w = max(w1, w2)
    max_h = max(h1, h2)

    base_canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
    curr_canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
    base_canvas.paste(img_base, (0, 0))
    curr_canvas.paste(img_curr, (0, 0))

    arr_base = np.array(base_canvas, dtype=np.int16)
    arr_curr = np.array(curr_canvas, dtype=np.int16)

    # Compute absolute channel difference (RGBA)
    diff = np.abs(arr_base - arr_curr)
    # A pixel is mismatched if any channel diff exceeds tolerance
    mismatch_mask = np.any(diff > color_tolerance, axis=2)

    total_pixels = max_w * max_h
    mismatched_pixels = int(np.sum(mismatch_mask))
    delta_pct = (mismatched_pixels / total_pixels) * 100.0 if total_pixels > 0 else 0.0

    if diff_output_path and delta_pct > 0:
        diff_arr = np.array(curr_canvas, dtype=np.uint8)
        # Highlight mismatched pixels in bright red/magenta
        diff_arr[mismatch_mask] = [255, 0, 80, 255]
        diff_img = Image.fromarray(diff_arr, mode="RGBA")
        diff_output_path.parent.mkdir(parents=True, exist_ok=True)
        diff_img.save(str(diff_output_path))

    return delta_pct, mismatched_pixels, total_pixels


def append_to_pipeline_log(
    log_file: Path,
    ticket_id: str,
    status: str,
    target: str,
    height: float,
    delta: float,
    duration: float,
    details: str
):
    """Append structured entry to aggie_pipeline.log."""
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"[{ts}] [{ticket_id}] ATF_VISUAL_TWIN_AUDIT "
            f"status={status} target={target} height={height:.1f}px "
            f"delta={delta:.2f}% duration={duration:.2f}s details=\"{details}\"\n"
        )
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"[WARN] Failed to write to pipeline log {log_file}: {e}")


def load_layout_contract(contract_path: Optional[Path], target_name: str) -> Dict[str, Any]:
    """Load layout schema invariant contract from JSON file if available."""
    contract = {
        "target": target_name,
        "selector": "#hero-vector-hud",
        "max_height": 145.0,
        "min_height": 0.0,
        "max_visual_delta_pct": 5.0,
        "allow_horizontal_scroll": False,
        "allow_vertical_scroll": False,
        "viewports": [
            {"name": "desktop", "width": 1280, "height": 720},
            {"name": "mobile", "width": 390, "height": 844}
        ]
    }

    resolved_path = None
    if contract_path and contract_path.exists():
        resolved_path = contract_path
    else:
        candidate = DEFAULT_CONTRACTS_DIR / f"{target_name}.json"
        if candidate.exists():
            resolved_path = candidate

    if resolved_path and resolved_path.exists():
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                contract.update(loaded)
                print(f"[CONTRACT] Loaded layout invariants from: {resolved_path}")
        except Exception as e:
            print(f"[WARN] Failed to parse contract {resolved_path}: {e}")

    return contract


def run_audit(
    url: str,
    target: str = "hero_vector_hud",
    selector: Optional[str] = None,
    max_height: Optional[float] = None,
    max_delta: Optional[float] = None,
    contract_path: Optional[Path] = None,
    save_baseline: bool = False,
    ticket_id: str = "WO0010487",
    log_file: Path = DEFAULT_LOG_FILE,
    baseline_dir: Path = DEFAULT_BASELINE_DIR,
    evidence_dir: Path = DEFAULT_EVIDENCE_DIR,
    allow_horizontal_scroll: Optional[bool] = None,
    allow_vertical_scroll: Optional[bool] = None,
    color_tolerance: int = 15
) -> int:
    """
    Execute headless Playwright Visual Digital Twin Audit.
    Returns: 0 on success, 1 on failure.
    """
    start_time = time.time()
    contract = load_layout_contract(contract_path, target)

    # CLI arguments override contract defaults
    final_selector = selector or contract.get("selector", "#hero-vector-hud")
    final_max_height = float(max_height if max_height is not None else contract.get("max_height", 145.0))
    final_max_delta = float(max_delta if max_delta is not None else contract.get("max_visual_delta_pct", 5.0))
    final_allow_h_scroll = allow_horizontal_scroll if allow_horizontal_scroll is not None else contract.get("allow_horizontal_scroll", False)
    final_allow_v_scroll = allow_vertical_scroll if allow_vertical_scroll is not None else contract.get("allow_vertical_scroll", False)
    viewports = contract.get("viewports", [
        {"name": "desktop", "width": 1280, "height": 720},
        {"name": "mobile", "width": 390, "height": 844}
    ])

    baseline_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Normalize local file paths to file:// URLs
    if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("file://"):
        resolved_file = Path(url).resolve()
        if resolved_file.exists():
            url = f"file://{resolved_file}"

    print("=" * 80)
    print("⚡ SOVEREIGN OS ATF: PLAYWRIGHT VISUAL DIGITAL TWIN AUDIT")
    print(f"Target:       {target}")
    print(f"URL:          {url}")
    print(f"Selector:     {final_selector}")
    print(f"Max Height:   {final_max_height}px")
    print(f"Max Delta:    {final_max_delta}%")
    print(f"Viewports:    {[vp['name'] for vp in viewports]}")
    print("=" * 80)

    violations: List[str] = []
    max_observed_height = 0.0
    max_observed_delta = 0.0

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in viewports:
            vp_name = vp.get("name", "custom")
            vp_w = vp.get("width", 1280)
            vp_h = vp.get("height", 720)

            print(f"\n--- VIEWPORT: {vp_name.upper()} ({vp_w}x{vp_h}) ---")
            context = browser.new_context(viewport={"width": vp_w, "height": vp_h})
            page = context.new_page()

            try:
                page.goto(url, wait_until="load", timeout=15000)
                # Allow layout settling
                page.wait_for_timeout(300)
            except Exception as e:
                msg = f"Navigation error on {vp_name}: {e}"
                print(f"[FAIL] {msg}")
                violations.append(msg)
                context.close()
                continue

            # 1. Geometry & Bounding Box Assertions
            locator = page.locator(final_selector)
            count = locator.count()
            if count == 0:
                msg = f"Element '{final_selector}' not found in DOM ({vp_name})"
                print(f"[FAIL] {msg}")
                violations.append(msg)
                context.close()
                continue

            elem = locator.first
            box = elem.bounding_box()
            if not box:
                msg = f"Element '{final_selector}' has no bounding box / not visible ({vp_name})"
                print(f"[FAIL] {msg}")
                violations.append(msg)
                context.close()
                continue

            elem_h = float(box["height"])
            elem_w = float(box["width"])
            if elem_h > max_observed_height:
                max_observed_height = elem_h

            print(f"[GEOMETRY] Element {final_selector}: width={elem_w:.1f}px, height={elem_h:.1f}px")

            # Hard assertion: height <= max_height (prevents vertical bloat)
            if elem_h > final_max_height:
                msg = (
                    f"Bounding box height violation ({vp_name}): {elem_h:.2f}px "
                    f"exceeds contract maximum limit of {final_max_height:.2f}px"
                )
                print(f"[FAIL] 🛑 {msg}")
                violations.append(msg)
            else:
                print(f"[PASS] ✅ Height constraint met: {elem_h:.1f}px <= {final_max_height:.1f}px")

            # Viewport assertion: verify no unexpected scroll spill
            spill = page.evaluate("""() => {
                const doc = document.documentElement;
                const body = document.body;
                const scrollW = Math.max(doc.scrollWidth, body ? body.scrollWidth : 0);
                const scrollH = Math.max(doc.scrollHeight, body ? body.scrollHeight : 0);
                const winW = window.innerWidth;
                const winH = window.innerHeight;
                return {
                    scrollW: scrollW,
                    winW: winW,
                    scrollH: scrollH,
                    winH: winH,
                    hasHSpill: scrollW > winW,
                    hasVSpill: scrollH > winH
                };
            }""")

            if not final_allow_h_scroll and spill.get("hasHSpill"):
                msg = (
                    f"Horizontal scroll spill detected ({vp_name}): "
                    f"scrollWidth={spill['scrollW']}px > innerWidth={spill['winW']}px"
                )
                print(f"[FAIL] 🛑 {msg}")
                violations.append(msg)
            else:
                print(f"[PASS] ✅ Horizontal viewport intact ({spill['scrollW']}px <= {spill['winW']}px)")

            if not final_allow_v_scroll and spill.get("hasVSpill"):
                msg = (
                    f"Vertical document scroll spill detected ({vp_name}): "
                    f"scrollHeight={spill['scrollH']}px > innerHeight={spill['winH']}px"
                )
                print(f"[FAIL] 🛑 {msg}")
                violations.append(msg)
            else:
                print(f"[PASS] ✅ Vertical viewport intact ({spill['scrollH']}px <= {spill['winH']}px)")

            # 2. Visual Snapshot Comparison
            curr_shot_path = evidence_dir / f"current_{target}_{vp_name}.png"
            try:
                elem.screenshot(path=str(curr_shot_path))
            except Exception as e:
                msg = f"Failed to capture element screenshot ({vp_name}): {e}"
                print(f"[FAIL] {msg}")
                violations.append(msg)
                context.close()
                continue

            # Determine baseline candidate paths
            baseline_vp = baseline_dir / f"baseline_{target}_{vp_name}.png"
            baseline_generic = baseline_dir / f"baseline_{target}.png"

            baseline_path = None
            if baseline_vp.exists():
                baseline_path = baseline_vp
            elif vp_name == "desktop" and baseline_generic.exists():
                baseline_path = baseline_generic
            elif len(viewports) == 1 and baseline_generic.exists():
                baseline_path = baseline_generic

            if baseline_path is None or save_baseline:
                target_base = baseline_vp
                curr_shot = Image.open(curr_shot_path)
                curr_shot.save(target_base)
                # Also maintain generic baseline reference
                if vp_name == "desktop" or not baseline_generic.exists():
                    curr_shot.save(baseline_generic)
                print(f"[BASELINE_CREATED] Established new visual baseline: {target_base}")
                delta_pct = 0.0
            else:
                diff_artifact_path = evidence_dir / f"diff_{timestamp_str}.png"
                delta_pct, mismatches, total_pix = compare_visual_snapshots(
                    baseline_path=baseline_path,
                    current_shot_path=curr_shot_path,
                    diff_output_path=diff_artifact_path,
                    color_tolerance=color_tolerance
                )
                if delta_pct > max_observed_delta:
                    max_observed_delta = delta_pct

                print(
                    f"[VISUAL_COMPARE] vs {baseline_path.name}: "
                    f"Delta={delta_pct:.2f}% ({mismatches}/{total_pix} pixels)"
                )

                if delta_pct > final_max_delta:
                    msg = (
                        f"Visual drift delta violation ({vp_name}): {delta_pct:.2f}% "
                        f"exceeds allowable threshold of {final_max_delta:.2f}%. "
                        f"Diff artifact saved to: {diff_artifact_path}"
                    )
                    print(f"[FAIL] 🛑 {msg}")
                    violations.append(msg)
                else:
                    print(f"[PASS] ✅ Visual stability confirmed (Delta {delta_pct:.2f}% <= {final_max_delta:.2f}%)")

            context.close()

        browser.close()

    duration = time.time() - start_time
    passed = len(violations) == 0
    status_str = "SUCCESS" if passed else "FAILED"
    details_str = "All geometric and visual delta assertions passed." if passed else " | ".join(violations)

    append_to_pipeline_log(
        log_file=log_file,
        ticket_id=ticket_id,
        status=status_str,
        target=target,
        height=max_observed_height,
        delta=max_observed_delta,
        duration=duration,
        details=details_str
    )

    print("\n" + "=" * 80)
    if passed:
        print(f"🎉 [ATF VISUAL TWIN AUDIT PASSED] (Duration: {duration:.2f}s)")
        print(f"Target '{target}' meets all geometry and visual stability criteria.")
        print("=" * 80)
        return 0
    else:
        print(f"🛑 [ATF VISUAL TWIN AUDIT FAILED] (Duration: {duration:.2f}s)")
        print(f"{len(violations)} violation(s) detected:")
        for v in violations:
            print(f"  - {v}")
        print("=" * 80)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Sovereign OS ATF Headless Playwright Visual Digital Twin Audit Harness"
    )
    parser.add_argument("--url", required=True, help="Target URL or local HTML file path")
    parser.add_argument("--target", default="hero_vector_hud", help="Target component slug (default: hero_vector_hud)")
    parser.add_argument("--selector", default=None, help="CSS selector for target element (default: #hero-vector-hud)")
    parser.add_argument("--max-height", type=float, default=None, help="Hard maximum height limit in px (default: 145.0)")
    parser.add_argument("--max-delta", type=float, default=None, help="Maximum visual mismatch delta percentage (default: 5.0)")
    parser.add_argument("--contract", type=Path, default=None, help="Path to layout contract JSON file")
    parser.add_argument("--save-baseline", action="store_true", help="Force save current render as baseline")
    parser.add_argument("--ticket", default=os.getenv("TICKET_ID", "WO0010487"), help="SDLC Ticket ID for audit logging")
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_FILE, help="Pipeline log file destination")
    parser.add_argument("--baseline-dir", type=Path, default=DEFAULT_BASELINE_DIR, help="Directory for baseline snapshots")
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR, help="Directory for audit diffs")
    parser.add_argument("--allow-horizontal-scroll", action="store_true", default=None, help="Allow horizontal scroll spill")
    parser.add_argument("--allow-vertical-scroll", action="store_true", default=None, help="Allow vertical scroll spill")
    parser.add_argument("--color-tolerance", type=int, default=15, help="Per-channel color tolerance (0-255)")

    args = parser.parse_args()

    exit_code = run_audit(
        url=args.url,
        target=args.target,
        selector=args.selector,
        max_height=args.max_height,
        max_delta=args.max_delta,
        contract_path=args.contract,
        save_baseline=args.save_baseline,
        ticket_id=args.ticket,
        log_file=args.log_file,
        baseline_dir=args.baseline_dir,
        evidence_dir=args.evidence_dir,
        allow_horizontal_scroll=args.allow_horizontal_scroll,
        allow_vertical_scroll=args.allow_vertical_scroll,
        color_tolerance=args.color_tolerance
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

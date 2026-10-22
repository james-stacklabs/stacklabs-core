#!/usr/bin/env python3
"""
Re-render Executive Prospectus HTML and PDF files for existing audits
StackLabs LLC - Smyrna, GA
Tool #49: Prospect Recon Sentinel
"""

import sys
import os

try:
    import playwright
except ImportError:
    venv_py = "/home/james/stacklabs/.venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)
    raise

import asyncio
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, List

from playwright.async_api import async_playwright

from prospect_recon_sentinel import (
    DEFAULT_DB_PATH,
    ARTIFACT_BASE_DIR,
    generate_executive_prospectus_html,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ProspectusReRenderer")

TARGET_SLUGS = [
    "johnny-carroll-custom-kitchens",
    "davidson-homes-malone",
    "stacklabs-llc",
    "better-properties-of-san-juan-islands",
]

TODAY_DIR = Path("/home/james/sovereign_inbox/today")


async def rerender_prospectus(
    conn: sqlite3.Connection,
    slug: str,
    browser_context,
) -> bool:
    prospect_row = conn.execute(
        "SELECT * FROM prospects WHERE prospect_id = ?", (slug,)
    ).fetchone()

    if not prospect_row:
        logger.warning(f"Prospect '{slug}' not found in database.")
        return False

    prospect = dict(prospect_row)

    run_row = conn.execute(
        "SELECT * FROM serp_audit_runs WHERE prospect_id = ? ORDER BY executed_at DESC LIMIT 1",
        (slug,),
    ).fetchone()

    if not run_row:
        logger.warning(f"No audit runs found for prospect '{slug}'.")
        return False

    run = dict(run_row)
    run_id = run["run_id"]

    results_rows = conn.execute(
        """
        SELECT skr.*, tk.keyword, tk.estimated_ticket_value, tk.intent_category
        FROM serp_keyword_results skr
        JOIN target_keywords tk ON skr.keyword_id = tk.keyword_id
        WHERE skr.run_id = ?
        ORDER BY skr.created_at ASC
        """,
        (run_id,),
    ).fetchall()

    if not results_rows:
        logger.warning(f"No keyword results found for run '{run_id}'.")
        return False

    summary_rows = []
    for r in results_rows:
        rank_val = (
            f"#{r['prospect_organic_rank']}"
            if r["prospect_organic_rank"] is not None
            else "Off-SERP (>30)"
        )
        top_3 = [
            u
            for u in [
                r["top_competitor_url_1"],
                r["top_competitor_url_2"],
                r["top_competitor_url_3"],
            ]
            if u
        ]
        summary_rows.append(
            {
                "keyword": r["keyword"],
                "ticket": float(r["estimated_ticket_value"]),
                "category": r["intent_category"],
                "prospect_rank": rank_val,
                "top_competitors": top_3,
                "aio_present": bool(r["ai_overview_present"]),
                "in_aio": bool(r["prospect_in_ai_overview"]),
                "html_hash": r["html_sha256"],
            }
        )

    html_content = generate_executive_prospectus_html(
        target_name=prospect["business_name"],
        prospect_slug=slug,
        vertical=prospect["vertical"],
        city=prospect["city"],
        state=prospect["state"],
        run_id=run_id,
        summary_rows=summary_rows,
        lat=float(prospect["latitude"]),
        lon=float(prospect["longitude"]),
        legacy_url=prospect.get("legacy_url"),
        edge_url=prospect.get("edge_showroom_url"),
    )

    day0_dir = ARTIFACT_BASE_DIR / slug / "day_0"
    day0_dir.mkdir(parents=True, exist_ok=True)

    html_path = day0_dir / f"{slug}_day_0_executive_prospectus.html"
    pdf_path = day0_dir / f"{slug}_day_0_executive_prospectus.pdf"

    html_path.write_text(html_content, encoding="utf-8")
    logger.info(f"Wrote updated HTML prospectus: {html_path}")

    # Mirror HTML to timestamp subfolders
    for sub in day0_dir.iterdir():
        if sub.is_dir():
            (sub / f"{slug}_day_0_executive_prospectus.html").write_text(
                html_content, encoding="utf-8"
            )

    # Render PDF via Playwright
    page = await browser_context.new_page()
    await page.set_content(html_content, wait_until="networkidle")

    await page.pdf(
        path=str(pdf_path),
        format="Letter",
        print_background=True,
        margin={"top": "0.5in", "bottom": "0.5in", "left": "0.6in", "right": "0.6in"},
    )
    logger.info(f"Rendered institutional Letter PDF: {pdf_path}")

    # Mirror PDF to timestamp subfolders
    for sub in day0_dir.iterdir():
        if sub.is_dir():
            shutil.copyfile(pdf_path, sub / f"{slug}_day_0_executive_prospectus.pdf")

    # If Johnny Carroll, capture high-res Playwright visual twin
    if slug == "johnny-carroll-custom-kitchens":
        TODAY_DIR.mkdir(parents=True, exist_ok=True)
        twin_path = TODAY_DIR / "wo0010297_johnny_carroll_pdf_twin.png"
        # Set viewport to standard US Letter proportions (e.g. 816x1056 at 96dpi, or 1020x1320)
        await page.set_viewport_size({"width": 900, "height": 1165})
        await page.screenshot(path=str(twin_path), full_page=True)
        logger.info(f"Captured visual twin: {twin_path}")

    await page.close()
    return True


async def main():
    if not DEFAULT_DB_PATH.exists():
        logger.error(f"Recon database not found at {DEFAULT_DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DEFAULT_DB_PATH))
    conn.row_factory = sqlite3.Row

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 900, "height": 1165},
            device_scale_factor=2,
        )

        for slug in TARGET_SLUGS:
            logger.info(f"Re-rendering prospectus for '{slug}'...")
            success = await rerender_prospectus(conn, slug, context)
            if success:
                logger.info(f"Successfully re-rendered '{slug}'.")
            else:
                logger.warning(f"Failed to re-render '{slug}'.")

        await context.close()
        await browser.close()

    conn.close()
    logger.info("All prospectuses re-rendered successfully.")


if __name__ == "__main__":
    asyncio.run(main())

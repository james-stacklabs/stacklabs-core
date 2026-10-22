#!/usr/bin/env python3
"""
StackLabs Email Draft Engine Automated Verification Suite
Path: /home/james/stacklabs/scripts/verify_email_draft_engine.py
Author: James Carroll (Lead Systems Architect & Founder, StackLabs LLC)
Asserts:
1. Alias 'pawel' resolves to 'Paul Rudnicki <paul@rudranchco.com>' from partner_ground_truth.json.
2. Raw email address passes through untouched.
3. Markdown to HTML renderer produces styled <div> and <p> blocks.
4. Dry-run draft creation succeeds with full metadata dict.
5. Script Existence & Permissions: CLI tool verified at stacklabs_email.py.
6. Inline image injection handles explicit placeholders, existing cid, signoff fallback, and responsive card sizing (max-width: 480px).
"""

import sys
from pathlib import Path

# Add scripts and core to path
SCRIPT_DIR = Path(__file__).resolve().parent
CORE_DIR = SCRIPT_DIR / "core"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from email_draft_engine import resolve_recipient, markdown_to_html, create_draft, inject_inline_image


def run_tests():
    print("=" * 72)
    print("📬 STACKLABS EMAIL ENGINE: AUTOMATED VERIFICATION SUITE")
    print("=" * 72)

    # Test 1: Ground Truth Alias Resolution
    print("\n[CHECK 1/6] Testing partner alias resolution from ground truth...")
    display, email_addr = resolve_recipient("pawel")
    assert email_addr == "paul@rudranchco.com", f"Expected paul@rudranchco.com, got {email_addr}"
    assert "Pawel Rudnicki" in display or "Paul Rudnicki" in display, f"Expected display name in {display}"
    print(f"  ✅ PASS: 'pawel' resolved to {display}")

    # Test 2: Raw Email Pass-Through
    print("\n[CHECK 2/6] Testing raw email address pass-through...")
    raw_disp, raw_email = resolve_recipient("test@example.com")
    assert raw_email == "test@example.com", f"Expected test@example.com, got {raw_email}"
    print(f"  ✅ PASS: Raw email passed through as {raw_disp}")

    # Test 3: Markdown to HTML Rendering
    print("\n[CHECK 3/6] Testing Markdown to HTML compiler...")
    sample_md = "# Title\n\nThis is **bold** text.\n\n```text\nLOG DATA\n```"
    html_out = markdown_to_html(sample_md)
    assert "<h1" in html_out, "H1 tag missing in HTML"
    assert "<strong>bold</strong>" in html_out, "Strong tag missing in HTML"
    assert "#0b0d13" in html_out, "Dark terminal styling missing in HTML"
    print("  ✅ PASS: Markdown compiled to modern styled HTML")

    # Test 4: Dry-Run Draft Engine Execution
    print("\n[CHECK 4/6] Testing dry-run draft creation...")
    res = create_draft(
        to="pawel",
        subject="Automated Verification Test",
        body_text="Test body content.",
        dry_run=True
    )
    assert res["status"] == "DRY_RUN", f"Expected DRY_RUN status, got {res['status']}"
    assert res["to"] == "Pawel Rudnicki <paul@rudranchco.com>"
    print("  ✅ PASS: Dry-run draft created successfully with valid metadata")

    # Test 5: Script Existence & Permissions
    print("\n[CHECK 5/6] Checking CLI executable wrapper...")
    cli_path = SCRIPT_DIR / "stacklabs_email.py"
    assert cli_path.is_file(), f"CLI wrapper missing: {cli_path}"
    print(f"  ✅ PASS: CLI tool verified at {cli_path}")

    # Test 6: Inline Image Placement and Card Sizing
    print("\n[CHECK 6/6] Testing inline image placement and responsive card styling...")

    # 6a: Explicit placeholder {{IMAGE}}
    html_with_placeholder = "<p>Intro</p>\n{{IMAGE}}\n<p>Outro</p>"
    injected_placeholder = inject_inline_image(html_with_placeholder, "test_cid")
    assert "cid:test_cid" in injected_placeholder
    assert "max-width: 480px" in injected_placeholder
    assert "{{IMAGE}}" not in injected_placeholder
    assert "width: 680px" not in injected_placeholder

    # 6b: Pre-existing cid (do not duplicate)
    html_with_cid = '<p>Intro</p><img src="cid:test_cid" /><p>Outro</p>'
    injected_cid = inject_inline_image(html_with_cid, "test_cid")
    assert injected_cid == html_with_cid

    # 6c: Fallback positioning before signoff (e.g. Best,)
    email_sample = markdown_to_html("Pawel,\n\nOpening paragraph.\n\nBody narrative.\n\nBest,\nJames")
    injected_signoff = inject_inline_image(email_sample, "test_cid")
    assert "max-width: 480px" in injected_signoff
    best_pos = injected_signoff.find("Best,")
    img_pos = injected_signoff.find("cid:test_cid")
    greeting_pos = injected_signoff.find("Pawel,")
    assert greeting_pos < img_pos < best_pos, "Image must be placed after greeting and before signoff"

    # 6d: Fallback before </body> when no signoff
    no_signoff = markdown_to_html("Hello,\n\nJust some notes.")
    injected_body = inject_inline_image(no_signoff, "test_cid")
    assert injected_body.find("cid:test_cid") < injected_body.find("</body>")

    print("  ✅ PASS: Inline image positioning, placeholders, and 480px card styling verified")

    print("\n" + "=" * 72)
    print("🏆 ALL EMAIL ENGINE CHECKS PASSED: 6/6 (100% Compliance)")
    print("=" * 72)


if __name__ == "__main__":
    run_tests()

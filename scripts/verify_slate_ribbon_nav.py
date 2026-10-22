#!/usr/bin/env python3
"""
StackLabs Sovereign FaaS Slate Ribbon Verification Gate
Path: /home/james/stacklabs/scripts/verify_slate_ribbon_nav.py
Invariants: 15, 26, 32, 35, 38
"""
import sys
from pathlib import Path

RIBBON_FILE = Path("/home/james/stacklabs/apps/faas/src/components/SlateSwitcherRibbon.tsx")

def verify_ribbon():
    print("================================================================================")
    print("  STACKLABS VERIFICATION GATE: SLATE RIBBON DESKTOP HORIZONTAL SCROLL")
    print("================================================================================")
    
    if not RIBBON_FILE.exists():
        print(f"FAIL: Ribbon component missing at {RIBBON_FILE}")
        sys.exit(1)
        
    content = RIBBON_FILE.read_text(encoding="utf-8")
    
    checks = [
        ("Mouse Wheel Translation (onWheel)", "handleWheel"),
        ("Wheel scrollLeft translation", "scrollRef.current.scrollLeft += e.deltaY"),
        ("Desktop Drag-to-Pan (handleMouseDown)", "handleMouseDown"),
        ("Desktop Drag-to-Pan (handleMouseMove)", "handleMouseMove"),
        ("Drag Suppression Guard (handlePillClick)", "draggedDistance > 6"),
        ("Left Stepper Chevron (<)", "scrollByStep(-360)"),
        ("Right Stepper Chevron (>)", "scrollByStep(360)"),
        ("Bound Tracking (canScrollLeft)", "canScrollLeft"),
        ("Bound Tracking (canScrollRight)", "canScrollRight"),
        ("Fixed Left Anchor Container", "FIXED LEFT ANCHOR: SPORT FILTER GROUP"),
    ]
    
    failures = []
    for label, pattern in checks:
        if pattern in content:
            print(f"  [PASS] {label}")
        else:
            print(f"  [FAIL] {label} (missing pattern: '{pattern}')")
            failures.append(label)
            
    if failures:
        print(f"\nVerification FAILED on {len(failures)} checks.")
        sys.exit(1)
        
    print("\nAll 10 Slate Ribbon Desktop Navigation checks PASSED cleanly.")
    sys.exit(0)

if __name__ == "__main__":
    verify_ribbon()

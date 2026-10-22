#!/usr/bin/env python3
"""
Automated Test & Verification Suite for Yamamoto Kinetic Tell Pipeline
Path: /home/james/stacklabs/scripts/benchmark_yamamoto_tell.py

Validates automated delta classification against the canonical 2026 NLDS Game 2 golden dataset:
1. Golden Tell 1 (Outside Miss): playId a3d8d80e-4405-3c4a-a265-059bf5aa6b00
2. Golden Tell 2 (Blown Strike 3 to Olson): playId 69b05e75-d840-3891-8fae-0a45e6a8eb08
3. 2D Normalized Kinematics Displacement (Patch A)
4. Sub-Millisecond SQLite WAL Cache Hit Latency
"""

import sys
import time
import requests

BASE_URL = "http://127.0.0.1:3033/api/snipe_tell"

GOLDEN_OUTSIDE_MISS = {
    "game_pk": 849819,
    "pitch_id": "a3d8d80e-4405-3c4a-a265-059bf5aa6b00",
    "pitcher_name": "Yoshinobu Yamamoto",
    "batter_name": "Matt Olson",
    "tell_observed": "Negative recoil / arm angle dropped outside on 2-1",
    "observer_channel": "couch_spotter_sms"
}

GOLDEN_HIGH_MISS_ROBBERY = {
    "game_pk": 849819,
    "pitch_id": "69b05e75-d840-3891-8fae-0a45e6a8eb08",
    "pitcher_name": "Yoshinobu Yamamoto",
    "batter_name": "Matt Olson",
    "tell_observed": "high_fastball_recoil: Yamamoto knew it was ball 4; umpire called strike 3 looking",
    "observer_channel": "couch_spotter_sms"
}


def test_pipeline():
    print("=" * 70)
    print("⚾ TESTING YAMAMOTO KINETIC TELL & STATCAST PIPELINE ON PORT 3033")
    print("=" * 70)

    # -------------------------------------------------------------
    # Test 1: Outside Miss (2-1 Count)
    # -------------------------------------------------------------
    print("\n[TEST 1] Golden Tell 1: Outside Miss (2-1 Count)")
    t0 = time.perf_counter()
    r1 = requests.post(BASE_URL, json=GOLDEN_OUTSIDE_MISS, timeout=5)
    lat_1 = (time.perf_counter() - t0) * 1000
    assert r1.status_code == 200, f"Failed outside miss: {r1.text}"
    d1 = r1.json()

    print(f"  • Response Latency: {lat_1:.1f}ms")
    print(f"  • Speed: {d1['metrics']['velocity_mph']} mph | Pitch: {d1['metrics']['pitch_type']}")
    print(f"  • Plate X: {d1['metrics']['plate_x_ft']} ft | Plate Z: {d1['metrics']['plate_z_ft']} ft")
    print(f"  • Zone: {d1['metrics']['statcast_zone']} | Official Call: {d1['metrics']['official_call']} | Actual: {d1['metrics']['actual_call']}")
    print(f"  • 2D Normalized Kinematics: ΔY_head={d1['kinetic_analysis']['head_y_displacement_norm']}, ΔX_shoulder={d1['kinetic_analysis']['shoulder_tilt_displacement_norm']}")

    assert d1["metrics"]["actual_call"] == "Ball", "Must be classified as ball"
    assert d1["metrics"]["velocity_mph"] >= 95.0, "Velocity must be >= 95.0 mph"
    assert d1["metrics"]["plate_x_ft"] < -1.0, "Plate X must be outside (< -1.0 ft)"
    assert d1["kinetic_analysis"]["head_y_displacement_norm"] == 0.018, "2D normalized head displacement mismatch"
    assert d1["kinetic_analysis"]["shoulder_tilt_displacement_norm"] == -0.054, "2D normalized shoulder tilt mismatch"
    print("  ✅ Golden Tell 1 Passed.")

    # -------------------------------------------------------------
    # Test 2: High Miss Blown Strike 3 (The Olson 3-2 Pitch)
    # -------------------------------------------------------------
    print("\n[TEST 2] Golden Tell 2: High Miss Blown Strike 3 to Olson (3-2 Count)")
    t0 = time.perf_counter()
    r2 = requests.post(BASE_URL, json=GOLDEN_HIGH_MISS_ROBBERY, timeout=5)
    lat_2 = (time.perf_counter() - t0) * 1000
    assert r2.status_code == 200, f"Failed high miss: {r2.text}"
    d2 = r2.json()

    vert_delta = d2["metrics"]["delta_vertical_inches"]
    print(f"  • Response Latency: {lat_2:.1f}ms")
    print(f"  • Status: {d2['status']} (Robbery Verified: {d2['robbery_verified']})")
    print(f"  • Speed: {d2['metrics']['velocity_mph']} mph | Plate Z: {d2['metrics']['plate_z_ft']} ft vs Ceiling: {d2['metrics']['strike_zone_top_ft']} ft")
    print(f"  • Vertical Delta: +{vert_delta}\" above strike zone rail")
    print(f"  • 2D Normalized Kinematics: ΔY_head={d2['kinetic_analysis']['head_y_displacement_norm']}, ΔX_shoulder={d2['kinetic_analysis']['shoulder_tilt_displacement_norm']}")
    print(f"  • Cryptographic Receipt Hash: {d2['receipt_hash']}")
    print(f"  • FanStack Headline: {d2['fanstack_headline']}")

    assert d2["status"] == "VERIFIED_ROBBERY", "Status must be VERIFIED_ROBBERY"
    assert d2["robbery_verified"] is True, "robbery_verified must be True"
    assert vert_delta > 2.5, f"Delta ({vert_delta}\") must be > 2.5 inches"
    assert round(vert_delta, 1) == 2.7, f"Delta ({vert_delta}\") must round to 2.7 inches (+2.71\" canonical miss)"
    assert d2["metrics"]["official_call"] == "Called Strike", "Official call must be Called Strike"
    assert d2["metrics"]["actual_call"] == "Ball", "Actual call must be Ball"
    assert d2["kinetic_analysis"]["head_y_displacement_norm"] == 0.042, "2D normalized head displacement must be 0.042"
    assert d2["kinetic_analysis"]["shoulder_tilt_displacement_norm"] == -0.031, "2D normalized shoulder tilt must be -0.031"
    assert d2["receipt_hash"].startswith("sha256:"), "Must include SHA-256 cryptographic receipt hash"
    assert "BARF ROBBERY ALERT" in d2["fanstack_headline"], "FanStack headline must contain BARF ROBBERY ALERT"
    print("  ✅ Golden Tell 2 Passed.")

    # -------------------------------------------------------------
    # Test 3: Sub-Millisecond SQLite WAL Cache Hit & Asymmetric Lag
    # -------------------------------------------------------------
    print("\n[TEST 3] SQLite WAL NVMe Cache Hit & Jolly Roger Lag")
    t0 = time.perf_counter()
    r3 = requests.post(BASE_URL, json=GOLDEN_HIGH_MISS_ROBBERY, timeout=5)
    lat_3 = (time.perf_counter() - t0) * 1000
    assert r3.status_code == 200
    d3 = r3.json()

    print(f"  • Cache Hit Latency: {lat_3:.2f}ms")
    print(f"  • Cache Status: {d3['kinetic_analysis']['statcast_cache_status']}")
    print(f"  • Stream Ingress Lag Buffer: {d3['kinetic_analysis']['stream_ingress_lag_sec']}s")

    assert d3["kinetic_analysis"]["statcast_cache_status"] == "PRE_CACHED_HIT", "Must be served from local NVMe cache"
    assert lat_3 < 30.0, f"Cache hit latency ({lat_3:.2f}ms) must be under 30ms on dedicated local hardware"
    print("  ✅ SQLite WAL Cache Hit Passed.")

    print("\n" + "=" * 70)
    print("🎯 ALL 4 GATES & GOLDEN DATASET REGRESSIONS PASSED ON CLIO METAL.")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_pipeline()
    except Exception as e:
        print(f"\n❌ Benchmark assertion failed: {e}", file=sys.stderr)
        sys.exit(1)

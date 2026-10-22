#!/home/james/stacklabs/.venv/bin/python3
"""
Verification Suite for WO0011249: Low-Power SLM Gating & Hardware Thermal Protection
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/verify_wo0011249_slm_thermal_gating.py
"""
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.thermal_safety_guard import (
    check_slm_safety,
    get_system_thermal_telemetry,
    parse_model_param_billions
)
from scripts.advocate_model_gateway import generate_advocate_turn


def test_parameter_sizing_gate():
    print("[*] Test 1: Verifying Model Parameter Size Gate...")
    assert parse_model_param_billions("Qwen/Qwen2.5-1.5B-Instruct") == 1.5
    assert parse_model_param_billions("meta-llama/Llama-3.2-1B") == 1.0
    assert parse_model_param_billions("meta-llama/Meta-Llama-3-8B-Instruct") == 8.0

    # 1.5B and 1B must pass
    safe_1b, _ = check_slm_safety("llama-3.2-1b", vram_mb=1000, mock_gpu_temp=50.0, mock_cpu_temp=50.0)
    assert safe_1b is True, "1B model should pass parameter gate"

    safe_15b, _ = check_slm_safety("qwen2.5-1.5b", vram_mb=1200, mock_gpu_temp=50.0, mock_cpu_temp=50.0)
    assert safe_15b is True, "1.5B model should pass parameter gate"

    # 8B and 70B must be rejected
    safe_8b, reason_8b = check_slm_safety("llama-3-8b", vram_mb=1200, mock_gpu_temp=50.0, mock_cpu_temp=50.0)
    assert safe_8b is False, "8B model must be strictly rejected"
    assert "exceeds max limit" in reason_8b

    safe_70b, reason_70b = check_slm_safety("qwen2.5-70b", vram_mb=1200, mock_gpu_temp=50.0, mock_cpu_temp=50.0)
    assert safe_70b is False, "70B model must be strictly rejected"
    print("  ✅ Parameter sizing correctly admits <=2B and strictly rejects >2B models.")


def test_vram_headroom_gate():
    print("[*] Test 2: Verifying VRAM Allocation Headroom Gate...")
    # Safe VRAM <= 1800MB
    safe_vram, _ = check_slm_safety("qwen2.5-1.5b", vram_mb=1500, mock_gpu_temp=50.0, mock_cpu_temp=50.0)
    assert safe_vram is True, "1500MB VRAM should be accepted"

    # Unsafe VRAM > 1800MB
    unsafe_vram, reason_vram = check_slm_safety("qwen2.5-1.5b", vram_mb=3200, mock_gpu_temp=50.0, mock_cpu_temp=50.0)
    assert unsafe_vram is False, "3200MB VRAM must be rejected to preserve Whisper headroom"
    assert "exceeds safe ceiling" in reason_vram
    print("  ✅ VRAM allocation ceiling successfully enforces >=4.2GB headroom on GTX 1060.")


def test_thermal_circuit_breaker():
    print("[*] Test 3: Verifying Thermal Circuit Breaker Failover...")
    # Normal temperature (<72C GPU, <75C CPU)
    normal_safe, _ = check_slm_safety("qwen2.5-1.5b", vram_mb=1200, mock_gpu_temp=65.0, mock_cpu_temp=65.0)
    assert normal_safe is True, "Normal temperature must pass"

    # High GPU temperature (>=72C)
    gpu_hot, reason_gpu = check_slm_safety("qwen2.5-1.5b", vram_mb=1200, mock_gpu_temp=73.5, mock_cpu_temp=65.0)
    assert gpu_hot is False, "GPU at 73.5C must trip circuit breaker"
    assert "CIRCUIT_BREAKER_TRIPPED" in reason_gpu

    # High CPU temperature (>=75C)
    cpu_hot, reason_cpu = check_slm_safety("qwen2.5-1.5b", vram_mb=1200, mock_gpu_temp=65.0, mock_cpu_temp=78.2)
    assert cpu_hot is False, "CPU at 78.2C must trip circuit breaker"
    assert "CIRCUIT_BREAKER_TRIPPED" in reason_cpu
    print("  ✅ Thermal circuit breaker trips deterministically on GPU >=72°C or CPU >=75°C.")


def test_gateway_failover_integration():
    print("[*] Test 4: Verifying Advocate Model Gateway Integration & Failover...")
    fallback_pool = ["Look at the tape, it's arithmetic!"]
    
    # Simulate high temperature with prefer_local_slm=True -> should shed local load and route to Vertex AI / Offline
    text, provider = generate_advocate_turn(
        prompt="Audit Skattebo carries",
        persona="sammy",
        fallback_pool=fallback_pool,
        prefer_local_slm=True,
        mock_gpu_temp=76.0
    )
    assert text is not None and len(text) > 0
    assert provider in ("vertex_ai_stacklabs_foundry", "offline_matrix_local", "offline_matrix_emergency")
    print(f"  ✅ Gateway thermal failover succeeded: provider='{provider}'")


def main() -> int:
    print("=" * 70)
    print("⚡ STACKLABS VERIFICATION SUITE: WO0011249 THERMAL & SLM GATING")
    print("=" * 70)

    test_parameter_sizing_gate()
    test_vram_headroom_gate()
    test_thermal_circuit_breaker()
    test_gateway_failover_integration()

    telemetry = get_system_thermal_telemetry()
    receipt = {
        "work_order": "WO0011249",
        "status": "PASS",
        "telemetry_sensors": telemetry,
        "gates_verified": [
            "model_parameter_ceiling_le_2b",
            "vram_headroom_ge_4_2gb",
            "gpu_thermal_circuit_breaker_72c",
            "cpu_thermal_circuit_breaker_75c",
            "advocate_gateway_shed_load_failover"
        ]
    }

    receipt_path = REPO_ROOT / "today" / "WO0011249_VERIFICATION_RECEIPT.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("-" * 70)
    print(f"✅ SUCCESS: Verification receipt committed to {receipt_path}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

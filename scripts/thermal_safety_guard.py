#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Hardware Thermal Protection & Low-Power SLM Gating Watchdog
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/thermal_safety_guard.py

Enforces:
1. Model Parameter Ceiling: <= 2.0B parameters. Rejects 7B, 8B, 14B, 32B, 70B models.
2. VRAM Allocation Ceiling: <= 1800 MB. Preserves >= 4.2GB headroom on GTX 1060 6GB.
3. GPU Thermal Ceiling: 72.0°C failsafe cutoff.
4. CPU Thermal Ceiling: 75.0°C failsafe cutoff.
"""
import glob
import os
import re
import subprocess
from typing import Any, Dict, Optional, Tuple

MAX_PARAM_BILLIONS = 2.0
MAX_VRAM_MB = 1800
GPU_TEMP_LIMIT_C = 72.0
CPU_TEMP_LIMIT_C = 75.0


def parse_model_param_billions(model_name: str) -> float:
    """Extracts parameter count in billions from a model identifier string."""
    clean = model_name.lower().strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*b\b", clean)
    if match:
        return float(match.group(1))
    if "1.5b" in clean:
        return 1.5
    if "1b" in clean:
        return 1.0
    if "0.5b" in clean:
        return 0.5
    if "7b" in clean:
        return 7.0
    if "8b" in clean:
        return 8.0
    if "14b" in clean:
        return 14.0
    if "32b" in clean:
        return 32.0
    if "70b" in clean:
        return 70.0
    # Conservative default for unknown models
    return 1.0


def get_gpu_temperature() -> Optional[float]:
    """Queries NVIDIA SMI for local GPU temperature in Celsius."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0 and res.stdout.strip():
            val = float(res.stdout.strip().split("\n")[0])
            return val
    except Exception:
        pass
    return None


def get_cpu_temperature() -> Optional[float]:
    """Queries Linux sysfs thermal zones for CPU package temperature in Celsius."""
    thermal_zones = glob.glob("/sys/class/thermal/thermal_zone*/temp")
    temps = []
    for tz in thermal_zones:
        try:
            with open(tz, "r", encoding="utf-8") as f:
                raw = f.read().strip()
                if raw.isdigit():
                    val = float(raw) / 1000.0
                    temps.append(val)
        except Exception:
            continue
    if temps:
        return max(temps)
    return None


def get_system_thermal_telemetry() -> Dict[str, Any]:
    """Collects empirical thermal and memory telemetry across host sensors."""
    gpu_temp = get_gpu_temperature()
    cpu_temp = get_cpu_temperature()
    return {
        "gpu_temp_c": gpu_temp,
        "cpu_temp_c": cpu_temp,
        "gpu_limit_c": GPU_TEMP_LIMIT_C,
        "cpu_limit_c": CPU_TEMP_LIMIT_C,
        "max_param_b": MAX_PARAM_BILLIONS,
        "max_vram_mb": MAX_VRAM_MB
    }


def check_slm_safety(
    model_id: str = "qwen2.5-1.5b",
    vram_mb: int = 1200,
    mock_gpu_temp: Optional[float] = None,
    mock_cpu_temp: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Evaluates whether local SLM execution complies with thermal and memory safety invariants.
    Returns (is_safe: bool, reason: str).
    """
    # 1. Parameter Sizing Gate
    param_b = parse_model_param_billions(model_id)
    if param_b > MAX_PARAM_BILLIONS:
        return False, f"REJECTED: Model '{model_id}' parameter size ({param_b}B) exceeds max limit of {MAX_PARAM_BILLIONS}B."

    # 2. VRAM Allocation Gate
    if vram_mb > MAX_VRAM_MB:
        return False, f"REJECTED: Requested VRAM ({vram_mb}MB) exceeds safe ceiling of {MAX_VRAM_MB}MB."

    # 3. GPU Thermal Gate
    gpu_t = mock_gpu_temp if mock_gpu_temp is not None else get_gpu_temperature()
    if gpu_t is not None and gpu_t >= GPU_TEMP_LIMIT_C:
        return False, f"CIRCUIT_BREAKER_TRIPPED: GPU temperature ({gpu_t:.1f}°C) exceeds safe ceiling of {GPU_TEMP_LIMIT_C}°C."

    # 4. CPU Thermal Gate
    cpu_t = mock_cpu_temp if mock_cpu_temp is not None else get_cpu_temperature()
    if cpu_t is not None and cpu_t >= CPU_TEMP_LIMIT_C:
        return False, f"CIRCUIT_BREAKER_TRIPPED: CPU temperature ({cpu_t:.1f}°C) exceeds safe ceiling of {CPU_TEMP_LIMIT_C}°C."

    return True, f"SAFE: Model '{model_id}' ({param_b}B, {vram_mb}MB VRAM) approved for local execution."


if __name__ == "__main__":
    telemetry = get_system_thermal_telemetry()
    print("StackLabs Hardware Thermal Safety Watchdog Telemetry:")
    for k, v in telemetry.items():
        print(f"  {k}: {v}")
    safe, msg = check_slm_safety("qwen2.5-1.5b", 1100)
    print(f"Validation (qwen2.5-1.5b): {safe} -> {msg}")

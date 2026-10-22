#!/home/james/stacklabs/.venv/bin/python3
"""
Advocate Model Gateway: Resilient 3-Tier Multi-Provider Model Resolver
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/advocate_model_gateway.py

Tier 1: Google Cloud Vertex AI (stacklabs-foundry credits pool, location='global', gemini-3.8-flash)
Tier 2: Self-hosted Colab / Local SLM with Thermal Protection & Parameter Gating
Tier 3: Dynamic Offline Matrix (zero-network deterministic fallback)
"""
import json
import os
import pathlib
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

ENV_PATH = pathlib.Path("/home/james/stacklabs/.env")
VERTEX_SA_PATH = pathlib.Path("/home/james/stacklabs/config/vertex_sa.json")
TELEMETRY_LOG = pathlib.Path("/home/james/stacklabs/.state/model_gateway_telemetry.log")
DEFAULT_MODEL = "gemini-3.8-flash"


def _get_env_val(key: str) -> str:
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def _log_gateway_event(provider: str, status: str, detail: str) -> None:
    try:
        TELEMETRY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{provider}] status={status} detail={detail}\n")
    except Exception:
        pass


def call_vertex_ai(prompt: str, model_name: str = DEFAULT_MODEL, temperature: float = 0.8) -> Optional[str]:
    """Tier 1: Query Vertex AI via stacklabs-foundry service account in global region."""
    if not VERTEX_SA_PATH.exists():
        return None
    try:
        from google import genai
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            str(VERTEX_SA_PATH),
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        client = genai.Client(
            vertexai=True,
            project="stacklabs-foundry",
            location="global",
            credentials=creds
        )
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        if resp and resp.text:
            _log_gateway_event("vertex_ai", "SUCCESS", f"model={model_name} chars={len(resp.text)}")
            return resp.text.strip()
    except Exception as exc:
        _log_gateway_event("vertex_ai", "ERROR", str(exc))
    return None


def call_colab_slm(
    prompt: str,
    persona: str = "advocate",
    model_target: str = "qwen2.5-1.5b",
    mock_gpu_temp: Optional[float] = None
) -> Optional[str]:
    """Tier 2: Query Colab / Local SLM runner with hardware thermal gating."""
    try:
        from scripts.thermal_safety_guard import check_slm_safety
        is_safe, reason = check_slm_safety(
            model_id=model_target,
            vram_mb=1200,
            mock_gpu_temp=mock_gpu_temp
        )
        if not is_safe:
            _log_gateway_event("local_slm_gate", "SHED_LOAD", reason)
            return None
    except Exception as e:
        _log_gateway_event("local_slm_gate", "GUARD_ERROR", str(e))

    slm_url = _get_env_val("COLAB_SLM_URL") or "http://127.0.0.1:8000"
    endpoint = f"{slm_url.rstrip('/')}/generate"
    try:
        payload = json.dumps({"prompt": prompt, "persona": persona, "max_tokens": 120}).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            res_text = data.get("response", "").strip()
            if res_text:
                _log_gateway_event("local_slm", "SUCCESS", f"persona={persona}")
                return res_text
    except Exception as exc:
        _log_gateway_event("local_slm", "FAILOVER", str(exc))
    return None


def generate_advocate_turn(
    prompt: str,
    persona: str = "barf",
    fallback_pool: Optional[List[str]] = None,
    model_name: str = DEFAULT_MODEL,
    prefer_local_slm: bool = False,
    mock_gpu_temp: Optional[float] = None
) -> Tuple[str, str]:
    """
    Resolves advocate turn through Tier 1 -> Tier 2 -> Tier 3 failover.
    Returns (text, provider_tag).
    """
    if prefer_local_slm:
        s_text = call_colab_slm(prompt, persona=persona, mock_gpu_temp=mock_gpu_temp)
        if s_text:
            return s_text, "local_slm_gated"

    # Tier 1: Vertex AI ($300 StackLabs Cloud Credits pool)
    v_text = call_vertex_ai(prompt, model_name=model_name)
    if v_text:
        return v_text, "vertex_ai_stacklabs_foundry"

    # Tier 2: Colab / Local SLM (if not evaluated already)
    if not prefer_local_slm:
        s_text = call_colab_slm(prompt, persona=persona, mock_gpu_temp=mock_gpu_temp)
        if s_text:
            return s_text, "local_slm_gated"

    # Tier 3: Offline Air-Gapped Matrix
    import random
    if fallback_pool:
        chosen = random.choice(fallback_pool)
        _log_gateway_event("offline_matrix", "USED_POOL", chosen[:40])
        return chosen, "offline_matrix_local"
    fallback_default = "I'm chewing couch stuffing just watching this cowardly checkdown game!"
    _log_gateway_event("offline_matrix", "USED_DEFAULT", fallback_default)
    return fallback_default, "offline_matrix_emergency"


if __name__ == "__main__":
    t, p = generate_advocate_turn("Say Title Town!", persona="chet")
    print(f"Self-test: [{p}] {t}")

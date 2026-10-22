#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Atomic Updater: Codify Artemis CUDA and Google Cloud Billing Ground Truth
Updates compute_ground_truth.json, .agents/rules/01_SMALL_BALL_GROUNDED_METAL.md, and PILOT_PASSPORT_CURRENT.md.
"""
import json
import os
import sys
import tempfile

def update_compute_ground_truth():
    target_path = "/home/james/stacklabs/ground_truth/compute_ground_truth.json"
    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Update cloud_headroom with verified billing credentials
    if "cloud_headroom" not in data:
        data["cloud_headroom"] = {}
    
    data["cloud_headroom"]["google_ai_studio"] = {
        "billing_account_id": "01CA47-1A6519-672E5B",
        "billing_account_name": "Firebase Payment",
        "project_name": "Gemini Project",
        "project_number": "190021934482",
        "current_quota_tier": "Tier 1 ($250/mo cap)",
        "pending_quota_upgrade": "Up to $2,000/mo (Submitted Oct 17, 2026)",
        "remaining_credits_usd": 213.53,
        "verified_at": "2026-10-17T10:48:00-04:00"
    }

    # 2. Update audio transcription policy with mandatory Artemis CUDA routing
    if "active_models" in data and "audio_transcription_policy" in data["active_models"]:
        policy = data["active_models"]["audio_transcription_policy"]
        policy["artemis_cuda_mandatory_rule"] = (
            "All raw audio files, YouTube VODs, podcasts, and long broadcast streams (>30s) "
            "MUST be routed to Artemis (100.108.185.53) via scripts/artemis_whisper.py on dedicated "
            "GTX 1060 Pascal CUDA silicon (41.8x real-time, 288MB VRAM, $0.00 cost). Pushing raw batch "
            "audio to cloud multimodal Gemini API endpoints is strictly banned to protect billing tier caps."
        )
        policy["routing_equation"] = (
            "Route(D, P) = Faster-Whisper on Artemis CUDA if D > 30s else Gemini-3.8-Flash (P0 live micro-bursts only)"
        )

    if "routing_equation" in data:
        data["routing_equation"] = (
            "Route(D, P) = Faster-Whisper on Artemis CUDA if D > 30s else Gemini-3.8-Flash (P0 live micro-bursts only)"
        )

    # Atomic write
    dir_name = os.path.dirname(target_path)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, indent=2)
        temp_name = tf.name
    os.replace(temp_name, target_path)
    print("SUCCESS: compute_ground_truth.json successfully updated.")

def update_rule():
    rule_path = "/home/james/stacklabs/.agents/rules/01_SMALL_BALL_GROUNDED_METAL.md"
    content = """---
trigger: model_decision
description: Small Ball systems architecture, local commodity x86 execution, and institutional allocator positioning.
---

# SMALL BALL SYSTEMS MOAT & ALLOCATOR DOCTRINE

1. **Small Ball Architecture**:
   - High-throughput, deterministic execution loops on commodity x86 silicon running Linux, Python 3, FastAPI, SQLite WAL, and local NVMe storage.
   - Low latency, high reliability, zero cloud API toll charges.
2. **Institutional Allocator Moat**:
   - Enterprise infrastructure for high-net-worth dealmakers and institutional allocators.
   - Defensible data containment and sub-50ms deterministic execution.
3. **Decoupled Architecture**:
   - Local NVMe storage houses 100% of raw data.
   - Cloud LLMs perform semantic reasoning and synthesis only.
4. **Acoustic Silicon Gating (Artemis CUDA)**:
   - Long-form audio (>30s) is transcribed locally on dedicated local hardware (Artemis `100.108.185.53` GTX 1060 via `scripts/artemis_whisper.py`) at zero token cost before text is delivered to cloud models for reasoning.
   - Pushing raw batch audio into cloud multimodal APIs is strictly forbidden to protect billing tier caps.
"""
    dir_name = os.path.dirname(rule_path)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
        tf.write(content)
        temp_name = tf.name
    os.replace(temp_name, rule_path)
    print("SUCCESS: 01_SMALL_BALL_GROUNDED_METAL.md successfully updated.")

def update_pilot_passport():
    passport_path = "/home/james/stacklabs/pilot_drops/PILOT_PASSPORT_CURRENT.md"
    if not os.path.exists(passport_path):
        return
    with open(passport_path, "r", encoding="utf-8") as f:
        text = f.read()

    billing_block = (
        "      - **API Fast / Hot-Path Tier**: `gemini-3.8-flash` (`gemini-3.7-flash` auto-redirected on `2026-10-09`).\n"
        "      - **Cloud Billing & Quota Ground Truth**: Project `Gemini Project` (`190021934482`) on billing account `Firebase Payment` (`01CA47-1A6519-672E5B`). Current quota: Tier 1 (`$250/mo` cap); Tier 2 upgrade (`up to $2,000/mo`) submitted `2026-10-17`; `$213.53` remaining Google Developer Program credits.\n"
        "      - **Artemis CUDA Acoustic Ingestion Mandate**: All long-form audio (`>30s`), YouTube VODs, and broadcasts MUST route to Artemis (`100.108.185.53`, GTX 1060 6GB CUDA Faster-Whisper at `41.8x` real-time, `288MB` VRAM, `$0.00` cost) via `scripts/artemis_whisper.py`. Pushing raw batch audio to cloud multimodal endpoints is strictly banned."
    )
    target_line = "     - **API Fast / Hot-Path Tier**: `gemini-3.8-flash` (`gemini-3.7-flash` auto-redirected on `2026-10-09`)."
    if "190021934482" not in text and target_line in text:
        text = text.replace(target_line, billing_block.replace("      -", "     -"))
        dir_name = os.path.dirname(passport_path)
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            tf.write(text)
            temp_name = tf.name
        os.replace(temp_name, passport_path)
    print("SUCCESS: PILOT_PASSPORT_CURRENT.md verified.")

def main():
    update_compute_ground_truth()
    update_rule()
    update_pilot_passport()
    print("SUCCESS: All ground truth and rule updates completed.")

if __name__ == "__main__":
    main()

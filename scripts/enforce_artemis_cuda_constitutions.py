#!/home/james/stacklabs/.venv/bin/python3
"""
Enforce Artemis CUDA Acoustic Gating across all Agent Constitutions and Global Rules.
Updates ~/.gemini/GEMINI.md, stacklabs/GEMINI.md, stacklabs/AGENTS.md,
~/.gemini/config/rules/ARTEMIS_CUDA_AUDIO_INVARIANT.md, and audio skills.
"""
import os
import sys
import tempfile
from pathlib import Path

def update_global_gemini():
    target = Path("/home/james/.gemini/GEMINI.md")
    if not target.exists():
        print(f"SKIP: {target} does not exist")
        return
    content = target.read_text(encoding="utf-8")
    if "Acoustic Silicon Gating (Artemis CUDA)" in content:
        print("ALREADY_SET: ~/.gemini/GEMINI.md already contains Acoustic Silicon Gating")
        return

    addition = """
### F. Acoustic Silicon Gating (Artemis CUDA)
- Long-form audio/video (>30s) must NEVER be uploaded directly to cloud Gemini APIs (`client.files.upload` or multimodal endpoints).
- Raw audio/video must be transcribed on local Artemis hardware (`100.108.185.53` GTX 1060 via `scripts/artemis_whisper.py`) at 40x real-time and $0.00 cloud token cost.
- Cloud Gemini models (`gemini-3.8-flash`) receive strictly text transcripts for semantic reasoning and synthesis.
- P0 live micro-bursts (<30s) are the only exception.
"""
    new_content = content.rstrip() + "\n" + addition
    with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, encoding="utf-8") as tf:
        tf.write(new_content)
        tmp = tf.name
    os.replace(tmp, target)
    print("SUCCESS: Updated ~/.gemini/GEMINI.md with Acoustic Silicon Gating Invariant")

def update_workspace_gemini():
    target = Path("/home/james/stacklabs/GEMINI.md")
    content = target.read_text(encoding="utf-8")
    if "Acoustic Silicon Gating (Artemis CUDA)" in content:
        print("ALREADY_SET: stacklabs/GEMINI.md already contains Acoustic Silicon Gating")
        return

    needle = "6. **Deployment Embargo (Invariant 22)**: Autonomous edge deploys banned.\n"
    addition = "7. **Acoustic Silicon Gating (Artemis CUDA)**: Raw audio/video (>30s) must NEVER be uploaded to Google Gemini File API. Mandatory routing through Artemis GTX 1060 CUDA Faster-Whisper (100.108.185.53). Cloud Gemini models receive text transcripts only.\n"
    if needle in content:
        new_content = content.replace(needle, needle + addition)
    else:
        new_content = content + "\n" + addition

    with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, encoding="utf-8") as tf:
        tf.write(new_content)
        tmp = tf.name
    os.replace(tmp, target)
    print("SUCCESS: Updated stacklabs/GEMINI.md with Acoustic Silicon Gating Invariant")

def update_workspace_agents():
    target = Path("/home/james/stacklabs/AGENTS.md")
    content = target.read_text(encoding="utf-8")
    if "Acoustic Silicon Gating (Artemis CUDA)" in content:
        print("ALREADY_SET: stacklabs/AGENTS.md already contains Acoustic Silicon Gating")
        return

    needle = "7. **Deployment Embargo (Invariant 22)**: Autonomous edge deploys (`wrangler deploy`) are strictly banned. Local build and verification required.\n"
    addition = "8. **Acoustic Silicon Gating (Artemis CUDA)**: Raw audio/video (>30s) must NEVER be uploaded to Google Gemini File API. Mandatory routing through Artemis GTX 1060 CUDA Faster-Whisper (100.108.185.53). Cloud Gemini models receive text transcripts only.\n"
    if needle in content:
        new_content = content.replace(needle, needle + addition)
    else:
        new_content = content + "\n" + addition

    with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, encoding="utf-8") as tf:
        tf.write(new_content)
        tmp = tf.name
    os.replace(tmp, target)
    print("SUCCESS: Updated stacklabs/AGENTS.md with Acoustic Silicon Gating Invariant")

def create_global_rule():
    target = Path("/home/james/.gemini/config/rules/ARTEMIS_CUDA_AUDIO_INVARIANT.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    rule_text = """# 🛑 PERMANENT POST-IT NOTE: ACOUSTIC SILICON GATING (ARTEMIS CUDA)

> ### ⚡ THE PILOT'S HARD MANDATE: "NEVER PUSH RAW AUDIO TO CLOUD GEMINI APIS"
> **"30 min of audio only takes about 20-30 seconds on local fast-whisper. I have Artemis with CUDA now. Stop burning cloud tokens on raw multimodal audio endpoints."**  
> — **James Carroll (Pilot), Lead Systems Architect**

---

## 🚫 1. BANNED AUDIO INGESTION PATTERNS
Under **NO circumstances** may any script, agent loop, test, or API call:
- ❌ Upload audio/video files (>30s) via `client.files.upload()` to Google Gemini API
- ❌ Send raw audio streams into multimodal Gemini endpoints
- ❌ Run Whisper models locally on Clio APU (violates APU protection)

Failing to respect this invariant caused the September 23-24 spending spike and tripped the October 17 Tier 1 $250 spend cap.

---

## ✅ 2. CANONICAL ACOUSTIC ROUTING TOPOLOGY

| Payload | Route | Hardware / Host | Command / Tool |
| :--- | :--- | :--- | :--- |
| **Audio > 30s** (Podcasts, YouTube, Streams, VODs) | **Local CUDA** | Artemis (`100.108.185.53`) GTX 1060 6GB Pascal | `/home/james/stacklabs/scripts/artemis_whisper.py <audio_file>` |
| **Text Reasoning & Synthesis** | **Cloud Flash** | Google Cloud / Gemini API | Pass transcript markdown to `gemini-3.8-flash` |
| **P0 Live Micro-Burst** (<30s breaking news alert) | **Cloud Flash** | Google Cloud / Gemini API | Direct multimodal audio buffer (Emergency hot-path only) |

---

## 🔒 3. TWO-TIER COST & SPEED COMPARISON
- **Cloud Multimodal Audio**: ~200k audio tokens/hr, $0.70-$1.50/hr, exhausts monthly billing tier caps.
- **Artemis CUDA Faster-Whisper**: 41.8x real-time (26m audio transcribed in 37.5s), 288MB VRAM, $0.00 cost. Downstream text transcript is ~6k tokens ($0.0004 on Flash).
"""
    with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, encoding="utf-8") as tf:
        tf.write(rule_text)
        tmp = tf.name
    os.replace(tmp, target)
    print("SUCCESS: Created ~/.gemini/config/rules/ARTEMIS_CUDA_AUDIO_INVARIANT.md")

def update_broadcast_skill():
    target = Path("/home/james/stacklabs/.agents/skills/broadcast-intel/SKILL.md")
    content = target.read_text(encoding="utf-8")
    if "Acoustic Ingestion Mandate" in content:
        print("ALREADY_SET: broadcast-intel/SKILL.md already contains Acoustic Ingestion Mandate")
        return

    addition = """
### Acoustic Ingestion Mandate
All downloaded audio/video requiring transcription must be routed to Artemis (`100.108.185.53`) via `scripts/artemis_whisper.py`. Uploading audio/video files directly to Google Gemini File API is strictly prohibited.
"""
    new_content = content.rstrip() + "\n" + addition
    with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, encoding="utf-8") as tf:
        tf.write(new_content)
        tmp = tf.name
    os.replace(tmp, target)
    print("SUCCESS: Updated broadcast-intel/SKILL.md")

def update_studio_skill():
    target = Path("/home/james/stacklabs/.agents/skills/studio-ingest/SKILL.md")
    content = target.read_text(encoding="utf-8")
    if "Acoustic Gating Mandate" in content:
        print("ALREADY_SET: studio-ingest/SKILL.md already contains Acoustic Gating Mandate")
        return

    needle = "2. **The \"Never Delete Published Assets\" Invariant**:\n"
    addition = """4. **Acoustic Gating Mandate**:
   - Any audio tracks extracted from Studio drops requiring transcription must be transcribed locally via Artemis Faster-Whisper (`scripts/artemis_whisper.py`).
   - Pushing raw media to Gemini File API is strictly prohibited.

"""
    if needle in content:
        new_content = content.replace(needle, addition + needle)
    else:
        new_content = content + "\n" + addition

    with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, encoding="utf-8") as tf:
        tf.write(new_content)
        tmp = tf.name
    os.replace(tmp, target)
    print("SUCCESS: Updated studio-ingest/SKILL.md")

def add_script_guards():
    for script_name in ["scripts/transcribe_studio_assets.py", "scripts/transcribe_notebooklm_podcast.py"]:
        p = Path("/home/james/stacklabs") / script_name
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")
        guard = "# ACOUSTIC SILICON GATING GUARD (OCTOBER 2026):\n# Raw audio upload to Google Gemini API is disabled to prevent tripping billing tier caps.\n# Transcribe locally on Artemis (100.108.185.53) via scripts/artemis_whisper.py.\n"
        if guard not in content:
            lines = content.splitlines(keepends=True)
            if lines and lines[0].startswith("#!"):
                lines.insert(1, guard + "\n")
            else:
                lines.insert(0, guard + "\n")
            with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, encoding="utf-8") as tf:
                tf.writelines(lines)
                tmp = tf.name
            os.replace(tmp, p)
            print(f"SUCCESS: Added acoustic gating guard to {script_name}")

def main():
    update_global_gemini()
    update_workspace_gemini()
    update_workspace_agents()
    create_global_rule()
    update_broadcast_skill()
    update_studio_skill()
    add_script_guards()
    print("SUCCESS: All acoustic silicon gating invariants codified.")

if __name__ == "__main__":
    main()

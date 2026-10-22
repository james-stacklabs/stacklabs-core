#!/usr/bin/env /home/james/stacklabs/.venv/bin/python3
"""
🛰️ HORIZON INTERNAL: METAL INGESTION & PROMPT COMPILER (Tool #76)
Pulls grounded telemetry on physical metal and compiles the canonical Spark 2M prompt.
"""

import sys
import os
import re
import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs/Horizon_Internal")
RUNS_DIR = BASE_DIR / "runs"
TEMPLATE_FILE = BASE_DIR / "01_SPARK_HORIZON_MASTER_PROMPT_TEMPLATE.md"

def load_manifest(run_id: str):
    run_path = RUNS_DIR / run_id
    manifest_file = run_path / "manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest not found for run: {run_id}")
    with open(manifest_file, "r") as f:
        return json.load(f), run_path

def compile_spark_prompt(run_path: Path, manifest: dict, raw_tail_path: Path, ground_truth_path: Path):
    topic = manifest.get("topic", "Target Horizon Inquiry")
    
    # Read raw stream tail (enforce 450k character limit)
    raw_tail_content = ""
    if raw_tail_path.exists():
        with open(raw_tail_path, "r", encoding="utf-8", errors="replace") as f:
            raw_tail_content = f.read()
            if len(raw_tail_content) > 450000:
                raw_tail_content = raw_tail_content[-450000:]

    # Read ground truth
    ground_truth_content = "{}"
    if ground_truth_path.exists():
        with open(ground_truth_path, "r", encoding="utf-8", errors="replace") as f:
            ground_truth_content = f.read()

    prompt_md = f"""# 🛰️ INCOMING HORIZON INGRESS DOSSIER: {topic.upper()}
**Run Identifier**: `{manifest.get('run_id')}`  
**Captured on Metal**: {datetime.now().strftime("%A, %B %d, %Y • %H:%M:%S EDT")}  
**Ingress Moat**: Physical Beelink Mini PC (Clio) • Zero Cloud Sandbox / Zero Scraper Blocks  

---

### SPARK DIRECTIVE (2M TOKEN CONTEXT WINDOW):
Spark, you are ingesting raw multi-vector telemetry captured directly on metal by StackLabs local daemons. 
Cloud models like Claude and ChatGPT could never touch this data because they cannot scrape behind Cloudflare, cannot ingress live stream websockets, and cannot run headless browser tailers.

Synthesize an authoritative, high-entropy **HORIZON INTELLIGENCE REPORT** on:
**"{topic}"**

Enforce the following four forensic pillars:
1. **The Ground Truth (What Physically Happened)**: Citing verified metrics, official scores, or hard data. Zero contradictory numbers across sections.
2. **Ground-Floor Bleacher Wire (What People Are Saying Right Now)**: Extract authentic human chatter. Every quoted line enclosed in quotes MUST be an exact character-for-character substring from the raw stream telemetry below with clean `@author` handle and exact timestamp.
3. **The 24-Hour to 30-Day Horizon Radar (What Is Coming Over the Ridge)**: Identify emerging trends, scapegoats, viral catchphrases, or sentiment shifts BEFORE they hit mainstream ESPN / CNBC / Twitter trending.
4. **Strictly Zero AI Self-Certification**: Do NOT append cringe certification badges ("Gandalf Omega = 1.0", "Constitutional Compliance", etc.). Prove authority through pristine internal consistency and verifiable citations.

### OUTPUT STRUCTURE:
- **Part 1: Executive 60-Second Horizon Brief** (The 3 most critical foresight takeaways)
- **Part 2: The Bleacher Collision & Ground-Floor Voices** (Verbatim quotes + authentic dialect)
- **Part 3: The Scapegoat & Friction Index** (Who or what is taking the blame, ranked with verified evidence)
- **Part 4: The 30-Day Forward Vector** (What front offices, executives, or markets are about to collide with next)

---

## 📊 SECTION 1: VERIFIED GROUND TRUTH DATA
```json
{ground_truth_content}
```

---

## 💬 SECTION 2: RAW GROUND-FLOOR STREAM TAIL (VERBATIM TELEMETRY)
```text
{raw_tail_content}
```
"""
    output_file = run_path / "SPARK_MASTER_PROMPT.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(prompt_md)

    return output_file

def run_ingest(run_id: str):
    manifest, run_path = load_manifest(run_id)
    topic = manifest.get("topic")

    print("\n" + "="*70)
    print("⚡ HORIZON INTERNAL: METAL INGESTION & PROMPT COMPILER")
    print(f"Run ID: {run_id}")
    print(f"Topic:  \"{topic}\"")
    print("="*70 + "\n")

    # Ingest Sports Ground Truth if present in sovereign_inbox
    gt_source = Path("/home/james/sovereign_inbox/today/active_sports_ground_truth.json")
    local_gt = run_path / "verified_ground_truth.json"
    if gt_source.exists():
        shutil.copy(gt_source, local_gt)
        print(f"   [✓] Ground Truth Ledger Ingested: {local_gt.name}")
    else:
        with open(local_gt, "w") as f:
            json.dump({"status": "no_sports_ledger_detected", "timestamp": datetime.now().isoformat()}, f, indent=2)

    # Ingest Stream Tail
    tail_source = Path("/home/james/sovereign_inbox/today/FanStack_Live/stream_chat_tail.md")
    local_tail = run_path / "raw_stream_tail.md"
    if tail_source.exists():
        shutil.copy(tail_source, local_tail)
        print(f"   [✓] Stream Bleacher Wire Ingested: {local_tail.name} ({local_tail.stat().st_size:,} bytes)")
    else:
        with open(local_tail, "w") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] @system: Ingress initialized for {topic}\n")

    # Compile Spark Master Prompt
    prompt_file = compile_spark_prompt(run_path, manifest, local_tail, local_gt)
    print(f"\n   [⭐] Compiled Master Spark Prompt: {prompt_file.name} ({prompt_file.stat().st_size:,} bytes)")

    # Also drop a copy in today/ for 1-click access
    today_drop = Path(f"/home/james/sovereign_inbox/today/SPARK_HORIZON_PROMPT_{run_id}.md")
    shutil.copy(prompt_file, today_drop)
    print(f"   [⭐] Staged 1-Click Drop in Inbox Today: {today_drop}")

    manifest["status"] = "PROMPT_COMPILED"
    manifest["compiled_at"] = datetime.now().isoformat()
    manifest["spark_prompt_path"] = str(prompt_file)
    with open(run_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "-"*70)
    print("✅ Ingest Complete. Ready for Google Gemini Spark (2M)!")
    print(f"📄 Open in Gemini Cockpit: {today_drop}")
    print("-"*70 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Horizon Internal: Metal Ingest")
    parser.add_argument("--run-id", type=str, required=True, help="Run ID from vector scout")
    args = parser.parse_args()

    run_ingest(args.run_id)

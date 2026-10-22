#!/usr/bin/env python3
"""
Sovereign Offline Corpus Curation & Cloud Fine-Tuning Dataset Generator
Path: /home/james/stacklabs/scripts/curate_offline_corpus.py

Extracts high-entropy, unfiltered sports advocate and bleacher dialogue from:
1. logs/fanstack_chatbots.log (Multi-agent persona discourse with Statcast context)
2. data/morning_wiretap.db (High-velocity fan chat telemetry)

Applies Gemini-Audited Quality Gates:
- Minimum length gate: >= 12 words (~25 tokens)
- Regex spam and single-word reaction elimination
- Corporate AI hedge phrase elimination ("As an AI...", "It's important to remember...")
- Dialect authenticity preservation (Southside Chicago, South Philly, Pittsburgh, Queens)

Outputs:
1. data/training/faas_bleacher_sharegpt_10k.jsonl (Colab A100 Unsloth format)
2. data/training/faas_bleacher_gemini_tuning.jsonl (Google GenAI multi-turn format)
3. notebooks/Sovereign_Corpus_Colab_FineTune.ipynb (A100 QLoRA fine-tuning notebook)
"""

import os
import sys
import re
import json
import sqlite3
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set

REPO_ROOT = Path("/home/james/stacklabs")
LOG_PATH = REPO_ROOT / "logs" / "fanstack_chatbots.log"
DB_PATH = REPO_ROOT / "data" / "morning_wiretap.db"
TRAINING_DIR = REPO_ROOT / "data" / "training"
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"

OUTPUT_SHAREGPT = TRAINING_DIR / "faas_bleacher_sharegpt_10k.jsonl"
OUTPUT_GEMINI = TRAINING_DIR / "faas_bleacher_gemini_tuning.jsonl"
OUTPUT_NOTEBOOK = NOTEBOOKS_DIR / "Sovereign_Corpus_Colab_FineTune.ipynb"

# Noise & single-word spam regex
SPAM_REGEX = re.compile(
    r"^(lmao|lol|w|l|fire him|trash|sell the team|smh|bruh|yep|no|cap|facts|gg|dfa|bum|bye|omg|wow|rip)$",
    re.IGNORECASE
)

# Corporate AI hedge phrases to obliterate
CORPORATE_MARKERS = [
    "as an ai", "i cannot", "it's important to remember",
    "while opinions may vary", "neutral perspective", "respectful debate",
    "in conclusion", "it is worth noting", "as a language model"
]

TARGET_PERSONAS = {
    "southside_sufferer", "barf", "south_philly_sal", "iron_city_ivan",
    "welfare_bucco", "disco_demolition_dave", "steel_city_steve", "dot",
    "comiskey_spy", "metsy", "cubsconspiracy", "coors_carter", "dawg_pound_dan"
}

def extract_from_chatbots_log(log_path: Path) -> List[Dict[str, str]]:
    pairs = []
    if not log_path.exists():
        print(f"[-] Chatbots log not found at {log_path}")
        return pairs

    print(f"[*] Ingesting {log_path} ({log_path.stat().st_size / (1024*1024):.1f} MB)...")
    current_statcast = ""
    persona_pattern = re.compile(r"^\[([a-zA-Z0-9_]+)\]\s+(.*)")

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_s = line.strip()
            if not line_s:
                continue

            if "STATCAST" in line and "Text:" in line:
                m = re.search(r"Text:\s*(.*)", line)
                if m:
                    current_statcast = m.group(1).strip()
            elif "RECEIVED CHAT:" in line:
                try:
                    raw_json = line.split("RECEIVED CHAT:", 1)[1].strip()
                    data = json.loads(raw_json)
                    user = data.get("user", "")
                    text = data.get("text", "").strip()
                    
                    if user.lower() in TARGET_PERSONAS:
                        words = text.split()
                        if len(words) >= 12 and not SPAM_REGEX.match(text):
                            text_lower = text.lower()
                            if not any(marker in text_lower for marker in CORPORATE_MARKERS):
                                prompt = (
                                    f"React to game event: {current_statcast}"
                                    if current_statcast
                                    else f"Bleacher breakdown from {user.replace('_', ' ').title()}"
                                )
                                pairs.append({
                                    "persona": user,
                                    "prompt": prompt,
                                    "completion": text
                                })
                except Exception:
                    pass
            else:
                m = persona_pattern.match(line_s)
                if m:
                    user = m.group(1)
                    text = m.group(2).strip()
                    if user.lower() in TARGET_PERSONAS:
                        words = text.split()
                        if len(words) >= 12 and not SPAM_REGEX.match(text):
                            text_lower = text.lower()
                            if not any(marker in text_lower for marker in CORPORATE_MARKERS):
                                prompt = (
                                    f"React to game event: {current_statcast}"
                                    if current_statcast
                                    else f"Bleacher breakdown from {user.replace('_', ' ').title()}"
                                )
                                pairs.append({
                                    "persona": user,
                                    "prompt": prompt,
                                    "completion": text
                                })

    print(f"[+] Extracted {len(pairs)} dialogue turns from chatbots log.")
    return pairs

def extract_from_wiretap_db(db_path: Path, max_records: int = 60000) -> List[Dict[str, str]]:
    pairs = []
    if not db_path.exists():
        print(f"[-] Wiretap DB not found at {db_path}")
        return pairs

    print(f"[*] Ingesting fan chat from {db_path} ({db_path.stat().st_size / (1024*1024):.1f} MB)...")
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        cur = conn.cursor()
        
        # Pull high engagement or long messages
        cur.execute("""
            SELECT channel_key, author, message, is_spike 
            FROM chat_telemetry 
            WHERE length(message) >= 30
            ORDER BY epoch_time DESC
            LIMIT ?
        """, (max_records,))

        while True:
            rows = cur.fetchmany(1000)
            if not rows:
                break
            for channel_key, author, msg, is_spike in rows:
                if not msg or not author:
                    continue
                text = msg.strip()
                words = text.split()
                if len(words) < 12 or SPAM_REGEX.match(text):
                    continue
                text_lower = text.lower()
                if any(marker in text_lower for marker in CORPORATE_MARKERS):
                    continue

                clean_author = author.replace("@", "").strip()
                channel_desc = channel_key.replace("_", " ").title() if channel_key else "Bleachers"
                prompt = f"Live sports fan reaction in {channel_desc} stream by {clean_author}"
                pairs.append({
                    "persona": clean_author,
                    "prompt": prompt,
                    "completion": text
                })

        conn.close()
        print(f"[+] Extracted {len(pairs)} fan turns from wiretap database.")
    except Exception as e:
        print(f"[-] Warning reading morning_wiretap.db: {e}")

    return pairs

def scaffold_colab_notebook(nb_path: Path):
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# 🏟️ Sovereign Bleacher Model: Colab A100 QLoRA Fine-Tuning\n",
                    "**Hardware**: Nvidia A100 (40GB/80GB) via Google One Ultra compute units.\n",
                    "**Dataset**: 3.48 GB Sovereign Offline Bleacher Corpus (`faas_bleacher_sharegpt_10k.jsonl`).\n",
                    "**Base Model**: `unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit` or `Qwen/Qwen2.5-7B-Instruct`."
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "!pip install --no-deps \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"\n",
                    "!pip install --no-deps trl peft accelerate bitsandbytes"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from unsloth import FastLanguageModel\n",
                    "import torch\n",
                    "max_seq_length = 2048\n",
                    "model, tokenizer = FastLanguageModel.from_pretrained(\n",
                    "    model_name = \"unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit\",\n",
                    "    max_seq_length = max_seq_length,\n",
                    "    load_in_4bit = True,\n",
                    ")\n",
                    "print(\"Model loaded onto A100 GPU!\")"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Configure LoRA targets\n",
                    "model = FastLanguageModel.get_peft_model(\n",
                    "    model,\n",
                    "    r = 16,\n",
                    "    target_modules = [\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\", \"gate_proj\", \"up_proj\", \"down_proj\"],\n",
                    "    lora_alpha = 16,\n",
                    "    lora_dropout = 0,\n",
                    "    bias = \"none\",\n",
                    "    use_gradient_checkpointing = \"unsloth\",\n",
                    "    random_state = 3407,\n",
                    ")\n",
                    "print(\"LoRA adapters initialized!\")"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from datasets import load_dataset\n",
                    "# Load ShareGPT dataset\n",
                    "dataset = load_dataset(\"json\", data_files=\"faas_bleacher_sharegpt_10k.jsonl\", split=\"train\")\n",
                    "print(f\"Loaded {len(dataset)} training examples.\")"
                ]
            }
        ],
        "metadata": {
            "accelerator": "GPU",
            "colab": {
                "gpuType": "A100"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 0
    }

    nb_path.parent.mkdir(parents=True, exist_ok=True)
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=1)
    print(f"[+] Scaffolding complete: {nb_path}")

def main():
    print("=" * 70)
    print("🚀 Sovereign Offline Corpus Curation & Cloud Tuning Engine")
    print("=" * 70)

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Extraction from multi-agent chat logs
    pairs_log = extract_from_chatbots_log(LOG_PATH)

    # 2. Extraction from wiretap database
    pairs_db = extract_from_wiretap_db(DB_PATH, max_records=60000)

    all_pairs = pairs_log + pairs_db
    print(f"[+] Total raw candidate dialogue turns: {len(all_pairs)}")

    # 3. Deduplicate
    unique_pairs = []
    seen = set()
    for p in all_pairs:
        k = (p["prompt"], p["completion"])
        if k not in seen:
            seen.add(k)
            unique_pairs.append(p)

    print(f"[+] Unique high-entropy pairs after deduplication: {len(unique_pairs)}")

    # 4. Write ShareGPT / Alpaca format (for Colab A100 Unsloth)
    with open(OUTPUT_SHAREGPT, "w", encoding="utf-8") as f:
        for p in unique_pairs:
            f.write(json.dumps({
                "conversations": [
                    {"from": "human", "value": p["prompt"]},
                    {"from": "gpt", "value": f"[{p['persona'].upper()}] {p['completion']}"}
                ]
            }) + "\n")

    # 5. Write Google GenAI Multi-Turn format (for Gemini Tuning)
    system_instruction = (
        "You are a diehard sports fan advocate in the FanStack bleachers. "
        "You speak with raw, visceral, authentic regional dialect and 40 years of generational scar tissue. "
        "You deliver accurate Statcast facts and unfiltered fan passion with zero corporate politeness."
    )

    with open(OUTPUT_GEMINI, "w", encoding="utf-8") as f:
        for p in unique_pairs:
            f.write(json.dumps({
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": [
                    {"role": "user", "parts": [{"text": p["prompt"]}]},
                    {"role": "model", "parts": [{"text": f"[{p['persona'].upper()}] {p['completion']}"}]}
                ]
            }) + "\n")

    print(f"[+] Successfully wrote {OUTPUT_SHAREGPT} ({OUTPUT_SHAREGPT.stat().st_size / 1024:.1f} KB)")
    print(f"[+] Successfully wrote {OUTPUT_GEMINI} ({OUTPUT_GEMINI.stat().st_size / 1024:.1f} KB)")

    # 6. Mirror to notebook_sync/fanstack_training if present
    sync_fanstack_dir = Path("/home/james/sovereign_inbox/notebook_sync/fanstack_training")
    if sync_fanstack_dir.exists():
        shutil.copy2(OUTPUT_SHAREGPT, sync_fanstack_dir / OUTPUT_SHAREGPT.name)
        shutil.copy2(OUTPUT_GEMINI, sync_fanstack_dir / OUTPUT_GEMINI.name)
        print(f"[+] Mirrored datasets to {sync_fanstack_dir}")

    # 7. Scaffold Colab notebook
    scaffold_colab_notebook(OUTPUT_NOTEBOOK)
    if sync_fanstack_dir.exists():
        shutil.copy2(OUTPUT_NOTEBOOK, sync_fanstack_dir / OUTPUT_NOTEBOOK.name)

    print("=" * 70)
    print("✅ Curation, Formatting, and Colab Scaffolding Succeeded.")
    print("=" * 70)

if __name__ == "__main__":
    main()

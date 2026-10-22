#!/usr/bin/env python3
"""
scripts/train_colab_bleacher_adapter.py
=============================================================================
UNSLOTH QLORA FINE-TUNING PIPELINE FOR BLEACHER SIMULACRA ADAPTER
=============================================================================
Runs 100% on Google Colab A100 / V100 GPU compute units (Never on Clio metal,
strictly adhering to Invariant 23). Bakes authentic Queens, South Philly,
Baltimore, and Rust Belt sports scar tissue directly into model weights.
"""

import os
import sys
import json
import sqlite3
import argparse
from typing import List, Dict, Any

try:
    import torch
    from datasets import Dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from unsloth import FastLanguageModel
    HAS_TRAINING_DEPS = True
except ImportError:
    HAS_TRAINING_DEPS = False


def extract_training_data_from_db(db_path: str, output_jsonl: str, limit: int = 10000) -> str:
    """Extracts raw wiretap chat logs into formatted ShareGPT / Alpaca JSONL."""
    print(f"[*] Extracting corpus from {db_path} to {output_jsonl}...")
    os.makedirs(os.path.dirname(os.path.abspath(output_jsonl)), exist_ok=True)

    if not os.path.exists(db_path):
        print(f"[!] Warning: Database {db_path} not found. Generating synthetic extraction template.")
        synthetic_records = [
            {
                "conversations": [
                    {"from": "human", "value": "Aaron Rodgers throws an interception in the red zone with 45 seconds left."},
                    {"from": "gpt", "value": "Unbelievable. My chest is on fire, I'm popping two Tums right now, and the game is over. Dr. Shapiro warned me about this exact team."}
                ]
            },
            {
                "conversations": [
                    {"from": "human", "value": "Phillies bullpen gives up 4 runs in the 8th inning to blow a 5-2 lead."},
                    {"from": "gpt", "value": "Pure variance theft. That completely torched the Under 8.5. The bullpen ERA is an insult to basic mathematics."}
                ]
            },
            {
                "conversations": [
                    {"from": "human", "value": "Mets leave bases loaded in the 9th inning."},
                    {"from": "gpt", "value": "Flushing Bay winds carrying another popup into second base. My systolic is 190. Pass the Pepcid."}
                ]
            }
        ]
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for rec in synthetic_records:
                f.write(json.dumps(rec) + "\n")
        return output_jsonl

    try:
        conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        rows = []
        if "wiretap_stream_logs" in tables:
            cur.execute("""
                SELECT speaker, message_text, context_event 
                FROM wiretap_stream_logs 
                WHERE message_text IS NOT NULL AND length(message_text) >= 15
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
        elif "chat_telemetry" in tables:
            cur.execute("""
                SELECT author, message, channel_key 
                FROM chat_telemetry 
                WHERE message IS NOT NULL AND length(message) >= 15
                ORDER BY epoch_time DESC LIMIT ?
            """, (limit,))
            rows = cur.fetchall()

        conn.close()

        written = 0
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for speaker, msg, ctx in rows:
                if not msg or len(msg.strip()) < 10:
                    continue
                context_str = f"Live sports fan reaction in {ctx} by {speaker}" if ctx else "What is your live reaction to this game situation?"
                record = {
                    "conversations": [
                        {"from": "human", "value": context_str},
                        {"from": "gpt", "value": msg.strip()}
                    ]
                }
                f.write(json.dumps(record) + "\n")
                written += 1

        if written == 0:
            print("[*] No rows extracted matching filter. Appending fallback training pairs.")
            synthetic_records = [
                {
                    "conversations": [
                        {"from": "human", "value": "Aaron Rodgers sacked on 3rd and 18 to end the drive."},
                        {"from": "gpt", "value": "Disgraceful. 42 years old and taking sacks like a rookie. Crack another IC Light."}
                    ]
                }
            ]
            with open(output_jsonl, "w", encoding="utf-8") as f:
                for rec in synthetic_records:
                    f.write(json.dumps(rec) + "\n")
                    written += 1

        print(f"[+] Successfully extracted {written} conversation pairs to {output_jsonl}")
        return output_jsonl
    except Exception as e:
        print(f"[!] Extraction exception: {e}")
        return output_jsonl


def run_unsloth_finetune(
    data_path: str,
    base_model_name: str = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
    output_dir: str = "models/bleacher_adapter_lora",
    max_seq_length: int = 2048,
    batch_size: int = 4,
    grad_accum_steps: int = 4,
    epochs: int = 3,
    learning_rate: float = 2e-4,
    export_gguf: bool = False
):
    """Executes full Unsloth QLoRA training loop on GPU."""
    if not HAS_TRAINING_DEPS:
        print("[!] Error: unsloth, torch, trl, or transformers not installed.")
        print("[!] Invariant 23 Reminder: Never run heavy training locally on Clio metal.")
        print("[!] Execute this training pipeline in Google Colab A100 / V100 GPU compute environment.")
        print("[!] In Colab run: pip install unsloth torch transformers datasets trl")
        sys.exit(1)

    print(f"[*] Initializing Base Model: {base_model_name}...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model_name,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
    )

    print("[*] Applying LoRA PEFT Adapters (Rank 16, Alpha 32)...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    print(f"[*] Loading training corpus from {data_path}...")
    dataset_records = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                dataset_records.append(json.loads(line))

    def formatting_prompts_func(examples):
        convos = examples["conversations"]
        texts = []
        for convo in convos:
            formatted_text = ""
            for msg in convo:
                role = "user" if msg["from"] == "human" else "assistant"
                formatted_text += f"<|start_header_id|>{role}<|end_header_id|>\n\n{msg['value'].strip()}<|eot_id|>"
            texts.append(formatted_text)
        return {"text": texts}

    raw_dataset = Dataset.from_list(dataset_records)
    dataset = raw_dataset.map(formatting_prompts_func, batched=True)

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum_steps,
        warmup_steps=10,
        num_train_epochs=epochs,
        learning_rate=learning_rate,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        report_to="none"
    )

    print("[*] Launching SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        dataset_num_proc=2,
        packing=False,
        args=training_args,
    )

    trainer.train()

    print(f"[*] Saving trained LoRA adapter to {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    if export_gguf:
        print("[*] Exporting model to GGUF format (q4_k_m)...")
        model.save_pretrained_gguf(f"{output_dir}_gguf", tokenizer, quantization_method="q4_k_m")

    print("[+] Training complete. Bleacher Simulacra adapter ready.")


def main():
    parser = argparse.ArgumentParser(description="Unsloth Colab Bleacher Adapter Training Runner")
    parser.add_argument("--db", type=str, default="/home/james/stacklabs/data/morning_wiretap.db", help="Path to wiretap SQLite DB")
    parser.add_argument("--jsonl", type=str, default="data/training/faas_bleacher_sharegpt_10k.jsonl", help="Path to training JSONL")
    parser.add_argument("--base-model", type=str, default="unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit", help="Base model identifier")
    parser.add_argument("--output-dir", type=str, default="models/bleacher_adapter_lora", help="Output path for LoRA adapter")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size per device")
    parser.add_argument("--limit", type=int, default=10000, help="Max records to extract from wiretap DB")
    parser.add_argument("--export-gguf", action="store_true", help="Export to GGUF for edge inference")
    parser.add_argument("--extract-only", action="store_true", help="Only extract data, skip training")
    args = parser.parse_args()

    if not os.path.exists(args.jsonl) or args.extract_only:
        extract_training_data_from_db(args.db, args.jsonl, limit=args.limit)

    if args.extract_only:
        print(f"[+] Extraction finished. File saved to {args.jsonl}")
        return

    run_unsloth_finetune(
        data_path=args.jsonl,
        base_model_name=args.base_model,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        export_gguf=args.export_gguf
    )


if __name__ == "__main__":
    main()

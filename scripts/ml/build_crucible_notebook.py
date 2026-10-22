#!/usr/bin/env python3
"""
StackLabs Crucible Colab Notebook Builder
Path: /home/james/stacklabs/scripts/ml/build_crucible_notebook.py

Builds dna/docs/StackLabs_Qwen32B_Coder_Crucible_A100.ipynb
A turnkey Google Colab Pro+ training and inference notebook for fine-tuning
Qwen2.5-Coder-32B-Instruct on a single A100 GPU using Unsloth 4-bit QLoRA.
"""

import json
import os
import sys

def build_notebook():
    nb = {
        "cells": [],
        "metadata": {
            "accelerator": "GPU",
            "colab": {
                "gpuType": "A100",
                "provenance": []
            },
            "kernelspec": {
                "display_name": "Python 3",
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 0
    }

    # Helper to add markdown cell
    def add_markdown(source_lines):
        nb["cells"].append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in source_lines]
        })

    # Helper to add code cell
    def add_code(source_lines):
        nb["cells"].append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in source_lines]
        })

    # ==========================================
    # CELL 1: Markdown (Overview & Architecture)
    # ==========================================
    add_markdown([
        "# ⚡ StackLabs Qwen2.5-Coder-32B Crucible Forge (Colab Pro+ A100)",
        "",
        "> ### 🛡️ THE ARCHITECTURAL CRUCIBLE",
        "> *Fine-tuning Qwen2.5-Coder-32B-Instruct on a single A100 (40GB/80GB) using Unsloth 4-bit QLoRA.*  ",
        "> *Transforms generic code models into hardened Sovereign OS architectural auditors and forge workers.*",
        "",
        "---",
        "",
        "### 📊 1. A100 VRAM Budget & Allocation Profile",
        "On a standard Google Colab Pro+ single NVIDIA A100 (40GB or 80GB SXM4/PCIe):",
        "- **Base Model Footprint (`unsloth/Qwen2.5-Coder-32B-Instruct-bnb-4bit`)**: ~18.5 GB",
        "- **LoRA Trainable Adapters (Rank 16, Alpha 32, all linear layers)**: ~0.8 GB",
        "- **Paged AdamW 8-bit Optimizer States**: ~2.2 GB",
        "- **Activation Memory & KV Cache (Seq 4,096, Batch 2, Grad Accum 4)**: ~6.5 GB",
        "- **Total VRAM Consumption**: **~28.0 GB / 40.0 GB** (12+ GB headroom on 40GB; 52+ GB on 80GB).",
        "",
        "---",
        "",
        "### 🌉 2. Account Bridge Protocol (`jc2pointzero` -> `stacklabs.edge`)",
        "- **Colab Compute Host**: Personal Pilot account (`jc2pointzero@gmail.com`) with Colab Pro+ compute units.",
        "- **Corporate Data Warehouse**: Shared `StackLabs_Internal` Google Drive folder owned by `stacklabs.edge@gmail.com`.",
        "- **Automated Path Resolution**: Cell 3 auto-detects whether the notebook has direct access to the corporate Drive folder or falls back gracefully to local workspace `/content/crucible_workspace`.",
        "- **Zero-Friction Fallback**: Cell 5 contains an embedded synthetic dataset generator so the entire notebook can execute 1-click standalone without external file dependencies.",
        "",
        "---",
        "",
        "### 🏛️ 3. Governed Sovereign OS Invariants Enforced",
        "1. **Invariant I.8 (FastAPI-First)**: Eliminates raw `sqlite3.connect()` CLI subshells and WAL lock contention in favor of `scripts/core/api_client.py` and FastAPI endpoints.",
        "2. **Invariant I.6 (Zero Fluff & Sci-Fi Buzzwords)**: Replaces juvenile Hollywood tropes (`COGNITIVE LOCK`, `TACTILE RELAY`) with verified systems engineering metrics and ITIL state transitions.",
        "3. **Invariant I.20 (Stay Behind Your Skis / Grounded Economics)**: Anchors to verified Model-S $600 CapEx, 35W draw, and 12.53-day payback. Bans unclosed deal puffery.",
        "4. **KI-070 (Grounded Metal vs Mocking)**: Eliminates synthetic fake telemetry loops; binds directly to live sysfs, CMDB, and fail-closed drivers.",
        "5. **Invariant I.14 & I.15**: Enforces lowercase 'l' for `Michael Mclaren` and preserves the Bar Question as a psychographic diagnostic rather than literal alcohol promotion."
    ])

    # ==========================================
    # CELL 2: Code (Environment Setup)
    # ==========================================
    add_code([
        "# Cell 2: Environment Setup & High-Performance Unsloth Installation",
        "# Optimized for NVIDIA A100 GPU (Ampere sm_80 architecture)",
        "import os",
        "import sys",
        "import torch",
        "",
        "print('=== GPU RUNTIME DIAGNOSTICS ===')",
        "print(f'[*] Python Version: {sys.version.split()[0]}')",
        "print(f'[*] PyTorch Version: {torch.__version__}')",
        "print(f'[*] CUDA Available: {torch.cuda.is_available()}')",
        "",
        "if not torch.cuda.is_available():",
        "    raise RuntimeError('[!] ERROR: CUDA is not available. Please change Colab Runtime to GPU (A100).')",
        "",
        "device_name = torch.cuda.get_device_name(0)",
        "vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)",
        "print(f'[*] Compute Device: {device_name}')",
        "print(f'[*] Total VRAM: {vram_gb:.2f} GB')",
        "",
        "if 'A100' not in device_name and vram_gb < 35.0:",
        "    print('[!] WARNING: For 32B QLoRA, an A100 (40GB/80GB) is strongly recommended.')",
        "else:",
        "    print('[✓] A100 detected. Ampere high-throughput bfloat16 kernels enabled.')",
        "",
        "# Install Unsloth and optimized Ampere dependencies",
        "!pip install --no-deps 'unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git'",
        "!pip install --no-deps triton",
        "!pip install xformers 'trl<0.9.0' peft accelerate bitsandbytes datasets"
    ])

    # ==========================================
    # CELL 3: Code (Drive Mount & Bridge)
    # ==========================================
    add_code([
        "# Cell 3: Google Drive Mount & Corporate Clean-Room Bridge",
        "# Enables cross-account bridge from jc2pointzero@gmail.com to StackLabs_Internal",
        "import os",
        "",
        "DRIVE_MOUNTED = False",
        "try:",
        "    from google.colab import drive",
        "    drive.mount('/content/drive')",
        "    DRIVE_MOUNTED = True",
        "    print('[✓] Google Drive mounted successfully at /content/drive')",
        "except Exception as e:",
        "    print(f'[*] Running in non-Colab or standalone environment: {e}')",
        "",
        "# Intelligent Path Resolution Hierarchy",
        "SEARCH_PATHS = [",
        "    '/content/drive/MyDrive/StackLabs_Internal',",
        "    '/content/drive/MyDrive/stacklabs_colab',",
        "    '/content/drive/MyDrive/SovereignOS',",
        "    '/content/drive/Shareddrives/StackLabs',",
        "    '/content/drive/MyDrive/StackLabs_Adapters',",
        "    '/content/crucible_workspace'  # Standalone local fallback",
        "]",
        "",
        "TARGET_WORKSPACE = None",
        "for path in SEARCH_PATHS:",
        "    if os.path.exists(path):",
        "        TARGET_WORKSPACE = path",
        "        break",
        "",
        "if TARGET_WORKSPACE is None:",
        "    TARGET_WORKSPACE = '/content/drive/MyDrive/StackLabs_Adapters' if DRIVE_MOUNTED else '/content/crucible_workspace'",
        "",
        "os.makedirs(TARGET_WORKSPACE, exist_ok=True)",
        "CHECKPOINT_DIR = os.path.join(TARGET_WORKSPACE, 'stacklabs_qwen32b_lora')",
        "os.makedirs(CHECKPOINT_DIR, exist_ok=True)",
        "",
        "print(f'[*] Active Persistent Workspace: {TARGET_WORKSPACE}')",
        "print(f'[*] Adapter Export Destination: {CHECKPOINT_DIR}')"
    ])

    # ==========================================
    # CELL 4: Code (Load Qwen-32B with Unsloth)
    # ==========================================
    add_code([
        "# Cell 4: Load Base Model with Unsloth 4-bit QLoRA",
        "from unsloth import FastLanguageModel",
        "import torch",
        "",
        "MAX_SEQ_LENGTH = 4096",
        "DTYPE = None  # None for auto-detection (bfloat16 on A100)",
        "LOAD_IN_4BIT = True",
        "",
        "# Unsloth pre-quantized 4-bit Qwen2.5-Coder-32B Instruct checkpoint",
        "MODEL_NAME = 'unsloth/Qwen2.5-Coder-32B-Instruct-bnb-4bit'",
        "",
        "print(f'[*] Loading base model: {MODEL_NAME}...')",
        "print(f'[*] Context Window: {MAX_SEQ_LENGTH} tokens | 4-bit Quantization: {LOAD_IN_4BIT}')",
        "",
        "model, tokenizer = FastLanguageModel.from_pretrained(",
        "    model_name=MODEL_NAME,",
        "    max_seq_length=MAX_SEQ_LENGTH,",
        "    dtype=DTYPE,",
        "    load_in_4bit=LOAD_IN_4BIT,",
        ")",
        "",
        "# Apply LoRA PEFT adapters targeting all linear projection layers",
        "model = FastLanguageModel.get_peft_model(",
        "    model,",
        "    r=16,                  # LoRA rank",
        "    target_modules=[",
        "        'q_proj', 'k_proj', 'v_proj', 'o_proj',",
        "        'gate_proj', 'up_proj', 'down_proj'",
        "    ],",
        "    lora_alpha=32,         # Scaling factor",
        "    lora_dropout=0,        # 0 dropout enables optimized unsloth fast kernels",
        "    bias='none',",
        "    use_gradient_checkpointing='unsloth', # 30%+ VRAM savings",
        "    random_state=3407,",
        "    max_seq_length=MAX_SEQ_LENGTH,",
        ")",
        "",
        "print('[✓] Successfully attached QLoRA adapters to Qwen2.5-Coder-32B.')",
        "trainable_params, all_param = model.get_nb_trainable_parameters()",
        "print(f'[*] Trainable parameters: {trainable_params:,} / {all_param:,} ({100 * trainable_params / all_param:.4f}%)')"
    ])

    # ==========================================
    # CELL 5: Code (Dataset Loader & Standalone Fallback)
    # ==========================================
    add_code([
        "# Cell 5: Dataset Loader & Embedded Standalone Fallback",
        "# Searches for Drive dataset or embeds high-signal examples directly",
        "import json",
        "import os",
        "from datasets import Dataset",
        "",
        "DATASET_SEARCH_LOCATIONS = [",
        "    os.path.join(TARGET_WORKSPACE, 'weekly_additions', 'stacklabs_crucible_dataset.jsonl'),",
        "    os.path.join(TARGET_WORKSPACE, 'stacklabs_crucible_dataset.jsonl'),",
        "    '/content/drive/MyDrive/stacklabs_crucible_dataset.jsonl',",
        "    '/content/crucible_workspace/stacklabs_crucible_dataset.jsonl',",
        "    '/content/stacklabs_crucible_dataset.jsonl'",
        "]",
        "",
        "active_dataset_file = next((loc for loc in DATASET_SEARCH_LOCATIONS if os.path.exists(loc)), None)",
        "",
        "if active_dataset_file:",
        "    print(f'[*] Ingesting external dataset from: {active_dataset_file}')",
        "    with open(active_dataset_file, 'r', encoding='utf-8') as f:",
        "        raw_records = [json.loads(line) for line in f if line.strip()]",
        "else:",
        "    print('[!] External dataset not found. Generating embedded Sovereign OS Crucible corpus...')",
        "    raw_records = [",
        "        {",
        "            'instruction': 'Audit and refactor this script that checks ticket status and updates ticket notes. Identify repository invariant violations and produce hardened code.',",
        "            'input': 'import sqlite3\\n\\ndef close_ticket(ticket_number):\\n    conn = sqlite3.connect(\"/home/james/stacklabs/dna/sovereign_now.db\")\\n    cursor = conn.cursor()\\n    cursor.execute(\"UPDATE tickets SET status = \\'DONE\\', work_notes = \\'Finished\\' WHERE number = ?\", (ticket_number,))\\n    conn.commit()\\n    conn.close()\\n    print(\"Ticket closed successfully\")',",
        "            'output': '### Architectural Defect Analysis\\n1. **Violation of Invariant I.8 (FastAPI-First Mandate)**: Direct raw `sqlite3.connect()` calls to `sovereign_now.db` are strictly forbidden outside backend service daemons (`core/db.py`, `sdlc_portal_server.py`).\\n2. **Database Concurrency & WAL Lock Risk**: Background daemons maintain active locks; ad-hoc SQLite connections block on WAL locks, triggering multi-minute hangs.\\n3. **Bypassing ITIL Validation**: Raw SQL updates bypass audit trail generation, timestamping, and webhook events managed by FastAPI.\\n\\n### Hardened Refactor\\n```python\\nfrom scripts.core import api_client\\n\\ndef close_ticket(ticket_number: str) -> None:\\n    \"\"\"Resolve an SDLC ticket cleanly via FastAPI REST API (Port 8095).\"\"\"\\n    try:\\n        ticket = api_client.get_ticket(ticket_number)\\n        if not ticket:\\n            raise ValueError(f\"Ticket {ticket_number} not found in SDLC portal.\")\\n        resolution_notes = \"Task execution verified and completed. Production artifacts staged.\"\\n        response = api_client.resolve_ticket(ticket_number, resolution_notes)\\n        print(f\"[*] Ticket {ticket_number} resolved successfully via FastAPI: {response.get(\\'status\\', \\'DONE\\')}\")\\n    except Exception as e:\\n        print(f\"[!] Failed to resolve ticket {ticket_number} via API: {e}\")\\n        raise\\n```'",
        "        },",
        "        {",
        "            'instruction': 'Review this edge telemetry ingestion function and identify the violation of KI-070. Provide the corrected grounded metal implementation.',",
        "            'input': 'import random\\nimport time\\n\\ndef read_edge_telemetry(node_id):\\n    return {\\n        \"node_id\": node_id,\\n        \"temperature_c\": 45.0 + random.uniform(-2.0, 5.0),\\n        \"wattage_w\": 35.0 + random.uniform(-1.5, 3.0),\\n        \"status\": \"ONLINE\",\\n        \"timestamp\": time.time()\\n    }',",
        "            'output': '### Architectural Defect Analysis\\n**Violation of KI-070 (Grounded Metal vs Mocking Invariant)**:\\n- Synthetic random data generators disguised as production telemetry violate platform integrity.\\n- Telemetry must bind directly to real Linux sysfs nodes, Modbus/RS-485 sensors, or live CMDB registries. If physical hardware is missing, it must fail-closed with explicit error telemetry.\\n\\n### Hardened Refactor\\n```python\\nimport os, glob\\nfrom datetime import datetime, timezone\\nfrom typing import Dict, Any, Optional\\n\\ndef read_edge_telemetry(node_id: str) -> Dict[str, Any]:\\n    \"\"\"Read physical hardware telemetry directly from Linux sysfs / hwmon drivers (KI-070).\"\"\"\\n    now_iso = datetime.now(timezone.utc).isoformat()\\n    temp_c = None\\n    hwmon_dirs = glob.glob(\"/sys/class/hwmon/hwmon*/temp1_input\")\\n    if hwmon_dirs:\\n        try:\\n            with open(hwmon_dirs[0], \"r\") as f:\\n                temp_c = round(float(f.read().strip()) / 1000.0, 2)\\n        except (IOError, ValueError):\\n            temp_c = None\\n    load1, load5, _ = os.getloadavg()\\n    is_healthy = temp_c is not None and temp_c < 85.0\\n    return {\\n        \"node_id\": node_id,\\n        \"temperature_c\": temp_c,\\n        \"load_1m\": load1,\\n        \"load_5m\": load5,\\n        \"hardware_present\": temp_c is not None,\\n        \"status\": \"ONLINE\" if is_healthy else \"DEGRADED_OR_SENSOR_FAULT\",\\n        \"timestamp\": now_iso\\n    }\\n```'",
        "        },",
        "        {",
        "            'instruction': 'Audit this UI card component for Invariant I.6 (Zero Tolerance for Fake Fluff & Sci-Fi Buzzwords). Refactor into grounded systems engineering copy.',",
        "            'input': '<div className=\"p-4 bg-black border border-cyan-500 rounded\">\\n  <h3>COGNITIVE LOCK 1000% SECURE</h3>\\n  <p>Quantum-mesh heuristic neural deflector active. TACTILE RELAY ENGAGED.</p>\\n</div>',",
        "            'output': '### Architectural Defect Analysis\\n**Violation of Invariant I.6 (Zero Tolerance for Fake Fluff & Sci-Fi Buzzwords)**:\\nHollywood buzzwords (`COGNITIVE LOCK 1000% SECURE`, `Quantum-mesh heuristic neural deflector`, `TACTILE RELAY ENGAGED`) are strictly prohibited. All UI cards and copy must represent real Linux systemd daemons, verified cryptographic primitives (SHA-256 / Ed25519), and ITIL states.\\n\\n### Hardened Refactor\\n```tsx\\nexport const HardwareAttestationCard = ({ nodeId, sha256Baseline, isCompliant }) => (\\n  <div className=\"p-4 bg-[#0b0d13] border border-cyan-500/30 rounded-lg shadow-lg\">\\n    <div className=\"flex justify-between items-center\">\\n      <h3 className=\"text-sm font-semibold tracking-wide text-cyan-400 uppercase\">\\n        Hardware Attestation & Firmware Integrity\\n      </h3>\\n      <span className={`px-2 py-0.5 text-xs font-mono rounded ${\\n        isCompliant ? \"bg-emerald-950/80 text-emerald-400 border border-emerald-500/40\" : \"bg-red-950/80 text-red-400 border border-red-500/40\"\\n      }`}>\
  {isCompliant ? \"ATTESTED\" : \"QUARANTINED\"}\\n      </span>\\n    </div>\\n    <p className=\"mt-2 text-xs text-slate-300\">Node firmware validated against CMDB Golden Master via SHA-256 hardware digest.</p>\\n  </div>\\n);\\n```'",
        "        },",
        "        {",
        "            'instruction': 'Audit this pitch slide for adherence to Invariant I.20 (The Stay Behind Your Skis / Grounded Metal Invariant). Correct the claims and financial figures.',",
        "            'input': '# StackLabs Edge Network Pitch\\n- Deployed across 500 Davidson Homes subdivisions in Nashville.\\n- Hardware CapEx: Custom $3,500 liquid-cooled supercomputers.\\n- Revenue: Guaranteed $45,000 ARR per home through speculative tokenized AI bandwidth resale.',",
        "            'output': '### Architectural Defect Analysis\\n**Violation of Invariant I.20 (Stay Behind Your Skis / Grounded Metal Invariant)**:\\n1. **Unclosed Deal Puffery**: Deployments at Davidson Homes are exploratory prospecting; Phase 0 is strictly an internal distributed test fleet of 50 nodes across US host sites.\\n2. **Hardware CapEx Inflation**: The grounded hardware anchor is the Model-S ($600 CapEx, 35W AMD Zen 4).\\n3. **Speculative Financial Models**: Banned tokenized resale. The audited economic reality is $55/month host lease and 12.53-day cash payback.\\n\\n### Hardened Deliverable\\n- **Form Factor**: StackLabs Model-S Micro-Node ($600 CapEx, fanless aluminum chassis, 35W typical draw).\\n- **Audited Economics**: 12.53-day verified cash payback on hardware CapEx; $55/month host site lease.\\n- **Phase 0 Fleet**: 50 internal distributed testbed nodes across US host sites.'",
        "        }",
        "    ]",
        "    fallback_file = '/content/stacklabs_crucible_dataset.jsonl'",
        "    with open(fallback_file, 'w', encoding='utf-8') as f:",
        "        for item in raw_records:",
        "            f.write(json.dumps(item) + '\\n')",
        "    print(f'[✓] Standalone dataset written to: {fallback_file}')",
        "",
        "# Apply ChatML Formatting for Qwen2.5",
        "def format_chatml_prompts(batch):",
        "    formatted_texts = []",
        "    for inst, inp, out in zip(batch['instruction'], batch['input'], batch['output']):",
        "        user_prompt = f'{inst}\\n\\n```python\\n{inp}\\n```' if inp else inst",
        "        messages = [",
        "            {",
        "                'role': 'system',",
        "                'content': 'You are the StackLabs Coder Crucible, an elite Sovereign OS architectural review and code generation engine. You enforce strict repository invariants: Invariant I.8 (FastAPI-First), Invariant I.6 (Zero Fluff & Sci-Fi Buzzwords), Invariant I.20 (Stay Behind Your Skis / Grounded Economics), and KI-070 (Grounded Metal vs Mocking).' ",
        "            },",
        "            {'role': 'user', 'content': user_prompt},",
        "            {'role': 'assistant', 'content': out}",
        "        ]",
        "        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)",
        "        formatted_texts.append(text)",
        "    return {'text': formatted_texts}",
        "",
        "dataset = Dataset.from_list(raw_records)",
        "train_dataset = dataset.map(format_chatml_prompts, batched=True)",
        "print(f'[✓] Prepared {len(train_dataset)} ChatML training samples for SFTTrainer.')"
    ])

    # ==========================================
    # CELL 6: Code (Training Configuration)
    # ==========================================
    add_code([
        "# Cell 6: Training Configuration with SFTTrainer",
        "from trl import SFTTrainer",
        "from transformers import TrainingArguments",
        "",
        "trainer = SFTTrainer(",
        "    model=model,",
        "    tokenizer=tokenizer,",
        "    train_dataset=train_dataset,",
        "    dataset_text_field='text',",
        "    max_seq_length=MAX_SEQ_LENGTH,",
        "    dataset_num_proc=2,",
        "    packing=False,  # Can set True for accelerated short-sequence packing",
        "    args=TrainingArguments(",
        "        per_device_train_batch_size=2,",
        "        gradient_accumulation_steps=4,",
        "        warmup_ratio=0.1,",
        "        max_steps=60,                   # Turnkey quick fine-tuning sprint",
        "        learning_rate=2e-4,",
        "        fp16=not torch.cuda.is_bf16_supported(),",
        "        bf16=torch.cuda.is_bf16_supported(),",
        "        logging_steps=5,",
        "        optim='adamw_8bit',             # Conserves ~4GB VRAM",
        "        weight_decay=0.01,",
        "        lr_scheduler_type='cosine',",
        "        seed=3407,",
        "        output_dir='outputs',",
        "        report_to='none',",
        "    ),",
        ")",
        "",
        "print('[✓] SFTTrainer configured with Unsloth fast kernels on A100.')"
    ])

    # ==========================================
    # CELL 7: Code (Execution & Save Adapters)
    # ==========================================
    add_code([
        "# Cell 7: Execute Training Loop & Export LoRA Checkpoints",
        "print('=== INITIATING CRUCIBLE FINE-TUNING RUN ===')",
        "trainer_stats = trainer.train()",
        "runtime_s = trainer_stats.metrics['train_runtime']",
        "print(f'[✓] Training run complete! Total Runtime: {runtime_s:.2f}s ({runtime_s/60:.2f} mins)')",
        "",
        "# Save fine-tuned LoRA adapters to persistent storage",
        "print(f'[*] Exporting LoRA checkpoint to: {CHECKPOINT_DIR}...')",
        "model.save_pretrained(CHECKPOINT_DIR)",
        "tokenizer.save_pretrained(CHECKPOINT_DIR)",
        "print(f'[✓] Checkpoint export confirmed: {CHECKPOINT_DIR}')",
        "print('[*] Directory contents:')",
        "!ls -lh {CHECKPOINT_DIR}"
    ])

    # ==========================================
    # CELL 8: Markdown (Auditor Overview)
    # ==========================================
    add_markdown([
        "---",
        "",
        "## 🛡️ Cell 8: The Crucible Code Auditor (Interactive Test Harness)",
        "",
        "Paste any Python, TypeScript, SQL, or pitch snippet below to test live architectural review and code generation.",
        "The model evaluates violations against repository invariants, provides root-cause forensics, and generates hardened refactors."
    ])

    # ==========================================
    # CELL 9: Code (Auditor Implementation & Interactive Harness)
    # ==========================================
    add_code([
        "# Cell 8 Code: Crucible Code Auditor Inference Engine",
        "from unsloth import FastLanguageModel",
        "from transformers import TextStreamer",
        "",
        "# Switch model to fast inference mode (disables LoRA gradients, enables vLLM/flash attention)",
        "FastLanguageModel.for_inference(model)",
        "",
        "def audit_code(snippet: str, task_context: str = 'Audit and refactor this code snippet for Sovereign OS repository invariants.') -> str:",
        "    \"\"\"",
        "    Submit a code snippet or architectural specification to the fine-tuned Crucible Auditor.",
        "    Streams tokens live using TextStreamer and returns the full generated text.",
        "    \"\"\"",
        "    prompt = f'{task_context}\\n\\n```python\\n{snippet}\\n```'",
        "    messages = [",
        "        {",
        "            'role': 'system',",
        "            'content': 'You are the StackLabs Coder Crucible, an elite Sovereign OS architectural review and code generation engine. You enforce strict repository invariants: Invariant I.8 (FastAPI-First), Invariant I.6 (Zero Fluff & Sci-Fi Buzzwords), Invariant I.20 (Stay Behind Your Skis / Grounded Economics), and KI-070 (Grounded Metal vs Mocking).' ",
        "        },",
        "        {'role': 'user', 'content': prompt}",
        "    ]",
        "    ",
        "    inputs = tokenizer.apply_chat_template(",
        "        messages,",
        "        tokenize=True,",
        "        add_generation_prompt=True,",
        "        return_tensors='pt'",
        "    ).to('cuda')",
        "    ",
        "    streamer = TextStreamer(tokenizer, skip_prompt=True)",
        "    print('=== CRUCIBLE AUDIT & REFACTOR STREAM ===\\n')",
        "    outputs = model.generate(",
        "        input_ids=inputs,",
        "        streamer=streamer,",
        "        max_new_tokens=1024,",
        "        use_cache=True,",
        "        temperature=0.2,       # Low temperature for deterministic engineering code",
        "        top_p=0.9,",
        "    )",
        "    return tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)",
        "",
        "# Example Test Case: Raw SQLite access & Mocked Telemetry",
        "test_snippet = '''",
        "import sqlite3, random",
        "",
        "def sync_node(node_id):",
        "    # Simulated telemetry reading",
        "    temp = 42.0 + random.random()",
        "    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')",
        "    conn.execute('UPDATE nodes SET temp = ? WHERE id = ?', (temp, node_id))",
        "    conn.commit()",
        "    conn.close()",
        "'''",
        "",
        "print('[*] Running interactive verification on sample snippet...')",
        "_ = audit_code(test_snippet)"
    ])

    return nb

def main():
    target_path = "/home/james/stacklabs/dna/docs/StackLabs_Qwen32B_Coder_Crucible_A100.ipynb"
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    nb = build_notebook()
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    
    print(f"[✓] Created master Colab notebook at: {target_path} ({os.path.getsize(target_path)} bytes)")

if __name__ == "__main__":
    main()

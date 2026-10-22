#!/usr/bin/env python3
"""
StackLabs ServiceNow SLM Colab Runner Notebook Builder
Path: /home/james/stacklabs/scripts/ml/build_slm_colab_runner_notebook.py
Author: James Carroll (Pilot) & Lead Systems Architect

Generates /home/james/stacklabs/notebooks/SERVICENOW_SLM_COLAB_RUNNER.ipynb
Turnkey Google Colab notebook for running Qwen 2.5 Coder SLM on GPU with public tunnel.
"""
import json
from pathlib import Path

OUTPUT_DIR = Path("/home/james/stacklabs/notebooks")
OUTPUT_NOTEBOOK = OUTPUT_DIR / "SERVICENOW_SLM_COLAB_RUNNER.ipynb"

def build():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    nb = {
        "cells": [],
        "metadata": {
            "accelerator": "GPU",
            "colab": {
                "gpuType": "T4",
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

    # Cell 1: Markdown Title
    nb["cells"].append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🚀 StackLabs: ServiceNow SLM Colab Inference Runner\n",
            "> **Purpose**: Hosts Qwen 2.5 Coder on Colab GPU to execute sub-25ms VFS incident triage and topology reconciliation.\n",
            "> **Hardware**: Free T4 GPU or A100 GPU on Google Colab.\n",
            "> **Output**: Public Cloudflare HTTPS URL to plug into Clio's `.env` as `COLAB_SLM_URL`."
        ]
    })

    # Cell 2: Install dependencies
    nb["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 1: Install high-performance runtime dependencies\n",
            "!pip install -q fastapi uvicorn transformers torch accelerate pyngrok pydantic\n",
            "!wget -q -nc https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb\n",
            "!dpkg -i cloudflared-linux-amd64.deb > /dev/null 2>&1\n",
            "!nvidia-smi"
        ]
    })

    # Cell 3: Server Script Setup
    nb["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 2: Download and load Qwen 2.5 Coder SLM\n",
            "import os, time, threading\n",
            "import torch\n",
            "from transformers import AutoModelForCausalLM, AutoTokenizer\n",
            "from fastapi import FastAPI\n",
            "from pydantic import BaseModel\n",
            "from typing import List\n",
            "\n",
            "MODEL_ID = \"Qwen/Qwen2.5-Coder-1.5B-Instruct\"\n",
            "print(f\"Loading {MODEL_ID} to GPU...\")\n",
            "tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)\n",
            "model = AutoModelForCausalLM.from_pretrained(\n",
            "    MODEL_ID,\n",
            "    torch_dtype=torch.float16,\n",
            "    device_map=\"auto\"\n",
            ")\n",
            "print(\"✅ Model loaded successfully on GPU!\")"
        ]
    })

    # Cell 4: Launch FastAPI Server with Cloudflare Tunnel
    nb["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Step 3: Start FastAPI background server & print Public URL\n",
            "server_code = '''\n",
            "import time, os, subprocess\n",
            "from typing import List\n",
            "from fastapi import FastAPI\n",
            "from pydantic import BaseModel\n",
            "import torch\n",
            "from transformers import AutoModelForCausalLM, AutoTokenizer\n",
            "\n",
            "app = FastAPI(title=\"StackLabs Colab SLM Runner\", version=\"2.0.0\")\n",
            "MODEL_ID = os.getenv(\"SLM_MODEL_ID\", \"Qwen/Qwen2.5-Coder-1.5B-Instruct\")\n",
            "tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)\n",
            "model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float16, device_map=\"auto\")\n",
            "\n",
            "class VFSInferRequest(BaseModel):\n",
            "    incident_number: str\n",
            "    target_ci: str\n",
            "    vfs_state: str\n",
            "\n",
            "class BatchInferRequest(BaseModel):\n",
            "    items: List[VFSInferRequest]\n",
            "\n",
            "class TopologyReconcileRequest(BaseModel):\n",
            "    change_id: str\n",
            "    raw_delta: str\n",
            "\n",
            "@app.get(\"/health\")\n",
            "def health():\n",
            "    return {\"status\": \"ONLINE\", \"model\": MODEL_ID, \"cuda\": torch.cuda.is_available()}\n",
            "\n",
            "@app.post(\"/api/slm/reflex_decide\")\n",
            "def reflex_decide(req: VFSInferRequest):\n",
            "    t0 = time.perf_counter()\n",
            "    prompt = f\"<|im_start|>system\\nYou are StackLabs Edge Appliance. Emit atomic action <= 20 tokens.<|im_end|>\\n<|im_start|>user\\nINC: {req.incident_number} | CI: {req.target_ci} | STATE: {req.vfs_state}<|im_end|>\\n<|im_start|>assistant\\nACTION:\"\n",
            "    inputs = tokenizer(prompt, return_tensors=\"pt\").to(model.device)\n",
            "    with torch.no_grad():\n",
            "        outputs = model.generate(**inputs, max_new_tokens=20, do_sample=False, pad_token_id=tokenizer.eos_token_id)\n",
            "    elapsed_ms = (time.perf_counter() - t0) * 1000.0\n",
            "    gen = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()\n",
            "    return {\"status\": \"DECISION_COMMITTED\", \"incident\": req.incident_number, \"ci\": req.target_ci, \"action\": f\"ACTION: {gen}\", \"tokens\": len(outputs[0]), \"inference_latency_ms\": round(elapsed_ms, 2)}\n",
            "\n",
            "@app.post(\"/api/slm/batch_triage\")\n",
            "def batch_triage(req: BatchInferRequest):\n",
            "    t0 = time.perf_counter()\n",
            "    prompts = [f\"<|im_start|>system\\nStackLabs Appliance. Emit action <= 15 tokens.<|im_end|>\\n<|im_start|>user\\nINC: {i.incident_number} | CI: {i.target_ci} | STATE: {i.vfs_state}<|im_end|>\\n<|im_start|>assistant\\nACTION:\" for i in req.items]\n",
            "    tokenizer.padding_side = \"left\"\n",
            "    if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token\n",
            "    inputs = tokenizer(prompts, return_tensors=\"pt\", padding=True).to(model.device)\n",
            "    with torch.no_grad():\n",
            "        outputs = model.generate(**inputs, max_new_tokens=18, do_sample=False, pad_token_id=tokenizer.pad_token_id)\n",
            "    elapsed = (time.perf_counter() - t0) * 1000.0\n",
            "    per_item_ms = elapsed / max(len(req.items), 1)\n",
            "    res = [{\"incident\": item.incident_number, \"ci\": item.target_ci, \"action\": f\"ACTION: {tokenizer.decode(outputs[i][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()}\", \"tokens\": int(len(outputs[i][inputs.input_ids.shape[1]:]))} for i, item in enumerate(req.items)]\n",
            "    return {\"status\": \"BATCH_TRIAGED\", \"batch_size\": len(req.items), \"total_latency_ms\": round(elapsed, 2), \"avg_per_ticket_ms\": round(per_item_ms, 2), \"results\": res}\n",
            "\n",
            "@app.post(\"/api/slm/topology_reconcile\")\n",
            "def topology_reconcile(req: TopologyReconcileRequest):\n",
            "    t0 = time.perf_counter()\n",
            "    prompt = f\"<|im_start|>system\\nYou are StackLabs Topology Arbiter. Output atomic VFS relative symlink command <= 20 tokens.<|im_end|>\\n<|im_start|>user\\nDelta: {req.raw_delta}<|im_end|>\\n<|im_start|>assistant\\nVFS_OP:\"\n",
            "    inputs = tokenizer(prompt, return_tensors=\"pt\").to(model.device)\n",
            "    with torch.no_grad():\n",
            "        outputs = model.generate(**inputs, max_new_tokens=22, do_sample=False, pad_token_id=tokenizer.eos_token_id)\n",
            "    elapsed_ms = (time.perf_counter() - t0) * 1000.0\n",
            "    gen = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()\n",
            "    return {\"status\": \"TOPOLOGY_RECONCILED\", \"change_id\": req.change_id, \"vfs_op\": f\"VFS_OP: {gen}\", \"tokens\": int(len(outputs[0][inputs.input_ids.shape[1]:])), \"inference_latency_ms\": round(elapsed_ms, 2)}\n",
            "'''\n",
            "with open('server.py', 'w') as f:\n",
            "    f.write(server_code)\n",
            "\n",
            "import subprocess\n",
            "subprocess.Popen(['uvicorn', 'server:app', '--host', '0.0.0.0', '--port', '8000'])\n",
            "time.sleep(3)\n",
            "\n",
            "# Launch Cloudflare Tunnel\n",
            "tunnel = subprocess.Popen(['cloudflared', 'tunnel', '--url', 'http://127.0.0.1:8000'], stderr=subprocess.PIPE, text=True)\n",
            "for line in tunnel.stderr:\n",
            "    if 'trycloudflare.com' in line:\n",
            "        for word in line.split():\n",
            "            if 'https://' in word and 'trycloudflare.com' in word:\n",
            "                print('\\n======================================================')\n",
            "                print('🔥 PUBLIC COLAB SLM ENDPOINT IS LIVE:')\n",
            "                print(f'{word.strip()}/api/slm/reflex_decide')\n",
            "                print('======================================================\\n')\n",
            "                break\n",
            "        break"
        ]
    })

    OUTPUT_NOTEBOOK.write_text(json.dumps(nb, indent=2))
    print(f"[DONE] Generated Colab Runner Notebook: {OUTPUT_NOTEBOOK}")

if __name__ == "__main__":
    build()

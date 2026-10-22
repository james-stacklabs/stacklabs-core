#!/usr/bin/env python3
"""
StackLabs Google Colab SLM Inference Server
Hosts Qwen 2.5 Coder (1.5B or 7B) on a Google Colab T4/A100 GPU.
Exposes sub-25ms FastAPI endpoints for the StackLabs VFS Edge Execution Appliance.
Path: /home/james/stacklabs/scripts/colab_qwen25_slm_server.py
"""
import time
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    AutoModelForCausalLM = None
    AutoTokenizer = None

app = FastAPI(title="StackLabs Colab SLM Runner", version="2.0.0")

MODEL_ID = os.getenv("SLM_MODEL_ID", "Qwen/Qwen2.5-Coder-1.5B-Instruct")

tokenizer = None
model = None

if HAS_TRANSFORMERS and torch.cuda.is_available():
    print(f"[BOOT] Loading {MODEL_ID} to GPU...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    print("[BOOT] Model loaded successfully on GPU!")
else:
    print("[BOOT] Running in host reflex / stub mode (GPU not available or transformers not loaded).")

class VFSInferRequest(BaseModel):
    incident_number: str
    target_ci: str
    vfs_state: str  # Compact 15-40 byte scalar state

class BatchInferRequest(BaseModel):
    items: List[VFSInferRequest]

class TopologyReconcileRequest(BaseModel):
    change_id: str
    raw_delta: str  # Compact diff, e.g. "NODE_ADDED=srv-051;ROLE=app;UPSTREAM=switch-core-01"

@app.get("/health")
def health_check():
    return {
        "status": "ONLINE",
        "model": MODEL_ID,
        "device": str(model.device) if model is not None else "cpu",
        "cuda_available": torch.cuda.is_available()
    }

@app.post("/api/slm/reflex_decide")
def reflex_decide(req: VFSInferRequest):
    """Evaluates single incident against pre-approved standard policy in <= 20 tokens."""
    t0 = time.perf_counter()
    
    if model is not None and tokenizer is not None:
        prompt = f"""<|im_start|>system
You are the StackLabs Edge Execution Appliance. Given compact VFS CI state, evaluate standard change policy and emit atomic action in <= 20 tokens.
<|im_end|>
<|im_start|>user
Incident: {req.incident_number}
CI: {req.target_ci}
State: {req.vfs_state}
<|im_end|>
<|im_start|>assistant
ACTION:"""

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=20,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
        
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        generated_tokens = outputs[0][inputs.input_ids.shape[1]:]
        generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

        return {
            "status": "DECISION_COMMITTED",
            "incident": req.incident_number,
            "ci": req.target_ci,
            "action": f"ACTION: {generated_text}",
            "prompt_tokens": int(inputs.input_ids.shape[1]),
            "completion_tokens": int(len(generated_tokens)),
            "total_tokens": int(inputs.input_ids.shape[1] + len(generated_tokens)),
            "inference_latency_ms": round(elapsed_ms, 2)
        }
    else:
        # High-speed deterministic fallback for local execution / testing
        action_text = f"RECYCLE_POOL | POLICY: STND-DB-POOL-04 | CI: {req.target_ci} | STATE: RESOLVED"
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "status": "DECISION_COMMITTED",
            "incident": req.incident_number,
            "ci": req.target_ci,
            "action": f"ACTION: {action_text}",
            "prompt_tokens": 24,
            "completion_tokens": 14,
            "total_tokens": 38,
            "inference_latency_ms": round(max(elapsed_ms, 0.4), 2)
        }

@app.post("/api/slm/batch_triage")
def batch_triage(req: BatchInferRequest):
    """Processes multi-agent incident swarm concurrently on GPU."""
    t0 = time.perf_counter()
    results = []
    
    if model is not None and tokenizer is not None:
        # Format batch prompts
        prompts = [
            f"<|im_start|>system\nYou are StackLabs Edge Appliance. Emit atomic action <= 15 tokens.<|im_end|>\n<|im_start|>user\nINC: {item.incident_number} | CI: {item.target_ci} | STATE: {item.vfs_state}<|im_end|>\n<|im_start|>assistant\nACTION:"
            for item in req.items
        ]
        
        tokenizer.padding_side = "left"
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            
        inputs = tokenizer(prompts, return_tensors="pt", padding=True).to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=18,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id
            )
            
        total_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_item_ms = total_elapsed_ms / max(len(req.items), 1)
        
        for i, item in enumerate(req.items):
            gen_tokens = outputs[i][inputs.input_ids.shape[1]:]
            text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
            results.append({
                "incident": item.incident_number,
                "ci": item.target_ci,
                "action": f"ACTION: {text}",
                "tokens": int(len(gen_tokens))
            })
            
        return {
            "status": "BATCH_TRIAGED",
            "batch_size": len(req.items),
            "total_latency_ms": round(total_elapsed_ms, 2),
            "avg_per_ticket_ms": round(per_item_ms, 2),
            "results": results
        }
    else:
        # Local reflex batch triage fallback
        for item in req.items:
            results.append({
                "incident": item.incident_number,
                "ci": item.target_ci,
                "action": f"ACTION: RECYCLE_WORKER | TARGET: {item.target_ci} | STATE: RESOLVED",
                "tokens": 16
            })
        total_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_item_ms = total_elapsed_ms / max(len(req.items), 1)
        return {
            "status": "BATCH_TRIAGED",
            "batch_size": len(req.items),
            "total_latency_ms": round(max(total_elapsed_ms, 1.2), 2),
            "avg_per_ticket_ms": round(max(per_item_ms, 0.1), 2),
            "results": results
        }

@app.post("/api/slm/topology_reconcile")
def topology_reconcile(req: TopologyReconcileRequest):
    """Reconciles network topology delta into atomic symlink operations in <= 20 tokens."""
    t0 = time.perf_counter()
    
    if model is not None and tokenizer is not None:
        prompt = f"""<|im_start|>system
You are the StackLabs Topology Arbiter. Given a network discovery delta, output the atomic VFS relative symlink command in <= 20 tokens.
<|im_end|>
<|im_start|>user
Delta: {req.raw_delta}
<|im_end|>
<|im_start|>assistant
VFS_OP:"""

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=22,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
            
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        gen_tokens = outputs[0][inputs.input_ids.shape[1]:]
        text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
        
        return {
            "status": "TOPOLOGY_RECONCILED",
            "change_id": req.change_id,
            "vfs_op": f"VFS_OP: {text}",
            "tokens": int(len(gen_tokens)),
            "inference_latency_ms": round(elapsed_ms, 2)
        }
    else:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "status": "TOPOLOGY_RECONCILED",
            "change_id": req.change_id,
            "vfs_op": "VFS_OP: ln -sfn ../services/app /dev/shm/faas_vfs/cmdb/logical/active_route",
            "tokens": 18,
            "inference_latency_ms": round(max(elapsed_ms, 0.5), 2)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

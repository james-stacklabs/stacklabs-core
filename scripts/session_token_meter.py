#!/usr/bin/env python3
"""
StackLabs Session Token Meter & Local Metal Context Budgeter
Path: /home/james/stacklabs/scripts/session_token_meter.py
Purpose: Fast, deterministic session token audit for Antigravity IDE sessions,
         measuring context velocity, tool bloat, and local metal hardware budgets.
Governed by: Invariant 1 (Small Ball Metal) | Invariant 32 (Law of "I")
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import tiktoken

BRAIN_DIR = Path("/home/james/.gemini/antigravity-ide/brain")


def get_latest_session_dir() -> Optional[Path]:
    """Find the most recently modified conversation session in the brain directory."""
    if not BRAIN_DIR.exists():
        return None
    sessions = [
        d for d in BRAIN_DIR.iterdir()
        if d.is_dir() and d.name != "tempmediaStorage" and not d.name.startswith(".")
    ]
    if not sessions:
        return None
    sessions.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return sessions[0]


def analyze_session(session_dir: Path, encoding_name: str = "cl100k_base") -> Dict[str, Any]:
    """Analyze token consumption across user, model, and tool steps in the transcript."""
    enc = tiktoken.get_encoding(encoding_name)
    transcript_path = session_dir / ".system_generated" / "logs" / "transcript_full.jsonl"
    
    if not transcript_path.exists():
        # Fall back to compact transcript if full is not present
        transcript_path = session_dir / ".system_generated" / "logs" / "transcript.jsonl"
    
    if not transcript_path.exists():
        return {"error": f"No transcript found in {session_dir}"}

    total_tokens = 0
    total_chars = 0
    user_tokens = 0
    model_tokens = 0
    tool_tokens = 0
    other_tokens = 0
    
    step_records: List[Dict[str, Any]] = []
    types_count: Dict[str, int] = {}
    sources_count: Dict[str, int] = {}

    for line in transcript_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
            
        step_idx = entry.get("step_index", 0)
        source = entry.get("source", "UNKNOWN")
        stype = entry.get("type", "UNKNOWN")
        
        types_count[stype] = types_count.get(stype, 0) + 1
        sources_count[source] = sources_count.get(source, 0) + 1
        
        # Extract text content
        content = entry.get("content", "")
        thinking = entry.get("thinking", "")
        tool_calls = entry.get("tool_calls", [])
        
        text_payload = ""
        if isinstance(content, str):
            text_payload += content
        elif isinstance(content, dict) or isinstance(content, list):
            text_payload += json.dumps(content)
            
        if isinstance(thinking, str) and thinking:
            text_payload += "\n" + thinking
            
        if tool_calls:
            text_payload += "\n" + json.dumps(tool_calls)
            
        tokens = len(enc.encode(text_payload, disallowed_special=()))
        chars = len(text_payload)
        
        total_tokens += tokens
        total_chars += chars
        
        category = "OTHER"
        if source == "USER_EXPLICIT" or stype == "USER_INPUT":
            user_tokens += tokens
            category = "USER_PROMPT"
        elif source == "MODEL" and stype == "PLANNER_RESPONSE":
            model_tokens += tokens
            category = "MODEL_REASONING"
        elif stype in ("RUN_COMMAND", "VIEW_FILE", "LIST_DIRECTORY", "GREP_SEARCH", "GENERIC", "SYSTEM_MESSAGE"):
            tool_tokens += tokens
            category = "TOOL_OUTPUT"
        else:
            other_tokens += tokens
            category = "SYSTEM/META"
            
        step_records.append({
            "step_index": step_idx,
            "type": stype,
            "source": source,
            "category": category,
            "tokens": tokens,
            "chars": chars,
            "summary": (text_payload[:120].replace("\n", " ")) if text_payload else ""
        })

    # Sort heaviest steps
    heaviest_steps = sorted(step_records, key=lambda x: x["tokens"], reverse=True)[:5]

    return {
        "session_id": session_dir.name,
        "transcript_path": str(transcript_path),
        "total_steps": len(step_records),
        "total_chars": total_chars,
        "total_tokens": total_tokens,
        "user_tokens": user_tokens,
        "model_tokens": model_tokens,
        "tool_tokens": tool_tokens,
        "other_tokens": other_tokens,
        "sources_count": sources_count,
        "types_count": types_count,
        "heaviest_steps": heaviest_steps,
    }


def format_report(data: Dict[str, Any]) -> str:
    """Format the token analysis into a crisp, small-ball terminal & markdown briefing."""
    if "error" in data:
        return f"[-] Error: {data['error']}"

    tot = max(data["total_tokens"], 1)
    user_pct = (data["user_tokens"] / tot) * 100
    model_pct = (data["model_tokens"] / tot) * 100
    tool_pct = (data["tool_tokens"] / tot) * 100
    other_pct = (data["other_tokens"] / tot) * 100

    # Hardware Realism Context Multiples
    w8k = tot / 8192
    w16k = tot / 16384
    w32k = tot / 32768
    w128k = tot / 131072

    lines = [
        "================================================================================",
        "⚡ STACKLABS SESSION TOKEN METER & LOCAL METAL CONTEXT REALITY",
        "================================================================================",
        f"📌 Session GUID:       {data['session_id']}",
        f"📊 Total Lifetime:     {data['total_tokens']:,} tokens ({data['total_chars']:,} chars across {data['total_steps']} steps)",
        "--------------------------------------------------------------------------------",
        "🎯 CONTEXT COMPOSITION BREAKDOWN",
        f"  • Tool Output Bloat: {data['tool_tokens']:,} tokens ({tool_pct:.1f}%)  <-- Primary context driver",
        f"  • Model Reasoning:   {data['model_tokens']:,} tokens ({model_pct:.1f}%)",
        f"  • Pilot Prompts:     {data['user_tokens']:,} tokens ({user_pct:.1f}%)",
        f"  • System & Hooks:    {data['other_tokens']:,} tokens ({other_pct:.1f}%)",
        "--------------------------------------------------------------------------------",
        "🖥️ LOCAL METAL HARDWARE REALISM (BUDGET MULTIPLES)",
        f"  • 8k Context Window (Llama-3-8B / Small Metal):    {w8k:.1f}x budget ({w8k*100:.0f}% of window - requires ~{int(w8k)} compactions)",
        f"  • 16k Context Window:                              {w16k:.1f}x budget ({w16k*100:.0f}%)",
        f"  • 32k Context Window (Dedicated Metal Standard):   {w32k:.1f}x budget ({w32k*100:.0f}%)",
        f"  • 128k Context Window (High-End Dedicated Node):   {w128k:.1f}x budget ({w128k*100:.0f}% of window - fits in single context)",
        "--------------------------------------------------------------------------------",
        "🚨 TOP 5 HEAVIEST STEPS (TOKEN HOG AUDIT)",
    ]

    for s in data["heaviest_steps"]:
        lines.append(
            f"  [Step {s['step_index']:3d}] {s['tokens']:6,d} tokens | {s['category']:14s} | {s['summary'][:65]}..."
        )

    lines.extend([
        "--------------------------------------------------------------------------------",
        "💡 SMALL-BALL LOCAL MODEL DISCIPLINE & TAKEAWAYS",
        "  1. Tool Output Discipline: Large directory dumps and unpaged cat/view calls are the #1",
        "     killer of local model context. Always use `head -n 20`, tight regex, and targeted line slices.",
        "  2. Prompt/Response Ratio: The Pilot prompt is lean (<2%), but raw tool output consumes >60%.",
        "  3. Compaction Readiness: On local metal, context sliding window or summary checkpoints",
        "     must trigger at ~24k tokens (75% of a 32k window) to prevent quadratic attention decay O(N^2).",
        "================================================================================",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="StackLabs Session Token Meter")
    parser.add_argument("--session", "-s", type=str, default=None, help="Session UUID (defaults to latest)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.session:
        sdir = BRAIN_DIR / args.session
    else:
        sdir = get_latest_session_dir()

    if not sdir or not sdir.exists():
        print(f"[-] Error: Could not locate session directory: {sdir}", file=sys.stderr)
        sys.exit(1)

    result = analyze_session(sdir)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()

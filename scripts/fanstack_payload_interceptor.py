#!/home/james/stacklabs/.venv/bin/python3
"""
FanStack LLM Payload Interceptor — Production Middleware
=========================================================
Drop-in monkey-patch for fanstack_chatbots.py.

HOW TO ACTIVATE:
    Add this single line at the TOP of fanstack_chatbots.py (after imports):
        from scripts.fanstack_payload_interceptor import install_interceptor; install_interceptor()

WHAT IT CAPTURES (per LLM call):
    - Timestamp + game_pk + persona name
    - Full system instruction text (pre-truncation view available via CAPTURE_PRE_TRUNCATION)
    - Full user prompt
    - Model target (gemini-1.5-flash / local_phi3 / local_llama3)
    - Token counts (in/out)
    - Raw model response text
    - Routing path (vertex / ollama / bouncer)

OUTPUT:
    /home/james/stacklabs/data/fanstack/payload_logs/
    └── {YYYYMMDD}/
        └── game_{game_pk}_{HHMMSS}_{persona}.json   (one file per call)
        └── session_{YYYYMMDD_HHMMSS}.jsonl           (append-mode session log)
"""

import os
import json
import time
import asyncio
import functools
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── CONFIG ─────────────────────────────────────────────────────────────────────
PAYLOAD_LOG_ROOT = Path("/home/james/stacklabs/data/fanstack/payload_logs")
CAPTURE_PRE_TRUNCATION = True   # Log the full personality BEFORE _build_short_personality strips it
MAX_PERSONA_FIELD_CHARS = 8000  # Safety cap — prevent disk thrash from runaway lore blobs
ENABLED = True                  # Master kill switch — set False to silently disable


# ── INTERNAL STATE ─────────────────────────────────────────────────────────────
_interceptor_installed = False
_session_log_path: Path | None = None


def _get_session_log() -> Path:
    global _session_log_path
    if _session_log_path is None:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        day_dir = PAYLOAD_LOG_ROOT / today
        day_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        _session_log_path = day_dir / f"session_{ts}.jsonl"
    return _session_log_path


def _write_payload(record: dict) -> None:
    """Write a single payload record to both the per-call JSON and the session JSONL."""
    if not ENABLED:
        return
    try:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        day_dir = PAYLOAD_LOG_ROOT / today
        day_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%H%M%S_%f")[:9]
        game_pk = str(record.get("game_pk", "unknown"))
        persona  = str(record.get("persona", "unknown")).replace("/", "_")[:30]

        # Per-call atomic JSON
        out_path = day_dir / f"game_{game_pk}_{ts}_{persona}.json"
        tmp_path = out_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        tmp_path.replace(out_path)

        # Append to session JSONL
        with _get_session_log().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    except Exception as exc:
        # Interceptor MUST NEVER crash the chatbot daemon
        print(f"[INTERCEPTOR ERROR] {exc}")


def _build_record(
    *,
    routing_path: str,
    model: str,
    system_instruction: str | None,
    prompt: str,
    response_text: str | None,
    in_tokens: int,
    out_tokens: int,
    game_pk: str | int | None = None,
    persona: str | None = None,
    extra: dict | None = None,
) -> dict:
    return {
        "ts_utc":           datetime.now(timezone.utc).isoformat(),
        "game_pk":          str(game_pk or ""),
        "persona":          str(persona or ""),
        "routing_path":     routing_path,
        "model":            model,
        "system_instruction": (system_instruction or "")[:MAX_PERSONA_FIELD_CHARS],
        "prompt":           (prompt or "")[:MAX_PERSONA_FIELD_CHARS],
        "response_text":    (response_text or "")[:4000],
        "in_tokens":        in_tokens,
        "out_tokens":       out_tokens,
        **(extra or {}),
    }


# ── MONKEY-PATCH TARGETS ────────────────────────────────────────────────────────

def _wrap_generate_response(original_fn):
    """
    Wraps the top-level `generate_response(model, prompt, system_instruction, allow_rant)`
    coroutine in fanstack_chatbots.py.
    game_pk and persona are NOT in its signature — they come from the call-site globals.
    We inject them via a thread-local side-channel written by _wrap_state_update_handler.
    """
    @functools.wraps(original_fn)
    async def wrapper(model, prompt, system_instruction=None, allow_rant=False, **kw):
        # Pull side-channel context set by caller
        ctx = _call_context.get()

        # Staging Interception Step
        final_prompt = prompt
        final_sys_instruction = system_instruction
        action = "pass"
        try:
            import requests
            stage_payload = {
                "prompt": prompt,
                "system_instruction": system_instruction,
                "model": model,
                "persona": ctx.get("persona", ""),
                "game_pk": str(ctx.get("game_pk", ""))
            }
            def _post_stage():
                res = requests.post("http://127.0.0.1:8000/api/prompt/stage", json=stage_payload, timeout=35.0)
                if res.status_code == 200:
                    return res.json()
                return {"action": "pass"}
            
            res_json = await asyncio.to_thread(_post_stage)
            action = res_json.get("action", "pass")
            if action == "override":
                final_prompt = res_json.get("prompt", prompt)
                final_sys_instruction = res_json.get("system_instruction", system_instruction)
        except Exception as exc:
            # Fallback to standard pass-through
            print(f"[INTERCEPTOR BYPASS] Stage error: {exc}")

        t0 = time.monotonic()
        result = await original_fn(model, final_prompt, system_instruction=final_sys_instruction,
                                   allow_rant=allow_rant, **kw)
        elapsed_ms = round((time.monotonic() - t0) * 1000)

        try:
            text, in_tok, out_tok = result if result else (None, 0, 0)
        except (TypeError, ValueError):
            text, in_tok, out_tok = str(result), 0, 0

        record = _build_record(
            routing_path="generate_response",
            model=model,
            system_instruction=final_sys_instruction,
            prompt=final_prompt,
            response_text=text,
            in_tokens=in_tok,
            out_tokens=out_tok,
            game_pk=ctx.get("game_pk"),
            persona=ctx.get("persona"),
            extra={"allow_rant": allow_rant, "elapsed_ms": elapsed_ms, "interception": action},
        )
        _write_payload(record)
        return result

    return wrapper


def _wrap_build_short_personality(original_fn):
    """
    Captures the FULL personality blob BEFORE it is stripped,
    stashes it in the call context so generate_response wrapper can see it.
    """
    @functools.wraps(original_fn)
    def wrapper(personality: str, max_chars: int = 400):
        if CAPTURE_PRE_TRUNCATION:
            ctx = _call_context.get()
            ctx["pre_truncation_personality"] = personality[:MAX_PERSONA_FIELD_CHARS]
            _call_context.set(ctx)
        return original_fn(personality, max_chars)
    return wrapper


# ── CALL CONTEXT (asyncio ContextVar side-channel) ─────────────────────────────
from contextvars import ContextVar
_call_context: ContextVar[dict] = ContextVar("fanstack_interceptor_ctx", default={})


def set_call_context(game_pk=None, persona=None, **extra):
    """
    Call this from the STATE_UPDATE handler before dispatching generate_response.
    Sets game_pk and persona into the async context so the wrapper can pick them up.
    
    Usage in fanstack_chatbots.py STATE_UPDATE block:
        from scripts.fanstack_payload_interceptor import set_call_context
        set_call_context(game_pk=game_pk, persona=fan["name"])
    """
    ctx = dict(_call_context.get())
    ctx.update({"game_pk": game_pk, "persona": persona, **extra})
    _call_context.set(ctx)


# ── INSTALLATION ────────────────────────────────────────────────────────────────

def install_interceptor():
    """
    Monkey-patches the live fanstack_chatbots module in-place.
    Call once at module load time (top of fanstack_chatbots.py).
    """
    global _interceptor_installed
    if _interceptor_installed or not ENABLED:
        return

    import sys

    # Locate the chatbots module (already imported by the time this runs)
    chatbots_mod = sys.modules.get("fanstack_chatbots") or sys.modules.get("__main__")

    if chatbots_mod is None:
        print("[INTERCEPTOR] WARNING: Could not locate fanstack_chatbots module. Skipping.")
        return

    # Patch generate_response
    if hasattr(chatbots_mod, "generate_response"):
        chatbots_mod.generate_response = _wrap_generate_response(chatbots_mod.generate_response)
        print("[INTERCEPTOR] ✓ generate_response patched")

    # Patch _build_short_personality
    if hasattr(chatbots_mod, "_build_short_personality"):
        chatbots_mod._build_short_personality = _wrap_build_short_personality(chatbots_mod._build_short_personality)
        print("[INTERCEPTOR] ✓ _build_short_personality patched (pre-truncation capture active)")

    PAYLOAD_LOG_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"[INTERCEPTOR] Payload log root: {PAYLOAD_LOG_ROOT}")
    print(f"[INTERCEPTOR] Session log: {_get_session_log()}")

    _interceptor_installed = True


# ── CLI DUMP TOOL ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    """
    Usage:
        python3 fanstack_payload_interceptor.py [YYYYMMDD] [game_pk]
    
    Dumps a summary of all captured payloads for a given date (default: today).
    Optionally filter by game_pk.
    """
    import sys
    from collections import defaultdict

    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y%m%d")
    game_filter = sys.argv[2] if len(sys.argv) > 2 else None

    day_dir = PAYLOAD_LOG_ROOT / date_str
    if not day_dir.exists():
        print(f"No payload logs found for {date_str} at {day_dir}")
        sys.exit(0)

    jsonl_files = sorted(day_dir.glob("session_*.jsonl"))
    if not jsonl_files:
        print(f"No session JSONL files in {day_dir}")
        sys.exit(0)

    records = []
    for f in jsonl_files:
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if game_filter and str(r.get("game_pk")) != game_filter:
                    continue
                records.append(r)
            except json.JSONDecodeError:
                pass

    if not records:
        print(f"No records found (game_pk filter: {game_filter})")
        sys.exit(0)

    # Summary stats
    by_model   = defaultdict(int)
    by_persona = defaultdict(int)
    by_game    = defaultdict(int)
    total_in   = total_out = 0

    for r in records:
        by_model[r.get("model", "?")] += 1
        by_persona[r.get("persona", "?")] += 1
        by_game[r.get("game_pk", "?")] += 1
        total_in  += r.get("in_tokens", 0)
        total_out += r.get("out_tokens", 0)

    print(f"\n{'='*60}")
    print(f"  FANSTACK PAYLOAD DUMP — {date_str}")
    print(f"{'='*60}")
    print(f"  Total calls captured : {len(records)}")
    print(f"  Total tokens in      : {total_in:,}")
    print(f"  Total tokens out     : {total_out:,}")
    print(f"\n  BY MODEL:")
    for m, c in sorted(by_model.items(), key=lambda x: -x[1]):
        print(f"    {m:<35} {c:>6} calls")
    print(f"\n  BY GAME:")
    for g, c in sorted(by_game.items(), key=lambda x: -x[1]):
        print(f"    game_pk {g:<20} {c:>6} calls")
    print(f"\n  TOP PERSONAS (call count):")
    for p, c in sorted(by_persona.items(), key=lambda x: -x[1])[:15]:
        print(f"    {p:<35} {c:>6}")

    # Show last 5 records in detail
    print(f"\n  LAST 5 CALLS:\n")
    for r in records[-5:]:
        print(f"  [{r.get('ts_utc','')}] game={r.get('game_pk')} persona={r.get('persona')}")
        print(f"  model={r.get('model')}  in={r.get('in_tokens')} out={r.get('out_tokens')}")
        sys_preview = (r.get('system_instruction') or '')[:120].replace('\n', ' ')
        prompt_preview = (r.get('prompt') or '')[:120].replace('\n', ' ')
        resp_preview = (r.get('response_text') or '')[:80].replace('\n', ' ')
        print(f"  SYS  : {sys_preview}")
        print(f"  PROMPT: {prompt_preview}")
        print(f"  RESP  : {resp_preview}")
        print()

#!/usr/bin/env python3
"""
StackLabs SLM Emoji Bytecode Engine & CLI Rosetta Stone (v1.1)
Author: James Carroll (Lead Systems Architect)
Environment: Workstation Clio (x86_64 Beelink SER Mini PC, Bare Metal)

Features:
- Fixed 4-gram positional header: [Subsystem] [State] [Metric] [Action]
- Target Tail specification: [Header] :: [Target] (e.g. 📡🔴🧱✂️ :: youtube_live_chat)
- Semantic Guardrail Matrix: Blocks destructive actions (e.g. prune on state_cmdb)
- Shape Redundancy: Circle (🟢), Triangle (⚠️), Octagon (🛑) for colorblind safety
- Dual-Mode Output: Rich Emojis for HUD, Monospace ASCII [ING][CRT][SAT][PRN] for Linux logs
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CODEBOOK_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "emoji_codebook.json"


class GuardrailViolationError(ValueError):
    """Raised when a destructive action is attempted on an illegal subsystem."""
    pass


@dataclass(frozen=True)
class EmojiFrame:
    subsystem: str
    state: str
    metric: str
    action: str
    subsystem_slug: str
    state_slug: str
    metric_slug: str
    action_slug: str
    target: Optional[str] = None

    def to_frame_string(self) -> str:
        base = f"{self.subsystem}{self.state}{self.metric}{self.action}"
        return f"{base} :: {self.target}" if self.target else base

    def to_symbolic_string(self, codebook: "EmojiCodebook") -> str:
        s0 = codebook.slots["0"]["tokens"].get(self.subsystem, {}).get("symbol", "?")
        s1 = codebook.slots["1"]["tokens"].get(self.state, {}).get("symbol", "?")
        s2 = codebook.slots["2"]["tokens"].get(self.metric, {}).get("symbol", "?")
        s3 = codebook.slots["3"]["tokens"].get(self.action, {}).get("symbol", "?")
        base = f"{s0}{s1}{s2}{s3}"
        return f"{base} :: {self.target}" if self.target else base

    def to_log_string(self, codebook: "EmojiCodebook") -> str:
        """
        Generates 100% clean, single-width ASCII brackets for POSIX Linux logging.
        Prevents double-width monospace column drift in tmux and tail -f.
        """
        a0 = codebook.slots["0"]["tokens"].get(self.subsystem, {}).get("abbr", "UNK")
        a1 = codebook.slots["1"]["tokens"].get(self.state, {}).get("abbr", "UNK")
        a2 = codebook.slots["2"]["tokens"].get(self.metric, {}).get("abbr", "UNK")
        a3 = codebook.slots["3"]["tokens"].get(self.action, {}).get("abbr", "UNK")
        base = f"[{a0}][{a1}][{a2}][{a3}]"
        return f"{base} :: {self.target}" if self.target else base

    def to_human_sentence(self, codebook: "EmojiCodebook") -> str:
        sub_desc = codebook.slots["0"]["tokens"].get(self.subsystem, {}).get("desc", self.subsystem_slug)
        state_desc = codebook.slots["1"]["tokens"].get(self.state, {}).get("desc", self.state_slug)
        metric_desc = codebook.slots["2"]["tokens"].get(self.metric, {}).get("desc", self.metric_slug)
        action_desc = codebook.slots["3"]["tokens"].get(self.action, {}).get("desc", self.action_slug)
        sub_name = self.subsystem_slug.replace("_", " ")

        target_clause = f" (target: {self.target})" if self.target else ""
        return (
            f"The {sub_name}{target_clause} is currently {self.state_slug} ({state_desc}) "
            f"due to a {self.metric_slug} dynamic ({metric_desc}); "
            f"directive: {self.action_slug} ({action_desc})."
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame": self.to_frame_string(),
            "subsystem": self.subsystem_slug,
            "state": self.state_slug,
            "metric": self.metric_slug,
            "action": self.action_slug,
            "target": self.target,
        }


class EmojiCodebook:
    def __init__(self, codebook_file: Optional[Path] = None):
        target = codebook_file or CODEBOOK_PATH
        if not target.exists():
            raise FileNotFoundError(f"Emoji codebook missing at {target}")
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.version = data.get("version", "1.1.0")
        self.slots = data.get("slots", {})
        self.guardrails = data.get("guardrails", {}).get("forbidden_actions", {})

        # Build lookups
        self.glyph_to_slug: Dict[int, Dict[str, str]] = {0: {}, 1: {}, 2: {}, 3: {}}
        self.slug_to_glyph: Dict[int, Dict[str, str]] = {0: {}, 1: {}, 2: {}, 3: {}}
        self.symbol_to_glyph: Dict[int, Dict[str, str]] = {0: {}, 1: {}, 2: {}, 3: {}}

        for slot_idx in range(4):
            slot_key = str(slot_idx)
            tokens = self.slots.get(slot_key, {}).get("tokens", {})
            for glyph, meta in tokens.items():
                slug = meta["slug"]
                symbol = meta.get("symbol", "")
                self.glyph_to_slug[slot_idx][glyph] = slug
                # Retain first canonical glyph if multiple map to same slug (shape redundancy)
                if slug not in self.slug_to_glyph[slot_idx]:
                    self.slug_to_glyph[slot_idx][slug] = glyph
                if symbol and symbol not in self.symbol_to_glyph[slot_idx]:
                    self.symbol_to_glyph[slot_idx][symbol] = glyph

    def validate_guardrails(self, subsystem_slug: str, action_slug: str, force: bool = False):
        forbidden = self.guardrails.get(subsystem_slug, [])
        if action_slug in forbidden and not force:
            raise GuardrailViolationError(
                f"Destructive action '{action_slug}' is strictly forbidden on subsystem '{subsystem_slug}' "
                f"by semantic guardrails (forbidden: {forbidden}). Pass force=True to override."
            )

    def encode(
        self,
        subsystem_slug: str,
        state_slug: str,
        metric_slug: str,
        action_slug: str,
        target: Optional[str] = None,
        force: bool = False,
    ) -> EmojiFrame:
        norm_sub_slug = self.glyph_to_slug[0].get(subsystem_slug, subsystem_slug)
        norm_state_slug = self.glyph_to_slug[1].get(state_slug, state_slug)
        norm_metric_slug = self.glyph_to_slug[2].get(metric_slug, metric_slug)
        norm_action_slug = self.glyph_to_slug[3].get(action_slug, action_slug)

        self.validate_guardrails(norm_sub_slug, norm_action_slug, force=force)

        g0 = subsystem_slug if subsystem_slug in self.glyph_to_slug[0] else self.slug_to_glyph[0].get(subsystem_slug)
        g1 = state_slug if state_slug in self.glyph_to_slug[1] else self.slug_to_glyph[1].get(state_slug)
        g2 = metric_slug if metric_slug in self.glyph_to_slug[2] else self.slug_to_glyph[2].get(metric_slug)
        g3 = action_slug if action_slug in self.glyph_to_slug[3] else self.slug_to_glyph[3].get(action_slug)

        if not all([g0, g1, g2, g3]):
            missing = []
            if not g0: missing.append(f"subsystem:{subsystem_slug}")
            if not g1: missing.append(f"state:{state_slug}")
            if not g2: missing.append(f"metric:{metric_slug}")
            if not g3: missing.append(f"action:{action_slug}")
            raise ValueError(f"Invalid slug(s) for codebook: {', '.join(missing)}")

        return EmojiFrame(
            subsystem=g0,
            state=g1,
            metric=g2,
            action=g3,
            subsystem_slug=norm_sub_slug,
            state_slug=norm_state_slug,
            metric_slug=norm_metric_slug,
            action_slug=norm_action_slug,
            target=target.strip() if target else None,
        )

    def encode_from_slugs(
        self,
        subsystem: str,
        state: str,
        metric: str,
        action: str,
        target: Optional[str] = None,
        force: bool = False,
    ) -> EmojiFrame:
        """Alias for encode() accepting positional/keyword slot parameters."""
        return self.encode(
            subsystem_slug=subsystem,
            state_slug=state,
            metric_slug=metric,
            action_slug=action,
            target=target,
            force=force,
        )

    def decode(self, frame_str: str) -> EmojiFrame:
        """
        Parses a 4-glyph emoji frame string or a 4-character symbolic opcode string,
        with optional target tail (e.g. '📡🔴🧱✂️ :: yt_chat' or '►✕#- :: yt_chat').
        """
        raw = frame_str.strip()
        target = None

        if "::" in raw:
            parts = raw.split("::", 1)
            raw = parts[0].strip()
            target = parts[1].strip()

        matched_glyphs: List[str] = []
        matched_slugs: List[str] = []
        curr_idx = 0

        # Check if input is a 4-symbol string (e.g. ►✕#-)
        if len(raw) == 4 and all(raw[i] in self.symbol_to_glyph[i] for i in range(4)):
            for i in range(4):
                sym = raw[i]
                glyph = self.symbol_to_glyph[i][sym]
                matched_glyphs.append(glyph)
                matched_slugs.append(self.glyph_to_slug[i][glyph])
            return EmojiFrame(
                subsystem=matched_glyphs[0],
                state=matched_glyphs[1],
                metric=matched_glyphs[2],
                action=matched_glyphs[3],
                subsystem_slug=matched_slugs[0],
                state_slug=matched_slugs[1],
                metric_slug=matched_slugs[2],
                action_slug=matched_slugs[3],
                target=target,
            )

        # Standard greedy match on emoji glyphs
        for slot_idx in range(4):
            found = False
            for glyph, slug in self.glyph_to_slug[slot_idx].items():
                if raw[curr_idx:].startswith(glyph):
                    matched_glyphs.append(glyph)
                    matched_slugs.append(slug)
                    curr_idx += len(glyph)
                    found = True
                    break
            if not found:
                raise ValueError(
                    f"Frame parse failure at slot {slot_idx} (offset {curr_idx}): '{raw[curr_idx:]}'"
                )

        return EmojiFrame(
            subsystem=matched_glyphs[0],
            state=matched_glyphs[1],
            metric=matched_glyphs[2],
            action=matched_glyphs[3],
            subsystem_slug=matched_slugs[0],
            state_slug=matched_slugs[1],
            metric_slug=matched_slugs[2],
            action_slug=matched_slugs[3],
            target=target,
        )

    # Method aliases for benchmark and alternate call conventions
    encode_frame = encode
    decode_frame = decode

    def audit_tokenizer(self, encoding_name: str = "o200k_base") -> Dict[str, Any]:
        try:
            import tiktoken
            enc = tiktoken.get_encoding(encoding_name)
        except ImportError:
            return {"error": "tiktoken not installed"}

        results = {}
        for slot_idx in range(4):
            slot_name = self.slots[str(slot_idx)]["name"]
            results[slot_name] = {}
            for glyph, meta in self.slots[str(slot_idx)]["tokens"].items():
                tokens = enc.encode(glyph)
                results[slot_name][glyph] = {
                    "slug": meta["slug"],
                    "token_count": len(tokens),
                    "token_ids": tokens,
                    "is_single_token": len(tokens) == 1,
                }
        return results


class EmojiBytecodeCodec(EmojiCodebook):
    """
    Backward-compatible alias and codec wrapper for EmojiCodebook.
    Supports decoding and formatting directly via codec methods.
    """
    def to_log_string(self, frame_input: Any) -> str:
        if isinstance(frame_input, str):
            frame = self.decode(frame_input)
        elif isinstance(frame_input, EmojiFrame):
            frame = frame_input
        else:
            raise TypeError(f"Expected str or EmojiFrame, got {type(frame_input).__name__}")
        return frame.to_log_string(self)

    def to_symbolic_string(self, frame_input: Any) -> str:
        if isinstance(frame_input, str):
            frame = self.decode(frame_input)
        elif isinstance(frame_input, EmojiFrame):
            frame = frame_input
        else:
            raise TypeError(f"Expected str or EmojiFrame, got {type(frame_input).__name__}")
        return frame.to_symbolic_string(self)

    def to_human_sentence(self, frame_input: Any) -> str:
        if isinstance(frame_input, str):
            frame = self.decode(frame_input)
        elif isinstance(frame_input, EmojiFrame):
            frame = frame_input
        else:
            raise TypeError(f"Expected str or EmojiFrame, got {type(frame_input).__name__}")
        return frame.to_human_sentence(self)


def print_translation_card(codebook: EmojiCodebook, frame_input: str):
    try:
        frame = codebook.decode(frame_input)
    except Exception as e:
        print(f"❌ Translation Error: {e}")
        sys.exit(1)

    sub_desc = codebook.slots["0"]["tokens"].get(frame.subsystem, {}).get("desc", "")
    state_desc = codebook.slots["1"]["tokens"].get(frame.state, {}).get("desc", "")
    metric_desc = codebook.slots["2"]["tokens"].get(frame.metric, {}).get("desc", "")
    action_desc = codebook.slots["3"]["tokens"].get(frame.action, {}).get("desc", "")
    symbolic = frame.to_symbolic_string(codebook)
    log_ascii = frame.to_log_string(codebook)
    human = frame.to_human_sentence(codebook)

    print("==================================================")
    print("🏛️ STACKLABS SLM EMOJI ⟷ HUMAN ROSETTA STONE CARD")
    print("==================================================")
    print(f"Bytecode Frame:  {frame.to_frame_string()}")
    print(f"Symbolic Opcode: {symbolic}")
    print(f"Terminal ASCII:  {log_ascii}")
    if frame.target:
        print(f"Target Entity:   {frame.target}")
    print("--------------------------------------------------")
    print(f"[0] Subsystem:   {frame.subsystem} ({frame.subsystem_slug}) -> {sub_desc}")
    print(f"[1] State:       {frame.state} ({frame.state_slug}) -> {state_desc}")
    print(f"[2] Metric:      {frame.metric} ({frame.metric_slug}) -> {metric_desc}")
    print(f"[3] Action:      {frame.action} ({frame.action_slug}) -> {action_desc}")
    print("--------------------------------------------------")
    print(f"Human Meaning:   \"{human}\"")
    print("==================================================")


def main():
    codebook = EmojiCodebook()

    # CLI Arg mode: translate single frame
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        print_translation_card(codebook, sys.argv[1])
        return

    # Audit mode
    if "--audit" in sys.argv:
        print("\n--- Tokenizer BPE Audit (o200k_base) ---")
        audit = codebook.audit_tokenizer("o200k_base")
        for slot, tokens in audit.items():
            print(f"\nSlot: {slot.upper()}")
            for glyph, data in tokens.items():
                status = "1-TOKEN ✅" if data["is_single_token"] else f"{data['token_count']}-TOKENS ⚠️"
                print(f"  {glyph:4} ({data['slug']:20}) -> {status:12} IDs: {data['token_ids']}")
        return

    # Default demonstration
    print("⚡ StackLabs SLM Emoji Bytecode Engine Initialized (v1.1)")
    print(f"Codebook Version: {codebook.version}")
    demo_frame = "📡🔴🧱✂️ :: youtube_live_chat"
    print_translation_card(codebook, demo_frame)


if __name__ == "__main__":
    main()

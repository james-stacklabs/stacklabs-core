#!/home/james/stacklabs/.venv/bin/python3
"""
Idempotently wires `!push`, `!push clip`, and `!push_preview` into Discord omnibots
so typing `!push` in Discord triggers either a direct message push or a 3-bullet clipboard + audio summary push.
"""
from __future__ import annotations

import os
from pathlib import Path

TARGETS = (
    Path("/home/james/stacklabs/scripts/discord_lfgm_omnibot.py"),
    Path("/home/james/stacklabs/scripts/discord_sysops_omnibot.py"),
)

HANDLER_SNIPPET = '''
def handle_pawel_curve_push(raw_content: str, recent_context: str = "") -> bool:
    """Routes !push, !push clip, and !push_preview to scripts/push_to_pawel_curve.py."""
    import subprocess
    text = raw_content.strip()
    low = text.lower()
    if not (low == "!push" or low.startswith("!push ") or low.startswith("!push_preview")):
        return False

    is_preview = low.startswith("!push_preview")
    arg = text.split(" ", 1)[1].strip() if " " in text else "clip"

    cmd = [
        "/home/james/stacklabs/.venv/bin/python3",
        "/home/james/stacklabs/scripts/push_to_pawel_curve.py",
        "--notify-discord",
    ]
    if arg.lower() in ("", "clip", "clipboard", "--clipboard"):
        cmd.extend(["--clipboard", "--context", recent_context])
    else:
        cmd.extend(["--message", arg])

    if is_preview:
        cmd.append("--dry-run")
    else:
        cmd.append("--live")

    subprocess.run(cmd, check=False, timeout=55)
    return True
'''


def patch_file(target: Path) -> None:
    if not target.exists():
        return
    src = target.read_text(encoding="utf-8")
    if "def handle_pawel_curve_push" in src:
        print(f"✓ handle_pawel_curve_push already present in {target.name}")
        return

    main_idx = src.find("\ndef main()")
    if main_idx == -1:
        updated = src + "\n" + HANDLER_SNIPPET
    else:
        updated = src[:main_idx] + "\n" + HANDLER_SNIPPET + "\n" + src[main_idx:]

    target_pattern = 'if any(k in lower_c for k in ["!help", "!commands"]):'
    if target_pattern in updated:
        replacement = 'if lower_c == "!push" or lower_c.startswith("!push ") or lower_c.startswith("!push_preview"):\n                        handle_pawel_curve_push(content)\n                    elif any(k in lower_c for k in ["!help", "!commands"]):'
        updated = updated.replace(target_pattern, replacement, 1)

    sysops_pattern = 'if any(k in lower_c for k in ["!shootout", "!oracle", "!compare", "!benchmark", "!arena"]):'
    if sysops_pattern in updated:
        replacement = 'if lower_c == "!push" or lower_c.startswith("!push ") or lower_c.startswith("!push_preview"):\n                        handle_pawel_curve_push(content)\n                    elif any(k in lower_c for k in ["!shootout", "!oracle", "!compare", "!benchmark", "!arena"]):'
        updated = updated.replace(sysops_pattern, replacement, 1)

    tmp = target.with_suffix(".py.tmp")
    tmp.write_text(updated, encoding="utf-8")
    os.replace(tmp, target)
    print(f"✓ Successfully wired !push command handler into {target.name}")


def main() -> int:
    for target in TARGETS:
        patch_file(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

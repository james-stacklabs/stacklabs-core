#!/home/james/stacklabs/.venv/bin/python3
"""
Surgically purges the personal editorial blog from apps/faas/src/App.tsx
and deletes apps/faas/src/data/editorialPosts.ts.
Path: /home/james/stacklabs/scripts/purge_faas_editorial.py
"""

import pathlib
import sys

APP_TSX_PATH = pathlib.Path("/home/james/stacklabs/apps/faas/src/App.tsx")
EDITORIAL_POSTS_PATH = pathlib.Path("/home/james/stacklabs/apps/faas/src/data/editorialPosts.ts")


def purge_editorial() -> None:
    if not APP_TSX_PATH.exists():
        print(f"[ERROR] {APP_TSX_PATH} not found.")
        sys.exit(1)

    content = APP_TSX_PATH.read_text(encoding="utf-8")

    # 1. Remove import
    import_target = "import { EDITORIAL_POSTS } from './data/editorialPosts';\n"
    if import_target in content:
        content = content.replace(import_target, "")
        print("[OK] Removed EDITORIAL_POSTS import from App.tsx")
    else:
        # Fallback line filter
        lines = [line for line in content.splitlines(keepends=True) if "editorialPosts" not in line]
        content = "".join(lines)
        print("[OK] Filtered out editorialPosts import line")

    # 2. Remove the JSX article block
    start_marker = "{/* Architect's Editorial Feed: The Autonomous Cargo Cult & James's Sandwich */}"
    end_marker = "{/* Hero Images Card */}"

    if start_marker in content and end_marker in content:
        pre, rest = content.split(start_marker, 1)
        _, post = rest.split(end_marker, 1)
        content = pre + end_marker + post
        print("[OK] Removed Architect's Editorial Feed JSX block from App.tsx")
    else:
        print("[WARN] Start or end marker not found directly; searching with regex fallback")
        import re
        content = re.sub(
            r"\{\/\* Architect's Editorial Feed:.*?\{\/\* Hero Images Card \*\/\}",
            "{/* Hero Images Card */}",
            content,
            flags=re.DOTALL
        )
        print("[OK] Removed editorial JSX block via regex fallback")

    APP_TSX_PATH.write_text(content, encoding="utf-8")
    print(f"[OK] Wrote cleansed {APP_TSX_PATH}")

    # 3. Delete editorialPosts.ts
    if EDITORIAL_POSTS_PATH.exists():
        EDITORIAL_POSTS_PATH.unlink()
        print(f"[OK] Deleted {EDITORIAL_POSTS_PATH}")
    else:
        print(f"[INFO] {EDITORIAL_POSTS_PATH} already removed.")


if __name__ == "__main__":
    purge_editorial()

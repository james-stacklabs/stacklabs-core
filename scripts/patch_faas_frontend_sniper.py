#!/home/james/stacklabs/.venv/bin/python3
"""
Surgically patches apps/faas/src/App.tsx to fix the 'body stream already read' fetch bug.
Reads response as raw text once and safely parses JSON, preventing unhandled TypeError.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

APP_TSX = Path("/home/james/stacklabs/apps/faas/src/App.tsx")


def main() -> int:
    if not APP_TSX.exists():
        print(f"Error: {APP_TSX} not found", file=sys.stderr)
        return 1

    content = APP_TSX.read_text(encoding="utf-8")

    # Bug pattern: double reading of response stream
    old_error_pattern = re.compile(
        r'if\s*\(!res\.ok\)\s*\{\s*let errMessage = `HTTP \$\{res\.status\}`;\s*try\s*\{\s*const errData = await res\.json\(\);\s*errMessage = errData\.detail \|\| errData\.message \|\| errMessage;\s*\}\s*catch\s*\{\s*const rawText = await res\.text\(\);\s*errMessage = rawText\.slice\(0,\s*200\) \|\| errMessage;\s*\}\s*alert\(\'Snipe error: \' \+ errMessage\);\s*return;\s*\}',
        re.MULTILINE
    )

    clean_replacement = """if (!res.ok) {
        const rawText = await res.text();
        let errMessage = `HTTP ${res.status}`;
        try {
          const errData = JSON.parse(rawText);
          errMessage = errData.detail || errData.message || errMessage;
        } catch {
          errMessage = rawText.slice(0, 200) || errMessage;
        }
        alert('Snipe error: ' + errMessage);
        return;
      }"""

    if old_error_pattern.search(content):
        content = old_error_pattern.sub(clean_replacement, content, count=1)
        APP_TSX.write_text(content, encoding="utf-8")
        print("✓ Patched apps/faas/src/App.tsx: Double-read body stream bug eradicated.")
        return 0
    else:
        # Fallback string replace if exact regex spacing differs
        target_marker = "const rawText = await res.text();"
        if target_marker in content and "const errData = await res.json();" in content:
            content = content.replace(
                "try {\n          const errData = await res.json();\n          errMessage = errData.detail || errData.message || errMessage;\n        } catch {\n          const rawText = await res.text();\n          errMessage = rawText.slice(0, 200) || errMessage;\n        }",
                "const rawText = await res.text();\n        try {\n          const errData = JSON.parse(rawText);\n          errMessage = errData.detail || errData.message || errMessage;\n        } catch {\n          errMessage = rawText.slice(0, 200) || errMessage;\n        }"
            )
            APP_TSX.write_text(content, encoding="utf-8")
            print("✓ Patched apps/faas/src/App.tsx via fallback replacement.")
            return 0

    print("ℹ️ apps/faas/src/App.tsx already patched or pattern clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

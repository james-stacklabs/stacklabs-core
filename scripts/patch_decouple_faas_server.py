#!/usr/bin/env python3
"""
StackLabs Decoupling Patcher for faas_server.py
Removes inline /api/snipe and /field-notes implementations and mounts
scripts.blueprints.stream_sniper_bp and scripts.blueprints.field_notes_bp.
"""

import sys
import re
from pathlib import Path

FAAS_SERVER_PATH = Path("/home/james/stacklabs/scripts/faas_server.py")

def main():
    if not FAAS_SERVER_PATH.exists():
        print(f"Error: {FAAS_SERVER_PATH} not found", file=sys.stderr)
        sys.exit(1)

    content = FAAS_SERVER_PATH.read_text(encoding="utf-8")

    # 1. Mount blueprints near top of router mounting section
    blueprint_imports = """
# Mount decoupled Stream Sniper and Field Notes blueprints (WO0011252)
try:
    from scripts.blueprints.stream_sniper_bp import stream_sniper_bp
    app.include_router(stream_sniper_bp)
    logger.info("Mounted decoupled Stream Sniper router on /api/snipe")
except Exception as e:
    logger.warning(f"Could not mount stream sniper blueprint: {e}")

try:
    from scripts.blueprints.field_notes_bp import field_notes_bp
    app.include_router(field_notes_bp)
    logger.info("Mounted decoupled Field Notes router on /field-notes")
except Exception as e:
    logger.warning(f"Could not mount field notes blueprint: {e}")
"""

    if "stream_sniper_bp" not in content:
        # Place right after tell_sniper mount
        marker = 'logger.error(f"Failed to mount tell_sniper router: {e}")'
        if marker in content:
            idx = content.find(marker)
            except_end = content.find("\n", idx)
            content = content[:except_end + 1] + blueprint_imports + content[except_end + 1:]
        else:
            # Append before first @app.api_route or @app.get
            first_route = content.find("@app.")
            content = content[:first_route] + blueprint_imports + "\n" + content[first_route:]

    # 2. Strip inline SnipeRequest & @app.post("/api/snipe") block
    # From class SnipeRequest up to @app.get("/api/hourly-stats")
    snipe_pattern = re.compile(
        r'class SnipeRequest\(BaseModel\):[\s\S]*?(?=@app\.get\("/api/hourly-stats"\))',
        re.MULTILINE
    )
    if snipe_pattern.search(content):
        content = snipe_pattern.sub(
            "# SnipeRequest and /api/snipe decoupled to scripts.blueprints.stream_sniper_bp (WO0011252)\n\n",
            content
        )
        print("✓ Decoupled inline /api/snipe block removed from faas_server.py")

    # 3. Strip inline FIELD_NOTE_OCT_14_PATH and /field-notes block
    # From # ARCHITECTURAL FIELD NOTES up to # STATIC FILES SERVING
    field_notes_pattern = re.compile(
        r'# -+\s*\n# ARCHITECTURAL FIELD NOTES[\s\S]*?(?=# -+\s*\n# STATIC FILES SERVING)',
        re.MULTILINE
    )
    if field_notes_pattern.search(content):
        content = field_notes_pattern.sub(
            "# Field notes decoupled to scripts.blueprints.field_notes_bp (WO0011252)\n\n",
            content
        )
        print("✓ Decoupled inline /field-notes block removed from faas_server.py")

    FAAS_SERVER_PATH.write_text(content, encoding="utf-8")
    print("✅ faas_server.py successfully patched and decoupled.")

if __name__ == "__main__":
    main()

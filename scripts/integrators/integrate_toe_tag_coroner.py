#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Toe-Tag Coroner Route Integrator.
Mounts GET /api/faas/body_bags on faas_vfs_telemetry.py and faas_server.py.
Adheres strictly to AST parsing and Argon Law 3 zero-regression standards.
"""

import ast
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.toe_tag_coroner import evaluate_and_compile_body_bags

logger = logging.getLogger("stacklabs.integrate_toe_tag")


def patch_faas_vfs_telemetry() -> None:
    telemetry_path = PROJECT_ROOT / "scripts" / "blueprints" / "faas_vfs_telemetry.py"
    if not telemetry_path.exists():
        raise FileNotFoundError(f"Missing {telemetry_path}")

    source = telemetry_path.read_text(encoding="utf-8")
    marker = "WO0011233_TOE_TAG_ROUTE"

    if marker not in source:
        route_block = """

# === WO0011233_TOE_TAG_ROUTE ===
from scripts.core.toe_tag_coroner import (
    BODY_BAGS_SHM_PATH,
    compute_sliding_10s_ring,
    evaluate_and_compile_body_bags,
)


@faas_lexicon_router.get("/body_bags")
def get_faas_body_bags() -> Dict[str, Any]:
    \"\"\"Expose settled Toe-Tag autopsies and live flatline status across FINAL games.\"\"\"
    if BODY_BAGS_SHM_PATH.exists():
        try:
            raw = json.loads(BODY_BAGS_SHM_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and time.time() - raw.get("updated_at", 0) <= 15:
                return raw
        except Exception as exc:
            logger.debug("SHM body bags read warning: %s", exc)
    return evaluate_and_compile_body_bags()


def get_body_bags_payload() -> Dict[str, Any]:
    \"\"\"Direct callable helper for root app route mounting.\"\"\"
    return get_faas_body_bags()
"""
        source = source + "\n" + route_block
        ast.parse(source)
        tmp = telemetry_path.with_suffix(".py.tmp")
        tmp.write_text(source, encoding="utf-8")
        tmp.replace(telemetry_path)
        logger.info("Patched faas_vfs_telemetry.py with /api/faas/lexicon/body_bags")


def patch_faas_server() -> None:
    server_path = PROJECT_ROOT / "scripts" / "faas_server.py"
    if not server_path.exists():
        raise FileNotFoundError(f"Missing {server_path}")

    source = server_path.read_text(encoding="utf-8")
    marker = "WO0011233_FAAS_BODY_BAGS_ROOT_ROUTE"

    if marker not in source:
        import_marker = "from scripts.blueprints.faas_vfs_telemetry import ("
        if import_marker in source:
            source = source.replace(
                import_marker,
                "from scripts.blueprints.faas_vfs_telemetry import (\n        get_body_bags_payload,",
            )
            route_mount = """
    # === WO0011233_FAAS_BODY_BAGS_ROOT_ROUTE ===
    app.add_api_route("/api/faas/body_bags", get_body_bags_payload, methods=["GET", "HEAD"])
    logger.info("Mounted Toe-Tag Body Bags route on /api/faas/body_bags")
"""
            anchor = 'app.add_api_route("/api/faas/slate/active_games", get_active_slate_games, methods=["GET", "HEAD"])'
            if anchor in source:
                source = source.replace(anchor, anchor + route_mount)

        ast.parse(source)
        tmp = server_path.with_suffix(".py.tmp")
        tmp.write_text(source, encoding="utf-8")
        tmp.replace(server_path)
        logger.info("Patched faas_server.py with /api/faas/body_bags")


if __name__ == "__main__":
    patch_faas_vfs_telemetry()
    patch_faas_server()
    res = evaluate_and_compile_body_bags()
    print("Integration complete. Body bags compiled:", res.get("total_body_bags", 0))

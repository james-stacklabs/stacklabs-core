#!/home/james/stacklabs/.venv/bin/python3
import json, sys
from pathlib import Path
p = Path("/home/james/stacklabs/vfs/collisions/latest_ranked_collisions.json")
if not p.is_file():
    sys.stderr.write("E_MISSING_COLLISION_INDEX\n")
    sys.exit(2)
d = json.loads(p.read_text(encoding="utf-8"))
top = d.get("top_collision") or {}
if "blind_spot_lenses_c_minus_a" not in top:
    sys.stderr.write("E_SCHEMA_DRIFT: key 'blind_spot_lenses_c_minus_a' missing; expected 'blind_spot_lenses_c_minus_a'\n")
    sys.exit(2)
print("SENTINEL_OK")
sys.exit(0)

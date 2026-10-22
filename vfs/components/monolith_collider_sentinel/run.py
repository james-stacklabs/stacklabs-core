#!/home/james/stacklabs/.venv/bin/python3
import sys
import subprocess

# Normal execution runs the monolith collider
res = subprocess.run(["/home/james/stacklabs/.venv/bin/python3", "/home/james/stacklabs/scripts/stacklabs_monolith_collider.py"])
if res.returncode != 0:
    sys.exit(res.returncode)

import sys
pass  # Fault healed

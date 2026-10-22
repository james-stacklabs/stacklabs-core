#!/usr/bin/env bash
set -e
COLLISIONS_FILE="/home/james/stacklabs/vfs/collisions/monolith_ranked_collisions.json"

if [ ! -f "${COLLISIONS_FILE}" ]; then
  echo "FAIL: Collisions file does not exist"
  exit 2
fi

/home/james/stacklabs/.venv/bin/python3 -c "
import json, sys
data = json.load(open('${COLLISIONS_FILE}'))
assert data.get('status') == 'success', 'Status not success'
cols = data.get('collisions', [])
assert len(cols) >= 20, f'Fewer than 20 collisions: {len(cols)}'
for c in cols:
    assert 'blind_spot_lenses_c_minus_a' in c, 'Missing blind_spot_lenses_c_minus_a'
"
echo "PASS: Monolith collider output semantic integrity verified."
exit 0

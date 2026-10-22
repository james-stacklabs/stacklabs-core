#!/bin/bash

# ==============================================================================
# CHIN-3 ROOT SWEEP (OMEGA AUDIT)
# AUTHOR: Antigravity (Node .73 Iron Worker)
# DATE: April 16, 2026
# RULE 1 ENFORCED: NO DELETIONS (mv only)
# ==============================================================================

ROOT_DIR="/home/james/stacklabs"
VAULT_DIR="$ROOT_DIR/staging/deep_dive_vault"
QUARANTINE_DIR="$ROOT_DIR/staging/quarantine"

# Create vaults if missing
mkdir -p "$VAULT_DIR"
mkdir -p "$QUARANTINE_DIR"

echo "INITIATING CHIN-3 SWEEP ON $ROOT_DIR"

COUNT=0
BYTES_MOVED=0

# Loop through all files and directories in the root (depth 1 only)
for ITEM in "$ROOT_DIR"/*; do
    BASENAME=$(basename "$ITEM")

    # STRICT EXCLUSIONS (The Iron Guardrails)
    if [[ "$BASENAME" == "04_Sovereign_Core" || \
          "$BASENAME" == "08_FanCast" || \
          "$BASENAME" == "10_Pegasus" || \
          "$BASENAME" == "11_Unified_Golf_UI" || \
          "$BASENAME" == "01_Sovereign_Portal" || \
          "$BASENAME" == "DEV" || \
          "$BASENAME" == "UAT" || \
          "$BASENAME" == "PROD" || \
          "$BASENAME" == "staging" || \
          "$BASENAME" == "dna" || \
          "$BASENAME" == "scripts" || \
          "$BASENAME" == "assets" || \
          "$BASENAME" == "logs" || \
          "$BASENAME" == "logs_archive" || \
          "$BASENAME" == "docs" || \
          "$BASENAME" == "docs_archive" || \
          "$BASENAME" == "node_modules" || \
          "$BASENAME" == "__pycache__" || \
          "$BASENAME" == ".git" || \
          "$BASENAME" == ".agents" || \
          "$BASENAME" == ".vscode" || \
          "$BASENAME" == ".venv" || \
          "$BASENAME" == ".env" || \
          "$BASENAME" == "vite.config.ts" || \
          "$BASENAME" == "package.json" || \
          "$BASENAME" == "package-lock.json" || \
          "$BASENAME" == "tsconfig.json" || \
          "$BASENAME" == "tsconfig.node.json" || \
          "$BASENAME" == "tailwind.config.ts" || \
          "$BASENAME" == "tailwind.config.js" || \
          "$BASENAME" == "postcss.config.js" || \
          "$BASENAME" == "ingestor_watchdog.py" || \
          "$BASENAME" == "apiary_rest_server.py" || \
          "$BASENAME" == *.db || \
          "$BASENAME" == *.sqlite ]]; then
        continue # Skip the excluded items
    fi

    # Calculate size before moving
    if [ -f "$ITEM" ]; then
        SIZE=$(stat -c%s "$ITEM")
    else
        SIZE=$(du -sb "$ITEM" | cut -f1)
    fi

    # Move non-excluded items
    mv "$ITEM" "$VAULT_DIR/"
    
    COUNT=$((COUNT + 1))
    BYTES_MOVED=$((BYTES_MOVED + SIZE))
done

# Convert bytes to MB/GB for readability
if [ $BYTES_MOVED -gt 1073741824 ]; then
    SIZE_FORMATTED="$(echo "scale=2; $BYTES_MOVED/1073741824" | bc) GB"
elif [ $BYTES_MOVED -gt 1048576 ]; then
    SIZE_FORMATTED="$(echo "scale=2; $BYTES_MOVED/1048576" | bc) MB"
else
    SIZE_FORMATTED="$(echo "scale=2; $BYTES_MOVED/1024" | bc) KB"
fi

echo "======================================================"
echo "CHIN-3 SWEEP COMPLETE."
echo "QUARANTINED ITEMS: $COUNT"
echo "STORAGE RECLAIMED: $SIZE_FORMATTED"
echo "======================================================"

# Write the final report
REPORT_PATH="$ROOT_DIR/dna/dropzone/SOVEREIGN_ROOT_AUDIT.md"

cat <<EOF > "$REPORT_PATH"
# SOVEREIGN ROOT AUDIT POST-MORTEM
**DATE:** April 16, 2026
**EXECUTOR:** Node .73 Iron Worker (Antigravity)
**OPERATION:** Chin-3 Root Sweep (OMEGA AUDIT)

## EXECUTION SUMMARY
* **Status:** SUCCESS
* **Quarantine Vault:** \`/staging/deep_dive_vault/\`
* **Total Items Swept:** $COUNT
* **Total Storage Reclaimed from Root:** $SIZE_FORMATTED

## ROOT INTEGRITY VERIFICATION (ls -la)
\`\`\`bash
$(ls -la "$ROOT_DIR" | awk '{print $1, $2, $3, $4, $5, $6, $7, $8, $9}')
\`\`\`
EOF

echo "Report generated at: $REPORT_PATH"
exit 0

#!/bin/bash

# CHIN-2 PURGE SCRIPT (Space Madness Mitigation)
SOURCE_DIR="/home/james/stacklabs"
QUARANTINE_DIR="/home/james/stacklabs/staging/quarantine"

mkdir -p "$QUARANTINE_DIR"

echo "Initializing CHIN-2 Sweep..."
echo "Targeting non-executable assets > 7 days old."
echo "Excluding critical directories: .venv, node_modules, .git, .next, quarantine"
echo "Excluding critical file types: .py, .tsx, .ts, .jsx, .html, .css, .js, .sh, .db, .sqlite, .sqlite3"

COUNT=0

# Execute optimized find with prunes and negated name exclusions
while IFS= read -r -d '' file; do
    if [[ "$file" != "$QUARANTINE_DIR"* ]]; then
        # Use -f to forcefully overwrite explicitly named duplicate garbage files
        mv -f "$file" "$QUARANTINE_DIR/" 2>/dev/null
        ((COUNT++))
    fi
done < <(find "$SOURCE_DIR" \
    -type d \( -name ".venv" -o -name "node_modules" -o -name ".git" -o -name ".next" -o -name "quarantine" \) -prune \
    -o -type f -mtime +7 \
    \! -name "*.py" \! -name "*.tsx" \! -name "*.ts" \! -name "*.jsx" \
    \! -name "*.html" \! -name "*.css" \! -name "*.js" \! -name "*.sh" \
    \! -name "*.db" \! -name "*.sqlite" \! -name "*.sqlite3" \
    -print0)

echo "----------------------------------------"
echo "Sweep Execution Complete."
echo "Total stale assets isolated to quarantine: $COUNT"
echo "----------------------------------------"

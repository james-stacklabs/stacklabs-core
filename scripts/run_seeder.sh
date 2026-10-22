#!/usr/bin/env bash
# =============================================================================
# Sovereign OS Ingestion Seeder Shortcut
# =============================================================================
# Overwritten per STRY1779973230 / ENHC0000518
# Takes an intake Markdown file and an optional media folder path.
# =============================================================================

set -euo pipefail

SEED_FILE="${1:-}"
MEDIA_DIRECTORY="${2:-}"

if [ -z "$SEED_FILE" ]; then
    echo "❌ Usage: ./scripts/run_seeder.sh <seed_file.md> [media_directory]"
    exit 1
fi

# Convert paths to absolute to prevent worktree directory resolution errors
ABS_SEED_FILE=$(realpath "$SEED_FILE")
ABS_MEDIA_DIR=""
if [ -n "$MEDIA_DIRECTORY" ]; then
    if [ -d "$MEDIA_DIRECTORY" ]; then
        ABS_MEDIA_DIR=$(realpath "$MEDIA_DIRECTORY")
    else
        echo "⚠️ Media directory does not exist or is not a directory: $MEDIA_DIRECTORY"
    fi
fi

# Resolve the database path natively
export SOVEREIGN_DB_PATH="${SOVEREIGN_DB_PATH:-/home/james/stacklabs/dna/sovereign_now.db}"

# Locate the active python virtual environment executable
PYTHON_EXEC="/home/james/stacklabs/.venv/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="python3"
fi

echo "🌱 Launching down-stream Dynamic Stack Seeder..."
echo "  ↳ DB: $SOVEREIGN_DB_PATH"
echo "  ↳ Seed: $ABS_SEED_FILE"
if [ -n "$ABS_MEDIA_DIR" ]; then
    echo "  ↳ Media: $ABS_MEDIA_DIR"
    "$PYTHON_EXEC" scripts/stack_seeder_cli.py "$ABS_SEED_FILE" --media-dir "$ABS_MEDIA_DIR"
else
    "$PYTHON_EXEC" scripts/stack_seeder_cli.py "$ABS_SEED_FILE"
fi

#!/bin/bash
# Sovereign OS Platform - Automated Stack Seeder Helper
# Mapped for Pilot: James Carroll

# Accept target file as first argument, defaulting to Aether Vet if empty
TARGET_FILE="${1:-/home/james/sovereign_inbox/today/aether_vet_stack_seed.md}"

if [ ! -f "$TARGET_FILE" ]; then
    echo "❌ [ERROR] Target seed file not found: $TARGET_FILE"
    exit 1
fi

echo "🚀 [INGEST] Executing automated stack seeding sweep..."
echo "📦 [INGEST] Target Brief: $TARGET_FILE"

# Run the python binary inside the virtual environment boundary cleanly
/home/james/stacklabs/.venv/bin/python /home/james/stacklabs/scripts/stack_seeder_cli.py "$TARGET_FILE"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ [SUCCESS] Ingestion cascade completed flawlessly. Exit code 0."
else
    echo "❌ [FAILURE] Ingestion aborted or terminated with error. Exit code $EXIT_CODE."
fi

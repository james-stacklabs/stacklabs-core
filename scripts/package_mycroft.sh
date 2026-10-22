#!/bin/bash

# MYCROFT PATENT PAYLOAD PACKAGER
ROOT_DIR="/home/james/stacklabs"
STAGING_DIR="/tmp/mycroft_staging"
ZIP_NAME="mycroft_ambsc_patent_pack.zip"
FINAL_ZIP_PATH="$ROOT_DIR/$ZIP_NAME"

echo "Initializing the Mycroft Patent Packager..."

# Clean up any existing staging dir or zip
rm -rf "$STAGING_DIR"
rm -f "$FINAL_ZIP_PATH"
mkdir -p "$STAGING_DIR"

echo "Searching for target assets..."

# Array of file patterns to find and copy
TARGETS=(
    "PROVISIONAL PATENT APPLICATION SPECIFICATION_ SOVEREIGN MULTI-LLM OPERATING SYSTEM.md"
    "PATENT SPECIFICATION AND § 101 ELIGIBILITY ANALYSIS_*.md"
    "MYCROFT_PATENT_LOG.md"
    "sentinel_audit_package.md"
    "rap_battle_8_mile_override.md"
    "SOVEREIGN_DNA.md"
    "CORRECTIONS_LEDGER.md*"
)

COUNT=0

for target in "${TARGETS[@]}"; do
    # Use find to locate files matching the pattern anywhere in the root directory
    # -print0 and xargs -0 cp -t safely handles spaces in filenames
    find "$ROOT_DIR" -type f -name "$target" -print0 | xargs -0 -r cp -t "$STAGING_DIR"
done

# Count how many files were actually found and copied
COUNT=$(ls -1q "$STAGING_DIR" | wc -l)

echo "Found and staged $COUNT files."

# Zip the contents of the staging directory
if [ $COUNT -gt 0 ]; then
    echo "Creating payload $ZIP_NAME..."
    cd "$STAGING_DIR" || exit
    zip -q -r "$FINAL_ZIP_PATH" ./*
    echo "Payload successfully generated at $FINAL_ZIP_PATH"
else
    echo "ERROR: No target files were found. Nothing to zip."
fi

# Cleanup
rm -rf "$STAGING_DIR"
echo "Mycroft payload packaging complete."

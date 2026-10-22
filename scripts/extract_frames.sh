#!/bin/bash
# ==============================================================================
# PIPELINE: SOVEREIGN EXTRACT FRAMES
# ==============================================================================
# SPRINT 065 SAFETY Catch: Prevents 100,000+ frame bloat spills.
# Hard Limit: No extraction is permitted to exceed 300 frames without --force.

FORCE_MODE=0
MAX_FRAMES=300

# Parse arguments for the --force flag and remove it from args to pass to ffmpeg
FFMPEG_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--force" ]]; then
        FORCE_MODE=1
    else
        FFMPEG_ARGS+=("$arg")
    fi
done

echo "[SYS] Sovereign Video Extractor Armed..."

if [[ "$FORCE_MODE" -eq 0 ]]; then
    echo "[!] SAFETY CATCH ENGAGED: Hard limit of $MAX_FRAMES max frames enforced."
    echo "[!] Appending '-frames:v $MAX_FRAMES' to prevent Vesper bloat."
    ffmpeg "${FFMPEG_ARGS[@]}" -frames:v $MAX_FRAMES
else
    echo "[!] WARNING: --force flag detected! Bypassing 300 frame limit."
    echo "[!] Manual override confirmed. Executing unrestricted flow..."
    ffmpeg "${FFMPEG_ARGS[@]}"
fi

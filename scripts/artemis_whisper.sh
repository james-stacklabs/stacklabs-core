#!/usr/bin/env bash
# StackLabs Launcher for Artemis Faster-Whisper on Metal
set -euo pipefail

export LD_LIBRARY_PATH="/data/artemis_env/lib/python3.12/site-packages/nvidia/cublas/lib:/data/artemis_env/lib/python3.12/site-packages/nvidia/cudnn/lib:${LD_LIBRARY_PATH:-}"
export HF_HOME="/data/cache/huggingface"

/data/artemis_env/bin/python3 /home/james/stacklabs/scripts/artemis_whisper.py "$@"

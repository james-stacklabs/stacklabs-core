#!/usr/bin/env bash
set -e

MODELS_DIR="/home/james/stacklabs/models"
HF_DIR="$MODELS_DIR/dolphin-fanstack"
F16_GGUF="$MODELS_DIR/dolphin-fanstack-f16.gguf"
Q4_GGUF="$MODELS_DIR/dolphin-fanstack-q4_k_m.gguf"
LLAMA_DIR="/home/james/stacklabs/tools/llama.cpp"
VENV_PYTHON="$LLAMA_DIR/venv/bin/python3"
QUANTIZE_BIN="$LLAMA_DIR/build/bin/llama-quantize"
PEGASUS_IP="100.96.77.20"
PEGASUS_DEST="/media/james/E6728B85728B5967/sovereign_models"

echo "================================================================="
echo "🦿 THE SOVEREIGN NEURAL FLYWHEEL: QUANTIZE & SHIP TO PEGASUS-1"
echo "================================================================="

echo "--- 1. Converting Hugging Face Safetensors to 16-bit GGUF ---"
$VENV_PYTHON $LLAMA_DIR/convert_hf_to_gguf.py \
    "$HF_DIR" \
    --outfile "$F16_GGUF" \
    --outtype f16

echo "--- 2. Quantizing to 4-bit q4_k_m with 16 CPU cores ---"
$QUANTIZE_BIN "$F16_GGUF" "$Q4_GGUF" q4_k_m 16

echo "--- 3. Removing intermediate 16-bit GGUF ---"
rm -f "$F16_GGUF"

echo "--- 4. Shipping 4.7GB GGUF to Pegasus over Tailscale ---"
scp -o ConnectTimeout=10 "$Q4_GGUF" james@$PEGASUS_IP:"$PEGASUS_DEST/"

echo "--- 5. Registering dolphin-fanstack on Pegasus Ollama ---"
ssh -o ConnectTimeout=10 james@$PEGASUS_IP "bash -c '
cat << \"EOF\" > $PEGASUS_DEST/Modelfile.fanstack
FROM $PEGASUS_DEST/dolphin-fanstack-q4_k_m.gguf
PARAMETER temperature 0.8
PARAMETER top_p 0.95
PARAMETER stop \"<|im_end|>\"
PARAMETER stop \"<|im_start|>\"

TEMPLATE \"\"\"<|im_start|>system
{{ .System }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
\"\"\"
EOF
ollama create dolphin-fanstack -f $PEGASUS_DEST/Modelfile.fanstack
ollama list | grep dolphin-fanstack
'"

echo "--- 6. Running Live FanStack Barf Inference on Pegasus ---"
curl -s http://$PEGASUS_IP:11434/api/generate -d '{
  "model": "dolphin-fanstack",
  "system": "You are @barf, a passionate, cynical, unfiltered die-hard New York Mets fan who speaks in thick Queens/Long Island dialect. You react to live MLB Statcast telemetry with sharp wit and uncensored Mets passion.",
  "prompt": "[STATCAST TELEMETRY: Top 9th, 2 Outs, Bases Loaded, Exit Velocity 108.4 mph, Launch Angle 29 deg, Expected Distance 418 ft, Pitcher Edwin Diaz vs Ronald Acuna Jr.]",
  "stream": false
}' | jq -r '.response'

echo "--- 7. Campsite Cleanup on Clio ---"
rm -rf "$HF_DIR"
echo "✅ Workflow Complete! dolphin-fanstack is live on Pegasus-1!"

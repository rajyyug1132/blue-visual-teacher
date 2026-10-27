#!/usr/bin/env bash
set -e

# Blue Visual Teacher — Linux/macOS Live Demo Runner
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OLLAMA_MODEL=qwen2.5:3b
export PYTHONUTF8=1

# Check environment & offline readiness
python3 exporter/check_env.py
if [ $? -ne 0 ]; then
    echo "Environment check failed. Aborting."
    exit 1
fi

echo "Environment check passed. Launching server on http://127.0.0.1:8000..."
python3 -m uvicorn exporter.app:app --host 127.0.0.1 --port 8000

#!/usr/bin/env bash
# Start the offline demo: env flags, Ollama (only if not already running), warm-up, then the app on 127.0.0.1:8000.
set -euo pipefail
cd "$(dirname "$0")"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUTF8=1
export OLLAMA_MAX_LOADED_MODELS=1          # one planner model in VRAM at a time (3b, or 7b while escalating)
export PLANNER_MODEL="${PLANNER_MODEL:-qwen2.5:3b}"
export PLANNER_ESCALATION_MODEL="${PLANNER_ESCALATION_MODEL-qwen2.5:7b}"
export DEVICE="${DEVICE:-cpu}"             # TTS + IndicTrans2 on CPU; the GPU belongs to the planner
PY="${PYTHON:-python}"

# Never restart a running Ollama server; start one only if nothing answers on 11434.
if ! curl -s --max-time 2 http://127.0.0.1:11434/api/version >/dev/null; then
  echo "Starting Ollama with OLLAMA_MAX_LOADED_MODELS=1"
  (ollama serve >/dev/null 2>&1 &)
  for _ in $(seq 1 30); do curl -s --max-time 1 http://127.0.0.1:11434/api/version >/dev/null && break; sleep 1; done
fi

# Pin the planner in memory (keep_alive=-1, a number) and load translator + TTS once.
"$PY" -c "from orchestrator.planner import warm_up_ollama; warm_up_ollama(); print('planner warm (keep_alive=-1)')"
"$PY" -c "from orchestrator.pipeline import warmup, available_languages; warmup(planner=False); print('languages:', available_languages())"

echo "Open http://127.0.0.1:8000"
exec "$PY" -m uvicorn exporter.app:app --host 127.0.0.1 --port 8000

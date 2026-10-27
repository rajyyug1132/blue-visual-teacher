# Start the offline demo on Windows: env flags, Ollama (only if not running), warm-up, then the app on 127.0.0.1:8000.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:PYTHONUTF8 = "1"
$env:OLLAMA_MAX_LOADED_MODELS = "1"   # one planner model in VRAM at a time
if (-not $env:PLANNER_MODEL) { $env:PLANNER_MODEL = "qwen2.5:3b" }
if ($null -eq $env:PLANNER_ESCALATION_MODEL) { $env:PLANNER_ESCALATION_MODEL = "qwen2.5:7b" }
if (-not $env:DEVICE) { $env:DEVICE = "cpu" }
$py = if ($env:PYTHON) { $env:PYTHON } else { "python" }

# Never restart a running Ollama server; start one only if nothing answers on 11434.
try { Invoke-RestMethod -TimeoutSec 2 http://127.0.0.1:11434/api/version | Out-Null }
catch {
  Write-Host "Starting Ollama with OLLAMA_MAX_LOADED_MODELS=1"
  Start-Process -WindowStyle Hidden ollama -ArgumentList "serve"
  for ($i = 0; $i -lt 30; $i++) {
    try { Invoke-RestMethod -TimeoutSec 1 http://127.0.0.1:11434/api/version | Out-Null; break } catch { Start-Sleep 1 }
  }
}

& $py -c "from orchestrator.planner import warm_up_ollama; warm_up_ollama(); print('planner warm (keep_alive=-1)')"
& $py -c "from orchestrator.pipeline import warmup, available_languages; warmup(planner=False); print('languages:', available_languages())"

Write-Host "Open http://127.0.0.1:8000"
Start-Process "http://127.0.0.1:8000"
& $py -m uvicorn exporter.app:app --host 127.0.0.1 --port 8000

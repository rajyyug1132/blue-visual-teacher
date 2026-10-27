# Blue Visual Teacher — Windows Live Demo Runner
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:OLLAMA_MODEL = "qwen2.5:3b"
$env:PYTHONUTF8 = "1"

# Check environment & offline readiness
python exporter/check_env.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Environment check failed. Aborting." -ForegroundColor Red
    exit 1
}

Write-Host "Environment check passed. Opening browser preview and launching server..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"
python -m uvicorn exporter.app:app --host 127.0.0.1 --port 8000

# Live demo UI on http://127.0.0.1:7860. Needs Ollama and the qwen2.5:3b model.
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:DEMO_MODE = "live"
& (Join-Path $root ".venv\Scripts\python.exe") -m src.ui

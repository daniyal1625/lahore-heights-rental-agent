# Replay-only demo UI on http://127.0.0.1:7860. No Ollama or Chroma needed.
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:DEMO_MODE = "replay"
& (Join-Path $root ".venv\Scripts\python.exe") -m src.ui

# Create .venv, install the CPU-only stack, and build the retrieval index.
# Run from anywhere:  .\scripts\setup.ps1
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"

# Native stderr (pip and tqdm progress) must not stop the script; exit codes do.
# Fresh virtual environment on Python 3.11.
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Could not create .venv with 'py -3.11'." }

# CPU-only PyTorch first so pip does not pull a CUDA wheel.
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed (exit $LASTEXITCODE)." }

& $python -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw "PyTorch install failed (exit $LASTEXITCODE)." }

# Project extras: dev (pytest/httpx), rag, agent and ui.
& $python -m pip install -e ".[dev,rag,agent,ui]"
if ($LASTEXITCODE -ne 0) { throw "Project install failed (exit $LASTEXITCODE)." }

# Build the local Chroma index from the manual and the city guide.
& $python -m src.rag build
if ($LASTEXITCODE -ne 0) { throw "Index build failed (exit $LASTEXITCODE)." }

Write-Host ""
Write-Host "Setup complete. Next steps:"
Write-Host "  .\scripts\check.ps1        # dataset check + tests"
Write-Host "  .\scripts\run_replay.ps1   # UI with saved runs, no Ollama"
Write-Host "  .\scripts\run_ui.ps1       # live UI (start Ollama first)"

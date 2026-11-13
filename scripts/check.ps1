# Check the dataset, then run the fast test suite (no Ollama needed).
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"

& $python eval/verify_dataset.py --guide data/local_guide/wikivoyage_lahore.txt
if ($LASTEXITCODE -ne 0) { throw "Dataset check failed (exit $LASTEXITCODE)." }

& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "pytest failed (exit $LASTEXITCODE)." }

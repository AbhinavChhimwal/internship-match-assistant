$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$matcherPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $matcherPython)) {
    throw 'Create .venv and install requirements.txt first; see README.md.'
}
$env:HF_HOME = Join-Path $PSScriptRoot 'runtime\model-cache'
& $matcherPython -m streamlit run app.py

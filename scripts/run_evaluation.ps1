$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
cd $RepoRoot

Write-Host "TAXITIQ Helper Command: python 10_evaluate_rag.py --run" -ForegroundColor Cyan
Invoke-Expression "python 10_evaluate_rag.py --run"
exit $LASTEXITCODE

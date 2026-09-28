$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
cd $RepoRoot

Write-Host "TAXITIQ Helper Command: python 12_results_integrity_audit.py" -ForegroundColor Cyan
Invoke-Expression "python 12_results_integrity_audit.py"
exit $LASTEXITCODE

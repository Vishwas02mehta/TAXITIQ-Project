$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
cd $RepoRoot

Write-Host "TAXITIQ Helper Command: python 11_statistical_analysis.py" -ForegroundColor Cyan
Invoke-Expression "python 11_statistical_analysis.py"
exit $LASTEXITCODE

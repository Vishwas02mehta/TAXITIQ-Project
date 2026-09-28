$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
cd $RepoRoot

Write-Host "TAXITIQ Helper Command: python 13_generate_paper_artifacts.py" -ForegroundColor Cyan
Invoke-Expression "python 13_generate_paper_artifacts.py"
exit $LASTEXITCODE

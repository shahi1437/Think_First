<#
.SYNOPSIS
    Safely stops the ThinkFirst Outbound Local Judge0 Execution Worker.
    Leaves all Docker containers and volumes completely untouched.
#>

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
$RunnerCtl = Join-Path $RepoRoot "backend\worker\runner_ctl.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Backend virtual environment not found at $VenvPython" -ForegroundColor Red
    exit 1
}

& $VenvPython $RunnerCtl stop
exit $LASTEXITCODE

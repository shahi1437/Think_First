<#
.SYNOPSIS
    Starts the ThinkFirst Local Judge0 Execution Stack and Outbound Worker safely.
#>

[CmdletBinding()]
param(
    [switch]$SelfCheckOnly
)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
$RunnerCtl = Join-Path $RepoRoot "backend\worker\runner_ctl.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Backend virtual environment not found at $VenvPython" -ForegroundColor Red
    exit 1
}

$Action = if ($SelfCheckOnly) { "self-check" } else { "start" }
& $VenvPython $RunnerCtl $Action
exit $LASTEXITCODE

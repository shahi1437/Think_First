<#
.SYNOPSIS
    Safely stops the ThinkFirst Outbound Local Judge0 Execution Worker.
.DESCRIPTION
    1. Signals the local worker to stop gracefully (finishing/releasing in-flight jobs and notifying Render offline).
    2. Waits up to 20 seconds for clean process exit before falling back to terminating only the worker PID.
    3. Preserves ALL Docker containers, volumes, databases, Redis, and unrelated services untouched.
#>

$ErrorActionPreference = "Stop"

$RunnerDir = Join-Path $env:LOCALAPPDATA "ThinkFirstCodeRunner"
$PidFile = Join-Path $RunnerDir "worker.pid"
$StopSignal = Join-Path $RunnerDir "stop.signal"

Write-Host "Stopping ThinkFirst Local Judge0 Code Runner..." -ForegroundColor Cyan

if (-not (Test-Path $PidFile)) {
    Write-Host "No active worker PID file found at $PidFile. Nothing to stop." -ForegroundColor Yellow
    if (Test-Path $StopSignal) {
        Remove-Item $StopSignal -Force -ErrorAction SilentlyContinue
    }
    Write-Host "STATUS: STOPPED (Docker volumes and containers left untouched)." -ForegroundColor Green
    exit 0
}

$rawPid = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not ($rawPid -match '^\d+$')) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Cleaned stale PID file. STATUS: STOPPED." -ForegroundColor Green
    exit 0
}

$workerPid = [int]$rawPid
$proc = Get-Process -Id $workerPid -ErrorAction SilentlyContinue
if (-not $proc) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    if (Test-Path $StopSignal) { Remove-Item $StopSignal -Force -ErrorAction SilentlyContinue }
    Write-Host "Worker (PID $workerPid) is already stopped. STATUS: STOPPED." -ForegroundColor Green
    exit 0
}

# Trigger graceful shutdown so in-flight jobs complete or release and Render receives /offline
New-Item -Path $StopSignal -ItemType File -Force | Out-Null
Write-Host "Sent graceful stop signal to worker PID $workerPid (waiting up to 20s for in-flight jobs)..." -ForegroundColor Gray

$stopped = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    if (-not (Get-Process -Id $workerPid -ErrorAction SilentlyContinue)) {
        $stopped = $true
        break
    }
}

if (-not $stopped) {
    Write-Host "Worker did not exit within 20s; terminating worker PID $workerPid only..." -ForegroundColor Yellow
    Stop-Process -Id $workerPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
Remove-Item $StopSignal -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  THINKFIRST CODE RUNNER STATUS: STOPPED SAFELY" -ForegroundColor Green
Write-Host "  All Docker containers and volumes were preserved untouched." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
exit 0

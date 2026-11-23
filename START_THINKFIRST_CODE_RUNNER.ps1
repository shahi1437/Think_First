<#
.SYNOPSIS
    Starts the ThinkFirst Local Judge0 Execution Stack and Outbound Worker safely.
.DESCRIPTION
    1. Checks Docker Desktop availability.
    2. Loads least-privilege credentials from %LOCALAPPDATA%\ThinkFirstCodeRunner\runner.env (never prints secrets).
    3. Ensures Judge0 PostgreSQL, Redis, Server, and Workers are running without deleting volumes.
    4. Verifies localhost Judge0 authentication and readiness (127.0.0.1:2359).
    5. Verifies outbound worker authentication and production queue access on Render.
    6. Starts the outbound execution worker cleanly in the background.
    7. Prints a clear READY or ERROR result.
#>

[CmdletBinding()]
param(
    [switch]$SelfCheckOnly
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunnerDir = Join-Path $env:LOCALAPPDATA "ThinkFirstCodeRunner"
$EnvFile = Join-Path $RunnerDir "runner.env"
$PidFile = Join-Path $RunnerDir "worker.pid"
$StopSignal = Join-Path $RunnerDir "stop.signal"
$LogFile = Join-Path $RunnerDir "worker.log"
$ErrLogFile = Join-Path $RunnerDir "worker.err.log"
$VenvPython = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"

function Fail-Runner {
    param([string]$Message)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "  THINKFIRST CODE RUNNER STATUS: ERROR" -ForegroundColor Red
    Write-Host "  $Message" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    exit 1
}

function Load-RunnerEnv {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path $Path)) {
        Fail-Runner "Missing runner credentials file at $Path. Run initial provisioning first."
    }
    foreach ($raw in Get-Content $Path) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { continue }
        $idx = $line.IndexOf("=")
        $k = $line.Substring(0, $idx).Trim()
        $v = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
        $map[$k] = $v
    }
    return $map
}

Write-Host "Starting ThinkFirst Local Judge0 Code Runner..." -ForegroundColor Cyan

# 1. Verify Python virtual environment
if (-not (Test-Path $VenvPython)) {
    Fail-Runner "Backend virtual environment not found at $VenvPython."
}

# 2. Load credentials securely without printing any secrets
$cfg = Load-RunnerEnv -Path $EnvFile
$j0Token = $cfg["JUDGE0_AUTH_TOKEN"]
$workerToken = $cfg["EXECUTION_WORKER_TOKEN"]
$apiBase = if ($cfg["THINKFIRST_API_BASE_URL"]) { $cfg["THINKFIRST_API_BASE_URL"] } else { "https://codementor-ai-backend-6sbr.onrender.com" }
$j0Base = if ($cfg["JUDGE0_BASE_URL"]) { $cfg["JUDGE0_BASE_URL"] } else { "http://127.0.0.1:2359" }

if ([string]::IsNullOrWhiteSpace($j0Token) -or [string]::IsNullOrWhiteSpace($workerToken)) {
    Fail-Runner "JUDGE0_AUTH_TOKEN or EXECUTION_WORKER_TOKEN is missing in $EnvFile."
}

# 3. Check Docker Desktop
Write-Host "[1/6] Checking Docker Desktop..." -ForegroundColor Gray
try {
    $null = & docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker daemon not reachable" }
} catch {
    Fail-Runner "Docker Desktop is not running. Please open Docker Desktop and wait until it is ready."
}

# 4. Verify PostgreSQL, Redis, and Judge0 containers (preserve all volumes)
Write-Host "[2/6] Verifying Judge0 PostgreSQL, Redis, Server, and Workers..." -ForegroundColor Gray
$env:JUDGE0_AUTH_TOKEN = $j0Token
Push-Location $RepoRoot
try {
    $required = @(
        "think_first-judge0-db-1",
        "think_first-judge0-redis-1",
        "think_first-judge0-server-1",
        "think_first-judge0-workers-1"
    )
    $running = & docker ps --format "{{.Names}}"
    $missing = @($required | Where-Object { $running -notcontains $_ })
    if ($missing.Count -gt 0) {
        Write-Host "      Starting Judge0 containers: $($missing -join ', ')..." -ForegroundColor Yellow
        & docker compose --profile execution up -d judge0-db judge0-redis judge0-server judge0-workers | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Fail-Runner "Failed to start Judge0 containers via docker compose."
        }
    }

    # Check PostgreSQL and Redis readiness inside containers
    $pgReady = & docker exec think_first-judge0-db-1 pg_isready -U judge0 -d judge0 2>&1
    if ($LASTEXITCODE -ne 0) {
        Fail-Runner "Judge0 PostgreSQL container is not ready: $pgReady"
    }
    $redisPing = & docker exec think_first-judge0-redis-1 sh -c 'redis-cli -a "${JUDGE0_REDIS_PASSWORD:-judge0_dev_redis}" ping' 2>&1
    if ($LASTEXITCODE -ne 0 -or ($redisPing -notmatch "PONG")) {
        Fail-Runner "Judge0 Redis container is not healthy."
    }

    # Verify strict localhost binding (127.0.0.1:2359)
    $portBind = & docker inspect think_first-judge0-server-1 --format "{{json .HostConfig.PortBindings}}"
    if ($portBind -notmatch '"HostIp":"127.0.0.1"') {
        Fail-Runner "Security check failed: judge0-server is not bound exclusively to 127.0.0.1."
    }
} finally {
    Pop-Location
}

# 5. Verify local Judge0 readiness and authentication
Write-Host "[3/6] Verifying local Judge0 authentication and readiness ($j0Base)..." -ForegroundColor Gray
$j0Ready = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "$j0Base/config_info" -Headers @{ "X-Auth-Token" = $j0Token } -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            $j0Ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $j0Ready) {
    Fail-Runner "Local Judge0 did not respond with HTTP 200 using configured X-Auth-Token."
}

# Confirm unauthenticated requests are blocked (401)
$unauthBlocked = $false
try {
    $null = Invoke-WebRequest -Uri "$j0Base/config_info" -UseBasicParsing -TimeoutSec 5
} catch {
    if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 401) {
        $unauthBlocked = $true
    }
}
if (-not $unauthBlocked) {
    Fail-Runner "Security check failed: local Judge0 allowed an unauthenticated request."
}

# 6. Verify worker authentication & production queue access via --self-check
Write-Host "[4/6] Verifying outbound worker authentication against $apiBase..." -ForegroundColor Gray
$selfCheckOut = & $VenvPython (Join-Path $RepoRoot "backend\worker\execution_worker.py") --env-file $EnvFile --self-check 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail-Runner "Worker self-check failed: $selfCheckOut"
}
Write-Host "      $($selfCheckOut | Select-Object -Last 1)" -ForegroundColor Green

if ($SelfCheckOnly) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  THINKFIRST CODE RUNNER STATUS: READY (SELF-CHECK PASSED)" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    exit 0
}

# 7. Check if worker is already running cleanly
Write-Host "[5/6] Starting outbound local execution worker..." -ForegroundColor Gray
if (Test-Path $StopSignal) {
    Remove-Item $StopSignal -Force -ErrorAction SilentlyContinue
}
if (Test-Path $PidFile) {
    $existingPid = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($existingPid -match '^\d+$') {
        $existingProc = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
        if ($existingProc) {
            Write-Host "      Worker is already running (PID $existingPid)." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "============================================================" -ForegroundColor Green
            Write-Host "  THINKFIRST CODE RUNNER STATUS: READY" -ForegroundColor Green
            Write-Host "  Worker PID : $existingPid" -ForegroundColor Green
            Write-Host "  Local Judge0: $j0Base (127.0.0.1 authenticated)" -ForegroundColor Green
            Write-Host "  Production  : $apiBase" -ForegroundColor Green
            Write-Host "============================================================" -ForegroundColor Green
            exit 0
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

$workerArgs = @(
    (Join-Path $RepoRoot "backend\worker\execution_worker.py"),
    "--env-file",
    $EnvFile
)
$proc = Start-Process -FilePath $VenvPython `
    -ArgumentList $workerArgs `
    -WorkingDirectory (Join-Path $RepoRoot "backend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrLogFile `
    -PassThru

Set-Content -Path $PidFile -Value $proc.Id -Encoding ASCII

# 8. Confirm worker stays alive after startup
Write-Host "[6/6] Confirming worker process stability..." -ForegroundColor Gray
Start-Sleep -Seconds 2
$alive = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
if (-not $alive) {
    $errTail = if (Test-Path $ErrLogFile) { (Get-Content $ErrLogFile -Tail 10) -join "`n" } else { "No stderr output" }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Fail-Runner "Worker exited immediately after startup. Error: $errTail"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  THINKFIRST CODE RUNNER STATUS: READY" -ForegroundColor Green
Write-Host "  Worker PID  : $($proc.Id)" -ForegroundColor Green
Write-Host "  Local Judge0: $j0Base (127.0.0.1 authenticated)" -ForegroundColor Green
Write-Host "  Production  : $apiBase (outbound HTTPS only)" -ForegroundColor Green
Write-Host "  Logs        : $LogFile" -ForegroundColor Green
Write-Host "  Stop command: .\STOP_THINKFIRST_CODE_RUNNER.ps1" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
exit 0

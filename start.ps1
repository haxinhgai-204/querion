# ============================================================
#  Querion - Start All Services
#  Usage: .\start.ps1
# ============================================================

$ErrorActionPreference = "Continue"
$ROOT = $PSScriptRoot
$PIDS_DIR = Join-Path $ROOT ".pids"

# Create .pids directory
if (-not (Test-Path $PIDS_DIR)) { New-Item -ItemType Directory -Path $PIDS_DIR -Force | Out-Null }

function Stop-ByPort {
    param([int]$Port)
    $pids = netstat -ano 2>$null | Select-String "LISTENING" | Select-String ":$Port\b" | ForEach-Object {
        ($_.Line.Trim() -split "\s+")[-1]
    } | Sort-Object -Unique | Where-Object { $_ -ne "0" }

    foreach ($p in $pids) {
        taskkill /PID $p /T /F 2>$null | Out-Null
    }
    if ($pids) { Start-Sleep -Seconds 1 }
}

function Save-Pid {
    param([string]$Name, [int]$ProcessId)
    Set-Content -Path (Join-Path $PIDS_DIR "$Name.pid") -Value $ProcessId
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Querion Services...        " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# -- 1. Docker Infrastructure --
Write-Host "[1/4] Docker infrastructure..." -ForegroundColor Yellow

$composeFile = Join-Path $ROOT "infra\docker\docker-compose.yml"
$dockerJson = docker compose -f $composeFile ps --format json 2>$null
$dockerRunning = @()
if ($dockerJson) {
    $dockerRunning = $dockerJson | ConvertFrom-Json | Where-Object { $_.State -eq "running" }
}

$expectedNames = @("postgres", "redis", "minio")
$allRunning = $true
foreach ($name in $expectedNames) {
    $found = $dockerRunning | Where-Object { $_.Name -match $name }
    if (-not $found) {
        $allRunning = $false
        break
    }
}

if ($allRunning -and @($dockerRunning).Count -ge 3) {
    Write-Host "  [OK] Docker containers already running - skipped" -ForegroundColor Green
}
else {
    Write-Host "  Starting containers..." -ForegroundColor Gray
    Push-Location (Join-Path $ROOT "infra\docker")
    docker compose up -d
    Pop-Location
    Write-Host "  [OK] Docker containers started" -ForegroundColor Green
}
Write-Host ""

# Wait for PostgreSQL to be healthy
Write-Host "  Waiting for PostgreSQL to be healthy..." -ForegroundColor Gray
$retries = 0
while ($retries -lt 30) {
    $pgJson = docker compose -f $composeFile ps --format json 2>$null
    if ($pgJson) {
        $pgStatus = $pgJson | ConvertFrom-Json | Where-Object { $_.Name -match "postgres" }
        if ($pgStatus.Health -eq "healthy" -or $pgStatus.Status -match "healthy") {
            break
        }
    }
    Start-Sleep -Seconds 2
    $retries++
}
Write-Host "  [OK] PostgreSQL is ready" -ForegroundColor Green
Write-Host ""

# -- 2. API Server --
Write-Host "[2/4] API server (port 8000)..." -ForegroundColor Yellow
Stop-ByPort -Port 8000
$apiExe = Join-Path $ROOT "apps\api\venv\Scripts\python.exe"
$apiDir = Join-Path $ROOT "apps\api"
$apiProc = Start-Process -PassThru -NoNewWindow -FilePath $apiExe `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory $apiDir
Save-Pid -Name "api" -ProcessId $apiProc.Id
Write-Host "  [OK] API server started (PID: $($apiProc.Id))" -ForegroundColor Green
Write-Host ""

# -- 3. Web Frontend --
Write-Host "[3/4] Web frontend (port 3000)..." -ForegroundColor Yellow
Stop-ByPort -Port 3000
$webDir = Join-Path $ROOT "apps\web"
$webProc = Start-Process -PassThru -NoNewWindow -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $webDir
Save-Pid -Name "web" -ProcessId $webProc.Id
Write-Host "  [OK] Web frontend started (PID: $($webProc.Id))" -ForegroundColor Green
Write-Host ""

# -- 4. Worker --
Write-Host "[4/4] Worker..." -ForegroundColor Yellow
# Kill any existing worker by saved PID
$workerPidFile = Join-Path $PIDS_DIR "worker.pid"
if (Test-Path $workerPidFile) {
    $oldPid = Get-Content $workerPidFile -ErrorAction SilentlyContinue
    if ($oldPid) { taskkill /PID $oldPid /T /F 2>$null | Out-Null }
    Remove-Item $workerPidFile -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

$workerExe = Join-Path $ROOT "apps\worker\venv\Scripts\python.exe"
$workerDir = Join-Path $ROOT "apps\worker"
$workerProc = Start-Process -PassThru -NoNewWindow -FilePath $workerExe `
    -ArgumentList "-m", "worker.main" `
    -WorkingDirectory $workerDir
Start-Sleep -Seconds 3
if ($workerProc.HasExited) {
    Write-Host "  [FAIL] Worker crashed on startup (exit code: $($workerProc.ExitCode))!" -ForegroundColor Red
} else {
    Save-Pid -Name "worker" -ProcessId $workerProc.Id
    Write-Host "  [OK] Worker started (PID: $($workerProc.Id))" -ForegroundColor Green
}
Write-Host ""

# -- Summary --
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   All services are running!            " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Web UI:      http://localhost:3000" -ForegroundColor White
Write-Host "  API Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "  MinIO:       http://localhost:9001" -ForegroundColor White
Write-Host ""
Write-Host "  Admin login: admin@querion.io / admin123" -ForegroundColor Gray
Write-Host ""
Write-Host "  Press Ctrl+C to stop all services." -ForegroundColor Yellow
Write-Host ""

# -- Keep alive and cleanup on Ctrl+C --
try {
    while ($true) {
        $apiAlive = -not $apiProc.HasExited
        $workerAlive = -not $workerProc.HasExited

        if (-not $apiAlive) {
            Write-Host "  [WARN] API server stopped unexpectedly!" -ForegroundColor Red
        }
        if (-not $workerAlive) {
            Write-Host "  [WARN] Worker stopped unexpectedly!" -ForegroundColor Red
        }
        Start-Sleep -Seconds 5
    }
}
finally {
    Write-Host ""
    Write-Host "Shutting down services..." -ForegroundColor Yellow

    # Kill by saved PIDs (fastest, most reliable)
    foreach ($svc in @("api", "web", "worker")) {
        $pidFile = Join-Path $PIDS_DIR "$svc.pid"
        if (Test-Path $pidFile) {
            $pid = Get-Content $pidFile -ErrorAction SilentlyContinue
            if ($pid) {
                taskkill /PID $pid /T /F 2>$null | Out-Null
                Write-Host "  [OK] $svc stopped (PID: $pid)" -ForegroundColor Green
            }
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        }
    }

    # Also kill by port as backup
    Stop-ByPort -Port 8000
    Stop-ByPort -Port 3000

    Write-Host ""
    Write-Host "All services stopped. Docker containers are still running." -ForegroundColor Gray
    Write-Host "To stop Docker: cd infra\docker; docker compose down" -ForegroundColor Gray
    Write-Host ""
}

# ============================================================
#  Querion - Stop All Services
#  Usage: .\stop.ps1           (keeps Docker running)
#         .\stop.ps1 -Docker   (also stops Docker)
# ============================================================

param([switch]$Docker)

$ErrorActionPreference = "SilentlyContinue"
$ROOT = $PSScriptRoot
$PIDS_DIR = Join-Path $ROOT ".pids"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Stopping Querion Services...        " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# -- Kill all python processes (API + Worker) --
$pyCount = (Get-Process -Name "python" -ErrorAction SilentlyContinue | Measure-Object).Count
if ($pyCount -gt 0) {
    Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] Stopped $pyCount python process(es) (API + Worker)" -ForegroundColor Green
} else {
    Write-Host "  [--] No python processes running" -ForegroundColor Gray
}

# -- Kill all node processes (Web frontend) --
$nodeCount = (Get-Process -Name "node" -ErrorAction SilentlyContinue | Measure-Object).Count
if ($nodeCount -gt 0) {
    Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] Stopped $nodeCount node process(es) (Web frontend)" -ForegroundColor Green
} else {
    Write-Host "  [--] No node processes running" -ForegroundColor Gray
}

# -- Clean up PID files --
if (Test-Path $PIDS_DIR) {
    Remove-Item "$PIDS_DIR\*.pid" -Force -ErrorAction SilentlyContinue
}

# -- Docker --
Write-Host ""
if ($Docker) {
    Write-Host "  Stopping Docker containers..." -ForegroundColor Yellow
    Push-Location (Join-Path $ROOT "infra\docker")
    docker compose down
    Pop-Location
    Write-Host "  [OK] Docker containers stopped" -ForegroundColor Green
} else {
    Write-Host "  Docker containers left running (use -Docker to stop)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   All services stopped!               " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

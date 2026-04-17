$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogsDir = Join-Path $RepoRoot "logs"
$BackendPidPath = Join-Path $LogsDir "dev-backend.pid"
$FrontendPidPath = Join-Path $LogsDir "dev-frontend.pid"

function Stop-TrackedProcess {
    param(
        [string]$Label,
        [string]$PidPath
    )

    if (!(Test-Path $PidPath)) {
        Write-Host "$Label pid file not found, skipping." -ForegroundColor Yellow
        return
    }

    $rawPid = (Get-Content $PidPath -ErrorAction Stop | Select-Object -First 1).Trim()
    if (-not $rawPid) {
        Remove-Item $PidPath -ErrorAction SilentlyContinue
        Write-Host "$Label pid file was empty, skipping." -ForegroundColor Yellow
        return
    }

    $pidValue = [int]$rawPid
    $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Remove-Item $PidPath -ErrorAction SilentlyContinue
        Write-Host "$Label process already stopped." -ForegroundColor Yellow
        return
    }

    Stop-Process -Id $pidValue
    Remove-Item $PidPath -ErrorAction SilentlyContinue
    Write-Host "Stopped $Label (PID $pidValue)." -ForegroundColor Green
}

Stop-TrackedProcess -Label "backend" -PidPath $BackendPidPath
Stop-TrackedProcess -Label "frontend" -PidPath $FrontendPidPath

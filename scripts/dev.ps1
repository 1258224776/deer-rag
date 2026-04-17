param(
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 3000,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$UiDir = Join-Path $RepoRoot "ui"
$UiEnvPath = Join-Path $UiDir ".env.local"
$LogsDir = Join-Path $RepoRoot "logs"
$BackendPidPath = Join-Path $LogsDir "dev-backend.pid"
$FrontendPidPath = Join-Path $LogsDir "dev-frontend.pid"

function Test-PortListening {
    param([int]$Port)

    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Get-ProcessIdByPort {
    param([int]$Port)

    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($null -eq $connection) {
        return $null
    }

    return $connection.OwningProcess
}

function Write-PidFile {
    param(
        [string]$Path,
        [int]$ProcessId
    )

    Set-Content -Path $Path -Value $ProcessId -Encoding ascii
}

if (!(Test-Path $BackendPython)) {
    throw "Backend virtualenv not found at $BackendPython"
}

if (!(Test-Path $UiDir)) {
    throw "UI directory not found at $UiDir"
}

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

$envLine = "NEXT_PUBLIC_DEER_RAG_API_BASE_URL=http://127.0.0.1:$BackendPort"
Set-Content -Path $UiEnvPath -Value $envLine -Encoding ascii

$backendAlreadyRunning = Test-PortListening -Port $BackendPort
$frontendAlreadyRunning = Test-PortListening -Port $FrontendPort

if ($backendAlreadyRunning) {
    $existingBackendPid = Get-ProcessIdByPort -Port $BackendPort
    if ($null -ne $existingBackendPid) {
        Write-PidFile -Path $BackendPidPath -ProcessId $existingBackendPid
    }
    Write-Host "Backend already listening on http://127.0.0.1:$BackendPort (PID $existingBackendPid)" -ForegroundColor Yellow
} else {
    $backendCommand = "Set-Location '$RepoRoot'; & '$BackendPython' -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort --reload"
    $backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $backendCommand -PassThru
    Write-PidFile -Path $BackendPidPath -ProcessId $backendProcess.Id
    Write-Host "Started backend on http://127.0.0.1:$BackendPort (PID $($backendProcess.Id))" -ForegroundColor Green
}

if (!(Test-Path (Join-Path $UiDir "node_modules"))) {
    Write-Host "Installing UI dependencies..." -ForegroundColor Cyan
    & npm install --prefix $UiDir
}

if ($frontendAlreadyRunning) {
    $existingFrontendPid = Get-ProcessIdByPort -Port $FrontendPort
    if ($null -ne $existingFrontendPid) {
        Write-PidFile -Path $FrontendPidPath -ProcessId $existingFrontendPid
    }
    Write-Host "Frontend already listening on http://localhost:$FrontendPort (PID $existingFrontendPid)" -ForegroundColor Yellow
} else {
    $frontendCommand = "Set-Location '$UiDir'; npm run dev -- --port $FrontendPort"
    $frontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $frontendCommand -PassThru
    Write-PidFile -Path $FrontendPidPath -ProcessId $frontendProcess.Id
    Write-Host "Started frontend on http://localhost:$FrontendPort (PID $($frontendProcess.Id))" -ForegroundColor Green
}

Write-Host ""
Write-Host "UI:      http://localhost:$FrontendPort/collections" -ForegroundColor Cyan
Write-Host "API:     http://127.0.0.1:$BackendPort/docs" -ForegroundColor Cyan
Write-Host "Stop all: .\dev-stop.ps1" -ForegroundColor Cyan

if ($OpenBrowser) {
    Start-Process "http://localhost:$FrontendPort/collections"
}

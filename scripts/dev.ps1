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
$BackendStdoutLog = Join-Path $LogsDir "backend.stdout.log"
$BackendStderrLog = Join-Path $LogsDir "backend.stderr.log"
$FrontendStdoutLog = Join-Path $LogsDir "frontend.stdout.log"
$FrontendStderrLog = Join-Path $LogsDir "frontend.stderr.log"

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

function Get-ProcessRecord {
    param([int]$ProcessId)

    return Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
}

function Get-ServiceRootProcessId {
    param(
        [int]$ProcessId,
        [string[]]$ExecutableNames
    )

    $currentId = $ProcessId
    $seen = @{}
    while ($currentId -and -not $seen.ContainsKey($currentId)) {
        $seen[$currentId] = $true
        $current = Get-ProcessRecord -ProcessId $currentId
        if ($null -eq $current) {
            break
        }

        $parentId = [int]$current.ParentProcessId
        if ($parentId -le 0) {
            break
        }

        $parent = Get-ProcessRecord -ProcessId $parentId
        if ($null -eq $parent) {
            break
        }

        $parentName = ""
        if ($null -ne $parent.Name) {
            $parentName = $parent.Name.ToLowerInvariant()
        }
        if ($parentName -notin $ExecutableNames) {
            break
        }

        $currentId = $parentId
    }

    return $currentId
}

function Write-PidFile {
    param(
        [string]$Path,
        [int]$ProcessId
    )

    Set-Content -Path $Path -Value $ProcessId -Encoding ascii
}

function Get-TrackedProcess {
    param([int]$ProcessId)

    return Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
}

function Show-RecentLog {
    param(
        [string]$Label,
        [string]$Path
    )

    if (Test-Path $Path) {
        Write-Host ""
        Write-Host "$Label log tail ($Path)" -ForegroundColor Yellow
        Get-Content -Path $Path -Tail 40
    }
}

function Wait-ForService {
    param(
        [string]$Label,
        [int]$Port,
        [System.Diagnostics.Process]$Process,
        [string]$StdoutLog,
        [string]$StderrLog,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening -Port $Port) {
            return
        }

        if ($null -ne $Process) {
            $tracked = Get-TrackedProcess -ProcessId $Process.Id
            if ($null -eq $tracked) {
                Show-RecentLog -Label "$Label stdout" -Path $StdoutLog
                Show-RecentLog -Label "$Label stderr" -Path $StderrLog
                throw "$Label exited before listening on port $Port"
            }
        }

        Start-Sleep -Milliseconds 500
    }

    Show-RecentLog -Label "$Label stdout" -Path $StdoutLog
    Show-RecentLog -Label "$Label stderr" -Path $StderrLog
    throw "Timed out waiting for $Label to listen on port $Port"
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

$npmCommand = (Get-Command npm.cmd -ErrorAction Stop).Source

$backendAlreadyRunning = Test-PortListening -Port $BackendPort
$frontendAlreadyRunning = Test-PortListening -Port $FrontendPort

if ($backendAlreadyRunning) {
    $existingBackendPid = Get-ProcessIdByPort -Port $BackendPort
    if ($null -ne $existingBackendPid) {
        Write-PidFile -Path $BackendPidPath -ProcessId $existingBackendPid
    }
    Write-Host "Backend already listening on http://127.0.0.1:$BackendPort (PID $existingBackendPid)" -ForegroundColor Yellow
} else {
    Remove-Item $BackendStdoutLog, $BackendStderrLog -ErrorAction SilentlyContinue
    $backendProcess = Start-Process `
        -FilePath $BackendPython `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort", "--reload") `
        -WorkingDirectory $RepoRoot `
        -RedirectStandardOutput $BackendStdoutLog `
        -RedirectStandardError $BackendStderrLog `
        -PassThru
    Write-PidFile -Path $BackendPidPath -ProcessId $backendProcess.Id
    Wait-ForService `
        -Label "backend" `
        -Port $BackendPort `
        -Process $backendProcess `
        -StdoutLog $BackendStdoutLog `
        -StderrLog $BackendStderrLog
    $backendPid = Get-ProcessIdByPort -Port $BackendPort
    if ($null -ne $backendPid) {
        $backendRootPid = Get-ServiceRootProcessId -ProcessId $backendPid -ExecutableNames @("python.exe", "cmd.exe")
        Write-PidFile -Path $BackendPidPath -ProcessId $backendRootPid
        Write-Host "Started backend on http://127.0.0.1:$BackendPort (PID $backendRootPid)" -ForegroundColor Green
    } else {
        Write-Host "Started backend on http://127.0.0.1:$BackendPort" -ForegroundColor Green
    }
}

if (!(Test-Path (Join-Path $UiDir "node_modules"))) {
    Write-Host "Installing UI dependencies..." -ForegroundColor Cyan
    & $npmCommand install --prefix $UiDir
}

if ($frontendAlreadyRunning) {
    $existingFrontendPid = Get-ProcessIdByPort -Port $FrontendPort
    if ($null -ne $existingFrontendPid) {
        Write-PidFile -Path $FrontendPidPath -ProcessId $existingFrontendPid
    }
    Write-Host "Frontend already listening on http://localhost:$FrontendPort (PID $existingFrontendPid)" -ForegroundColor Yellow
} else {
    Remove-Item $FrontendStdoutLog, $FrontendStderrLog -ErrorAction SilentlyContinue
    $frontendProcess = Start-Process `
        -FilePath $npmCommand `
        -ArgumentList @("run", "dev", "--", "--port", "$FrontendPort") `
        -WorkingDirectory $UiDir `
        -RedirectStandardOutput $FrontendStdoutLog `
        -RedirectStandardError $FrontendStderrLog `
        -PassThru
    Write-PidFile -Path $FrontendPidPath -ProcessId $frontendProcess.Id
    Wait-ForService `
        -Label "frontend" `
        -Port $FrontendPort `
        -Process $frontendProcess `
        -StdoutLog $FrontendStdoutLog `
        -StderrLog $FrontendStderrLog
    $frontendPid = Get-ProcessIdByPort -Port $FrontendPort
    if ($null -ne $frontendPid) {
        $frontendRootPid = Get-ServiceRootProcessId -ProcessId $frontendPid -ExecutableNames @("node.exe", "cmd.exe")
        Write-PidFile -Path $FrontendPidPath -ProcessId $frontendRootPid
        Write-Host "Started frontend on http://localhost:$FrontendPort (PID $frontendRootPid)" -ForegroundColor Green
    } else {
        Write-Host "Started frontend on http://localhost:$FrontendPort" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "UI:      http://localhost:$FrontendPort/collections" -ForegroundColor Cyan
Write-Host "API:     http://127.0.0.1:$BackendPort/docs" -ForegroundColor Cyan
Write-Host "Stop all: .\dev-stop.ps1" -ForegroundColor Cyan
Write-Host "Logs:    $LogsDir" -ForegroundColor Cyan

if ($OpenBrowser) {
    Start-Process "http://localhost:$FrontendPort/collections"
}

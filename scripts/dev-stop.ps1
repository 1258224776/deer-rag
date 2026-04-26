$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogsDir = Join-Path $RepoRoot "logs"
$BackendPidPath = Join-Path $LogsDir "dev-backend.pid"
$FrontendPidPath = Join-Path $LogsDir "dev-frontend.pid"

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

function Get-DescendantProcessIds {
    param([int]$RootProcessId)

    $all = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    $childrenByParent = @{}
    foreach ($proc in $all) {
        $parentId = [int]$proc.ParentProcessId
        if (-not $childrenByParent.ContainsKey($parentId)) {
            $childrenByParent[$parentId] = New-Object System.Collections.Generic.List[int]
        }
        $childrenByParent[$parentId].Add([int]$proc.ProcessId)
    }

    $queue = New-Object System.Collections.Generic.Queue[int]
    $queue.Enqueue($RootProcessId)
    $seen = @{}
    $descendants = New-Object System.Collections.Generic.List[int]

    while ($queue.Count -gt 0) {
        $currentId = $queue.Dequeue()
        if ($seen.ContainsKey($currentId)) {
            continue
        }
        $seen[$currentId] = $true

        if ($childrenByParent.ContainsKey($currentId)) {
            foreach ($childId in $childrenByParent[$currentId]) {
                if (-not $seen.ContainsKey($childId)) {
                    $descendants.Add($childId)
                    $queue.Enqueue($childId)
                }
            }
        }
    }

    return $descendants | Sort-Object -Descending -Unique
}

function Stop-TrackedProcess {
    param(
        [string]$Label,
        [string]$PidPath,
        [int]$Port,
        [string[]]$ExecutableNames
    )

    $candidateIds = New-Object System.Collections.Generic.List[int]

    if (Test-Path $PidPath) {
        $rawPid = (Get-Content $PidPath -ErrorAction Stop | Select-Object -First 1).Trim()
        if ($rawPid) {
            $candidateIds.Add([int]$rawPid)
        } else {
            Remove-Item $PidPath -ErrorAction SilentlyContinue
        }
    }

    $portOwner = Get-ProcessIdByPort -Port $Port
    if ($null -ne $portOwner) {
        $candidateIds.Add((Get-ServiceRootProcessId -ProcessId $portOwner -ExecutableNames $ExecutableNames))
    }

    $rootIds = $candidateIds | Where-Object { $_ -gt 0 } | Sort-Object -Unique
    if ($rootIds.Count -eq 0) {
        Remove-Item $PidPath -ErrorAction SilentlyContinue
        Write-Host "$Label process already stopped." -ForegroundColor Yellow
        return
    }

    foreach ($rootId in $rootIds) {
        $process = Get-Process -Id $rootId -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            continue
        }

        $descendants = Get-DescendantProcessIds -RootProcessId $rootId
        if ($descendants.Count -gt 0) {
            Get-Process -Id $descendants -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        }
        Stop-Process -Id $rootId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped $Label (PID $rootId)." -ForegroundColor Green
    }

    Remove-Item $PidPath -ErrorAction SilentlyContinue
}

Stop-TrackedProcess -Label "backend" -PidPath $BackendPidPath -Port 8010 -ExecutableNames @("python.exe", "cmd.exe")
Stop-TrackedProcess -Label "frontend" -PidPath $FrontendPidPath -Port 3000 -ExecutableNames @("node.exe", "cmd.exe")

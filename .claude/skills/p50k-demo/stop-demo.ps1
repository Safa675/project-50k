<#
Stop the local Project 50K demo started from THIS repository: the launcher process trees recorded by
start-demo.ps1, then any remaining demo listener whose command line runs from this repository.
Processes from other folders (for example another checkout's demo) and stale PIDs are never stopped.
#>
param([int]$FrontendPort = 3060, [int]$ApiPort = 8767, [int]$DatedApiPort = 8768)
# start-demo.ps1 -Restart calls this script with its 'Stop' preference; taskkill's stderr must not abort it.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
# A trailing separator keeps C:\x\project-50k from matching C:\x\project-50k-dated.
$prefix = $repo.TrimEnd('\') + '\'
function Get-CommandLine([int]$id) {
  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
  if ($proc) { return [string]$proc.CommandLine }
  return $null
}
function Test-Ours([string]$line, [string[]]$markers) {
  if (-not $line -or $line.IndexOf($prefix, [StringComparison]::OrdinalIgnoreCase) -lt 0) { return $false }
  foreach ($marker in $markers) { if ($line.IndexOf($marker, [StringComparison]::OrdinalIgnoreCase) -ge 0) { return $true } }
  return $false
}

$pids = Join-Path $repo '.claude\p50k-demo.pids.local.json'
if (Test-Path $pids) {
  $p = Get-Content $pids -Raw | ConvertFrom-Json
  foreach ($id in @($p.fixed, $p.dated)) {
    if (-not $id) { continue }
    if (Test-Ours (Get-CommandLine $id) @('run_app.py', 'run_dated_app.py')) {
      & taskkill.exe /T /F /PID $id 2>$null | Out-Null
      Write-Output "Stopped launcher PID $id"
    } else {
      Write-Output "Recorded PID $id is no longer a demo launcher from this repository; left alone."
    }
  }
  Remove-Item $pids -Force
}
foreach ($port in @($FrontendPort, $ApiPort, $DatedApiPort)) {
  foreach ($c in @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    $line = Get-CommandLine $c.OwningProcess
    if (Test-Ours $line @('uvicorn p50k.api', 'next\dist\bin\next', 'next/dist/bin/next', 'run_app.py', 'run_dated_app.py')) {
      & taskkill.exe /T /F /PID $c.OwningProcess 2>$null | Out-Null
      Write-Output "Stopped PID $($c.OwningProcess) on port $port"
    } elseif ($line) {
      Write-Output "Port $port is held by PID $($c.OwningProcess) outside this repository; left running."
    }
  }
}

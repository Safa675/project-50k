<#
Stop the local Project 50K demo started from THIS repository: the launcher process trees recorded by
start-demo.ps1, then any remaining listener on the demo ports whose command line points into this repository.
Processes from other folders (for example another checkout's demo) are never stopped.
#>
param([int]$FrontendPort = 3060, [int]$ApiPort = 8767, [int]$DatedApiPort = 8768)
# start-demo.ps1 -Restart calls this script with its 'Stop' preference; taskkill's stderr must not abort it.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$pids = Join-Path $repo '.claude\p50k-demo.pids.local.json'
if (Test-Path $pids) {
  $p = Get-Content $pids -Raw | ConvertFrom-Json
  foreach ($id in @($p.fixed, $p.dated)) { if ($id) { & taskkill.exe /T /F /PID $id 2>$null | Out-Null } }
  Remove-Item $pids -Force
}
foreach ($port in @($FrontendPort, $ApiPort, $DatedApiPort)) {
  foreach ($c in @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)" -ErrorAction SilentlyContinue
    if ($proc -and $proc.CommandLine -and $proc.CommandLine.IndexOf($repo, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
      & taskkill.exe /T /F /PID $c.OwningProcess 2>$null | Out-Null
      Write-Output "Stopped PID $($c.OwningProcess) on port $port"
    } elseif ($proc) {
      Write-Output "Port $port is held by PID $($c.OwningProcess) outside this repository; left running."
    }
  }
}

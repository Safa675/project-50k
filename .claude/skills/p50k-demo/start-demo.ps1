<#
Start the local Project 50K demo: fixed-date API (8767) + frontend (3060) via ops/local/run_app.py,
and the dated D1 API (8768) via ops/local/run_dated_app.py. Loopback only; nothing is computed or downloaded.

Usage (repository root):
  powershell -ExecutionPolicy Bypass -File .claude/skills/p50k-demo/start-demo.ps1 `
    -FixedBundle <sealed fixed-date bundle dir> -DatedIndex <sealed dated index dir> [-Restart]
Without -FixedBundle/-DatedIndex the values are read from .claude/p50k-demo.local.json:
  {"fixed_bundle": "<dir>", "dated_index": "<dir>"}
-Restart first stops processes from this repository that hold the demo ports (stop-demo.ps1).
#>
param(
  [string]$FixedBundle,
  [string]$DatedIndex,
  [int]$FrontendPort = 3060,
  [int]$ApiPort = 8767,
  [int]$DatedApiPort = 8768,
  [switch]$Restart
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$py = Join-Path $repo '.venv\Scripts\python.exe'
$config = Join-Path $repo '.claude\p50k-demo.local.json'
if ((-not $FixedBundle -or -not $DatedIndex) -and (Test-Path $config)) {
  $c = Get-Content $config -Raw | ConvertFrom-Json
  if (-not $FixedBundle) { $FixedBundle = $c.fixed_bundle }
  if (-not $DatedIndex) { $DatedIndex = $c.dated_index }
}
if (-not $FixedBundle -or -not $DatedIndex) { throw 'Pass -FixedBundle and -DatedIndex, or create .claude/p50k-demo.local.json.' }
# A trailing separator would escape the closing quote added below.
$FixedBundle = $FixedBundle.TrimEnd([char[]]'\/')
$DatedIndex = $DatedIndex.TrimEnd([char[]]'\/')
if (-not (Test-Path $py)) { throw "Missing $py. Run: uv sync --locked --extra api --extra api-test --extra research" }
if (-not (Test-Path (Join-Path $repo 'frontend\.next\BUILD_ID'))) { throw 'Missing frontend build. Run in frontend/: npm run build' }

if ($Restart) { & (Join-Path $PSScriptRoot 'stop-demo.ps1') -FrontendPort $FrontendPort -ApiPort $ApiPort -DatedApiPort $DatedApiPort }
$ports = @($FrontendPort, $ApiPort, $DatedApiPort)
$freeBy = (Get-Date).AddSeconds($(if ($Restart) { 20 } else { 0 }))
while ($true) {
  $busy = @(Get-NetTCPConnection -LocalPort $ports -State Listen -ErrorAction SilentlyContinue)
  if (-not $busy) { break }
  if ((Get-Date) -gt $freeBy) { throw "Port $($busy[0].LocalPort) is in use by PID $($busy[0].OwningProcess). Stop it first or use -Restart." }
  Start-Sleep -Milliseconds 500
}

$logs = Join-Path $repo '.claude\demo-logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NEXT_TELEMETRY_DISABLED = '1'
$env:P50K_DATED_API_ORIGIN = "http://127.0.0.1:$DatedApiPort"

$dated = Start-Process -FilePath $py -WorkingDirectory $repo -PassThru -WindowStyle Hidden `
  -ArgumentList @('ops/local/run_dated_app.py', '--index', "`"$DatedIndex`"", '--api-port', "$DatedApiPort") `
  -RedirectStandardOutput (Join-Path $logs 'dated.out.log') -RedirectStandardError (Join-Path $logs 'dated.err.log')
$fixed = Start-Process -FilePath $py -WorkingDirectory $repo -PassThru -WindowStyle Hidden `
  -ArgumentList @('ops/local/run_app.py', '--bundle', "`"$FixedBundle`"", '--mode', 'production', '--api-port', "$ApiPort", '--frontend-port', "$FrontendPort") `
  -RedirectStandardOutput (Join-Path $logs 'fixed.out.log') -RedirectStandardError (Join-Path $logs 'fixed.err.log')
@{dated = $dated.Id; fixed = $fixed.Id} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $repo '.claude\p50k-demo.pids.local.json')

$checks = @("http://127.0.0.1:$ApiPort/research/v1/health", "http://127.0.0.1:$DatedApiPort/research-dated/v1/dates", "http://127.0.0.1:$FrontendPort/")
$deadline = (Get-Date).AddSeconds(90)
foreach ($url in $checks) {
  while ($true) {
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 5; if ($r.StatusCode -eq 200) { Write-Output "OK  $url"; break } } catch { }
    if ((Get-Date) -gt $deadline) { Write-Output "FAILED $url (see .claude/demo-logs)"; exit 1 }
    Start-Sleep -Milliseconds 500
  }
}
Write-Output "Demo running: http://127.0.0.1:$FrontendPort/ and http://127.0.0.1:$FrontendPort/dates (launcher PIDs fixed=$($fixed.Id) dated=$($dated.Id))"

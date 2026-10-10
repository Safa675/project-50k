<#
Collect today's TEFAS fund snapshots on Windows; the equivalent of ops/systemd for a Windows machine.
Writes to a separate database that no sealed research bundle reads (default
~/.local/share/project-50k/fund_snapshots_forward.sqlite3). A rerun keeps the rows already stored for a date and adds
the missing ones, so a run stopped by TEFAS errors can simply be repeated. Real data stays outside git.
#>
param([string]$Db = (Join-Path $HOME '.local\share\project-50k\fund_snapshots_forward.sqlite3'))
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$py = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "Missing $py; run uv sync --locked in $repo" }
$dir = Split-Path $Db
New-Item -ItemType Directory -Force $dir | Out-Null
$log = Join-Path $dir ("snapshots-{0:yyyy-MM-dd}.log" -f (Get-Date))
$env:PYTHONPATH = Join-Path $repo 'services'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
Set-Location $repo
[IO.File]::AppendAllText($log, "=== $(Get-Date -Format o) start`n")
# cmd does the redirection: Windows PowerShell 5.1 turns redirected stderr (Python's logging) into errors.
$arguments = "/d /s /c `"`"$py`" -m p50k.jobs.fund_snapshots --tefas-only --db `"$Db`" >> `"$log`" 2>&1`""
$process = Start-Process -FilePath $env:ComSpec -ArgumentList $arguments -NoNewWindow -Wait -PassThru
$code = $process.ExitCode
[IO.File]::AppendAllText($log, "=== $(Get-Date -Format o) exit $code`n")
exit $code

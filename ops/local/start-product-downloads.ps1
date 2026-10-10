param(
    [Parameter(Mandatory = $true)][string]$ArchiveRoot,
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [int[]]$SnapshotProcessIds = @(),
    [switch]$DryRun,
    [string]$SnapshotDatabase = (Join-Path $env:USERPROFILE '.local\share\project-50k\overnight\2026-10-10\snapshots-all.sqlite3')
)

$ErrorActionPreference = 'Stop'
$productRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$downloadRoot = Join-Path $env:USERPROFILE '.local\share\project-50k\overnight\2026-10-10'
$downloadLogDirectory = Join-Path $downloadRoot 'logs'
# Inventory failure aborts the launcher. Command lines are filtered locally and
# never emitted; both the legacy launcher and its child must finish first.
$discoveredCollectors = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.Name -match '^python(w)?\.exe$' -and
    $_.CommandLine -match '(?:^|\s)-m\s+p50k\.jobs\.fund_snapshots(?:\s|$)'
})
$collectorProcessIds = @((@($SnapshotProcessIds) + @($discoveredCollectors | ForEach-Object { [int]$_.ProcessId })) |
    Sort-Object -Unique)
if (@($collectorProcessIds | Where-Object { $_ -le 0 }).Count -gt 0) {
    throw 'Snapshot process IDs must be positive'
}
if (-not $DryRun) { New-Item -ItemType Directory -Force -Path $downloadLogDirectory | Out-Null }
$env:PYTHONPATH = Join-Path $productRoot 'services'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'

foreach ($source in @('tefas', 'spk', 'kap')) {
    # Quote paths for Windows CreateProcess; no shell interpolates these values.
    $sourceArguments = @('-m', 'p50k.product.downloads', $source,
        '--archive-root', ('"' + $ArchiveRoot + '"'),
        '--out-root', ('"' + $downloadRoot + '"'),
        '--snapshot-db', ('"' + $SnapshotDatabase + '"'))
    if ($source -eq 'tefas') {
        if ($collectorProcessIds.Count -gt 0) {
            $sourceArguments += '--wait-pid'
            $sourceArguments += $collectorProcessIds | ForEach-Object { $_.ToString() }
        } else {
            $sourceArguments += '--no-existing-collector'
        }
    }
    if ($source -eq 'kap') { $sourceArguments += '--watch-profiles' }
    if ($DryRun) {
        [PSCustomObject]@{ Source = $source; Arguments = $sourceArguments } | ConvertTo-Json -Compress
        continue
    }
    $sourceProcess = Start-Process -FilePath $PythonExecutable -ArgumentList $sourceArguments `
        -WorkingDirectory $productRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $downloadLogDirectory ($source + '-runner.log')) `
        -RedirectStandardError (Join-Path $downloadLogDirectory ($source + '-runner.err.log'))
    Write-Output ($source + ' launcher PID ' + $sourceProcess.Id)
}

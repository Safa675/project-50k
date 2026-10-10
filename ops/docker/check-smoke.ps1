param([switch]$KeepRunning)
$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$smokeVariables = @{
    P50K_DB_NAME = 'p50k_dev'
    P50K_TEST_ENDPOINTS = 'true'
    P50K_WEB_PORT = '3071'
    P50K_API_PORT = '8771'
}
$previousVariables = @{}
foreach ($variableName in $smokeVariables.Keys) {
    $previousVariables[$variableName] = [Environment]::GetEnvironmentVariable($variableName, 'Process')
    [Environment]::SetEnvironmentVariable($variableName, $smokeVariables[$variableName], 'Process')
}
Push-Location $workspaceRoot
try {
    & (Join-Path $PSScriptRoot 'setup-secrets.ps1') -Workspace $workspaceRoot
    docker compose --project-name p50k-smoke -f compose.yaml config --no-interpolate --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Smoke Compose configuration is invalid.' }
    docker compose --project-name p50k-smoke -f compose.yaml up -d --wait --wait-timeout 120
    if ($LASTEXITCODE -ne 0) { throw 'Smoke services failed to become healthy.' }
    & (Join-Path $workspaceRoot '.venv/Scripts/python.exe') ops/local/check-product-proxy.py --port 3071
    if ($LASTEXITCODE -ne 0) { throw 'Cookie, Origin, CSRF or streaming verification failed.' }
} finally {
    if (-not $KeepRunning) {
        # The isolated smoke volume is the only volume this script may remove.
        docker compose --project-name p50k-smoke -f compose.yaml down -v
    }
    Pop-Location
    foreach ($variableName in $previousVariables.Keys) {
        [Environment]::SetEnvironmentVariable($variableName, $previousVariables[$variableName], 'Process')
    }
}

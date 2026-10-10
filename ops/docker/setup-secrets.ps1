param([string]$Workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path)
$ErrorActionPreference = 'Stop'
$workspaceRoot = [IO.Path]::GetFullPath($Workspace).TrimEnd('\', '/')
$secretFolder = [IO.Path]::GetFullPath((Join-Path $workspaceRoot 'secrets'))
if (-not $secretFolder.StartsWith($workspaceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Secret directory must be inside the selected workspace.'
}
New-Item -ItemType Directory -Path $secretFolder -Force | Out-Null
$encoding = New-Object System.Text.UTF8Encoding($false)
foreach ($secretName in @('db_owner_password', 'db_app_password', 'auth_pepper')) {
    $secretPath = Join-Path $secretFolder $secretName
    if (Test-Path -LiteralPath $secretPath) { continue }
    $bytes = New-Object byte[] 48
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    $secretValue = [Convert]::ToBase64String($bytes)
    $temporary = Join-Path $secretFolder ('.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    [IO.File]::WriteAllText($temporary, $secretValue, $encoding)
    try { Move-Item -LiteralPath $temporary -Destination $secretPath -ErrorAction Stop }
    finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
    [Array]::Clear($bytes, 0, $bytes.Length)
    $secretValue = $null
}
Write-Output 'Runtime credential files are ready. Existing files were preserved; values were not displayed.'

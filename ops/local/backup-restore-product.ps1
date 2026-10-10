param(
    [switch]$KeepRestore
)

# T6.3: readonly product backup, isolated restore and count/checksum verification.
# No credentials or data rows are written to stdout. Never invoke down -v here.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$backupRoot = [IO.Path]::GetFullPath((Join-Path $workspace 'backups'))
if (-not $backupRoot.StartsWith($workspace + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Backup directory must stay within the product worktree.'
}
$runToken = [Guid]::NewGuid().ToString('N')
$runStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$restoreName = 'p50k-restore-rehearsal-' + $runToken
$restoreVolume = $restoreName + '-data'
$sourceDump = '/tmp/p50k-rehearsal-' + $runToken + '.dump'
$dumpName = 'p50k-' + $runStamp + '-' + $runToken + '.dump'
$dumpPath = Join-Path $backupRoot $dumpName
$summaryPath = Join-Path $backupRoot ('p50k-' + $runStamp + '-' + $runToken + '.summary.json')
$summaryTemp = $summaryPath + '.tmp'
$utf8 = New-Object Text.UTF8Encoding($false)
$sourceContainer = $null
$snapshotProcess = $null
$snapshotError = $null
$createdContainer = $false
$createdVolume = $false
$restoreVerified = $false
$result = $null

function Invoke-DockerChecked {
    param([string[]]$Arguments, [string]$Action)
    $previousPreference=$ErrorActionPreference
    try { $ErrorActionPreference='Continue'; $output = & docker @Arguments 2>&1; $code=$LASTEXITCODE }
    finally { $ErrorActionPreference=$previousPreference }
    if ($code -ne 0) { throw ('Docker action failed: ' + $Action) }
    return @($output | ForEach-Object { $_.ToString() })
}

function Invoke-PsqlChecked {
    param([string]$Container, [string]$Database, [string]$Sql, [string]$Action)
    $previousPreference=$ErrorActionPreference
    try { $ErrorActionPreference='Continue'; $output = $Sql | & docker exec -i $Container psql -X -qAt -v ON_ERROR_STOP=1 -U p50k_owner -d $Database 2>&1; $code=$LASTEXITCODE }
    finally { $ErrorActionPreference=$previousPreference }
    if ($code -ne 0) { throw ('Database check failed: ' + $Action) }
    return @($output | ForEach-Object { $_.ToString() })
}

$summarySql = @'
SET TIME ZONE 'UTC';
WITH tables AS (
    SELECT namespace.nspname AS schema_name,relation.relname AS table_name
    FROM pg_class relation JOIN pg_namespace namespace ON namespace.oid=relation.relnamespace
    WHERE relation.relkind='r' AND namespace.nspname IN ('ref','obs','det','ai','auth','b2b','ops')
), counts AS (
    SELECT schema_name||'.'||table_name AS name,
      ((xpath('/row/value/text()',query_to_xml(
          format('SELECT count(*) value FROM %I.%I',schema_name,table_name),false,true,'')))[1]::text)::bigint AS count
    FROM tables
), evidence_checksums AS (
    SELECT schema_name||'.'||table_name AS name,
      (xpath('/row/value/text()',query_to_xml(
          format('SELECT md5(COALESCE(string_agg(row_hash,'''' ORDER BY row_hash),'''')) value FROM (SELECT md5(row_to_json(row)::text) row_hash FROM %I.%I row) hashed',schema_name,table_name),false,true,'')))[1]::text AS checksum
    FROM tables WHERE schema_name IN ('det','ai')
), immutable_triggers AS (
    SELECT namespace.nspname||'.'||relation.relname AS name,
      count(*) FILTER(WHERE trigger.tgname IN ('immutable_rows','immutable_truncate')
        AND trigger.tgfoid='ops.reject_immutable_change'::regproc AND trigger.tgenabled='O') AS count
    FROM pg_class relation JOIN pg_namespace namespace ON namespace.oid=relation.relnamespace
      JOIN pg_trigger trigger ON trigger.tgrelid=relation.oid
    WHERE namespace.nspname IN ('ref','obs','det','ai','ops')
      AND trigger.tgname IN ('immutable_rows','immutable_truncate')
    GROUP BY namespace.nspname,relation.relname
)
SELECT 'P50K_SUMMARY|' || jsonb_build_object(
    'tables',(SELECT jsonb_object_agg(name,count) FROM counts),
    'migrations',(SELECT jsonb_object_agg(filename,sha256) FROM ops.schema_migrations),
    'evidence_checksums',(SELECT jsonb_object_agg(name,checksum) FROM evidence_checksums),
    'immutable_triggers',(SELECT jsonb_object_agg(name,count) FROM immutable_triggers)
)::text;
'@

function Get-MarkedSummary {
    param([string[]]$Lines)
    $selected = @($Lines | Where-Object { $_.StartsWith('P50K_SUMMARY|') })
    if ($selected.Count -ne 1) { throw 'Database summary is missing or ambiguous.' }
    return $selected[0].Substring('P50K_SUMMARY|'.Length)
}

try {
    Push-Location $workspace
    try {
        & git check-ignore --quiet --no-index -- ('backups/' + $dumpName)
        if ($LASTEXITCODE -ne 0) { throw 'The dump must be ignored by Git before backup.' }
        & git check-ignore --quiet --no-index -- ('backups/' + [IO.Path]::GetFileName($summaryPath))
        if ($LASTEXITCODE -ne 0) { throw 'The private summary must be ignored by Git.' }
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        $sourceContainer = (@(Invoke-DockerChecked @('compose','-f','compose.yaml','ps','-q','db') 'discover product database') -join '').Trim()
        if ($sourceContainer -notmatch '^[a-f0-9]{12,64}$') { throw 'Exactly one product database container is required.' }
        $labels = ((@(Invoke-DockerChecked @('inspect','--format','{{json .Config.Labels}}',$sourceContainer) 'verify product database labels') -join '') | ConvertFrom-Json)
        $image = (@(Invoke-DockerChecked @('inspect','--format','{{.Config.Image}}',$sourceContainer) 'verify product database image') -join '').Trim()
        if ($labels.'com.docker.compose.project' -ne 'p50k' -or $labels.'com.docker.compose.service' -ne 'db' -or $image -ne 'postgres:18.6') { throw 'Backup source must be the pinned p50k product database.' }
        $databaseName = (@(Invoke-PsqlChecked $sourceContainer 'p50k' 'SELECT current_database();' 'verify source database') -join '').Trim()
        if ($databaseName -ne 'p50k') { throw 'Backup source database identity differs.' }

        # Keep an exported readonly snapshot alive for both the source summary and
        # pg_dump. Concurrent product writes remain outside this consistent backup.
        $startInfo = New-Object Diagnostics.ProcessStartInfo
        $startInfo.FileName = 'docker'
        $startInfo.Arguments = 'exec -i ' + $sourceContainer + ' psql -X -qAt -v ON_ERROR_STOP=1 -U p50k_owner -d p50k'
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $startInfo.RedirectStandardInput = $true
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $snapshotProcess = New-Object Diagnostics.Process
        $snapshotProcess.StartInfo = $startInfo
        if (-not $snapshotProcess.Start()) { throw 'Could not begin a readonly backup snapshot.' }
        $snapshotError = $snapshotProcess.StandardError.ReadToEndAsync()
        $snapshotProcess.StandardInput.WriteLine("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL statement_timeout='60s'; SELECT 'P50K_SNAPSHOT|'||pg_export_snapshot();")
        $snapshotProcess.StandardInput.Flush()
        $snapshotLine = $snapshotProcess.StandardOutput.ReadLine()
        if (-not $snapshotLine -or -not $snapshotLine.StartsWith('P50K_SNAPSHOT|')) { throw 'Could not export the readonly database snapshot.' }
        $snapshot = $snapshotLine.Substring('P50K_SNAPSHOT|'.Length)
        if ($snapshot -notmatch '^[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9]+$') { throw 'Exported snapshot identifier is invalid.' }
        $snapshotProcess.StandardInput.WriteLine($summarySql)
        $snapshotProcess.StandardInput.Flush()
        $sourceSummary = Get-MarkedSummary @($snapshotProcess.StandardOutput.ReadLine())
        Write-Output 'Product readonly snapshot recorded; creating local custom-format dump.'
        Invoke-DockerChecked @('exec',$sourceContainer,'pg_dump','-U','p50k_owner','-d','p50k','--format=custom',('--snapshot=' + $snapshot),'--file',$sourceDump) 'create readonly product dump' | Out-Null
        Invoke-DockerChecked @('cp',($sourceContainer + ':' + $sourceDump),$dumpPath) 'copy dump into ignored backups' | Out-Null
        $snapshotProcess.StandardInput.WriteLine('ROLLBACK;')
        $snapshotProcess.StandardInput.Close()
        $snapshotProcess.WaitForExit()
        if ($snapshotProcess.ExitCode -ne 0) { throw 'Readonly backup snapshot failed.' }
        $snapshotProcess.Dispose()
        $snapshotProcess = $null
        $dumpHash = (Get-FileHash -LiteralPath $dumpPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $dumpBytes = (Get-Item -LiteralPath $dumpPath).Length
        if ($dumpBytes -le 0) { throw 'Backup dump is empty.' }

        Invoke-DockerChecked @('volume','create','--label','p50k.restore-rehearsal=true','--label',('p50k.run-token=' + $runToken),$restoreVolume) 'create isolated restore volume' | Out-Null
        $createdVolume = $true
        # Trust applies only within this networkless container. No role password,
        # host port, API or worker is created for the isolated rehearsal database.
        Invoke-DockerChecked @('run','--detach','--name',$restoreName,'--network','none','--label','p50k.restore-rehearsal=true','--label',('p50k.run-token=' + $runToken),
            '--env','POSTGRES_DB=p50k_restore','--env','POSTGRES_USER=p50k_owner','--env','POSTGRES_HOST_AUTH_METHOD=trust',
            '--mount',('type=volume,source=' + $restoreVolume + ',target=/var/lib/postgresql'),'postgres:18.6') 'start networkless restore container' | Out-Null
        $createdContainer = $true
        $ready = $false
        for ($attempt=0; $attempt -lt 45; $attempt++) {
            & docker exec $restoreName pg_isready -U p50k_owner -d p50k_restore *> $null
            if ($LASTEXITCODE -eq 0) { $ready=$true; break }
            Start-Sleep -Seconds 1
        }
        if (-not $ready) { throw 'Isolated restore database did not become ready.' }
        $network = (@(Invoke-DockerChecked @('inspect','--format','{{.HostConfig.NetworkMode}}',$restoreName) 'verify restore network isolation') -join '').Trim()
        if ($network -ne 'none' -or @(Invoke-DockerChecked @('port',$restoreName) 'verify no restore host ports').Count -ne 0) {
            throw 'Restore sandbox must have no network or published ports.'
        }
        Invoke-PsqlChecked $restoreName 'p50k_restore' 'CREATE ROLE p50k_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;' 'create credential-free restore application role' | Out-Null
        Invoke-DockerChecked @('cp',$dumpPath,($restoreName + ':/tmp/product.dump')) 'copy backup into isolated restore container' | Out-Null
        Write-Output 'Restoring into networkless p50k_restore; product database remains running.'
        Invoke-DockerChecked @('exec',$restoreName,'pg_restore','-U','p50k_owner','-d','p50k_restore','--exit-on-error','--single-transaction','/tmp/product.dump') 'restore original ownership and ACLs' | Out-Null
        $restoredSummary = Get-MarkedSummary (Invoke-PsqlChecked $restoreName 'p50k_restore' $summarySql 'read restored count/checksum summary')
        if ($restoredSummary -cne $sourceSummary) { throw 'Restored counts, migrations, evidence hashes or trigger registrations differ from the exported snapshot.' }
        $immutableSql = @'
DO $$
DECLARE table_name text; checked integer:=0; has_rows boolean;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['det.evidence_items','ai.decisions','obs.stock_prices'] LOOP
        IF to_regclass(table_name) IS NULL THEN CONTINUE; END IF;
        EXECUTE format('SELECT EXISTS(SELECT 1 FROM %s)',table_name) INTO has_rows;
        IF NOT has_rows THEN CONTINUE; END IF;
        BEGIN
            IF table_name='det.evidence_items' THEN
                UPDATE det.evidence_items SET state=state WHERE ctid=(SELECT ctid FROM det.evidence_items LIMIT 1);
            ELSIF table_name='ai.decisions' THEN
                UPDATE ai.decisions SET validation_state=validation_state WHERE ctid=(SELECT ctid FROM ai.decisions LIMIT 1);
            ELSE
                EXECUTE format('UPDATE %s SET close=close WHERE ctid=(SELECT ctid FROM %s LIMIT 1)',table_name,table_name);
            END IF;
            RAISE EXCEPTION 'Immutability verification failed' USING ERRCODE='P0001';
        EXCEPTION WHEN SQLSTATE '55000' THEN
            checked:=checked+1;
        END;
    END LOOP;
    IF checked<2 THEN RAISE EXCEPTION 'Insufficient restored immutable records'; END IF;
END $$;
SELECT 'P50K_IMMUTABILITY|verified';
'@
        $immutableOutput = Invoke-PsqlChecked $restoreName 'p50k_restore' $immutableSql 'verify restored owner cannot change evidence/AI/prices'
        if ($immutableOutput -notcontains 'P50K_IMMUTABILITY|verified') { throw 'Restored immutability check did not finish.' }
        $permissionSql = @'
BEGIN READ ONLY;
SET LOCAL ROLE p50k_app;
SELECT 'P50K_ACL|'||(SELECT count(*) FROM det.evidence_items)::text||'|'||(SELECT count(*) FROM ai.decisions)::text;
ROLLBACK;
SELECT 'P50K_ROLE|'||(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls)::text FROM pg_roles WHERE rolname='p50k_app';
'@
        $permissionOutput = Invoke-PsqlChecked $restoreName 'p50k_restore' $permissionSql 'verify restored application read permissions and role restrictions'
        if (@($permissionOutput | Where-Object { $_.StartsWith('P50K_ACL|') }).Count -ne 1 -or $permissionOutput -notcontains 'P50K_ROLE|true') {
            throw 'Restored application permissions differ.'
        }
        $parsedSummary = $sourceSummary | ConvertFrom-Json
        $result = [ordered]@{
            status='VERIFIED'; captured_at_utc=[DateTime]::UtcNow.ToString('o');
            source_database='p50k'; restore_database='p50k_restore'; postgres_image='postgres:18.6';
            dump_file=$dumpName; dump_sha256=$dumpHash; dump_bytes=$dumpBytes;
            tables=$parsedSummary.tables; migrations=$parsedSummary.migrations;
            evidence_checksums=$parsedSummary.evidence_checksums; immutable_triggers=$parsedSummary.immutable_triggers;
            restored_counts_match=$true; restored_evidence_match=$true; restored_immutability_verified=$true;
            restored_permissions_verified=$true; restore_network='none'; restore_published_ports=0;
            restore_container=$restoreName; restore_volume=$restoreVolume; kept_restore=[bool]$KeepRestore
        }
        [IO.File]::WriteAllText($summaryTemp,($result | ConvertTo-Json -Depth 8),$utf8)
        [IO.File]::Move($summaryTemp,$summaryPath)
        $restoreVerified = $true
        Write-Output ('Backup/restore VERIFIED: ' + $dumpName + '; bytes=' + $dumpBytes + '; tables=' + @($parsedSummary.tables.PSObject.Properties).Count + '; migrations=' + @($parsedSummary.migrations.PSObject.Properties).Count)
    }
    finally { Pop-Location }
}
finally {
    if ($snapshotProcess) {
        try { $snapshotProcess.StandardInput.WriteLine('ROLLBACK;'); $snapshotProcess.StandardInput.Close(); $snapshotProcess.WaitForExit(5000) | Out-Null } catch {}
        if (-not $snapshotProcess.HasExited) { $snapshotProcess.Kill() }
        $snapshotProcess.Dispose()
    }
    if ($sourceContainer) {
        try { Invoke-DockerChecked @('exec',$sourceContainer,'rm','-f','--',$sourceDump) 'remove only this rehearsal temporary container dump' | Out-Null } catch {}
    }
    if ($createdContainer -and -not $KeepRestore) {
        $labels = ((@(Invoke-DockerChecked @('inspect','--format','{{json .Config.Labels}}',$restoreName) 'verify owned restore container') -join '') | ConvertFrom-Json)
        if ($labels.'p50k.run-token' -ne $runToken -or $restoreName -notmatch '^p50k-restore-rehearsal-[a-f0-9]{32}$') { throw 'Refusing cleanup of an unrelated container.' }
        Invoke-DockerChecked @('rm','--force',$restoreName) 'remove this isolated restore container' | Out-Null
    }
    if ($createdVolume -and -not $KeepRestore) {
        $labels = ((@(Invoke-DockerChecked @('volume','inspect','--format','{{json .Labels}}',$restoreVolume) 'verify owned restore volume') -join '') | ConvertFrom-Json)
        if ($labels.'p50k.run-token' -ne $runToken -or $restoreVolume -notmatch '^p50k-restore-rehearsal-[a-f0-9]{32}-data$') { throw 'Refusing cleanup of an unrelated volume.' }
        Invoke-DockerChecked @('volume','rm',$restoreVolume) 'remove only this isolated restore volume' | Out-Null
    }
}

if (-not $restoreVerified) { throw 'Backup/restore verification did not complete.' }

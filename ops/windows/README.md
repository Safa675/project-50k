# Daily fund snapshots on Windows

TEFAS serves only today's fund size, units outstanding and investor count, so a missed business day is lost.
`fund-snapshots.ps1` runs `p50k.jobs.fund_snapshots --tefas-only` with the repository's locked environment and
writes to `~/.local/share/project-50k/fund_snapshots_forward.sqlite3`. That database is separate from any
snapshot database that sealed research bundles read, so collection never invalidates a bundle (see
`ops/systemd/README.md` for that hazard). Logs: `~/.local/share/project-50k/snapshots-<date>.log`.

Run once by hand. A full run takes one to several hours: the job pauses 1.5 s between requests, and TEFAS
responses were slow on 2026-10-10. If TEFAS errors stop it early, run it again: rows already stored are kept,
not duplicated.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops\windows\fund-snapshots.ps1
```

Schedule weekdays at 21:00 Istanbul time for the current user (runs a missed start when the PC is next on):

```powershell
$repo = (Resolve-Path .).Path
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$repo\ops\windows\fund-snapshots.ps1`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 21:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 8)
Register-ScheduledTask -TaskName 'P50K fund snapshots' -Action $action -Trigger $trigger -Settings $settings `
  -Description 'Project 50K daily TEFAS snapshot collection (DEC-027)'
```

Remove it with `Unregister-ScheduledTask -TaskName 'P50K fund snapshots' -Confirm:$false`.
The schedule assumes the machine's clock is on Istanbul time. Collected values stay private and are never
committed.

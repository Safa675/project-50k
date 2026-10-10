# BlackSwan database backup/restore rehearsal, 2026-10-10

T6.3 backup/restore preparation is verified. The Sunday freeze backup, freeze
merge, tag and cold-boot rehearsal remain separate tasks.

Changed files: `ops/local/backup-restore-product.ps1` and this report. The script
creates a custom-format PostgreSQL backup in the ignored worktree `backups/`
folder, then restores it into a fresh `postgres:18.6` container/database named
`p50k_restore`. The sandbox has network mode `none`, zero published ports and
its own labelled volume. No API, worker or funded AI consumer starts there.

The source summary and `pg_dump --snapshot` share one exported repeatable-read,
read-only snapshot. Product writes can continue while that consistent backup
is copied and verified. Original ownership and ACLs are retained. The restore
creates a credential-free `p50k_app` role, then checks its restored read access
and restrictions through `SET ROLE`. Global role/password dumps are not used.
Native database errors are captured and replaced with operation names, so
private data and credential-bearing database errors do not enter stdout.

## Actual run and retained artifacts

From `C:/Users/mirza/Desktop/Hackathon/project-50k-app`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/local/backup-restore-product.ps1
```

Exit 0. Final output:

```text
Backup/restore VERIFIED: p50k-20261010T155854Z-dc0e5ab0092e4a57bc67d72320deb3b9.dump; bytes=31708840; tables=34; migrations=8
```

The ignored dump and matching `.summary.json` remain under `backups/`.
Dump SHA-256:
`cf0d9570f46b91eec38e23dbebb9a53c6d2dbe378b219696a4674fe968a4f8c4`.
The private summary stores table counts, migration checksums, detector/AI row
checksums and immutable-trigger counts. It contains no data rows or credentials.

Representative restored counts matched the exact source snapshot:

| Table | Rows |
|---|---:|
| `ref.funds` | 2,133 |
| `obs.fund_prices` | 1,738,179 |
| `obs.fund_snapshots` | 3,304 |
| `obs.kap_documents` | 12,111 |
| `ref.stock_instruments` | 30 |
| `obs.stock_prices` | 870 |
| `obs.stock_actions` | 5 |
| `det.signals` | 34,128 |
| `det.detector_versions` | 1 |
| `ai.decisions` | 1 |
| `ai.chat_turns` | 3 |
| `auth.users` | 1 |

## Verification and operations

- All 34 table counts and eight migration hashes matched.
- Row checksums matched for every detector and AI table, including original
  packets, proposals, reviews, chat audit records, calls and budget records.
- Immutable-trigger registrations matched. Actual owner updates to restored
  evidence, AI proposals and stock prices were rejected with SQLSTATE `55000`.
- The restored application role could read evidence/proposals and had no
  superuser, database-creation, role-creation or RLS-bypass privilege.
- Restore network mode was `none`, with zero published ports.
- The script removed only its labelled restore container/volume and its own
  temporary dump inside the source container. Host backups remain intact.
- Git ignore checks passed for both retained artifacts. No secrets, `.env`
  files, raw inputs, frozen protocols or registered demo files were inspected
  or changed by the rehearsal.
- Product PostgreSQL remained healthy. Fallback listener processes remained
  27116 on 3060, 19280 on 8767 and 32216 on 8768.

PowerShell parser verification returned `PowerShell syntax OK`. The first launch
found a Windows native-argument quoting issue in the Docker label lookup before
any dump was created. JSON label parsing replaced that lookup; the corrected
script completed the actual rehearsal above. No synthetic tests were added to
mirror the script; the full restore was the meaningful verification.

To retain the isolated restored database for local inspection, pass
`-KeepRestore`. Its exact generated container/volume names are recorded in the
private summary. Cleanup is restricted to the run token labels and the
`p50k-restore-rehearsal-<token>` names. Never remove the product volume.

## Second actual run after final import and migrations 009/010

The first rehearsal above is retained as history. A second standard run from
the same `product/build` worktree captured the updated product database after
the final data import and Figma workflow migrations:

```powershell
& .\ops\local\backup-restore-product.ps1
```

Exit 0. Completed at `2026-10-10T17:11:15.4253906Z` (20:11 Istanbul).
Final output:

```text
Backup/restore VERIFIED: p50k-20261010T170943Z-0b862fc9099648388892a0a85f31e52a.dump; bytes=34400149; tables=38; migrations=10
```

Retained local artifacts under the ignored worktree `backups/` folder:

- `p50k-20261010T170943Z-0b862fc9099648388892a0a85f31e52a.dump`
- `p50k-20261010T170943Z-0b862fc9099648388892a0a85f31e52a.summary.json`

Dump SHA-256:
`37750467446b9fd07f40c27e301d673acdec36a8c92c5baf4f44fed469f5562f`.
The dump contains 34,400,149 bytes. All 38 table counts, all ten migration hashes,
detector/AI row checksums and immutable-trigger registrations matched the exact
exported source snapshot. Migrations `009_watchlist_notifications.sql` and
`010_evidence_feedback.sql` are included.

Representative restored counts for this second snapshot:

| Table | Rows |
|---|---:|
| `ref.funds` | 2,133 |
| `obs.fund_prices` | 1,755,010 |
| `obs.fund_snapshots` | 3,304 |
| `obs.kap_documents` | 12,111 |
| `ref.stock_instruments` | 30 |
| `obs.stock_prices` | 870 |
| `obs.stock_actions` | 5 |
| `det.signals` | 51,192 |
| `det.detector_versions` | 1 |
| `ai.decisions` | 2 |
| `ai.chat_turns` | 3 |
| `auth.users` | 1 |

Restored immutability and application-role permission checks passed. The restore
used network mode `none` with zero published ports. `KeepRestore` was false;
post-run Docker listings confirmed that this run's labelled restore container
and volume had been removed. Both retained artifact paths passed `git check-ignore`.
No other tests or fixture changes were performed during this rehearsal. The
same database-only recovery limitations below still apply.

## Release snapshot after migration 011 and startup-readiness correction

The first two verified runs above are preserved. After the updated product
release, the same standard command was run again:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/local/backup-restore-product.ps1
```

The first attempt retained
`p50k-20261010T180440Z-b9c7378c96cf441a9ca1fd518b09ee63.dump`, but failed while
creating the credential-free role in the isolated restore database. This dump
is **not verified** and has no successful restore summary. The product database
was not changed. The script's cleanup removed its isolated restore resources;
the dump was kept.

A standard retry succeeded without script changes:

```text
Backup/restore VERIFIED: p50k-20261010T180524Z-b73e0eb6106e4fdd912b448edd2072af.dump; bytes=34419954; tables=39; migrations=11
```

Its completion time was `2026-10-10T18:06:19.8501864Z`, with SHA-256
`0ff9804e5051c00985f49a101122b62924c81e5c7453f5711547945085a72763`.
The dump and matching `.summary.json` remain in ignored `backups/`.

The readiness race was then corrected with one command-argument change:
`pg_isready -h 127.0.0.1` now waits for the final PostgreSQL TCP listener inside
the isolated container. The pinned image's `/usr/local/bin/docker-entrypoint.sh`
was inspected read-only: line 297 starts its temporary initialization server
with `listen_addresses=''`, so a Unix-socket readiness probe could succeed
before normal startup was complete. Network mode remains `none`; no host port,
credential, ownership, restore or cleanup behavior was changed.

The updated script completed a further full dump/restore verification, exit 0:

```text
Backup/restore VERIFIED: p50k-20261010T180646Z-c6a0b94390324035849de26df9ea8875.dump; bytes=34419956; tables=39; migrations=11
```

Completed at `2026-10-10T18:07:36.7497218Z` (21:07 Istanbul). Latest verified
artifact SHA-256:
`71c3ec93fb8926265be29931a7d05392ca2e5df9f7c7122c7f01e3b0d5618c19`.
Both its dump and matching `.summary.json` are retained under ignored `backups/`.

All 39 table counts, eleven migration hashes, detector/AI row checksums and
immutable-trigger registrations matched the exported source snapshot in both
successful release runs. Their representative counts were identical:

| Table | Rows |
|---|---:|
| `ref.funds` | 2,133 |
| `obs.fund_prices` | 1,755,010 |
| `obs.fund_snapshots` | 3,304 |
| `obs.kap_documents` | 12,111 |
| `ref.stock_instruments` | 30 |
| `obs.stock_prices` | 870 |
| `obs.stock_actions` | 5 |
| `det.signals` | 51,192 |
| `det.detector_versions` | 1 |
| `ai.decisions` | 15 |
| `ai.chat_turns` | 6 |
| `ai.chat_stream_chunks` | 0 |
| `auth.users` | 1 |

Migration `011_chat_stream_chunks.sql` and its table/ACL definitions are included.
The table had no rows at the snapshot; its migration hash, trigger registration
and empty checksum matched. Populated paragraph restoration and a separate
application-role query against that table were not exercised.
The standard owner-update rejection checks for evidence, decisions and stock
prices and the restored application-role checks passed.

`KeepRestore` was false. After the corrected-script run, Docker listings showed
zero containers and zero volumes with that run's ownership label. The restore
had network mode `none` and zero published ports. Product ports remained present;
the fallback listener PIDs remained 27116/19280/32216 on 3060/8767/8768.
No secrets or data rows were printed, and no other test fixtures were mutated.
The remaining recovery limitations below still apply.

## Scope and remaining work

The backup carries the private DELAYED product data and immutable development
evidence. Data rights remain unreviewed; it stays on this machine. This is a
database rehearsal: original external raw archives and mounted secret files
remain required for complete product recovery. Application authentication,
browser behavior and cold boot against the restored database were not tested.
No scheduler or remote backup destination was created.

Repeat the script at the planned Sunday 11:00 backup after final data and review
changes. Then complete the freeze merge/tag and cold-boot/demo rehearsals.

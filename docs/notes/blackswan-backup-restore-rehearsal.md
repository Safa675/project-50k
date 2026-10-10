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

## Scope and remaining work

The backup carries the private DELAYED product data and immutable development
evidence. Data rights remain unreviewed; it stays on this machine. This is a
database rehearsal: original external raw archives and mounted secret files
remain required for complete product recovery. Application authentication,
browser behavior and cold boot against the restored database were not tested.
No scheduler or remote backup destination was created.

Repeat the script at the planned Sunday 11:00 backup after final data and review
changes. Then complete the freeze merge/tag and cold-boot/demo rehearsals.

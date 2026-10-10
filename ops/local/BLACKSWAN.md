# BlackSwan Phase 1 local operations

Run product commands from `project-50k-app` on `product/build`, never from the
dated demo clone. The original demo stays on 3060/8767/8768. Product web/API use
3070/8770. Real fund routes require session auth. AI defaults to off.

## Start the product

Start Docker Desktop, then from PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/docker/setup-secrets.ps1
docker compose config --no-interpolate --quiet
docker compose up --build -d --wait
```

The setup generates database credentials and an auth pepper locally without
printing values or overwriting existing files. The base stack does not require
an OpenAI key. Mirza alone places it in `secrets/openai_api_key`, never in chat.
`compose.ai.yaml` mounts that file only into API/worker and does not turn AI on.
Agents never read `.env*` or `secrets/`; runtime consumers read the mounted files.

Local admin: `mirza@blackswan.local`. Mirza can open ignored
`secrets/local-admin-login.json` manually for its generated password; agents never
inspect it. Visit `http://127.0.0.1:3070/login`, then fund pages and review.
There is no public signup or email service.

Check `http://127.0.0.1:3070/api/p/health/ready`. Product containers should be healthy;
`migrate` should have exited successfully. Add `-f compose.dev.yaml` only when
host PostgreSQL access on loopback 5433 is needed. Never remove the product volume.
Shutdown means `docker compose down`, without `-v`.

## Read-only archive import

Copy `compose.override.example.yaml` to the ignored `compose.override.yaml`,
then configure its four `P50K_INPUT_*` host paths. The archive and both SQLite
inputs must be stable; do not bind the actively collected overnight database.
No bind is writable and no raw data enters the Docker build context.

```powershell
docker compose run --rm worker python -m p50k.product.cli import-archive --raw-dir /inputs/raw --snapshot-db /inputs/snapshots-local.sqlite3 --snapshot-db /inputs/snapshots-forward.sqlite3 --event-map /inputs/spk-mapping.json
```

The existing Windows override already contains the correct paths. The importer
prints only aggregate counts and hashes; a repeat inserts no observations.
Changing input bytes during import, active SQLite journals or attachment revisions
without new list provenance fail closed. Missing NAV stays missing. Identity mapping checks are complete; confirmed versions retain unknown publication time and cannot trigger.

## Resume authorized downloads immediately

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/local/start-product-downloads.ps1 -ArchiveRoot C:/Users/mirza/Desktop/Hackathon/project-50k/raw -PythonExecutable C:/Users/mirza/Desktop/Hackathon/project-50k-app/.venv/Scripts/python.exe
```

The launcher discovers the existing snapshot processes before any TEFAS request.
Profiles then prices share one coordinator. KAP/SPK use independent paced streams;
per-host locks prevent duplicate launches. All output is external:
`C:/Users/mirza/.local/share/project-50k/overnight/2026-10-10/`.
Status JSON is under `status/`; request provenance and error classes are under
`logs/`. Three consecutive failures stop a runner. Resume with the same command;
verified downloads are retained. The machine must remain on and online.

## Isolated verification

`ops/docker/check-smoke.ps1` uses only the `p50k-smoke` project, `p50k_dev` database,
3071/8771 and its own synthetic volume. Its test endpoints cannot be enabled in
the real-data database. The script may remove only that synthetic volume.
Product/archive counts, exact checks and limitations are in
[`blackswan-phase1-completion.md`](../../docs/notes/blackswan-phase1-completion.md).

Verify registered paths before pulling remote `main` into the load-bearing main checkout during the demo.
Continue in the product worktree; decoupling the demo remains K4 after the event.

## Live AI and completed-download refresh

The key is supplied in the ignored `secrets/openai_api_key` file. Runtime checks
passed; the current product runs live on-demand AI under existing budgets. To
recreate that configuration, use all current local overlays:

```powershell
$env:P50K_AI_MODE='live'
docker compose -f compose.yaml -f compose.override.yaml -f compose.dev.yaml -f compose.ai.yaml up -d --no-build --wait
```

After remaining downloads complete, run the incremental importer (read-only inputs):

```powershell
docker compose -f compose.yaml run --rm --no-deps --volume C:/Users/mirza/.local/share/project-50k/overnight/2026-10-10:/inputs/overnight:ro worker python -m p50k.product.overnight_import --overnight-dir /inputs/overnight
```

It preserves the fixed fund/category universe and admits revisions conservatively.
Run detectors afterward with the existing calibration; never recalibrate silently.
The final tuning/batch gate, stocks and freeze rehearsals remain outstanding.
See [chat/refresh completion](../../docs/notes/blackswan-chat-refresh-completion.md).

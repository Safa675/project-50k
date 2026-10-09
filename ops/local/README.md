# Local archived research runner

Install dependencies explicitly from the repository root. `uv.lock` is the
resolved Python dependency lock; the core package keeps no third-party runtime
dependencies. API dependencies and their tests use a separate ignored `.venv`.

```sh
uv sync --frozen --extra api --extra api-test --extra research --python /home/safa/miniforge3/bin/python3
cd frontend
npm ci
```

The locked install prepares the local PDF.js worker, fonts and decoders.
The direct launcher verifies these assets before starting either app process.
If install scripts were disabled, explicitly run `npm run prepare:pdfjs` from
`frontend/`. Asset preparation copies installed package files without downloads.

Select the **exact** existing sealed bundle directory. Raw data is private and
absent from Git. The launcher refuses missing or corrupt bundles, changed
originals, changed PDF copies, occupied ports and uninstalled dependencies.
It never selects the newest bundle, collects data, recalibrates, builds or
installs anything automatically.

```sh
# From the repository root; replace <fingerprint> with the selected bundle ID.
.venv/bin/python ops/local/run_app.py --bundle raw/research/fund-review-app/<fingerprint> --check
.venv/bin/python ops/local/run_app.py --bundle raw/research/fund-review-app/<fingerprint>
```

The frontend is at `http://127.0.0.1:3060`; API health is at
`http://127.0.0.1:8767/research/v1/health`. Both listeners bind to loopback only.
`--api-port` and `--frontend-port` allow isolated alternative ports.
`--api-only` omits the UI. Ctrl+C stops the child processes started by the
launcher. No systemd service or production authentication is modified.

For a built frontend, build explicitly and then choose production mode:

```sh
# In frontend/
NEXT_TELEMETRY_DISABLED=1 npm run build
# Back in the repository root
.venv/bin/python ops/local/run_app.py --bundle raw/research/fund-review-app/<fingerprint> --mode production
```

All requests use the same fixed cutoff and immutable bundle. JSON errors use a
null `immutable_bundle_id` when no bundle can be authenticated. Successful PDFs
bind the bundle and cutoff in `X-Research-Bundle-Id` and
`X-Research-Cutoff-At` headers; they retain `no-store` like JSON and errors.
Source requests accept opaque manifest IDs only. No arbitrary paths or URLs are
accepted. Unknown rights and historical availability remain unknown.

Run the optional API acceptance tests in the locked environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest tests.unit.test_research_api -v
```

API tests use Starlette's currently supported `httpx2` TestClient dependency.
The standard-library environment explicitly skips API tests if optional
dependencies are absent; skips are not a passing API verification. Dependencies
were resolved against the official [FastAPI](https://fastapi.tiangolo.com/),
[Pydantic strict-mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)
and [Starlette TestClient](https://starlette.dev/testclient/) documentation.
NumPy stays at the original detector environment's `2.4.6` version.

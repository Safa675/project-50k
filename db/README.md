# BlackSwan PostgreSQL foundations

T1.4 implements DEC-028 and the plan's provenance, immutable evidence, and human-review rules.
The `p50k_owner` migration role owns every table. `p50k_app` imports through staging and
`INSERT ... ON CONFLICT DO NOTHING`; it cannot update or delete observations, evidence,
packets, decisions, reviews, or audit entries. Triggers also reject those mutations by the owner.
Authentication sessions, job leases, import summaries, and worker heartbeats are operational
records and may change. Migration files are UTF-8 LF bytes, checked by SHA-256 on every run.

The runner is `python -m p50k.product.migrate`, using owner credentials from
`P50K_DB_PASSWORD_FILE` and the application credential from `P50K_APP_PASSWORD_FILE`.
The API, worker, and importer use the application's own credential. Credentials are read by
runtime code; the runner reports error classes only. The database `p50k` rejects mock AI and
synthetic observations; the separate `p50k_dev` database permits synthetic integration tests.

## Archive importer contract

Every observation includes `source_id`, `source_version`, `source_sha256`, `origin`, `unit`,
`published_at`, `available_at`, `observed_at`, `ingested_at`, `availability_rule`,
`rights_status`, and `metadata` (JSONB). Only `ingested_at` defaults to the actual database
clock. Unknown source timestamps remain NULL. Table-specific defaults identify the provider
and unit; the importer supplies the actual hash, availability rule, and origin.

| Table | Additional columns | Identity |
|---|---|---|
| `ref.sources` | `source_id`, `label`, `rights_status`, `metadata` | `source_id` |
| `ref.funds` | `fund_code`, `name`, `category`, `tefas_status`, `listing_as_of`, `source_id`, `source_sha256`, `observed_at`, `metadata` | `fund_code` |
| `obs.fund_prices` | `fund_code`, `effective_date` DATE, `nav` NUMERIC nullable | fund, date, source, hash |
| `obs.fund_snapshots` | `fund_code`, `snapshot_key`, `effective_date` DATE nullable, `nav`, `total_value`, `units_outstanding`, `investors`, `daily_return_pct` | fund, snapshot key, source, hash |
| `obs.kap_documents` | `document_key` (`code:disclosure_index`), `fund_code`, `report_period` TEXT nullable, `relative_path` nullable | document key, source, hash |
| `obs.kap_series` | `fund_code`, `series_key`, `report_period` TEXT, `cadence` monthly/weekly, `document_key` nullable | fund, series key, source, hash |
| `obs.regulatory_events` | `event_id`, `fund_code`, `event_type`, `effective_date` DATE nullable, `status`, `confirmed_by`, `confirmed_at`, `quotation` | event ID, source, hash, status |
| `obs.ingest_runs` | `run_id` UUID, `archive_sha256`, `started_at`, `finished_at`, `status`, `counts`, `error_class` | run ID |

`report_period` accepts an original monthly (`YYYY-MM`) or weekly (`YYYY-WNN`) label;
it is not converted to an invented date. `kap_series` is one row per report, with original
parsed values retained in `metadata`. Document metadata retains cadence and the PDF/hash
listing, and a missing PDF has no invented path. Snapshot `observed_at` is the original
retrieval time; metadata retains the original category and consistency checks. Fund-list
metadata records that category/status/membership describe the retrieved current list only.
The bulletin's known date does not manufacture an exact `published_at` timestamp.

Zero and non-finite NAV are forbidden: the importer converts provider zero to NULL. Price
currency is labelled unreported until supported by its own source. Numeric values use
PostgreSQL NUMERIC and Python Decimal. Reruns retain missing values and old source versions.
Regulatory confirmation appends a new `CONFIRMED` version beside a `CANDIDATE`; it requires
the actor and confirmation time. Other metadata, including source URLs and mapping methods,
lives in the observation's JSONB metadata.

`ops.worker_heartbeats(worker_id, last_seen_at, status, details)` is the worker health
contract. `ops.schema_migrations(filename, sha256, applied_at)` belongs only to the owner.

## Decision groundwork

Model decisions retain their model, prompt/schema versions, AI mode, packet hash, call ID,
and creation time. Human reviews remain beside the original decisions. The
`ai.effective_decisions` view selects the latest human review for the latest packet across
single and team methods. Rejection yields `UNDECIDED`; a newer AI result cannot displace
that review. A changed packet yields `UNDECIDED` until evaluated and reports whether an
older packet has a human review. Current values are separate for each origin/replay cutoff,
so creating a historical replay packet cannot replace the current published-data view.
This storage does not implement the Phase 3 validator,
decision engine, or authentication endpoints.

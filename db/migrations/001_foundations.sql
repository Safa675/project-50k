-- T1.4: provider provenance and durable operational records.
CREATE SCHEMA ref;
CREATE SCHEMA obs;
CREATE SCHEMA det;
CREATE SCHEMA ai;
CREATE SCHEMA auth;
CREATE SCHEMA b2b;
-- ops is created by the checksum-tracking migration runner.

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA ref, obs, det, ai, auth, b2b, ops FROM PUBLIC;
GRANT USAGE ON SCHEMA ref, obs, det, ai, auth, b2b, ops TO p50k_app;

CREATE DOMAIN ref.sha256 AS TEXT
    CHECK (VALUE ~ '^[a-f0-9]{64}$');
CREATE DOMAIN ref.data_origin AS TEXT
    CHECK (VALUE IN ('LIVE', 'DELAYED', 'HISTORICAL_REPLAY', 'SYNTHETIC'));

CREATE TABLE ref.sources (
    source_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    rights_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ref.sources (source_id, label) VALUES
    ('TEFAS', 'TEFAS'), ('KAP', 'KAP'), ('SPK', 'SPK');

CREATE TABLE ref.funds (
    fund_code TEXT PRIMARY KEY CHECK (fund_code ~ '^[A-Z0-9]{2,12}$'),
    name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
    category TEXT,
    tefas_status TEXT,
    listing_as_of DATE,
    source_id TEXT NOT NULL DEFAULT 'TEFAS' REFERENCES ref.sources(source_id),
    source_sha256 ref.sha256 NOT NULL,
    observed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE obs.fund_prices (
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    effective_date DATE NOT NULL,
    nav NUMERIC CHECK (nav > 0 AND nav NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC)),
    source_id TEXT NOT NULL DEFAULT 'TEFAS' REFERENCES ref.sources(source_id),
    source_version TEXT NOT NULL DEFAULT 'archive-v1',
    source_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    unit TEXT NOT NULL DEFAULT 'NAV/unit (currency unreported)',
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    availability_rule TEXT NOT NULL,
    rights_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (fund_code, effective_date, source_id, source_sha256)
);
CREATE INDEX fund_prices_available_idx ON obs.fund_prices (fund_code, available_at);

CREATE TABLE obs.fund_snapshots (
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    snapshot_key TEXT NOT NULL,
    effective_date DATE,
    nav NUMERIC CHECK (nav > 0 AND nav NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC)),
    total_value NUMERIC CHECK (total_value >= 0 AND total_value NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC)),
    units_outstanding NUMERIC CHECK (units_outstanding >= 0 AND units_outstanding NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC)),
    investors BIGINT CHECK (investors >= 0),
    daily_return_pct NUMERIC CHECK (daily_return_pct NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC, '-Infinity'::NUMERIC)),
    source_id TEXT NOT NULL DEFAULT 'TEFAS' REFERENCES ref.sources(source_id),
    source_version TEXT NOT NULL DEFAULT 'archive-v1',
    source_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    unit TEXT NOT NULL DEFAULT 'TRY total value; units outstanding; investors; NAV currency unreported',
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    availability_rule TEXT NOT NULL,
    rights_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (fund_code, snapshot_key, source_id, source_sha256)
);

CREATE TABLE obs.kap_documents (
    document_key TEXT NOT NULL,
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    report_period TEXT,
    relative_path TEXT,
    source_id TEXT NOT NULL DEFAULT 'KAP' REFERENCES ref.sources(source_id),
    source_version TEXT NOT NULL DEFAULT 'archive-v1',
    source_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    unit TEXT NOT NULL DEFAULT 'document',
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    availability_rule TEXT NOT NULL,
    rights_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (document_key, source_id, source_sha256),
    CHECK (report_period IS NULL OR report_period ~ '^[0-9]{4}-(0[1-9]|1[0-2]|W(0[1-9]|[1-4][0-9]|5[0-3]))$')
);

CREATE TABLE obs.kap_series (
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    series_key TEXT NOT NULL,
    report_period TEXT NOT NULL,
    cadence TEXT NOT NULL CHECK (cadence IN ('monthly', 'weekly')),
    document_key TEXT,
    source_id TEXT NOT NULL DEFAULT 'KAP' REFERENCES ref.sources(source_id),
    source_version TEXT NOT NULL DEFAULT 'archive-v1',
    source_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    unit TEXT NOT NULL DEFAULT 'report',
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    availability_rule TEXT NOT NULL,
    rights_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (fund_code, series_key, source_id, source_sha256),
    CHECK ((cadence = 'monthly' AND report_period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$')
        OR (cadence = 'weekly' AND report_period ~ '^[0-9]{4}-W(0[1-9]|[1-4][0-9]|5[0-3])$'))
);

CREATE TABLE obs.regulatory_events (
    event_id TEXT NOT NULL,
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    event_type TEXT NOT NULL,
    effective_date DATE,
    status TEXT NOT NULL DEFAULT 'CANDIDATE' CHECK (status IN ('CANDIDATE', 'CONFIRMED')),
    confirmed_by TEXT,
    confirmed_at TIMESTAMPTZ,
    quotation TEXT,
    source_id TEXT NOT NULL DEFAULT 'SPK' REFERENCES ref.sources(source_id),
    source_version TEXT NOT NULL DEFAULT 'archive-v1',
    source_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    unit TEXT NOT NULL DEFAULT 'event',
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    availability_rule TEXT NOT NULL,
    rights_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (event_id, source_id, source_sha256, status),
    CHECK ((status = 'CONFIRMED' AND confirmed_by IS NOT NULL
        AND length(btrim(confirmed_by)) > 0 AND confirmed_at IS NOT NULL)
        OR (status = 'CANDIDATE' AND confirmed_by IS NULL AND confirmed_at IS NULL))
);

CREATE TABLE obs.ingest_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    archive_sha256 ref.sha256 NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED')),
    counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_class TEXT,
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX ingest_runs_archive_idx ON obs.ingest_runs (archive_sha256, started_at);

CREATE TABLE auth.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE CHECK (email = lower(btrim(email))),
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'analyst', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    disabled_at TIMESTAMPTZ
);
CREATE TABLE auth.sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id),
    token_sha256 ref.sha256 NOT NULL UNIQUE,
    csrf_sha256 ref.sha256 NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CHECK (expires_at > created_at)
);
CREATE INDEX sessions_user_idx ON auth.sessions (user_id);
CREATE TABLE auth.login_attempts (
    attempt_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email_sha256 ref.sha256 NOT NULL,
    ip_sha256 ref.sha256 NOT NULL,
    succeeded BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX login_attempts_email_idx ON auth.login_attempts (email_sha256, created_at);
CREATE INDEX login_attempts_ip_idx ON auth.login_attempts (ip_sha256, created_at);

CREATE TABLE ops.worker_heartbeats (
    worker_id TEXT PRIMARY KEY,
    last_seen_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE ops.jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'READY' CHECK (status IN ('READY', 'RUNNING', 'SUCCEEDED', 'FAILED')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    available_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    lease_until TIMESTAMPTZ,
    error_class TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX jobs_claim_idx ON ops.jobs (available_at, created_at) WHERE status = 'READY';
CREATE TABLE ops.audit_log (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    action TEXT NOT NULL,
    actor_id UUID REFERENCES auth.users(user_id),
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION ops.reject_immutable_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Immutable record cannot be changed' USING ERRCODE = '55000';
END;
$$;
CREATE FUNCTION ops.guard_synthetic_origin() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.origin = 'SYNTHETIC' AND current_database() <> 'p50k_dev' THEN
        RAISE EXCEPTION 'Synthetic observations require p50k_dev' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DO $$
DECLARE table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['fund_prices', 'fund_snapshots', 'kap_documents', 'kap_series', 'regulatory_events'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON obs.%I FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON obs.%I FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER synthetic_origin_guard BEFORE INSERT ON obs.%I FOR EACH ROW EXECUTE FUNCTION ops.guard_synthetic_origin()', table_name);
    END LOOP;
END;
$$;
CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON ops.audit_log
    FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change();
CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON ops.audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change();

GRANT SELECT, INSERT ON ref.sources, ref.funds TO p50k_app;
GRANT SELECT, INSERT ON obs.fund_prices, obs.fund_snapshots, obs.kap_documents,
    obs.kap_series, obs.regulatory_events, ops.audit_log TO p50k_app;
GRANT SELECT, INSERT, UPDATE ON obs.ingest_runs, ops.jobs, ops.worker_heartbeats TO p50k_app;
GRANT SELECT ON auth.users TO p50k_app;
GRANT INSERT (email, password_hash) ON auth.users TO p50k_app;
GRANT SELECT, INSERT ON auth.login_attempts TO p50k_app;
GRANT UPDATE (password_hash, disabled_at) ON auth.users TO p50k_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON auth.sessions TO p50k_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auth, ops TO p50k_app;
GRANT SELECT ON ops.schema_migrations TO p50k_app;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA ops FROM PUBLIC;

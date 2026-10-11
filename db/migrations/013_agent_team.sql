-- DEC-035: the always-on agent team. Cases, tasks and their leases are operational
-- records; agent messages, sentinel scans and user requests are append-only.
CREATE SCHEMA agents;
REVOKE ALL ON SCHEMA agents FROM PUBLIC;
GRANT USAGE ON SCHEMA agents TO p50k_app;

CREATE TABLE agents.cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_scope_key TEXT NOT NULL
        CHECK (analysis_scope_key ~ '^(live|asof:[0-9]{4}-[0-9]{2}-[0-9]{2})$'),
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    opened_by TEXT NOT NULL CHECK (opened_by IN ('sentinel', 'user')),
    requested_by UUID REFERENCES auth.users(user_id),
    priority INTEGER NOT NULL DEFAULT 0 CHECK (priority BETWEEN 0 AND 100),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'investigating', 'reported', 'closed')),
    detector_run_id UUID NOT NULL REFERENCES det.detector_runs(run_id),
    packet_sha256 ref.sha256,
    decision_id BIGINT REFERENCES ai.decisions(decision_id),
    title_tr TEXT NOT NULL CHECK (length(btrim(title_tr)) BETWEEN 1 AND 240),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    started_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    CHECK ((status = 'closed') = (closed_at IS NOT NULL)),
    CHECK (status = 'open' OR started_at IS NOT NULL OR status = 'closed')
);
-- One case that is not closed per analysis view and fund.
CREATE UNIQUE INDEX cases_one_active_idx ON agents.cases (analysis_scope_key, fund_code)
    WHERE status <> 'closed';
CREATE INDEX cases_scope_idx ON agents.cases (analysis_scope_key, status, priority DESC, opened_at);
CREATE INDEX cases_started_idx ON agents.cases (started_at DESC) WHERE started_at IS NOT NULL;

CREATE TABLE agents.tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES agents.cases(case_id),
    role TEXT NOT NULL CHECK (role IN ('sentinel', 'hypothesizer', 'skeptic', 'verifier', 'reporter')),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'done', 'failed', 'waiting_budget', 'skipped')),
    priority INTEGER NOT NULL DEFAULT 0 CHECK (priority BETWEEN 0 AND 100),
    source TEXT NOT NULL CHECK (source IN ('system', 'user')),
    requested_by UUID REFERENCES auth.users(user_id),
    depends_on UUID[] NOT NULL DEFAULT '{}' CHECK (cardinality(depends_on) <= 4),
    title_tr TEXT NOT NULL CHECK (length(btrim(title_tr)) BETWEEN 1 AND 240),
    not_before TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    lease_owner TEXT,
    lease_until TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 10),
    call_id TEXT,
    cost_usd NUMERIC CHECK (cost_usd >= 0 AND cost_usd NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC)),
    error_class TEXT CHECK (error_class IS NULL OR error_class ~ '^[A-Za-z][A-Za-z0-9_]{1,63}$'),
    UNIQUE (case_id, role),
    CHECK ((status = 'running') = (lease_owner IS NOT NULL AND lease_until IS NOT NULL))
);
CREATE INDEX tasks_claim_idx ON agents.tasks (priority DESC, created_at)
    WHERE status IN ('queued', 'waiting_budget', 'running');
CREATE INDEX tasks_case_idx ON agents.tasks (case_id, role);
CREATE INDEX tasks_finished_idx ON agents.tasks (finished_at DESC) WHERE finished_at IS NOT NULL;

CREATE TABLE agents.messages (
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES agents.cases(case_id),
    task_id UUID REFERENCES agents.tasks(task_id),
    from_role TEXT NOT NULL
        CHECK (from_role IN ('sentinel', 'hypothesizer', 'skeptic', 'verifier', 'reporter')),
    to_role TEXT NOT NULL
        CHECK (to_role IN ('sentinel', 'hypothesizer', 'skeptic', 'verifier', 'reporter', 'team', 'human')),
    kind TEXT NOT NULL CHECK (kind IN ('case_opened', 'hypothesis', 'counter', 'test_plan', 'test_result',
        'verification', 'report', 'handoff', 'note')),
    -- Validated, server-rendered text only; never raw model output.
    body_tr TEXT NOT NULL CHECK (length(btrim(body_tr)) BETWEEN 1 AND 6000),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
    model_id TEXT,
    prompt_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK ((model_id IS NULL) = (prompt_version IS NULL)),
    CHECK (from_role <> to_role)
);
CREATE INDEX messages_case_idx ON agents.messages (case_id, message_id);
CREATE INDEX messages_recent_idx ON agents.messages (created_at DESC, message_id DESC);

CREATE TABLE agents.sentinel_scans (
    scan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_scope_key TEXT NOT NULL
        CHECK (analysis_scope_key ~ '^(live|asof:[0-9]{4}-[0-9]{2}-[0-9]{2})$'),
    detector_run_id UUID REFERENCES det.detector_runs(run_id),
    funds_scanned INTEGER NOT NULL CHECK (funds_scanned >= 0),
    cases_opened INTEGER NOT NULL CHECK (cases_opened >= 0),
    cases_refreshed INTEGER NOT NULL DEFAULT 0 CHECK (cases_refreshed >= 0),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    CHECK (finished_at >= started_at)
);
CREATE INDEX sentinel_scans_scope_idx ON agents.sentinel_scans (analysis_scope_key, finished_at DESC);

-- Rate limits and analysis-view activity. Page visits are recorded at most once
-- per user, view and short interval; investigation requests are bounded per hour.
CREATE TABLE agents.requests (
    request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(user_id),
    analysis_scope_key TEXT NOT NULL
        CHECK (analysis_scope_key ~ '^(live|asof:[0-9]{4}-[0-9]{2}-[0-9]{2})$'),
    fund_code TEXT REFERENCES ref.funds(fund_code),
    kind TEXT NOT NULL CHECK (kind IN ('investigate', 'page_visit')),
    case_id UUID REFERENCES agents.cases(case_id),
    outcome TEXT NOT NULL CHECK (outcome IN ('opened', 'raised', 'unchanged', 'activity')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (kind <> 'investigate' OR fund_code IS NOT NULL)
);
CREATE INDEX requests_user_idx ON agents.requests (user_id, kind, created_at DESC);
CREATE INDEX requests_recent_idx ON agents.requests (created_at DESC);

CREATE FUNCTION agents.guard_case_update() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.case_id <> OLD.case_id OR NEW.analysis_scope_key <> OLD.analysis_scope_key
            OR NEW.fund_code <> OLD.fund_code OR NEW.opened_by <> OLD.opened_by
            OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
            OR NEW.opened_at <> OLD.opened_at OR OLD.status = 'closed'
            OR (OLD.decision_id IS NOT NULL AND NEW.decision_id IS DISTINCT FROM OLD.decision_id)
            OR (OLD.packet_sha256 IS NOT NULL AND NEW.packet_sha256 IS DISTINCT FROM OLD.packet_sha256
                AND NEW.detector_run_id = OLD.detector_run_id) THEN
        RAISE EXCEPTION 'Agent case identity, closure or filed decision cannot change' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION agents.guard_task_update() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.task_id <> OLD.task_id OR NEW.case_id <> OLD.case_id OR NEW.role <> OLD.role
            OR NEW.created_at <> OLD.created_at OR NEW.depends_on <> OLD.depends_on
            OR (OLD.status = 'done' AND NEW.status <> 'done') THEN
        RAISE EXCEPTION 'Agent task identity or completed state cannot change' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION agents.guard_synthetic_message() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.model_id = 'synthetic' AND current_database() <> 'p50k_dev' THEN
        RAISE EXCEPTION 'Synthetic agent output requires p50k_dev' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER case_update_guard BEFORE UPDATE ON agents.cases
    FOR EACH ROW EXECUTE FUNCTION agents.guard_case_update();
CREATE TRIGGER task_update_guard BEFORE UPDATE ON agents.tasks
    FOR EACH ROW EXECUTE FUNCTION agents.guard_task_update();
CREATE TRIGGER synthetic_message_guard BEFORE INSERT ON agents.messages
    FOR EACH ROW EXECUTE FUNCTION agents.guard_synthetic_message();

DO $$
DECLARE table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['cases', 'tasks'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_delete BEFORE DELETE ON agents.%I FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON agents.%I FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
    END LOOP;
    FOREACH table_name IN ARRAY ARRAY['messages', 'sentinel_scans', 'requests'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON agents.%I FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON agents.%I FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
    END LOOP;
END;
$$;

GRANT SELECT, INSERT, UPDATE ON agents.cases, agents.tasks TO p50k_app;
GRANT SELECT, INSERT ON agents.messages, agents.sentinel_scans, agents.requests TO p50k_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA agents TO p50k_app;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA agents FROM PUBLIC;

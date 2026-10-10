-- Local AI reservations and leases; prompts and secrets never enter job errors.
CREATE TABLE ai.budget_buckets (
    bucket TEXT PRIMARY KEY,
    cap_usd NUMERIC NOT NULL CHECK (cap_usd >= 0),
    spent_usd NUMERIC NOT NULL DEFAULT 0 CHECK (spent_usd >= 0),
    reserved_usd NUMERIC NOT NULL DEFAULT 0 CHECK (reserved_usd >= 0),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (spent_usd + reserved_usd <= cap_usd)
);
INSERT INTO ai.budget_buckets(bucket,cap_usd,enabled) VALUES
    ('tuning',1,true),('batch',5,true),('team',3,true),('chat',5,true),
    ('reserve',5,false),('unallocated',1,false);
CREATE TABLE ai.reservations (
    reservation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket TEXT NOT NULL REFERENCES ai.budget_buckets(bucket),
    amount_usd NUMERIC NOT NULL CHECK (amount_usd > 0),
    expires_at TIMESTAMPTZ NOT NULL,
    settled_at TIMESTAMPTZ,
    settled_usd NUMERIC,
    CHECK (settled_usd IS NULL OR settled_usd BETWEEN 0 AND amount_usd)
);
CREATE TABLE ai.calls (
    call_id TEXT PRIMARY KEY,
    reservation_id UUID REFERENCES ai.reservations(reservation_id),
    model_id TEXT NOT NULL,
    ai_mode TEXT NOT NULL CHECK (ai_mode IN ('off','mock','live')),
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
    output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
    cost_usd NUMERIC NOT NULL CHECK (cost_usd >= 0),
    outcome TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON ai.calls
    FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change();
CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON ai.calls
    FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change();
CREATE TRIGGER mock_ai_guard BEFORE INSERT ON ai.calls
    FOR EACH ROW EXECUTE FUNCTION ops.guard_mock_ai();

ALTER TABLE ops.jobs ADD COLUMN lease_owner TEXT;
ALTER TABLE ops.jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 5);
ALTER TABLE ops.jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 10;
CREATE INDEX jobs_lease_idx ON ops.jobs(lease_until) WHERE status='RUNNING';

CREATE TABLE ai.chat_threads (
    thread_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id),
    fund_code TEXT REFERENCES ref.funds(fund_code),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE ai.chat_messages (
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    thread_id UUID NOT NULL REFERENCES ai.chat_threads(thread_id),
    role TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL,
    evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
GRANT SELECT, INSERT, UPDATE ON ai.budget_buckets,ai.reservations TO p50k_app;
GRANT SELECT, INSERT ON ai.calls,ai.chat_threads,ai.chat_messages TO p50k_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA ai TO p50k_app;

-- Append-only owner-scoped chat usage and evidence provenance.
CREATE TABLE ai.chat_turns (
    turn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES ai.chat_threads(thread_id),
    user_id UUID NOT NULL REFERENCES auth.users(user_id),
    packet_sha256 TEXT NOT NULL CHECK (packet_sha256 ~ '^[a-f0-9]{64}$'),
    packet JSONB NOT NULL,
    run_id UUID NOT NULL REFERENCES det.detector_runs(run_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX chat_user_day_idx ON ai.chat_turns(user_id,created_at);
CREATE TABLE ai.chat_results (
    turn_id UUID PRIMARY KEY REFERENCES ai.chat_turns(turn_id),
    outcome TEXT NOT NULL CHECK (outcome IN ('VALID','FAILED')),
    error_code TEXT,
    model_id TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    call_ids JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK ((outcome='VALID' AND error_code IS NULL) OR (outcome='FAILED' AND error_code IS NOT NULL))
);
DO $$
DECLARE table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['chat_threads','chat_messages','chat_turns','chat_results'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON ai.%I FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON ai.%I FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
    END LOOP;
END $$;
GRANT SELECT,INSERT ON ai.chat_turns,ai.chat_results TO p50k_app;

-- T1.4: immutable detector evidence and AI decisions with human precedence.
CREATE TABLE det.detector_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_version TEXT NOT NULL,
    protocol_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    cutoff TIMESTAMPTZ,
    development_result BOOLEAN NOT NULL DEFAULT TRUE CHECK (development_result),
    parameters JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (origin <> 'HISTORICAL_REPLAY' OR cutoff IS NOT NULL)
);
CREATE TABLE det.evidence_items (
    evidence_id TEXT PRIMARY KEY,
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    run_id UUID REFERENCES det.detector_runs(run_id),
    detector_id TEXT NOT NULL,
    origin ref.data_origin NOT NULL,
    effective_date DATE,
    available_at TIMESTAMPTZ,
    unit TEXT NOT NULL,
    values JSONB NOT NULL,
    thresholds JSONB NOT NULL DEFAULT '{}'::jsonb,
    triggered BOOLEAN,
    state TEXT NOT NULL,
    source_references JSONB NOT NULL,
    development_result BOOLEAN NOT NULL DEFAULT TRUE CHECK (development_result),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX evidence_fund_idx ON det.evidence_items (fund_code, created_at);

CREATE TABLE ai.packets (
    packet_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    decision_type TEXT NOT NULL DEFAULT 'MATERIALITY',
    packet_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    as_of DATE,
    cutoff TIMESTAMPTZ,
    payload JSONB NOT NULL,
    allowed_options JSONB NOT NULL,
    -- Packets are deterministic records, rather than model-generated text.
    model_id TEXT NOT NULL DEFAULT 'deterministic',
    prompt_version TEXT NOT NULL DEFAULT 'packet-builder-v1',
    schema_version TEXT NOT NULL DEFAULT 'packet-v1',
    ai_mode TEXT NOT NULL DEFAULT 'off' CHECK (ai_mode IN ('off', 'live', 'mock')),
    call_id TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (fund_code, decision_type, packet_sha256),
    UNIQUE (packet_id, fund_code, decision_type, packet_sha256),
    CHECK (origin <> 'HISTORICAL_REPLAY' OR cutoff IS NOT NULL),
    CHECK (jsonb_typeof(allowed_options) = 'array'
        AND jsonb_array_length(allowed_options) BETWEEN 1 AND 4
        AND allowed_options <@ '["MATERIAL", "NOT_MATERIAL", "DATA_ISSUE", "INSUFFICIENT_EVIDENCE"]'::jsonb)
);

CREATE TABLE ai.decisions (
    decision_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    packet_id BIGINT NOT NULL,
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    decision_type TEXT NOT NULL DEFAULT 'MATERIALITY',
    packet_sha256 ref.sha256 NOT NULL,
    decision_value TEXT CHECK (decision_value IN ('MATERIAL', 'NOT_MATERIAL', 'DATA_ISSUE', 'INSUFFICIENT_EVIDENCE')),
    validation_state TEXT NOT NULL CHECK (validation_state IN ('VALID', 'INVALID')),
    evidence_ids JSONB NOT NULL,
    rationale TEXT,
    output JSONB,
    model_id TEXT NOT NULL CHECK (length(btrim(model_id)) > 0),
    prompt_version TEXT NOT NULL CHECK (length(btrim(prompt_version)) > 0),
    schema_version TEXT NOT NULL CHECK (length(btrim(schema_version)) > 0),
    ai_mode TEXT NOT NULL CHECK (ai_mode IN ('off', 'live', 'mock')),
    effort TEXT NOT NULL DEFAULT 'none',
    method TEXT NOT NULL DEFAULT 'SINGLE' CHECK (method IN ('SINGLE', 'TEAM')),
    call_id TEXT NOT NULL CHECK (length(btrim(call_id)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (packet_id, fund_code, decision_type, packet_sha256)
        REFERENCES ai.packets (packet_id, fund_code, decision_type, packet_sha256),
    UNIQUE (decision_id, packet_sha256),
    CHECK (jsonb_typeof(evidence_ids) = 'array'),
    CHECK (validation_state <> 'VALID' OR decision_value IS NOT NULL)
);
CREATE INDEX decisions_packet_idx ON ai.decisions (packet_id, created_at, decision_id);

CREATE TABLE ai.decision_reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    decision_id BIGINT NOT NULL,
    packet_sha256 ref.sha256 NOT NULL,
    field_name TEXT NOT NULL DEFAULT 'decision_value',
    action TEXT NOT NULL CHECK (action IN ('ACCEPT', 'OVERRIDE', 'REJECT')),
    override_value TEXT CHECK (override_value IN ('MATERIAL', 'NOT_MATERIAL', 'DATA_ISSUE', 'INSUFFICIENT_EVIDENCE')),
    reason TEXT,
    reviewer_id UUID NOT NULL REFERENCES auth.users(user_id),
    model_id TEXT NOT NULL DEFAULT 'human',
    prompt_version TEXT NOT NULL DEFAULT 'human-review-v1',
    schema_version TEXT NOT NULL DEFAULT 'review-v1',
    ai_mode TEXT NOT NULL DEFAULT 'off' CHECK (ai_mode = 'off'),
    call_id TEXT NOT NULL DEFAULT gen_random_uuid()::text,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (decision_id, packet_sha256) REFERENCES ai.decisions (decision_id, packet_sha256),
    CHECK ((action = 'OVERRIDE' AND override_value IS NOT NULL
        AND reason IS NOT NULL AND length(btrim(reason)) > 0)
        OR (action = 'ACCEPT' AND override_value IS NULL)
        OR (action = 'REJECT' AND override_value IS NULL
        AND reason IS NOT NULL AND length(btrim(reason)) > 0))
);
CREATE INDEX decision_reviews_decision_idx ON ai.decision_reviews (decision_id, created_at, review_id);

CREATE FUNCTION ops.guard_mock_ai() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.ai_mode = 'mock' AND current_database() <> 'p50k_dev' THEN
        RAISE EXCEPTION 'Mock AI records require p50k_dev' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION ai.guard_allowed_decision() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE options JSONB;
BEGIN
    IF NEW.validation_state = 'VALID' THEN
        SELECT allowed_options INTO options FROM ai.packets WHERE packet_id = NEW.packet_id;
        IF NOT (options ? NEW.decision_value) THEN
            RAISE EXCEPTION 'Decision is not allowed by its evidence packet' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DO $$
DECLARE table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['packets', 'decisions', 'decision_reviews'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON ai.%I FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON ai.%I FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER mock_ai_guard BEFORE INSERT ON ai.%I FOR EACH ROW EXECUTE FUNCTION ops.guard_mock_ai()', table_name);
    END LOOP;
    FOREACH table_name IN ARRAY ARRAY['detector_runs', 'evidence_items'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON det.%I FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON det.%I FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER synthetic_origin_guard BEFORE INSERT ON det.%I FOR EACH ROW EXECUTE FUNCTION ops.guard_synthetic_origin()', table_name);
    END LOOP;
END;
$$;
CREATE TRIGGER synthetic_origin_guard BEFORE INSERT ON ai.packets
    FOR EACH ROW EXECUTE FUNCTION ops.guard_synthetic_origin();
CREATE TRIGGER allowed_decision_guard BEFORE INSERT ON ai.decisions
    FOR EACH ROW EXECUTE FUNCTION ai.guard_allowed_decision();

CREATE VIEW ai.effective_decisions AS
WITH current_packets AS (
    SELECT DISTINCT ON (fund_code, decision_type, origin, cutoff) *
    FROM ai.packets
    ORDER BY fund_code, decision_type, origin, cutoff, created_at DESC, packet_id DESC
)
SELECT packet.fund_code, packet.decision_type, packet.packet_id, packet.packet_sha256,
    packet.origin, packet.as_of, packet.cutoff,
    COALESCE(reviewed.decision_id, latest.decision_id) AS decision_id,
    reviewed.review_id,
    CASE
        WHEN reviewed.action = 'REJECT' THEN 'UNDECIDED'
        WHEN reviewed.action = 'OVERRIDE' THEN reviewed.override_value
        WHEN reviewed.action = 'ACCEPT' AND reviewed.validation_state = 'VALID' THEN reviewed.decision_value
        WHEN reviewed.review_id IS NOT NULL THEN 'UNDECIDED'
        WHEN latest.validation_state = 'VALID' THEN latest.decision_value
        ELSE 'UNDECIDED'
    END AS effective_value,
    CASE WHEN reviewed.review_id IS NOT NULL THEN 'HUMAN'
        WHEN latest.validation_state = 'VALID' THEN 'AI' ELSE 'UNDECIDED' END AS effective_source,
    EXISTS (
        SELECT 1 FROM ai.decision_reviews old_review
        JOIN ai.decisions old_decision USING (decision_id)
        JOIN ai.packets old_packet ON old_packet.packet_id = old_decision.packet_id
        WHERE old_decision.fund_code = packet.fund_code
            AND old_decision.decision_type = packet.decision_type
            AND old_decision.packet_id <> packet.packet_id
            AND old_packet.origin = packet.origin
            AND old_packet.cutoff IS NOT DISTINCT FROM packet.cutoff
            AND old_review.field_name = 'decision_value'
    ) AS stale_review_exists,
    reviewed.review_id IS NOT NULL AS has_current_review
FROM current_packets packet
LEFT JOIN LATERAL (
    SELECT decision_id, validation_state, decision_value
    FROM ai.decisions
    WHERE packet_id = packet.packet_id
    ORDER BY created_at DESC, decision_id DESC LIMIT 1
) latest ON TRUE
LEFT JOIN LATERAL (
    SELECT review.review_id, review.action, review.override_value,
        decision.decision_id, decision.validation_state, decision.decision_value
    FROM ai.decision_reviews review
    JOIN ai.decisions decision USING (decision_id)
    WHERE decision.packet_id = packet.packet_id AND review.field_name = 'decision_value'
    ORDER BY review.created_at DESC, review.review_id DESC LIMIT 1
) reviewed ON TRUE;

GRANT SELECT, INSERT ON det.detector_runs, det.evidence_items,
    ai.packets, ai.decisions, ai.decision_reviews TO p50k_app;
GRANT SELECT ON ai.effective_decisions TO p50k_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai TO p50k_app;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA ai FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA ops FROM PUBLIC;

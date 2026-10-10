-- T2.1/T2.2: fixed calibration versions, complete runs and immutable signals.
CREATE TABLE det.detector_versions (
    version_id TEXT PRIMARY KEY CHECK (length(btrim(version_id)) > 0),
    protocol_version TEXT NOT NULL CHECK (length(btrim(protocol_version)) > 0),
    protocol_sha256 ref.sha256 NOT NULL,
    code_sha256 ref.sha256 NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{"rights_status":"UNREVIEWED","development_result":true,"label_tr":"geliştirme sonucu; eşikler olaydan sonra belirlendi"}'::jsonb
        CHECK (jsonb_typeof(parameters) = 'object'),
    thresholds JSONB NOT NULL CHECK (jsonb_typeof(thresholds) = 'object'),
    calibration_input_sha256 ref.sha256 NOT NULL,
    calibration_cutoff TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE det.run_inputs (
    run_id UUID PRIMARY KEY REFERENCES det.detector_runs(run_id),
    version_id TEXT NOT NULL REFERENCES det.detector_versions(version_id),
    input_sha256 ref.sha256 NOT NULL,
    input_watermark TIMESTAMPTZ,
    as_of DATE NOT NULL,
    origin ref.data_origin NOT NULL,
    cutoff TIMESTAMPTZ,
    complete BOOLEAN NOT NULL DEFAULT TRUE CHECK (complete),
    UNIQUE NULLS NOT DISTINCT (version_id, input_sha256, origin, cutoff),
    CHECK (origin <> 'HISTORICAL_REPLAY' OR cutoff IS NOT NULL)
);
CREATE INDEX run_inputs_version_idx ON det.run_inputs (version_id, as_of);

CREATE TABLE det.signals (
    run_id UUID NOT NULL REFERENCES det.detector_runs(run_id),
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    detector_id TEXT NOT NULL CHECK (length(btrim(detector_id)) > 0),
    state TEXT NOT NULL CHECK (state IN ('TRIGGERED', 'NOT_TRIGGERED', 'ABSTAINED')),
    reason TEXT NOT NULL CHECK (length(btrim(reason)) > 0),
    value NUMERIC CHECK (value NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC, '-Infinity'::NUMERIC)),
    threshold NUMERIC CHECK (threshold NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC, '-Infinity'::NUMERIC)),
    evidence_id TEXT NOT NULL REFERENCES det.evidence_items(evidence_id),
    as_of DATE NOT NULL,
    development_result BOOLEAN NOT NULL DEFAULT TRUE CHECK (development_result),
    PRIMARY KEY (run_id, fund_code, detector_id)
);
CREATE INDEX signals_fund_run_idx ON det.signals (fund_code, run_id, detector_id);
CREATE INDEX signals_state_idx ON det.signals (run_id, state);

CREATE FUNCTION det.guard_run_inputs() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    stored_run det.detector_runs%ROWTYPE;
    registered_version det.detector_versions%ROWTYPE;
BEGIN
    SELECT * INTO stored_run FROM det.detector_runs WHERE run_id = NEW.run_id;
    SELECT * INTO registered_version FROM det.detector_versions WHERE version_id = NEW.version_id;
    IF stored_run.run_id IS NULL OR registered_version.version_id IS NULL THEN
        RAISE EXCEPTION 'Detector run or version is absent' USING ERRCODE = '23514';
    END IF;
    IF stored_run.protocol_version <> registered_version.protocol_version
            OR stored_run.protocol_sha256 <> registered_version.protocol_sha256
            OR NEW.origin <> stored_run.origin
            OR NEW.cutoff IS DISTINCT FROM stored_run.cutoff THEN
        RAISE EXCEPTION 'Detector input does not match its registered run' USING ERRCODE = '23514';
    END IF;
    IF stored_run.cutoff IS NOT NULL AND (
            NEW.as_of > (stored_run.cutoff AT TIME ZONE 'Europe/Istanbul')::date
            OR NEW.input_watermark > stored_run.cutoff) THEN
        RAISE EXCEPTION 'Detector input exceeds its cutoff' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION det.guard_run_evidence() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE stored_run det.detector_runs%ROWTYPE;
BEGIN
    -- Phase 1 also permits standalone evidence; run-bound evidence is stricter.
    IF NEW.run_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT * INTO stored_run FROM det.detector_runs WHERE run_id = NEW.run_id;
    IF stored_run.run_id IS NULL OR NEW.origin <> stored_run.origin
            OR NEW.state NOT IN ('TRIGGERED', 'NOT_TRIGGERED', 'ABSTAINED')
            OR (NEW.state = 'ABSTAINED' AND NEW.triggered IS NOT NULL)
            OR (NEW.state = 'TRIGGERED' AND NEW.triggered IS DISTINCT FROM TRUE)
            OR (NEW.state = 'NOT_TRIGGERED' AND NEW.triggered IS DISTINCT FROM FALSE) THEN
        RAISE EXCEPTION 'Evidence does not match its detector run' USING ERRCODE = '23514';
    END IF;
    IF stored_run.cutoff IS NOT NULL AND (
            NEW.available_at > stored_run.cutoff
            OR NEW.effective_date > (stored_run.cutoff AT TIME ZONE 'Europe/Istanbul')::date
            OR (NEW.state = 'TRIGGERED' AND NEW.available_at IS NULL)) THEN
        RAISE EXCEPTION 'Evidence exceeds or lacks its availability cutoff' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION det.guard_signal_evidence() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    linked_evidence det.evidence_items%ROWTYPE;
    stored_run det.detector_runs%ROWTYPE;
BEGIN
    SELECT * INTO linked_evidence FROM det.evidence_items WHERE evidence_id = NEW.evidence_id;
    SELECT * INTO stored_run FROM det.detector_runs WHERE run_id = NEW.run_id;
    IF linked_evidence.evidence_id IS NULL
            OR linked_evidence.run_id IS DISTINCT FROM NEW.run_id
            OR linked_evidence.fund_code <> NEW.fund_code
            OR linked_evidence.detector_id <> NEW.detector_id
            OR linked_evidence.state <> NEW.state THEN
        RAISE EXCEPTION 'Signal is not bound to its evidence' USING ERRCODE = '23514';
    END IF;
    IF stored_run.cutoff IS NOT NULL
            AND NEW.as_of > (stored_run.cutoff AT TIME ZONE 'Europe/Istanbul')::date THEN
        RAISE EXCEPTION 'Signal exceeds its cutoff' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DO $$
DECLARE table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['detector_versions', 'run_inputs', 'signals'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON det.%I FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON det.%I FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change()', table_name);
    END LOOP;
END;
$$;
CREATE TRIGGER synthetic_origin_guard BEFORE INSERT ON det.run_inputs
    FOR EACH ROW EXECUTE FUNCTION ops.guard_synthetic_origin();
CREATE TRIGGER run_input_guard BEFORE INSERT ON det.run_inputs
    FOR EACH ROW EXECUTE FUNCTION det.guard_run_inputs();
CREATE TRIGGER run_evidence_guard BEFORE INSERT ON det.evidence_items
    FOR EACH ROW EXECUTE FUNCTION det.guard_run_evidence();
CREATE TRIGGER signal_evidence_guard BEFORE INSERT ON det.signals
    FOR EACH ROW EXECUTE FUNCTION det.guard_signal_evidence();

GRANT SELECT, INSERT ON det.detector_versions, det.run_inputs, det.signals TO p50k_app;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA det FROM PUBLIC;

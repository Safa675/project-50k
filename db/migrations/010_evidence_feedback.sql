-- Feedback is separate from immutable detector evidence and materiality reviews.
CREATE TABLE b2b.evidence_feedback (
    feedback_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(user_id),
    evidence_id TEXT NOT NULL REFERENCES det.evidence_items(evidence_id),
    helpful BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX evidence_feedback_owner_idx ON b2b.evidence_feedback(user_id,evidence_id,feedback_id DESC);
CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON b2b.evidence_feedback
    FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change();
CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON b2b.evidence_feedback
    FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change();
GRANT SELECT,INSERT ON b2b.evidence_feedback TO p50k_app;
GRANT USAGE,SELECT ON SEQUENCE b2b.evidence_feedback_feedback_id_seq TO p50k_app;

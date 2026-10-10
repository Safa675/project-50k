-- Only validated paragraphs are emitted; retain them even if a stream is interrupted.
CREATE TABLE ai.chat_stream_chunks (
    chunk_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    turn_id UUID NOT NULL REFERENCES ai.chat_turns(turn_id),
    attempt INTEGER NOT NULL CHECK (attempt BETWEEN 0 AND 2),
    paragraph_index INTEGER NOT NULL CHECK (paragraph_index BETWEEN 0 AND 3),
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 12000),
    evidence_ids JSONB NOT NULL CHECK (jsonb_typeof(evidence_ids)='array'),
    prompt_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(turn_id,attempt,paragraph_index)
);
CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON ai.chat_stream_chunks
    FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change();
CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON ai.chat_stream_chunks
    FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change();
GRANT SELECT,INSERT ON ai.chat_stream_chunks TO p50k_app;
GRANT USAGE,SELECT ON SEQUENCE ai.chat_stream_chunks_chunk_id_seq TO p50k_app;

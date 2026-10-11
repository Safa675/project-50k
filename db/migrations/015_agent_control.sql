-- Persistent global control for the local agent team. In-flight work can finish;
-- pause changes admission of new work, never prior messages or decisions.
CREATE TABLE agents.team_control (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    paused BOOLEAN NOT NULL DEFAULT FALSE,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    changed_by UUID REFERENCES auth.users(user_id)
);
INSERT INTO agents.team_control(singleton) VALUES (TRUE);

CREATE TABLE agents.control_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    action TEXT NOT NULL CHECK (action IN ('PAUSE', 'RESUME')),
    actor_id UUID NOT NULL REFERENCES auth.users(user_id),
    paused BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER control_events_immutable_update BEFORE UPDATE OR DELETE ON agents.control_events
    FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change();
CREATE TRIGGER control_events_immutable_truncate BEFORE TRUNCATE ON agents.control_events
    FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change();
GRANT SELECT, UPDATE ON agents.team_control TO p50k_app;
GRANT SELECT, INSERT ON agents.control_events TO p50k_app;
GRANT USAGE, SELECT ON SEQUENCE agents.control_events_event_id_seq TO p50k_app;

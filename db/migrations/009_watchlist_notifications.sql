-- Personal saved funds and read state; detector evidence remains immutable.
CREATE TABLE auth.watchlist_funds (
    user_id UUID NOT NULL REFERENCES auth.users(user_id),
    fund_code TEXT NOT NULL REFERENCES ref.funds(fund_code),
    saved_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (user_id, fund_code)
);
CREATE TABLE auth.notification_reads (
    user_id UUID NOT NULL REFERENCES auth.users(user_id),
    evidence_id TEXT NOT NULL REFERENCES det.evidence_items(evidence_id),
    read_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (user_id, evidence_id)
);
CREATE TABLE auth.notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(user_id),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
GRANT SELECT, INSERT, DELETE ON auth.watchlist_funds TO p50k_app;
GRANT SELECT, INSERT ON auth.notification_reads TO p50k_app;
GRANT SELECT, INSERT, UPDATE ON auth.notification_preferences TO p50k_app;

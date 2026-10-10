-- Isolated BIST30 current catalog and immutable daily close observations.
CREATE TABLE ref.stock_instruments (
    symbol TEXT PRIMARY KEY CHECK (symbol ~ '^[A-Z][A-Z0-9]{1,11}$'),
    name TEXT NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 240),
    exchange TEXT NOT NULL DEFAULT 'BIST' CHECK (exchange = 'BIST'),
    currency TEXT NOT NULL DEFAULT 'TRY' CHECK (currency = 'TRY'),
    source_id TEXT NOT NULL,
    source_sha256 ref.sha256 NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE ref.stock_catalogs (
    catalog_sha256 ref.sha256 PRIMARY KEY,
    universe TEXT NOT NULL CHECK (universe = 'XU030'),
    captured_at TIMESTAMPTZ NOT NULL,
    symbols TEXT[] NOT NULL CHECK (cardinality(symbols) BETWEEN 1 AND 30),
    source_id TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX stock_catalog_captured_idx ON ref.stock_catalogs(captured_at DESC);

CREATE TABLE obs.stock_prices (
    symbol TEXT NOT NULL REFERENCES ref.stock_instruments(symbol),
    effective_date DATE NOT NULL,
    close NUMERIC CHECK (close > 0 AND close NOT IN ('NaN'::NUMERIC,'Infinity'::NUMERIC)),
    source_id TEXT NOT NULL,
    source_sha256 ref.sha256 NOT NULL,
    raw_source_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    availability_rule TEXT NOT NULL,
    price_adjustment TEXT NOT NULL CHECK (price_adjustment IN ('UNVERIFIED','UNADJUSTED','ADJUSTED')),
    rights_status TEXT NOT NULL DEFAULT 'UNREVIEWED' CHECK (rights_status='UNREVIEWED'),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(symbol,effective_date,source_id,source_sha256),
    CHECK (effective_date <= (available_at AT TIME ZONE 'Europe/Istanbul')::date),
    CHECK (available_at >= observed_at)
);
CREATE INDEX stock_prices_available_idx ON obs.stock_prices(symbol,available_at,effective_date);
CREATE TABLE obs.stock_actions (
    symbol TEXT NOT NULL REFERENCES ref.stock_instruments(symbol),
    event_id TEXT NOT NULL CHECK (length(event_id) BETWEEN 1 AND 160),
    action_type TEXT NOT NULL CHECK (action_type IN ('SPLIT','DIVIDEND','CAPITAL_INCREASE','RIGHTS','OTHER')),
    effective_date DATE NOT NULL,
    factor NUMERIC CHECK (factor>0 AND factor NOT IN ('NaN'::NUMERIC,'Infinity'::NUMERIC)),
    cash_amount NUMERIC CHECK (cash_amount>=0 AND cash_amount NOT IN ('NaN'::NUMERIC,'Infinity'::NUMERIC)),
    source_id TEXT NOT NULL,
    source_sha256 ref.sha256 NOT NULL,
    raw_source_sha256 ref.sha256 NOT NULL,
    origin ref.data_origin NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    rights_status TEXT NOT NULL DEFAULT 'UNREVIEWED' CHECK (rights_status='UNREVIEWED'),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(symbol,event_id,source_id,source_sha256),
    CHECK (available_at >= observed_at)
);
DO $$
DECLARE item TEXT;
BEGIN
    FOREACH item IN ARRAY ARRAY['stock_prices','stock_actions'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON obs.%I FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change()',item);
        EXECUTE format('CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON obs.%I FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change()',item);
        EXECUTE format('CREATE TRIGGER synthetic_origin_guard BEFORE INSERT ON obs.%I FOR EACH ROW EXECUTE FUNCTION ops.guard_synthetic_origin()',item);
    END LOOP;
END $$;
CREATE TRIGGER immutable_rows BEFORE UPDATE OR DELETE ON ref.stock_catalogs
    FOR EACH ROW EXECUTE FUNCTION ops.reject_immutable_change();
CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON ref.stock_catalogs
    FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_immutable_change();
GRANT SELECT,INSERT,UPDATE ON ref.stock_instruments TO p50k_app;
GRANT SELECT,INSERT ON ref.stock_catalogs,obs.stock_prices,obs.stock_actions TO p50k_app;

-- Completed runs are sealed: no evidence or signal can be appended afterward.
CREATE FUNCTION det.guard_closed_run() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.run_id IS NULL THEN
        RETURN NEW;
    END IF;
    -- Serialize child inserts and finalization, including separate transactions.
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.run_id::text, 50000024));
    IF TG_TABLE_NAME <> 'run_inputs' AND EXISTS (
            SELECT 1 FROM det.run_inputs WHERE run_id = NEW.run_id AND complete) THEN
        RAISE EXCEPTION 'Completed detector run cannot receive new records' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER closed_run_guard BEFORE INSERT ON det.evidence_items
    FOR EACH ROW EXECUTE FUNCTION det.guard_closed_run();
CREATE TRIGGER closed_run_guard BEFORE INSERT ON det.signals
    FOR EACH ROW EXECUTE FUNCTION det.guard_closed_run();
CREATE TRIGGER closed_run_guard BEFORE INSERT ON det.run_inputs
    FOR EACH ROW EXECUTE FUNCTION det.guard_closed_run();
REVOKE ALL ON FUNCTION det.guard_closed_run() FROM PUBLIC;

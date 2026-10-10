"""Read-only institutional workflow totals tied to the current evidence run."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from psycopg import Connection
from psycopg.rows import dict_row
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RunProvenance(Contract):
    run_id: str
    version_id: str
    protocol_version: str
    protocol_sha256: str
    code_sha256: str
    input_sha256: str
    as_of: date
    cutoff: AwareDatetime
    created_at: AwareDatetime
    calibration_cutoff: AwareDatetime
    origin: Literal["DELAYED", "SYNTHETIC"]


class EvidenceTotals(Contract):
    total: int = Field(ge=0)
    funds: int = Field(ge=0)
    triggered: int = Field(ge=0)
    not_triggered: int = Field(ge=0)
    abstained: int = Field(ge=0)
    attributes: int = Field(ge=0)


class ModelProvenance(Contract):
    model_id: str
    prompt_version: str
    schema_version: str
    ai_mode: Literal["off", "live", "mock"]
    latest_at: AwareDatetime


class DecisionTotals(Contract):
    packets: int = Field(ge=0)
    valid_live: int = Field(ge=0)
    valid_synthetic: int = Field(ge=0)
    valid_deterministic: int = Field(ge=0)
    invalid: int = Field(ge=0)
    awaiting_proposal: int = Field(ge=0)
    reviewed: int = Field(ge=0)
    accepted: int = Field(ge=0)
    overridden: int = Field(ge=0)
    rejected: int = Field(ge=0)
    models: list[ModelProvenance] = Field(default_factory=list, max_length=8)


class IngestStatus(Contract):
    run_id: str
    status: Literal["RUNNING", "SUCCEEDED", "FAILED"]
    started_at: AwareDatetime
    finished_at: AwareDatetime | None
    counts: dict[str, dict[str, int]]


class JobTotals(Contract):
    ready: int = Field(ge=0)
    running: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)


class StockAvailability(Contract):
    state: Literal["SCHEMA_ABSENT", "NO_CATALOG", "CATALOG_ONLY", "DAILY_PRICES_AVAILABLE"]
    catalog_members: int = Field(ge=0, le=30)
    symbols_with_prices: int = Field(ge=0, le=30)
    price_observations: int = Field(ge=0)
    catalog_captured_at: AwareDatetime | None


class WorkflowOverview(Contract):
    observed_at: AwareDatetime
    data_mode: Literal["DELAYED", "SYNTHETIC"]
    fund_catalog_count: int = Field(ge=0)
    run: RunProvenance | None
    evidence: EvidenceTotals
    decisions: DecisionTotals
    latest_ingest: IngestStatus | None
    jobs: JobTotals
    stocks: StockAvailability
    development_result: Literal[True] = True
    rights_status: Literal["UNREVIEWED"] = "UNREVIEWED"
    workflow_method: Literal["SINGLE_PROPOSAL_WITH_HUMAN_REVIEW"] = "SINGLE_PROPOSAL_WITH_HUMAN_REVIEW"


CURRENT_PACKETS = """
    WITH current_packets AS (
        SELECT DISTINCT ON (packet.fund_code) packet.packet_id
        FROM ai.packets packet
        WHERE packet.payload->>'run_id' = %s AND packet.origin = %s
            AND packet.created_at <= %s
        ORDER BY packet.fund_code, packet.created_at DESC, packet.packet_id DESC
    ), latest AS (
        SELECT packet.packet_id, proposal.validation_state, proposal.ai_mode,
            review.action
        FROM current_packets packet
        LEFT JOIN LATERAL (
            SELECT decision_id, validation_state, ai_mode FROM ai.decisions
            WHERE packet_id = packet.packet_id AND created_at <= %s
            ORDER BY created_at DESC, decision_id DESC LIMIT 1
        ) proposal ON TRUE
        LEFT JOIN LATERAL (
            SELECT review.action FROM ai.decision_reviews review
            JOIN ai.decisions decision USING (decision_id)
            WHERE decision.packet_id = packet.packet_id AND review.created_at <= %s
                AND review.field_name = 'decision_value'
            ORDER BY review.created_at DESC, review.review_id DESC LIMIT 1
        ) review ON TRUE
    )
"""


def safe_ingest_counts(value: Any) -> dict[str, dict[str, int]]:
    """Expose only known count columns, never arbitrary ingest metadata or paths."""
    if not isinstance(value, dict):
        return {}
    result: dict[str, dict[str, int]] = {}
    for table in ("ref.funds", "obs.fund_prices", "obs.fund_snapshots", "obs.kap_documents",
                  "obs.kap_series", "obs.regulatory_events", "ref.stock_instruments", "obs.stock_prices"):
        counts = value.get(table)
        if isinstance(counts, dict):
            result[table] = {key: number for key in ("input", "inserted", "missing", "non_null")
                             if isinstance(number := counts.get(key), int)
                             and not isinstance(number, bool) and number >= 0}
    # The isolated stock importer records a flat numeric summary.
    stock_counts = {key: number for key in ("instruments", "prices", "actions", "inserted_prices", "missing_prices", "inserted_actions")
                    if isinstance(number := value.get(key), int) and not isinstance(number, bool) and number >= 0}
    if stock_counts:
        result["stocks"] = stock_counts
    return result


class WorkflowQueries:
    def __init__(self, connection: Connection):
        self.connection = connection

    def rows(self, statement: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(statement, parameters)
            return cursor.fetchall()

    def overview(self, cutoff: datetime, *, synthetic: bool = False) -> WorkflowOverview:
        origin = "SYNTHETIC" if synthetic else "DELAYED"
        catalog = self.rows("SELECT count(*) AS total FROM ref.funds")[0]["total"]
        runs = self.rows("""
            SELECT run.run_id::text, inputs.version_id, run.protocol_version,
                run.protocol_sha256, version.code_sha256, inputs.input_sha256,
                inputs.as_of, run.cutoff, run.created_at, version.calibration_cutoff, run.origin
            FROM det.detector_runs run JOIN det.run_inputs inputs USING (run_id)
            JOIN det.detector_versions version USING (version_id)
            WHERE run.origin = %s AND inputs.complete AND run.cutoff IS NOT NULL
                AND run.cutoff <= %s AND run.created_at <= %s
                AND version.calibration_cutoff <= run.cutoff
            ORDER BY run.cutoff DESC, run.created_at DESC, run.run_id DESC LIMIT 1
        """, (origin, cutoff, cutoff))
        run = RunProvenance(**runs[0]) if runs else None
        evidence = EvidenceTotals(total=0, funds=0, triggered=0, not_triggered=0, abstained=0, attributes=0)
        decisions = DecisionTotals(packets=0, valid_live=0, valid_synthetic=0, valid_deterministic=0,
                                  invalid=0, awaiting_proposal=0, reviewed=0, accepted=0, overridden=0, rejected=0)
        if run:
            evidence = EvidenceTotals(**self.rows("""
                SELECT count(*) AS total, count(DISTINCT signal.fund_code) AS funds,
                    count(*) FILTER (WHERE signal.state='TRIGGERED' AND NOT COALESCE((item.metadata->>'is_attribute')::boolean,false)) AS triggered,
                    count(*) FILTER (WHERE signal.state='NOT_TRIGGERED' AND NOT COALESCE((item.metadata->>'is_attribute')::boolean,false)) AS not_triggered,
                    count(*) FILTER (WHERE signal.state='ABSTAINED' AND NOT COALESCE((item.metadata->>'is_attribute')::boolean,false)) AS abstained,
                    count(*) FILTER (WHERE COALESCE((item.metadata->>'is_attribute')::boolean,false)) AS attributes
                FROM det.signals signal JOIN det.evidence_items item USING (evidence_id)
                WHERE signal.run_id=%s AND signal.as_of<=%s
                    AND (item.available_at<=%s OR (item.available_at IS NULL AND signal.state='ABSTAINED'))
            """, (run.run_id, run.as_of, cutoff))[0])
            parameters = (run.run_id, origin, cutoff, cutoff, cutoff)
            totals = self.rows(CURRENT_PACKETS + """
                SELECT count(*) AS packets,
                    count(*) FILTER (WHERE validation_state='VALID' AND ai_mode='live') AS valid_live,
                    count(*) FILTER (WHERE validation_state='VALID' AND ai_mode='mock') AS valid_synthetic,
                    count(*) FILTER (WHERE validation_state='VALID' AND ai_mode='off') AS valid_deterministic,
                    count(*) FILTER (WHERE validation_state='INVALID') AS invalid,
                    count(*) FILTER (WHERE validation_state IS NULL) AS awaiting_proposal,
                    count(action) AS reviewed,
                    count(*) FILTER (WHERE action='ACCEPT') AS accepted,
                    count(*) FILTER (WHERE action='OVERRIDE') AS overridden,
                    count(*) FILTER (WHERE action='REJECT') AS rejected
                FROM latest
            """, parameters)[0]
            models = self.rows(CURRENT_PACKETS + """
                SELECT decision.model_id, decision.prompt_version, decision.schema_version,
                    decision.ai_mode, max(decision.created_at) AS latest_at
                FROM current_packets packet JOIN ai.decisions decision USING (packet_id)
                WHERE decision.created_at<=%s
                GROUP BY decision.model_id, decision.prompt_version, decision.schema_version, decision.ai_mode
                ORDER BY latest_at DESC LIMIT 8
            """, parameters + (cutoff,))
            decisions = DecisionTotals(**totals, models=[ModelProvenance(**row) for row in models])
        ingests = self.rows("""
            SELECT run_id::text, status, started_at, finished_at, counts FROM obs.ingest_runs
            WHERE started_at<=%s ORDER BY started_at DESC, run_id DESC LIMIT 1
        """, (cutoff,))
        ingest = IngestStatus(**{**ingests[0], "counts": safe_ingest_counts(ingests[0]["counts"])}) if ingests else None
        jobs = JobTotals(**self.rows("""
            SELECT count(*) FILTER (WHERE status='READY') AS ready,
                count(*) FILTER (WHERE status='RUNNING') AS running,
                count(*) FILTER (WHERE status='SUCCEEDED') AS succeeded,
                count(*) FILTER (WHERE status='FAILED') AS failed
            FROM ops.jobs WHERE job_type='ai_decide' AND created_at<=%s
        """, (cutoff,))[0])
        return WorkflowOverview(observed_at=cutoff, data_mode=origin, fund_catalog_count=catalog,
                                run=run, evidence=evidence, decisions=decisions, latest_ingest=ingest,
                                jobs=jobs, stocks=self.stock_availability(cutoff))

    def stock_availability(self, cutoff: datetime) -> StockAvailability:
        absent = StockAvailability(state="SCHEMA_ABSENT", catalog_members=0, symbols_with_prices=0,
                                   price_observations=0, catalog_captured_at=None)
        exists = self.rows("SELECT to_regclass('ref.stock_catalogs') IS NOT NULL AND to_regclass('obs.stock_prices') IS NOT NULL AS present")[0]["present"]
        if not exists:
            return absent
        catalogs = self.rows("SELECT captured_at,symbols FROM ref.stock_catalogs WHERE captured_at<=%s ORDER BY captured_at DESC,catalog_sha256 DESC LIMIT 1", (cutoff,))
        if not catalogs:
            return absent.model_copy(update={"state": "NO_CATALOG"})
        catalog = catalogs[0]
        counts = self.rows("""
            SELECT count(*) AS price_observations, count(DISTINCT symbol) AS symbols_with_prices
            FROM obs.stock_prices WHERE symbol=ANY(%s) AND available_at<=%s
        """, (catalog["symbols"], cutoff))[0]
        return StockAvailability(state="DAILY_PRICES_AVAILABLE" if counts["price_observations"] else "CATALOG_ONLY",
                                 catalog_members=len(catalog["symbols"]), catalog_captured_at=catalog["captured_at"], **counts)

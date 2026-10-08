"""Time-bounded views of one immutable evidence bundle, without live I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from p50k.evidence_store import EvidenceStore, InvalidObservation, Observation, normalize_timestamp, parse_timestamp


class AmbiguousRevision(InvalidObservation):
    """Distinct eligible revisions have no demonstrated temporal order."""


@dataclass(frozen=True)
class ReplayCursor:
    store: EvidenceStore
    bundle_id: str
    cutoff: str
    _limit: datetime = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cutoff", normalize_timestamp(self.cutoff))
        object.__setattr__(self, "_limit", parse_timestamp(self.cutoff))
        self.store.manifest(self.bundle_id)

    def observations(self, fund: str | None = None) -> list[Observation]:
        latest = {}
        ranks = {}
        for row in self.store.observations(self.bundle_id):
            if fund is not None and row.fund != fund:
                continue
            if row.availability_provenance == "UNKNOWN" or row.available_at is None:
                continue
            if any(parse_timestamp(value) > self._limit for value in
                   (row.available_at, row.published_at, row.effective_at, row.observed_at) if value is not None):
                continue
            rank = (parse_timestamp(row.available_at), parse_timestamp(row.published_at)
                    if row.published_at else datetime.min.replace(tzinfo=timezone.utc))
            key = row.observation_key
            if key not in ranks or rank > ranks[key]:
                latest[key], ranks[key] = [row], rank
            elif rank == ranks[key]:
                latest[key].append(row)
        out = []
        for key in sorted(latest):
            if len({row.source_version for row in latest[key]}) > 1:
                raise AmbiguousRevision(f"No temporal order for revisions of {key}")
            out.append(latest[key][0])
        return out

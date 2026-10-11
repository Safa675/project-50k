# Retrospective results (2026-10-11)

The authenticated `/evaluation/retrospective` read endpoint compares the stored
12 September scan with confirmed SPK liquidation-order events effective on
17 September. It selects the completed historical run by its Istanbul cutoff
day and current detector version; the input price date can be the previous day.
The endpoint starts a read-only database transaction. It has no write path and
does not provide event-list information to detectors, agent evidence or chat.

The universe is the distinct funds in that run. Later confirmed events are
deduplicated per fund. Candidate records and synthetic events on the real
database are excluded. Regulatory-record checks and history attributes cannot
count as detections. Evidence must match its fund, detector, run and origin,
and be effective and available within that run's dated inputs and cutoff.

Price and data-quality results are shown separately. Listed funds that were
not flagged are split into assessed misses and funds without an assessable
result; the latter never count as quiet. The page displays both the total
without a flag and this split. Data-quality flags are not event predictions.
Flags outside the official list do not establish that the flag was wrong.

Every count and rate is computed from stored rows at request time. Rates are
rounded deterministically with Decimal; an undefined denominator stays missing.
The UI shows the scan day, last input price date, cutoff and official source.
It explicitly labels the comparison as after the fact and a development result:
the peer-divergence idea followed examination of THF and TP2, with no separate
validation cohort. Neither a flag nor a liquidation order establishes wrongdoing.

Synthetic unit/database fixtures cover counts, regulatory exclusion,
abstentions, candidate exclusion, future-evidence rejection, source filtering
and authenticated reads. Real scan observations are read only and never copied
into committed fixture files.

---
paths:
  - "services/p50k/research_reviews/**"
  - "services/p50k/replay.py"
  - "services/p50k/evidence_store.py"
  - "services/p50k/detectors/**"
  - "services/p50k/providers/**"
  - "research/events/**/run.py"
  - "research/events/2026-09-17-spk-liquidations/top100_funds.txt"
---

# Files bound into sealed research bundles

Sealed bundles under `raw/research/` re-hash their registered code, protocol and source files on every load.
Editing any of them makes the running app answer 503 `BUNDLE_INVALID` until every affected bundle is resealed.
The fixed-date (v1/v2) set is listed in `tests/unit/registered_sources.lock.json`; dated bundles also bind
`services/p50k/research_reviews/dated_*.py` and `fund_review_dated/run.py`.

- Add new behaviour in new modules beside these files; import the old helpers read-only.
- Runners compare working bytes with `git show HEAD:` and refuse uncommitted or CRLF files. Commit first.
- An intended change needs: user approval, `.claude/allow-registered-edits.local` (gitignored) for the edit,
  a commit, a reseal of every affected bundle (`/p50k-seal-dated`, the v1/v2 runners) and a note of the new IDs.
- The registered-sources tripwire test (`tests/unit/test_registered_sources_lock.py`) must stay green; update its
  lock only in a reviewed commit that states why.

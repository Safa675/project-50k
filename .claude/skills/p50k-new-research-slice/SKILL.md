---
name: p50k-new-research-slice
description: Plan and implement a new Project 50K research or app slice the way this repository requires - one small vertical slice, protocol committed before any real calculation, new modules beside sealed code, synthetic tests, leak scan, completion note and merge commit. Use when starting any new detector, research run, bundle extension or app feature that uses real archive data.
---

# New research or app slice

## 1. Check and plan (before any code)

- Read `docs/notes/current-state.md`, the latest decisions in `docs/decisions/`, and the relevant protocol(s).
- Propose exactly one vertical slice: requirement IDs (partial contribution only; all 284 stay
  NOT_IMPLEMENTED), file plan, acceptance tests, dependencies, data mode and open choices. List ambiguities that
  could cause an irreversible or unsafe choice. Implement only after the user approves.
- Scope is Turkish funds only (DEC-024). Use only the 100 opened funds in `top100_funds.txt`; never read or compute
  anything on the other 1,922 downloaded price files.

## 2. Preregister

- Write a new protocol file (never edit a committed one) that fixes universe, inputs, dates/periods, every
  threshold with its earlier committed source, freshness, ordering, counting, exact user-facing sentences,
  sealing and the tests. Include an "Already seen before writing this" list.
- Commit the protocol (and its decision record) alone, before any runtime commit or real output, and push it so
  the timestamp is external.

## 3. Build without breaking sealed bundles

- Files listed in `tests/unit/registered_sources.lock.json`, the dated modules and the runners are re-hashed
  whenever a sealed bundle loads. Do not edit them; add new modules beside them (as `bundle_v2.py` and
  `dated_*.py` did). The protect-paths hook blocks such edits unless `.claude/allow-registered-edits.local` exists.
- Runners refuse uncommitted bytes, CRLF and protocol changes; reuse that registration pattern.
- Missing stays missing (TEFAS 0 is no price); no gap filling; `Decimal` for money; explicit UTF-8; fixed `+03:00`.
- Every detector or replay change needs a look-ahead test: mutate data after the cutoff, assert identical output,
  and show the test fails without the guard.
- Tests use invented codes and values only.

## 4. Verify and record

- `/p50k-verify`, then `/p50k-leak-scan` with zero hits. Run an independent review for non-trivial slices.
- Seal real outputs only after the runtime is committed; keep outputs under `raw/`.
- Write a completion note (handoff `AGENTS.md` format): requirement IDs, changed files, exact commands and
  results, what is untested, data mode, limitations, migration effects, next slice.
- Merge with a merge commit (`git merge --no-ff`), never squash or force-push; the owner only pulls (DEC-027).

## Never

Claim fraud, prediction, accuracy, lead time or "would have caught"; name funds other than the eight liquidated
targets in committed files; publish real data; deploy, spend, create accounts or contact third parties without
explicit authorization.

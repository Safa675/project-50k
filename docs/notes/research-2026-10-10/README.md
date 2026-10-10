# Planning research, 2026-10-10

Five read-only reviews written by Claude Code subagents on 2026-10-10, between about 12:10 and 12:45 Istanbul time.
They are the inputs to `plans/2026-10-10-product-build-plan.md`.

| File | Covers |
|---|---|
| `inventory-code.md` | Existing code, reuse verdicts, gaps for a deploy-ready product |
| `inventory-specs.md` | Handoff v0.5 and DEC-024–029 mapped to the new direction: catalog coverage, AI design, requirement slices, collisions |
| `inventory-data.md` | Local data counts, external sources, a data plan |
| `research-product.md` | Insurance and B2B data ideas: Turkish regulation, comparables, defensible product shapes, questions for Safa |
| `research-runtime.md` | Docker, PostgreSQL, worker, auth, OpenAI integration, CI, effort estimate |
| `plan-review-integrity.md`, `plan-review-feasibility.md` | Adversarial reviews of the first plan draft; their fixes are folded into the plan |

How to read them:

- They hold only counts, dates, field names and public sources. No real values appear, and no fund other than the
  eight targets is named.
- Web facts were read on 2026-10-10. Many are marked unverified, and the regulatory notes are orientation, not legal
  advice.
- They are a snapshot. Decisions recorded later in `docs/decisions/` take precedence. In particular, the code
  inventory was written before DEC-029 opened all funds.

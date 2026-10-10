# DEC-028 — Deploy-ready, AI-native product build; team roles

**Date:** 2026-10-10 (Europe/Istanbul)
**Source:** Mirza (technical lead), in chat on 2026-10-10 between 12:00 and 12:25, during Startup Weekend Urla.

## Team

| Person | Role |
|---|---|
| Mirza | Technical lead. Does all development (frontend, backend, database, infrastructure) and owns data gathering, including finding new sources |
| Safa | Business person and repository owner. Makes no repository writes (DEC-027). Found some of the data sources |
| Barış | Designer of the pitch deck and the website's design system. Designs most screens, not all |

## Decisions

| Item | Decision |
|---|---|
| Build target | A deploy-ready full-stack product: frontend, backend, database and every other component connected. It works with real data and runs on localhost. It is not deployed during the event |
| Code freeze | Sunday 2026-10-11 13:00 |
| AI-native (non-negotiable) | An LLM makes decisions responsibly, using the scientific data where necessary, and users interact with it in the product interface. See the AI rules below |
| LLM provider | OpenAI API. Mirza provides the key, which lives only in a gitignored `.env`. The account's spending limit is $25 for the event and counts toward the TRY 5,000 ceiling. Model IDs come from current OpenAI documentation and stay configurable |
| Stack | Plain PostgreSQL and the product's own email/password auth, all in Docker on localhost. This deliberately departs from the handoff's Supabase and Google-only sign-in; both can be added later |
| Product story | Build the shared core first: data ingestion, the anomaly pipeline, fund pages, the API and the AI layer. The team picks the headline story (insurance policies or B2B anomaly data) on Saturday evening; see `docs/notes/product-direction.md` |
| Status of earlier specs | The handoff's product requirements and earlier product decisions are guides, not hard rules. Important changes or collisions are raised with Mirza, or with Safa, Barış or the team when it is their call |

## AI rules

- **Scores.** Detectors compute every score, threshold and trigger deterministically. The LLM never alters a computed number.
- **Decisions.**
  - The LLM may decide, for example which anomalies are material and why, or whether a trigger or policy condition appears to be met.
  - Each decision is stored with its evidence references, the model and prompt version, and a timestamp.
  - A human must be able to override any LLM decision. The override is stored beside the original, never in place of it.
- **Chat.** Users can talk to the LLM in the interface. Its tools are read-only and bounded, and the server validates their arguments.
- **Integrity rules stay binding for AI output.**
  - Material claims cite existing evidence.
  - Insufficient evidence is stated as such.
  - Nothing calls a fund or company fraudulent or manipulated.
  - No buy, hold or sell advice and no personalized recommendations.
  - Retrieved content is treated as data, not instructions.
  - User secrets never go into external queries.

## Unchanged

- Binding rules:
  - no real TEFAS, KAP or MKK data in git;
  - provenance and point-in-time discipline;
  - no fabricated tests or results;
  - no spending, accounts, deployment or external contact beyond what is authorized here.
- The TRY 5,000 ceiling still applies.
- DEC-024's scope: funds first, with stocks only if time and data allow.
- DEC-027: the owner only pulls, merges use merge commits, and real data appears only on localhost.
- All 284 requirement statuses stay NOT_IMPLEMENTED until delivered and tested.

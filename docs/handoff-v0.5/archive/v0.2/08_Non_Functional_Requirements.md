# Project 50K — Non-Functional Requirements

**Document status:** Draft v0.2  
**Date:** 2026-10-02  
**Requirement prefix:** `NFR`

---

## 1. Purpose

This document defines the quality attributes and constraints that Project 50K must satisfy beyond individual product functions. These requirements are especially important because the product handles financial information, automated anomaly detection, LLM-generated explanations, current data, and user notifications.

Targets are divided into **MVP targets** and, where useful, **production direction**. The Techstars weekend should not be over-engineered, but the prototype should avoid architectural decisions that make the core product unsafe or impossible to evolve.

---

# 2. Reliability and Graceful Degradation

### NFR-001 — No fabricated data
**Priority:** P0  
The system shall never invent a market value, fund metric, source event, timestamp, or on-chain fact because a provider failed or returned incomplete data.

If data is unavailable, the UI/AI shall display an unavailable/stale/insufficient state.

### NFR-002 — Partial-source resilience
**Priority:** P0  
Failure of one non-critical source shall not cause the entire asset page or event system to fail when other evidence can still be displayed safely.

Example: if trusted-news retrieval fails, deterministic market evidence may still render with a limitation notice.

### NFR-003 — Source outage visibility
**Priority:** P0  
Critical source outages or stale ingestion shall be visible in the admin area.

### NFR-004 — Duplicate-event resistance
**Priority:** P0  
Retries, repeated ingestion, or repeated detector runs shall not generate uncontrolled duplicate events/notifications.

### NFR-005 — Demo reliability
**Priority:** P0  
The jury demonstration shall not depend on the occurrence of a live anomaly. Historical replay shall provide a deterministic backup demonstration path.

---

# 3. Performance

### NFR-006 — Public page performance
**Priority:** P0  
For the MVP deployment under normal demo load, the landing page and cached/public asset shell should become usable within approximately 2.5 seconds on a typical broadband connection, excluding slow third-party source retrieval performed after initial rendering.

### NFR-007 — Search responsiveness
**Priority:** P0  
Asset search should return local/cached catalog matches within approximately 500 ms at the application/API level under normal MVP load.

### NFR-008 — Asset intelligence responsiveness
**Priority:** P0  
Previously computed intelligence events shall load from Project 50K storage rather than requiring full anomaly recomputation on every page request.

### NFR-009 — AI chat responsiveness
**Priority:** P0  
The UI shall provide immediate progress/streaming feedback for AI research requests expected to exceed approximately two seconds.

### NFR-010 — Asynchronous long-running work
**Priority:** P0  
Data ingestion, historical detector runs, e-mail delivery, and other potentially slow operations shall not block interactive web requests when they can be executed asynchronously.

---

# 4. Security

### NFR-011 — OAuth-only end-user credentials
**Priority:** P0  
Project 50K shall not store application-specific user passwords in the MVP.

### NFR-012 — Server-side authorization
**Priority:** P0  
Authorization decisions, especially admin access, shall be enforced server-side and shall not rely on hidden UI elements or client-only checks.

### NFR-013 — Secrets management
**Priority:** P0  
API keys, OAuth secrets, e-mail credentials, database secrets, and AI provider secrets shall be stored in environment/secret-management systems and never committed to the repository.

### NFR-014 — Principle of least privilege
**Priority:** P0  
Database/service credentials used by web clients, backend services, and workers shall have only the minimum permissions necessary for their responsibilities.

### NFR-015 — Input validation
**Priority:** P0  
All externally supplied inputs shall be validated at API boundaries, including asset identifiers, search inputs, chat messages, admin configuration values, and provider payloads.

### NFR-016 — Rate limiting / abuse controls
**Priority:** P1  
Public search and AI endpoints should support basic rate limiting or quota controls to reduce abuse and protect paid provider/model budgets.

### NFR-017 — Admin configuration safety
**Priority:** P0  
The admin UI shall not allow arbitrary code execution, raw SQL, or unrestricted prompt/code editing.

---

# 5. Privacy

### NFR-018 — Data minimization
**Priority:** P0  
The MVP shall store only user data necessary for account identity, watchlist, preferences, notifications, feedback, and product operation.

### NFR-019 — No unnecessary financial-position collection
**Priority:** P0  
The MVP shall not require quantity, cost basis, transaction history, bank credentials, or brokerage credentials.

### NFR-020 — Sensitive logging restriction
**Priority:** P0  
Logs shall avoid storing OAuth tokens, secret keys, full authentication headers, or other credentials.

### NFR-021 — Conversation data awareness
**Priority:** P1  
If chat history is persisted, the user should be informed that conversations are stored and the system should define retention/deletion behavior before production launch.

---

# 6. Financial Information Integrity

### NFR-022 — Source provenance
**Priority:** P0  
Every material intelligence event shall be traceable to its underlying data/source records.

### NFR-023 — Timestamp provenance
**Priority:** P0  
The system shall distinguish, where available:

- source publication/market timestamp;
- ingestion timestamp;
- detector execution timestamp;
- user notification timestamp.

### NFR-024 — Data freshness disclosure
**Priority:** P0  
The UI shall not imply real-time data when the underlying source is delayed or stale.

### NFR-025 — Provider normalization testing
**Priority:** P1  
Provider adapters should have fixture-based tests for symbol mapping, timestamp parsing, numeric units, and missing-value behavior.

### NFR-026 — Unit consistency
**Priority:** P0  
Financial calculations shall use explicit units/currencies/percentage conventions to prevent silent scale errors.

---

# 7. AI Reliability and Grounding

### NFR-027 — Grounded material claims
**Priority:** P0  
Material factual claims in AI-generated user-facing content shall be grounded in retrieved/structured evidence and accompanied by inspectable sources where applicable.

### NFR-028 — No invented source citations
**Priority:** P0  
The AI layer shall not display a source reference unless that source was actually retrieved or included in the evidence packet.

### NFR-029 — Insufficient-evidence behavior
**Priority:** P0  
The system shall prefer an explicit insufficient-evidence response over an unsupported causal explanation.

### NFR-030 — Deterministic confidence ownership
**Priority:** P0  
Numeric confidence shall be produced by the Project 50K decision/calibration logic, not by asking the LLM to guess its confidence.

### NFR-031 — AI output schema validation
**Priority:** P0  
Structured LLM outputs used by the application shall be schema-validated before being persisted or used for decisions.

### NFR-032 — Prompt injection containment
**Priority:** P1  
Retrieved web/source content shall be treated as untrusted data and shall not be allowed to override system/developer instructions or trigger arbitrary tools.

### NFR-033 — Source quality hierarchy
**Priority:** P0  
Retrieval/synthesis logic shall rank official/regulatory/issuer sources above lower-authority sources when relevant evidence is available.

### NFR-034 — Model/provider replaceability
**Priority:** P0  
AI integration shall be abstracted so that one provider or model can be replaced without redesigning the core event schema or product API.

---

# 8. Statistical/Decision-Engine Quality

### NFR-035 — Reproducibility
**Priority:** P0  
Given the same historical input dataset and detector/decision configuration, the deterministic/statistical portion of the engine should produce reproducible outputs.

### NFR-036 — Versioned detectors
**Priority:** P0  
Detector versions and decision-rule configurations shall be versioned and recorded with generated events.

### NFR-037 — Backtestability
**Priority:** P0  
Detectors selected for the product shall support historical replay/backtesting on time-ordered data.

### NFR-038 — No future leakage
**Priority:** P0  
Historical validation/replay shall prevent future information from influencing a detector result at an earlier timestamp.

### NFR-039 — Precision-over-noise bias for alerts
**Priority:** P0  
For user notifications, the product shall prefer fewer higher-quality events over excessive low-confidence alerts.

### NFR-040 — Calibration readiness
**Priority:** P1  
The event schema shall retain sufficient outcome/feedback features to evaluate and later calibrate severity/confidence thresholds.

---

# 9. Observability and Operations

### NFR-041 — Structured logging
**Priority:** P0  
Backend/worker logs shall be structured enough to identify request/job type, asset/provider where appropriate, status, and error category.

### NFR-042 — Correlation identifiers
**Priority:** P1  
Important asynchronous flows should use job/event/request identifiers that allow ingestion → signal → event → notification debugging.

### NFR-043 — Health checks
**Priority:** P0  
The web/API deployment and critical workers/providers shall expose enough state to support basic health monitoring.

### NFR-044 — Failure visibility
**Priority:** P0  
Silent failures are not acceptable for critical ingestion/notification jobs; failures shall be recorded and surfaced to admin/observability tooling.

### NFR-045 — Cost observability
**Priority:** P1  
AI/search/e-mail/provider usage should be measurable so the team can identify unexpectedly expensive workflows before production scale.

---

# 10. Scalability and Data Architecture

### NFR-046 — Precompute intelligence
**Priority:** P0  
Core anomaly/event generation shall be performed by scheduled/event-driven workers and stored, rather than recomputed independently for every user viewing the same public asset.

### NFR-047 — Shared event model
**Priority:** P0  
A single detected market event shall be reusable across many users; personalization should primarily affect ranking/notification eligibility rather than duplicating the underlying event computation.

### NFR-048 — Horizontal worker evolution
**Priority:** P1  
The worker architecture should be capable of later parallelization by asset universe, provider, or detector family.

### NFR-049 — Provider-rate-limit awareness
**Priority:** P0  
Ingestion logic shall implement caching, batching, backoff, or scheduling appropriate to upstream rate limits, especially TEFAS-like sources.

---

# 11. Maintainability and Agentic Development

### NFR-050 — Monorepo clarity
**Priority:** P0  
The repository shall use a clear structure separating web UI, API/backend, workers/intelligence, shared contracts, documentation, and research artifacts.

### NFR-051 — English engineering language
**Priority:** P0  
Code, internal API names, database schema, engineering documentation, tests, and LLM development prompts shall use English unless preserving an official source term.

### NFR-052 — Typed contracts
**Priority:** P0  
Frontend/backend boundaries shall use explicit typed/schema-validated contracts.

### NFR-053 — Small composable services
**Priority:** P0  
Agents and developers should implement data providers, detectors, decision logic, and AI tasks as modular components with narrow responsibilities.

### NFR-054 — Requirements traceability
**Priority:** P0  
Important implementation tasks and tests should reference requirement IDs where practical.

### NFR-055 — Documentation-as-context
**Priority:** P0  
The `/docs` and `/research` content shall be treated as authoritative agentic-development context and kept synchronized with locked product decisions.

---

# 12. Visual Design Quality

### NFR-056 — No generic AI-slop aesthetic
**Priority:** P0  
The product shall avoid common low-quality generated-dashboard patterns such as excessive glassmorphism, decorative gradient blobs, arbitrary neon effects, nested card-on-card layouts, repetitive status chips, and visual elements with no informational purpose.

### NFR-057 — Information hierarchy over card density
**Priority:** P0  
Dense financial information shall be organized using hierarchy, typography, spacing, grouping, and progressive disclosure rather than wrapping every element in an identical card.

### NFR-058 — Design system
**Priority:** P0  
The MVP shall define reusable design tokens for at least typography, spacing, radius, borders, surface hierarchy, semantic states, and chart/event styling.

### NFR-059 — Impeccable review workflow
**Priority:** P0 process requirement  
Agent-generated frontend work shall be reviewed using the team's Impeccable-based design-quality workflow and then reviewed by the team's UI/UX designer before final acceptance where time allows.

### NFR-060 — Semantic status design
**Priority:** P0  
Severity, confidence, positive/negative financial movement, and data-quality states shall not rely on color alone; text/iconography/labels shall provide meaning.

### NFR-061 — Progressive disclosure
**Priority:** P0  
Advanced methodology and evidence shall remain accessible without overwhelming the default event summary.

---

# 13. Accessibility and Interaction

### NFR-062 — Keyboard accessibility
**Priority:** P1  
Core desktop interactions should be keyboard accessible, especially search, navigation, dialogs, and event expansion.

### NFR-063 — Contrast/readability
**Priority:** P0  
Text and critical UI states shall maintain readable contrast; decorative visual choices shall not reduce financial-data legibility.

### NFR-064 — Touch usability
**Priority:** P0  
The responsive MVP shall maintain usable touch targets and avoid interactions that only work with mouse hover.

### NFR-065 — Reduced-motion respect
**Priority:** P1  
Non-essential animation should respect reduced-motion preferences.

---

# 14. Localization, Time, and Formatting

### NFR-066 — Turkish locale
**Priority:** P0  
The MVP shall use `tr-TR` formatting and natural Turkish UI copy.

### NFR-067 — Istanbul timezone default
**Priority:** P0  
User-facing timestamps for the MVP shall default to `Europe/Istanbul` unless the UI explicitly communicates another market-local time.

### NFR-068 — Market-time correctness
**Priority:** P0  
The system shall distinguish market hours/trading calendars where needed; crypto shall be treated as 24/7.

### NFR-069 — Decimal/currency clarity
**Priority:** P0  
Numbers shall be formatted consistently with clear currency/percentage units and without ambiguous decimal separators.

---

# 15. Compliance and Product-Safety Constraints

### NFR-070 — Informational positioning
**Priority:** P0  
Project 50K shall present itself as an investment intelligence/information product rather than an automated personalized investment-advisory service.

### NFR-071 — No Project-owned Buy/Hold/Sell verdict
**Priority:** P0  
The product shall not generate its own direct Buy/Hold/Sell verdict as a core output.

### NFR-072 — Anomaly vs. legal finding distinction
**Priority:** P0  
Product copy shall distinguish statistical/behavioral anomalies from legal findings of manipulation, fraud, or misconduct.

### NFR-073 — Data-rights readiness
**Priority:** P0  
Provider boundaries shall be designed so that hackathon data sources can later be replaced by appropriately licensed commercial feeds without rewriting the product core.

### NFR-074 — Attribution/license compliance
**Priority:** P0  
The team shall review and honor attribution, display, redistribution, and commercial-use requirements for every data source/library before production use.

---

# 16. Deployment and Recovery

### NFR-075 — Reproducible deployment
**Priority:** P0  
The web/API deployment shall be reproducible from repository code and documented environment variables.

### NFR-076 — Separate development/production secrets
**Priority:** P0  
Local development secrets and deployed environment secrets shall be managed separately.

### NFR-077 — Database migration discipline
**Priority:** P0  
Database schema changes shall use migrations rather than undocumented manual production edits.

### NFR-078 — Demo backup plan
**Priority:** P0  
The team shall maintain a known-good deployed build and a prepared historical replay dataset before the jury session.

---

# 17. Testing and Validation Quality

### NFR-079 — Critical-path automated tests
**Priority:** P0  
At minimum, automated tests should cover:

- signal calculation on fixtures;
- event severity/confidence calculation;
- watchlist authorization;
- admin authorization;
- AI structured-output validation;
- notification idempotency.

### NFR-080 — Historical detector validation
**Priority:** P0  
The selected P0 anomaly detectors shall be validated on historical examples before being used in the jury demonstration.

### NFR-081 — Source-grounding checks
**Priority:** P0  
The team shall manually test representative AI answers to confirm that displayed citations support the claims made.

### NFR-082 — Turkish copy review
**Priority:** P0  
High-visibility user-facing Turkish copy shall receive human review before the jury demonstration.

---

# 18. MVP Quality Gate

The MVP should not be considered jury-ready until all of the following are true:

- core pages deploy successfully;
- Google login works;
- one BIST historical event is fully replayable;
- at least one fund-specific event is credible;
- one crypto cross-signal example exists;
- severity and confidence are visibly distinct;
- every showcased AI explanation has valid sources;
- insufficient-evidence behavior has been tested;
- no core demo flow depends on a third-party service with no fallback;
- admin can see data freshness;
- mobile-width layout is usable;
- designer has reviewed final high-visibility screens;
- a backup demo path exists.

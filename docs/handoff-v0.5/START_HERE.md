# Project 50K v0.5 research extension — Start here

**Purpose:** implementation-ready planning, research, contracts and coding-agent context for a Türkiye-first AI-native investment intelligence product.

**Actual delivery:** specifications plus offline reference helpers/tests. **Not delivered:** working product, live-provider verification, licensing, empirical predictive validation, hosted deployment or external email.

## Read first
[Decisions and corrections](docs/00_Decisions_and_Corrections.md) → [release gates](docs/25_Release_Gates_and_Open_Decisions.md) → [package audit](reports/PACKAGE_AUDIT.md). These resolve earlier broad promises and explain what remains unknown.

## Product and requirements
Documents 01–05 define vision/problem/scope/MVP/personas. [User requirements](docs/06_User_Requirements.md), [functional requirements](docs/07_Functional_Requirements.md) and [non-functional requirements](docs/08_Non_Functional_Requirements.md) preserve 284 stable IDs. [Traceability](docs/09_Requirements_Traceability_Matrix.md) maps them to planned tasks and acceptance families; none is labeled fully implemented.

## Research and engineering
[Data matrix](docs/10_Data_Requirements_and_Provider_Matrix.md) → [literature review](docs/11_Literature_Review.md) → [28-anomaly catalog](docs/12_Anomaly_Catalog.md) → [decision/evidence model](docs/13_Decision_Confidence_and_Validation.md) → documents 14–20 for architecture, persistence, API, AI, design, security and testing. [Source register](research/SOURCE_REGISTER.md) includes review depth; papers are not presented as replicated experiments.

## For the developer / coding agent
Read [AGENTS.md](AGENTS.md), [PRODUCT.md](PRODUCT.md), [DESIGN.md](DESIGN.md) and [implementation backlog](docs/21_Implementation_Backlog_and_Traceability.md). Choose [Claude Code startup prompt](prompts/CLAUDE_CODE_START.md) or [Codex startup prompt](prompts/CODEX_START.md). Their first action is a task-scoped current-state check and plan; the substantive handoff audit is already complete.

Read research/USER_DECISIONS_2026-10-02.md: the selected weekend target is four markets with meaningful on-chain; preparation is owner-authorized; no service accounts; total ceiling TRY 5,000 excluding development Claude/Codex subscriptions. Organizer ruling is still absent and required before competition use of prepared materials. Paid actions/data/remote actions need separate scoped authorization. Do not copy the entire archive into the agent context as an equal authority. The Work handoff is complete. Read reports/AUDIT_REPORT.md and reports/CORRECTION_LOG.md before choosing the next scoped implementation task.

## For the designer
Read [design specification](docs/18_UX_Design_and_Turkish_Content.md), DESIGN.md and the proposed tokens. Approve visual direction and Turkish wording before broad component generation. Impeccable commands must be checked against the actually installed version; no production frontend exists here to audit yet; the v0.5 standalone brand preview is an untested design exploration.

## For business/development
Read [validation/demo plan](docs/23_Startup_Validation_and_Demo.md), [competitor review](docs/24_Competitor_Evidence_and_Positioning.md), [operations/costs](docs/22_Deployment_Operations_and_Costs.md) and gate document 25. Use interview, organizer, provider-rights and cost templates. Do not pitch hypotheses or synthetic outputs as measured traction/results.

## Local checks
```sh
python -m unittest discover -s tests -v
# Optional documentation validation environment; no application install:
python -m pip install -r requirements-validation.txt
python scripts/validate_package.py
python scripts/make_manifest.py
```
The first command needs only standard Python libraries. The package validator also needs PyYAML/jsonschema/referencing. No API credentials are required. Read the generated [validation report](reports/VALIDATION_REPORT.md) before interpreting a test pass.

## Authority order
Confirmed user decisions → approved later decisions → current audited specifications/contracts → v0.5 research recommendations → original archived drafts. If current specs/contracts disagree, record a correction and review it before implementation. Proposed defaults remain subject to actual tests and owner approval.

## v0.5 research extension — read before the next task
The owner authorized further engine research, offline experiments, naming/design and imagegen exploration on 2026-10-02. Read reports/RESEARCH_REPORT.md, research/engine_lab/ENGINE_SYSTEM_DESIGN.md and HYPOTHESES.json; detailed labs and raw results are linked there. Read research/brand_lab/NAMING_AND_LOGO.md and DESIGN_EXPLORATION.md for proposals. Current working package is v0.5; v0.4 and all received history remain preserved. No product requirement is upgraded by synthetic experiments, and research conclusions do not override confirmed four-market/on-chain scope or the total TRY 5,000 budget. İzvanta/name/logo/palettes are proposals, not an approved rebrand. No official trademark/domain clearance or live market/LLM/UI validation was obtained.

## Risk review continuation — 2026-10-03 (Europe/Istanbul)

Read reports/RISK_REVIEW.md and research/risk_review/RISK_REGISTER.json before selecting the next implementation/validation task. Five specialist reviews distinguish known limits, official descriptions and untested failure mechanisms; 24 consolidated entries keep ordinal consequence separate from unestimated likelihood. The arithmetic risk scenarios are authored sensitivity cases, not actual alert performance or vendor prices. Priorities are usable/entitled data, a bounded cumulative operating plan, observed user advantage and complete required paths with failure tests. No reduced market target, cleared release gate, legal classification, observed vulnerability or completed product requirement is inferred. Existing v0.5 science/design proposals and owner decisions remain unchanged.

## Problem solution and market research continuation 3 October 2026

Read reports/PROBLEM_MARKET_RESEARCH.md and research/problem_market/ANOMALY_FREQUENCY_MAP.json before the next task. Real events, existing information seeking and a substantial dated investor population are supported; recurring unmet Turkish user pain, our incremental task advantage and willingness to pay remain unvalidated. KAP already offers following/instant notifications. Complete 2025 KAP publications and historical paper detections have different units and cannot estimate our 28 catalog frequencies, all currently unknown. Use research/problem_market/PROBLEM_SOLUTION_HYPOTHESES.json and the proposed measurement protocol to seek disconfirmation. No customer study or empirical detector backtest was executed. Preserve the confirmed four-market/on-chain target, TRY 5,000 cumulative ceiling, G01 status and all 284 NOT_IMPLEMENTED requirements.

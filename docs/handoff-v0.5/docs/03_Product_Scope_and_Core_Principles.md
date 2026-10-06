# Project 50K — Product Scope & Core Principles

**Version:** 0.3 · **Date:** 2026-10-02
**Status:** specification; not implemented product functionality.

## Confirmed product scope
BIST, Turkish investment funds, popular crypto and restricted US equities; public asset discovery; Google-only accounts; persistent watchlist; personal and market-wide event feed; source-backed per-asset AI research/chat; category-based event status with separate evidence strength; in-app plus preference-controlled immediate/digest email; protected admin health/configuration; responsive web now and mobile-first vision later.

Turkish investment funds are a main USP. They use actual publication cadence; intraday underlying/disclosure developments are labeled separately. EVM and Solana are desired on-chain coverage, not a guarantee that all monitored coins exist on those chains. BTC itself is not an EVM token.

## Roles
Anonymous users view public rights-cleared projections. Signed-in users control only their own watchlist, preferences, chats and feedback. Admins use a protected server-owned membership to inspect safe metrics, pause processing/sending and change typed bounded settings with audit. Workers use privileged credentials only for authorized server jobs; the model has no write privileges.

## Core principles
1. Evidence before persuasion: sources, time, provenance and limitations remain visible.
2. AI-native investigation: the LLM performs useful bounded research/context work, not merely decorative summarization.
3. Numerical integrity: formulas and scoring are reviewed/versioned; no guessed prices, probabilities or claims.
4. Honest coverage: unknown, unavailable, stale, delayed, replay and synthetic are distinct.
5. Low cognitive load: meaningful event cards and optional drill-down; not a mandatory chat-only workflow.
6. Native Turkish: investor terminology, clear number formats and financial precision.
7. Quiet by default: opt-in email, deduplication, cooldowns and narrow global critical policy.
8. Deliberate design: designer-led hierarchy and Impeccable review; no generic dashboard skin.
9. Minimum data collection: no required position sizes/cost basis or brokerage credentials.
10. Reproducible decisions: immutable evidence versions and replay cutoff; no future data leakage.

## Scope layers
**Product backlog:** all 80 UR,122 FR,82 NFR retained with stable IDs. **First weekend execution cut:** two core BIST/fund paths and shared account/evidence/chat/operations experience. **Conditional breadth:** authorized email, expanded crypto/US and on-chain adapters. **Later:** large-scale monitoring, evaluated learned calibration, mobile clients, holdings graphs and optional portfolio exposure.

This is an explicit scheduling proposal, not removal of user-requested features. Failure to ship conditional desired features means reduced demo acceptance. The machine map separates phase, task mapping and actual implementation status.

## Exclusions
Buy/Hold/Sell verdicts, price targets or personalized sizing; fraud/Ponzi/manipulation conclusions by the platform; trade execution or wallet signing; social-media ingestion; browser push; actual portfolio accounting; bulk unsolicited email; unlicensed market/news redistribution. No compensation guarantee.

## Confidence and notification contracts
User confidence need is met by disclosed evidence strength, not a false probability. Global critical email requires explicit user opt-in, current valid evidence, policy eligibility and MVP admin release. Replay/synthetic events never send externally. A policy threshold cannot override data validity, rights or consent.

## Decision authority
Document 00 resolves earlier draft conflicts. Documents 10–25 define detailed contracts and gates. Archive/v0.2 is historical only. Proposed defaults require testing and approval; exact dependencies, budgets, rights and competition eligibility remain open until evidenced.

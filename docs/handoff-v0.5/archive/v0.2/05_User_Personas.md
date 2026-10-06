# Project 50K — User Personas

**Document status:** Draft v0.2  
**Date:** 2026-10-02  
**Working codename:** Project 50K  
**Related documents:** Product Vision, Problem Analysis, Product Scope, Techstars MVP Scope

---

## 1. Purpose

This document defines the primary user archetypes that Project 50K is designed to serve. The personas are **behavioral product personas**, not demographic stereotypes. They represent different levels of investment experience, monitoring intensity, and desired depth of explanation.

Project 50K should not become three separate products for three separate user types. The same product should serve all three retail-investor personas through **progressive disclosure**:

1. surface the important event in simple language;
2. show the evidence and metrics one level deeper;
3. offer detailed investigation and AI-assisted research for users who want it.

The product is Turkey-first, but the personas are intentionally general enough to remain useful if the product later expands geographically.

---

## 2. Persona Priority

### Primary design reference

**P2 — Independent Retail Investor**

This user best represents the core product thesis. They understand the basics of investing, follow multiple asset classes, consume financial information from several sources, but cannot continuously monitor everything they care about.

### Secondary personas

- **P1 — Guided Investor:** validates clarity, onboarding, and explanation quality.
- **P3 — Active Market Watcher:** validates intraday usefulness, evidence depth, and speed.
- **P4 — Platform Administrator / Intelligence Operator:** validates operational control, data freshness, and system observability.

The product should remain useful to all three investor personas without forcing the beginner to understand advanced metrics or forcing the advanced user to accept oversimplified explanations.

---

# 3. Persona P1 — Guided Investor

## Summary

A relatively new retail investor who owns or follows a small number of BIST shares, investment funds, or major crypto assets. They understand basic concepts such as price change, return, and risk, but financial disclosures and market microstructure are often difficult to interpret.

## Typical behavior

- checks investment apps several times per week;
- often learns about events through social media, friends, or headlines;
- may own funds because they are easier to understand than selecting individual securities;
- rarely reads full KAP disclosures or financial statements;
- does not know which technical indicators or alert rules should be configured;
- may overreact to isolated price moves because context is missing.

## Goals

- know when something genuinely important happens;
- understand the event without having to learn specialist terminology first;
- see the original source before trusting an interpretation;
- avoid missing serious developments affecting followed assets;
- ask simple questions in natural Turkish.

## Pain points

- too many financial websites and applications;
- financial terminology is intimidating;
- news feeds contain large amounts of irrelevant content;
- existing alert systems require the user to know what threshold to monitor;
- it is difficult to distinguish ordinary market noise from an event worth investigating;
- may confuse opinion, rumor, and official information.

## What Project 50K must do for this persona

- use plain, established Turkish investment terminology;
- lead with the event and why it matters rather than with raw indicators;
- clearly distinguish observation from interpretation;
- show severity and confidence without pretending to provide certainty;
- provide short explanations first and deeper detail on demand;
- cite official or reliable sources;
- never pressure the user toward a Buy/Hold/Sell action.

## UX implications

The first screen should answer:

> **“Do I need to pay attention to anything right now?”**

It should not require the user to interpret RSI, Bollinger Bands, or statistical jargon before understanding why an event was surfaced.

---

# 4. Persona P2 — Independent Retail Investor

## Summary

The primary persona. An intermediate retail investor who actively follows BIST, funds, crypto, and possibly U.S. equities. They understand financial ratios and common market concepts but still rely on several tools to monitor their investments.

## Typical behavior

- maintains a watchlist across multiple applications;
- checks TradingView-like charts, KAP, TEFAS/fund tools, broker apps, and financial news;
- follows several funds and stocks simultaneously;
- reads important disclosures but does not have time to read everything;
- is interested in the reason behind a move, not only the move itself;
- values independent decision-making and does not want opaque automated trading advice.

## Goals

- reduce the number of sources that must be checked manually;
- detect unusual behavior earlier;
- understand whether price action is supported by a disclosure, news event, sector move, or another observable cause;
- compare a fund with peers and detect unusual allocation or flow behavior;
- receive alerts that are selective rather than noisy;
- investigate an event interactively when necessary.

## Pain points

- fragmented information across market-data, disclosure, fund, and news products;
- manually correlating event timing with price/volume behavior;
- repetitive daily monitoring;
- alert fatigue from simplistic threshold notifications;
- difficulty determining whether an unusual event has a credible public explanation;
- fund information is available but often not surfaced as intelligence.

## What Project 50K must do for this persona

- automatically correlate multiple data sources;
- provide quantitative evidence behind each event;
- show source links and timestamps;
- distinguish `severity` from `confidence`;
- support intraday BIST monitoring;
- provide meaningful fund intelligence, not only performance charts;
- allow contextual AI research directly from the asset page;
- personalize the feed through a simple watchlist.

## UX implications

This persona should be able to move quickly from:

> **Event summary → evidence → historical context → source → follow-up question**

without leaving the asset page.

---

# 5. Persona P3 — Active Market Watcher

## Summary

An experienced retail investor or active trader who monitors markets frequently and cares about intraday changes. They are comfortable with charts, market statistics, and financial terminology and are sensitive to latency, false positives, and unsupported claims.

## Typical behavior

- monitors markets during trading hours;
- uses advanced charting and multiple watchlists;
- already has some price or technical alerts;
- reacts to KAP disclosures, volume spikes, volatility changes, and sector divergence;
- may follow both BIST and crypto in the same day;
- expects evidence to be inspectable rather than hidden behind a score.

## Goals

- identify unusual combinations of signals before manually discovering them;
- reduce noise from single-metric alerts;
- see exactly why an event was classified as unusual;
- understand data freshness and source timing;
- review historical analogues;
- use AI for investigation rather than as an oracle.

## Pain points

- simplistic alerts fire too often;
- tools rarely correlate price, disclosure, news, fundamentals, and on-chain evidence in one workflow;
- black-box risk scores are difficult to trust;
- explanations may arrive too late to be useful;
- market data from different providers can have timestamp or normalization inconsistencies.

## What Project 50K must do for this persona

- support intraday monitoring where data rights and availability allow;
- display exact evidence values;
- provide timestamps and freshness indicators;
- allow event filtering and historical exploration;
- support confidence methodology that is not generated arbitrarily by an LLM;
- keep AI output grounded in the underlying event evidence.

## UX implications

Advanced evidence should be accessible but should not dominate the default view. The product should feel fast, precise, and information-dense without becoming visually chaotic.

---

# 6. Persona P4 — Platform Administrator / Intelligence Operator

## Summary

An internal Project 50K operator responsible for ensuring that data ingestion, anomaly generation, AI interpretation, and notifications are functioning correctly.

During the hackathon, this persona is effectively the founding team. In a production product, it may evolve into operations, data, compliance, or product-administration roles.

## Goals

- know whether each data source is current and healthy;
- inspect recently generated events;
- identify failed jobs or stale data;
- adjust approved thresholds or feature flags without redeploying the application;
- monitor notification delivery;
- monitor AI configuration/prompt version;
- inspect user feedback on event relevance.

## Pain points

- a broken data source may silently create incorrect conclusions;
- an anomaly detector may become too noisy after market-regime changes;
- AI responses may degrade if source retrieval fails;
- debugging becomes difficult if event evidence and model versions are not recorded.

## What Project 50K must do for this persona

- provide a protected admin dashboard;
- use role-based access;
- show data freshness and ingestion health;
- expose event metrics and recent high-severity events;
- allow carefully scoped configuration changes;
- retain auditability for event generation and AI explanation paths.

---

# 7. Access States vs. Personas

`Anonymous Visitor` and `Authenticated User` are **access states**, not independent personas.

## Anonymous visitor

May:

- use asset search;
- open public asset pages;
- inspect selected public intelligence events;
- view source-backed explanations;
- view the landing page.

May not:

- create a persistent watchlist;
- receive personal alerts;
- retain chat history;
- access the admin dashboard.

## Authenticated investor

May:

- persist a watchlist;
- receive personalized alerts;
- access notification history;
- retain preferences and feedback;
- use personalized AI context where enabled.

Authentication for the MVP is **Google OAuth only**.

---

# 8. Shared User Principles

Across all investor personas, Project 50K should assume that:

1. the user wants to make their own investment decisions;
2. attention is scarce;
3. unexplained certainty is harmful;
4. source transparency improves trust;
5. simplicity should come from good prioritization, not by hiding evidence;
6. advanced detail should be available without making the default experience intimidating;
7. the product should reduce monitoring effort rather than create another feed the user must constantly check.

---

# 9. Persona-to-Feature Emphasis

| Capability | P1 Guided | P2 Independent | P3 Active | P4 Admin |
|---|---:|---:|---:|---:|
| Simple event explanation | High | High | Medium | Low |
| Evidence/source access | High | High | Very High | High |
| Intraday BIST intelligence | Medium | High | Very High | Medium |
| Fund intelligence | High | Very High | High | Medium |
| On-chain intelligence | Low/Medium | High | High | Medium |
| Contextual AI chat | High | Very High | High | Low |
| Watchlist alerts | High | Very High | Very High | Low |
| Historical replay/context | Medium | High | Very High | Medium |
| Data-health monitoring | None | None | None | Very High |
| Threshold/configuration tools | None | None | None | High |

---

# 10. Persona Validation Questions for User Interviews

These are not requirements; they are validation prompts for the Techstars weekend and later research.

### Monitoring behavior

- Which investment sources do you currently check every day or every week?
- What is the last important development you learned about too late?
- Which alerts do you currently use, and which ones do you ignore?

### Trust

- What evidence would make you trust an automatically generated market alert?
- Do you prefer a single score, an explanation, raw metrics, or a combination?
- When an AI explains a financial event, which sources do you consider credible?

### Funds

- How often do you inspect fund allocation, fund size, or investor-count changes?
- Would an alert about unusual fund flow or allocation changes be useful?
- Do you understand what is held inside the funds you own?

### AI assistant

- What questions would you ask after seeing an unusual market event?
- Would you trust the assistant more if every factual claim included a source?
- Is “I cannot find enough evidence” an acceptable answer from a financial assistant?

---

# 11. Design Reference Decision

For the MVP, product and UI decisions should be tested against this question:

> **Can an intermediate retail investor understand the important event in under ten seconds, while an advanced user can inspect the evidence without leaving the page?**

If the answer is no, the information architecture should be simplified or reorganized.

# Project 50K — Startup Validation & Demo Plan

**Version:** 0.4 audit + owner decisions · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 1. Product thesis and proof burden
Hypothesis: Turkish retail investors value fewer, source-backed, intelligible investment events over more raw signals. A broad asset catalog alone is not differentiation; existing tools already offer watchlist and multi-dimensional alerts [S30,S31]. Candidate differentiation is the quality of Turkish fund/BIST context, evidence timeliness and low-effort explanation across markets.

Fund relevance is supported by official developments, not by a claim that this product would have prevented them. SPK reported 131 funds across seven portfolio-management companies and 455,758 unique investors according to MKK in the relevant liquidation context [S02]. These figures are **not** losses, confirmed fraud counts or our addressable paying-user estimate. SPK's observations about certain funds and low-free-float shares must be attributed precisely [S03]. Use original official links rather than sensational secondary headlines.

## 2. Primary first user versus broad vision
All retail experience levels remain supported. For initial validation, include people who already monitor BIST securities or Turkish funds, including satisfied incumbent users and those with no recent monitoring problem; do not select only people who report overload. Beginners, active traders and fund-focused investors have different alert tolerances; interview them separately. Personas are hypotheses, not surveyed population estimates.

## 3. Interview protocol
Conduct 6–10 brief interviews as a proposed minimum learning exercise, not a statistically representative study. Ask about the last real missed development, sources used, time spent, current alarms, false-alert frustration and what evidence changes trust. Observe a source-backed event card and ask the person to explain it in their own words. Do not ask only “would you use an AI app?”

Record consent, anonymized quote, behavior evidence, alternatives and disconfirming findings. A price question is a willingness-to-pay hypothesis; do not fabricate revenue, customer logos, sign-ups or market-size numbers. See `templates/USER_INTERVIEW.md`.

## 4. Metrics to validate
Activation: user finds an asset, understands a sample event and follows it. Value: user correctly identifies why an event was flagged and its limitations. Retention hypothesis: repeated useful reviews, not raw alert-open rate alone. Harm/quality: misleading causal inference, perceived buy/sell advice, notification overload and false certainty. No metrics have been collected here.

## 5. Demonstration modes
The selected weekend target, confirmed 2026-10-02, includes BIST, Turkish funds, crypto and US equities plus meaningful on-chain experience. No reduced BIST+fund endpoint is approved. Every required path must expose actual identity, evidence, source/time, mode and limitations. Pre-event preparation is owner-authorized; organizer permission for its competition use remains unresolved. No service accounts exist; cumulative project ceiling is TRY 5,000 excluding development Claude/Codex subscriptions.
**Live:** a currently entitled provider responds, with visible venue and delay. **Historical replay:** timestamp-correct sourced event sequence, identified as replay. **Synthetic:** clearly fictional identifiers and constructed inputs, demonstrates behavior only. Never switch labels invisibly.

Demo sequence (target 3–4 minutes, adjust to organizer rules):
- 0:00–0:30: missed-information problem and concise product promise.
- 0:30–1:20: BIST-like event, chart, data freshness, evidence, no crime verdict.
- 1:20–2:00: fund-specific allocation/NAV context. Flow only with valid real or explicitly synthetic inputs.
- 2:00–2:40: asset chat asks “Bu neden önemli?”; tool-backed answer with sources and uncertainty.
- 2:40–3:10: follow, in-app notification, email dry-run; explain mobile-first longer-term use.
- 3:10–3:40: crypto market event with meaningful finalized on-chain evidence, and a US event; reuse the source/time/mode view rather than claim broad untested coverage.
- 3:40–4:00: admin pause/quality control and actual validation results. Rehearse against the real presentation limit; keep full evidence paths available for inspection beyond the short pitch.

A synthetic demonstration cannot support “we predicted this real event.” An available historical event does not establish predictive generalization. Exact scope and measured test results must appear in the pitch appendix.

## 6. Roles and schedule
Developer/BA owns the core slice and data/provenance. Designer owns identity, component hierarchy, Turkish comprehension and demo flow. Business teammate owns organizer clarification, interviews, competitor verification, provider outreach and pitch. Everyone tests the final flow.

Follow the supplied local schedule: Friday evening idea/team/Lean Canvas; Saturday validation and mentor sessions; Sunday presentation preparation from 13:30 and presentations from 17:00. General Techstars pages [S33] do not settle the local pre-work rule. Keep a before/during-event contribution log.

## 7. Business hypotheses
Start without investment execution, paid recommendations or brokerage integration. A future subscription could price sustained monitoring/explanation convenience, but no tariff is selected. Investigate data/news redistribution costs before claiming unit economics. Referral or issuer-funded models may create conflicts; disclose and review before considering them.

## 8. Pitch-ready claim boundaries
Allowed: “The prototype combines a deterministic anomaly signal with source-backed Turkish investigation.” Only after actually built/tested. Not allowed without evidence: “Detects scams,” “prevents losses,” “no competitor,” “all Turkish funds live,” “91% accurate,” or “predicted the liquidation.”

## 2026-10-03 risk review

Observe switching, recurring value, comprehension and ordinary-period usefulness against the same existing user jobs. No customer contact/study/payment was performed. G01 competition use remains unresolved. Current synthesis: reports/RISK_REVIEW.md; register: research/risk_review/RISK_REGISTER.json.

## Problem solution and market research continuation 3 October 2026

Use a last-real-incident walkthrough, quiet/no-event cases and satisfied incumbent users before a demo. Measure correct source-verified completion, effort and unsupported conclusions; test ordinary-use recurrence and payment separately. Registry totals/selected affected cohorts are not a paying TAM. No outreach or study has occurred. See `reports/PROBLEM_MARKET_RESEARCH.md` and the linked source-depth appendices.

# Project 50K — Anomaly & Event Catalog

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## Interpretation and readiness
Every entry distinguishes unusual observations from misconduct. `CORE` means selected for the implementation sequence, not implemented. `CONDITIONAL` is blocked by particular data/credentials. `NEXT` follows a stable core. `LATER` is product roadmap. These phases override indiscriminate legacy P0 wording; missing a user-requested conditional feature must be disclosed, not silently called complete.

All numerical thresholds are starting hypotheses authored for this project. No paper has validated them for this product. Backtest by market, session, asset class and frequency. Do not tune using the jury example and then report that example as independent validation.

## Common detector contract
Inputs include canonical asset ID, point-in-time eligible observations, cutoff, market session, source capability/rights and configuration version. Output is either `TRIGGERED`, `NOT_TRIGGERED` or `ABSTAINED` with reason, metrics, evidence IDs, time window, baseline sample size and dependencies. ABSTAINED is not a no-risk result. Category names and UI labels must be stable; title text can be localized.

## Core mathematical conventions
Return is log for detection and simple percentage for display; store units. MAD = median absolute deviation around the reference median. The 1.4826 factor is a scale convention, not evidence of normally distributed finance data. Reference windows exclude the test observation and all future observations. Zero/near-zero scale must produce abstention unless a separately validated absolute-change fallback is configured.

For fund flow, use `NAV ratio` only when the NAV/total-return convention and distributions are understood. With AUM 100 → 99 and NAV 1 → 0.99, estimated flow is zero, not minus one. With AUM 100 → 80 and unchanged NAV, estimated flow is minus 20. Examples are synthetic arithmetic, not fund observations.

For allocation, 40/60 → 60/40 has distance 0.20 and a 20 percentage-point category shift. Call this a change between the two **published snapshots**; do not claim to know when trades happened. No categorical mix chart should discard short/leveraged positions.

## Catalog

### AN-MKT-001 — Relative volume
**Phase:** CORE. **Trace:** FR-049. **Reading:** R02.

**Required evidence:** Final bar volume; 20 previous comparable session-slot volumes; venue and unit.

**Method:** RVOL = current / median(previous same-slot volumes). Candidate at RVOL >= 3 with at least 20 valid observations. Threshold is provisional.

**False positives / abstention:** Exclude opening/closing auctions, half-days, unit changes and nonpositive baselines. A news-driven increase is still unusual but not misconduct.

**Natural Turkish label:** “İşlem hacminde sıra dışı artış”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-MKT-002 — Robust return deviation
**Phase:** CORE. **Trace:** FR-050. **Reading:** R01,R02.

**Required evidence:** Completed closes; corporate actions; prior same-interval log returns.

**Method:** r=ln(Ct/Ct-1); z=(r-median(history))/(1.4826*MAD(history)). Candidate |z|>=4 and |simple return|>=1%, after 20 valid references.

**False positives / abstention:** Exclude corporate-action discontinuities; zero MAD means abstain, not infinity. No sigma-to-probability conversion.

**Natural Turkish label:** “Fiyatta olağandışı hareket”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-MKT-003 — Benchmark divergence
**Phase:** CORE. **Trace:** FR-052. **Reading:** R01.

**Required evidence:** Aligned asset and benchmark returns; point-in-time benchmark mapping.

**Method:** Default residual e=asset log return-benchmark log return (beta=1 explicitly). Flag robust residual |z|>=4; fitted alpha/beta is later.

**False positives / abstention:** A beta-one baseline is approximate; reject mismatched time windows or stale benchmark. No claim that benchmark fully explains causality.

**Natural Turkish label:** “Endeksten belirgin ayrışma”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-MKT-004 — Realized volatility shift
**Phase:** NEXT. **Trace:** FR-051. **Reading:** R02,R04.

**Required evidence:** Final returns over current and preceding equal-size windows.

**Method:** Compare sqrt(sum(r^2)) for equal-duration comparable windows; investigate high past-distribution quantile.

**False positives / abstention:** Overlapping windows are dependent; remove overnight gaps and adjust for missing bars.

**Natural Turkish label:** “Fiyat dalgalanması arttı”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-MKT-005 — Joint price and volume event
**Phase:** CORE. **Trace:** FR-053. **Reading:** R11.

**Required evidence:** AN-MKT-001 and 002; optional 003; same completed window.

**Method:** Join qualifying signals within one bar interval into one event; default HIGH, not CRITICAL.

**False positives / abstention:** Treat return/momentum/volatility as one market-price family; syndicated news does not provide independent confirmation.

**Natural Turkish label:** “Fiyat ve işlem hacminde olağandışı hareket”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-MKT-006 — Spread/liquidity deterioration
**Phase:** LATER. **Trace:** FR-048. **Reading:** R01.

**Required evidence:** Licensed synchronized bid/ask observations; quote age; tick size.

**Method:** Relative spread=(ask-bid)/mid; compare same-slot distribution and persistence.

**False positives / abstention:** Trades/OHLCV cannot reconstruct a spread; crossed/stale quotes are data errors.

**Natural Turkish label:** “Alış-satış farkı genişledi”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-MKT-007 — Cross-venue price divergence
**Phase:** LATER. **Trace:** FR-048. **Reading:** R01.

**Required evidence:** Simultaneous prices of identical economic asset, FX and fees.

**Method:** Compare FX-normalized robust venue differences against own baseline.

**False positives / abstention:** Bridged/wrapped assets, stale books and transfer restrictions can explain differences. Not an arbitrage recommendation.

**Natural Turkish label:** “Piyasalar arasında fiyat farkı arttı”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-FND-001 — Fund NAV/category divergence
**Phase:** NEXT. **Trace:** FR-036. **Reading:** R10.

**Required evidence:** Published NAV total returns; dated category membership; comparable peers.

**Method:** Compare matched valuation dates and currencies; median peer return plus robust residual, minimum 10 eligible peers.

**False positives / abstention:** Foreign-market valuation lag, FX, mandate and distributions can explain differences; daily not intraday NAV.

**Natural Turkish label:** “Fon getirisi benzerlerinden ayrıştı”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-FND-002 — Return-adjusted net-flow estimate
**Phase:** CONDITIONAL. **Trace:** FR-037. **Reading:** R10.

**Required evidence:** Two aligned AUM and NAV observations; distribution and unit-change status.

**Method:** Estimated flow=At-Aprev*(NAVt/NAVprev); rate=flow/Aprev. Investigate |rate|>=10% only after historical baseline checks.

**False positives / abstention:** No dates, placeholders or corporate restructuring => abstain. End-period approximation, not reported cash flow. Investor counts do not measure flow.

**Natural Turkish label:** “Tahmini net fon akışında belirgin değişim”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-FND-003 — Investor count change
**Phase:** CONDITIONAL. **Trace:** FR-034. **Reading:** R10.

**Required evidence:** At least two dated valid investor counts; history of comparable frequency.

**Method:** Percent and absolute change against past distribution; use provisional absolute percentage change >=10% plus absolute count change >=100 investors as a review trigger.

**False positives / abstention:** Source defaults zero are missing; count definition changes/mergers cause breaks. Does not measure capital moved.

**Natural Turkish label:** “Yatırımcı sayısında belirgin değişim”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-FND-004 — Asset-type allocation shift
**Phase:** CORE. **Trace:** FR-035. **Reading:** S06.

**Required evidence:** Two comparable published allocation snapshots; stable category mapping.

**Method:** For nonnegative distributions summing to one: D=0.5*sum(abs(wt-wprev)); candidate D>=0.20 or single category >=20 percentage points.

**False positives / abstention:** Price effects may change weights without trades. Negative/leverage weights use a separate signed exposure model; do not normalize them away.

**Natural Turkish label:** “Fonun varlık dağılımında belirgin değişim”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-FND-005 — Fund access/regulatory event
**Phase:** CORE. **Trace:** FR-055. **Reading:** S02,S03.

**Required evidence:** Official decision; exact affected fund identities; publication/effective dates.

**Method:** Structured extraction and entity validation; classify access restriction, liquidation notice or material prospectus change.

**False positives / abstention:** Notice is a verified event, not a statistical anomaly or verdict on unlisted funds. Current status requires subsequent updates.

**Natural Turkish label:** “Fonun işlem koşullarında önemli değişiklik”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-FND-006 — Reported holding concentration
**Phase:** LATER. **Trace:** FR-038. **Reading:** R10.

**Required evidence:** Security-level published holdings and reporting dates.

**Method:** Compute sum of top positions or HHI over verified comparable security weights.

**False positives / abstention:** Asset-type allocation cannot supply this signal; stale holdings and fund-of-fund look-through must be labeled.

**Natural Turkish label:** “Son açıklanan portföyde yoğunlaşma”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-FND-007 — Potential liquidity mismatch
**Phase:** LATER. **Trace:** FR-038. **Reading:** S03.

**Required evidence:** Dated holdings, redemption terms and licensed underlying liquidity measures.

**Method:** Review weighted illiquid exposure against disclosed redemption horizon.

**False positives / abstention:** Without reliable holdings and terms, insufficient evidence; not a claim of inability to redeem.

**Natural Turkish label:** “Likidite açısından incelenmesi gereken durum”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-EVT-001 — Material issuer disclosure
**Phase:** CORE. **Trace:** FR-055. **Reading:** S34,R13.

**Required evidence:** KAP text; amount/currency/period; matching financial scale.

**Method:** LLM extracts structured claims; deterministic math computes disclosed contract/TTM sales ratio if comparable.

**False positives / abstention:** Multi-year contract is not current-year revenue; currency/date/tax context required; no contract-profit inference.

**Natural Turkish label:** “Şirketten önemli açıklama”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-EVT-002 — US filing/earnings context
**Phase:** NEXT. **Trace:** FR-047. **Reading:** S09.

**Required evidence:** SEC accession and acceptance time; valid financial-period facts.

**Method:** Classify event, retrieve prior comparable period and calculate supported differences.

**False positives / abstention:** GAAP/non-GAAP, cumulative periods and revised facts cannot be mixed. No EPS surprise without licensed point-in-time consensus.

**Natural Turkish label:** “Finansal sonuçlar açıklandı”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-EVT-003 — Profit/cash-flow divergence
**Phase:** LATER. **Trace:** FR-048. **Reading:** S09.

**Required evidence:** Comparable filed income/cash-flow statements; sector and accounting regime.

**Method:** Compare earnings, operating cash flow and receivables using period-consistent ratios.

**False positives / abstention:** Negative denominators, inflation restatements, seasonality and bank accounting require separate models. Not accounting fraud.

**Natural Turkish label:** “Kâr ve nakit akışı farklı yönlerde değişti”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-EVT-004 — Source correction/material update
**Phase:** CORE. **Trace:** FR-070. **Reading:** R15.

**Required evidence:** Prior and new official document versions; affected event IDs.

**Method:** Content/version diff; revalidate citations and update or invalidate dependent events.

**False positives / abstention:** Do not erase original record; correction notifications require separate dedup class.

**Natural Turkish label:** “Önceki gelişmeyle ilgili düzeltme”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-ONC-001 — Large finalized transfer
**Phase:** CONDITIONAL. **Trace:** FR-043. **Reading:** S11,R12.

**Required evidence:** Verified chain/contract, decimals, finalized tx/log; supply or past transfer baseline.

**Method:** Compare transfer size with known supply/past sizes. MVP may display fact only where baseline absent.

**False positives / abstention:** Transfer is not sale; exchange attribution unknown unless dated label evidence. Internal treasury transfers and bridges are alternatives.

**Natural Turkish label:** “Büyük tutarlı zincir üstü transfer”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-ONC-002 — Token-account concentration
**Phase:** CONDITIONAL. **Trace:** FR-043. **Reading:** S12.

**Required evidence:** Mint/contract supply and verified account balances; account roles where known.

**Method:** Compute observed top-account share; Solana top 20 is partial account coverage.

**False positives / abstention:** Exchanges, liquidity pools, vesting and burn accounts are not independent beneficial owners. No wallet clustering claim.

**Natural Turkish label:** “Token hesaplarında yoğunlaşma”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-ONC-003 — Pool-liquidity change
**Phase:** LATER. **Trace:** FR-043. **Reading:** S13.

**Required evidence:** Comparable same-pool reserve/supply snapshots and prices.

**Method:** Separate reserve-unit changes from mark-to-market USD changes; compare against own history.

**False positives / abstention:** Single current snapshot cannot establish prior withdrawal; V3 liquidity ranges and rebalancing need specialized handling.

**Natural Turkish label:** “Havuz likiditesinde belirgin değişim”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-ONC-004 — Token authority/contract change
**Phase:** LATER. **Trace:** FR-043. **Reading:** S11,S12.

**Required evidence:** Known ABI/program capability and finalized verified state transitions.

**Method:** Compare supported mint/freeze/upgrade/admin permissions across versions.

**False positives / abstention:** Permission existence alone is not exploit evidence; proxy/Token-2022 semantics require explicit support.

**Natural Turkish label:** “Token yetkilerinde değişiklik”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-ONC-005 — Scheduled supply unlock
**Phase:** LATER. **Trace:** FR-043. **Reading:** R12.

**Required evidence:** Verified issuer vesting schedule; circulating supply; revisions.

**Method:** Calculate dated scheduled unlock share and relevance; label scheduled, not observed transfer.

**False positives / abstention:** Schedule can change; already liquid allocations differ from new supply. No forecasted price effect.

**Natural Turkish label:** “Token kilit açılışı yaklaşıyor”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-CMP-001 — Market/on-chain contextual event
**Phase:** CONDITIONAL. **Trace:** FR-044. **Reading:** R11,R12,R14.

**Required evidence:** Qualified market event plus finalized on-chain observation with matching asset/window.

**Method:** Create one event with separate evidence families; LLM investigates plausible links and alternatives.

**False positives / abstention:** Temporal co-occurrence is not causal coordination; combined magnitude alone cannot become global CRITICAL.

**Natural Turkish label:** “Piyasa ve zincir üstü verilerde eş zamanlı hareket”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-CMP-002 — Fund/share relationship event
**Phase:** LATER. **Trace:** FR-038. **Reading:** S03.

**Required evidence:** Published security holdings, fund event, licensed stock event, availability timestamps.

**Method:** Relate historical disclosed exposure to contemporaneous market evidence.

**False positives / abstention:** Never infer present-day holdings or directional causation from old allocation classes.

**Natural Turkish label:** “Fonun açıklanan yatırımlarında önemli gelişme”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-DQ-001 — Stale or failed source
**Phase:** CORE. **Trace:** FR-103. **Reading:** S04.

**Required evidence:** Expected calendar/cadence; heartbeat; last valid observation.

**Method:** Compare last valid availability against source schedule; set stale/circuit-open.

**False positives / abstention:** Weekends and unreleased NAV are not outages. Operational warning, not asset financial severity.

**Natural Turkish label:** “Bu veri kaynağı güncel değil”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-DQ-002 — Missing/placeholder/invalid observation
**Phase:** CORE. **Trace:** FR-048. **Reading:** S06.

**Required evidence:** Provider raw record and schema; field-level quality.

**Method:** Flag null/default placeholders, inconsistent units, invalid OHLC or unidentified dates.

**False positives / abstention:** Do not convert missing into zero. Quarantine record; skip dependent detector.

**Natural Turkish label:** “Bu gösterge için yeterli veri yok”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

### AN-DQ-003 — Corporate-action/session break
**Phase:** CORE. **Trace:** FR-050. **Reading:** R01,R02.

**Required evidence:** Action calendar, adjusted-state metadata, session calendar.

**Method:** Mark baseline-incompatible periods and suppress mechanically induced discontinuities.

**False positives / abstention:** Price split is not a crash; unresolved adjustment means no claim, not guessed correction.

**Natural Turkish label:** “Hesaplama için veri düzeltmesi gerekiyor”.

**Acceptance:** positive fixture triggers only with required evidence; normal control does not trigger; missing/stale input abstains; later-added evidence cannot change a frozen earlier decision. No standalone criminal label or trading instruction.

## Catalog selection checkpoint
For the first end-to-end demonstration select MKT-001/002/003/005, FND-004 or a verified FND-005, EVT-001 and DQ guards. FND-002/003 require real historical AUM/count data and stay disabled by default. ONC-001/002 and CMP-001 are enabled only after chain identity/finality coverage is demonstrated. Fund category divergence can substitute only if valid peers exist; no substitute metric is fabricated.


## v0.4 source-role clarification
`research/anomaly_source_roles.json` and each catalog object distinguish method, data, background, project heuristic and validation sources for all 28 entries. Every validation list is empty: no empirical Project 50K detector evaluation has been completed. KAP interface support is S34, not SEC EDGAR S09. R10 does not derive the holdings/HHI formula; R12 is background for unlock risk rather than validation of a vesting detector. Thresholds/formulas not derived from the stated research remain project hypotheses. AN-FND-002 uses a neutral signed-flow label; inflow and outflow must not share an outflow-only headline.

## v0.5 research continuation
The v0.5 engine labs test selected interpretation/quality failures, not all 28 catalog detectors or their thresholds. In particular, fund endpoint residual is not generally exact cash; count is not money; composition distance is not turnover. Read research/engine_lab/FUND_ENGINE.md before detector implementation. No configured threshold changed in this research task.

## Problem solution and market research continuation 3 October 2026

All28 definitions/configured thresholds remain unchanged and all empirical frequencies are NOT_ESTIMATED/null in the frequency map. Count raw candidates, distinct episodes, user-relevant investigations and actual deliveries separately. Scheduled unlocks/revisions and observed finalized transfers require different exposures. See `reports/PROBLEM_MARKET_RESEARCH.md` and the linked source-depth appendices.

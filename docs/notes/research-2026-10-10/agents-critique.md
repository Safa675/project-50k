# Adversarial review: agent-team design

Read-only, 2026-10-10. Nothing was installed, run or written. Inputs: the design; DEC-027, DEC-028 and DEC-029; the plan; `docs/notes/research-2026-10-10/*`; `uv.lock`; the TradingAgents clone at `1394a3f`; six web pages. Hours and dollars are estimates. **[U]** = unverified.

**Verdict.** Approve (d) only in the cut form of finding 3. Fix 1, 4, 5, 6 and 7 before any live run, and fix 2 before a mentor or judge sees anything.

### 1. Critical: a fund under the SPK order can come out "önemli değil"
- **Break.**
  - Plan §6 removes `NOT_MATERIAL` only when no detector covers the fund. A CONFIRMED AN-FND-005 event removes neither `NOT_MATERIAL` nor `DATA_ISSUE`.
  - C argues benign codes, and `SUPPORTED_BY_PACKET` needs only a cited ID that exists. The validator checks that the ID exists and its `kind`, not whether it supports the claim.
  - The halt freezes the price, so AN-DQ fires (plan §5) and `DATA_QUALITY` looks supported. The 131 funds were ordered on one date, so `MARKET_WIDE_MOVE` can look supported too.
  - K then proposes `NOT_MATERIAL` or `DATA_ISSUE` for a fund under a liquidation order. In the transcript and the B2B report, that reads as "safe".
- **Fix.**
  - The server computes `allowed_alternatives` for each packet from preconditions fixed in DEC-030 before any run:
    - `SHORT_HISTORY` needs a D5 age bound.
    - `DATA_QUALITY` needs an AN-DQ event that the halt does not explain.
    - `NATURALLY_SMOOTH_FUND_TYPE` needs a fixed category list.
    - `MARKET_WIDE_MOVE` needs a fixed same-date share of category triggers.
  - `OTHER` never supports `NOT_MATERIAL`.
  - A confirmed in-scope event removes `NOT_MATERIAL` and `DATA_ISSUE`, and alternatives cannot target it.
  - C's and K's dispositions cannot be overridden, so they stay in the app as "ara çıktı" and out of the B2B export.

### 2. High: the PDF still reads as a policy schedule
- **Break.** Together, these make a policy form with blanks:
  - the "Koşul Özeti" title;
  - blank rows for premium, rate, cap, limit, waiting period and payout;
  - blank insurer and channel fields;
  - "exclusions";
  - the statuses "ONAY BEKLİYOR" and "İÇ ONAYLI".

  "Onaylı … koşul" echoes the regulator-approved general conditions (Law 5684 art. 11, `research-product.md:18`; legal reading [U]). Section 6's AI assessment can only repeat `trigger_fired` or say `UNDETERMINED` (design §1), so all it adds is the look of a claims opinion. Claims investigation reportedly became a licensed support service in July 2026 (`research-product.md:21`, secondary source [U]). W adds only two phrases to the wording list.
- **Fix.**
  - Retitle the document "Tetikleyici Endeksi ve Kanıt Spesifikasyonu (sigortacı incelemesi için taslak)".
  - Replace the blank rows and parties with one fixed sentence: cover, premium, payment and eligibility belong to a licensed insurer, and no agreement with an insurer or channel exists. Safa's answers appear as questions, never as values.
  - Rename the statuses "İNCELEME BEKLİYOR" and "İÇ İNCELEMEDEN GEÇTİ".
  - Replace the exclusions with the fixed text "tetikleyici tanımına girmeyen olaylar", and drop `exclusions_rationale_tr`.
  - Show section 6 only in the app, with its override.
  - Ban the coverage vocabulary in all LLM text: teminat, kapsam, tazminat, hasar, prim, poliçe, sigortalı, sigorta ettiren, ödenecek, hak kazanır, muafiyet.

### 3. High: the design does not fit before the freeze, and two calls give the same demo value
- **Break.**
  - Before its cuts, the plan was about 30 h of work against 14–16 h available. This design adds another 7–10 h (§7).
  - Its gate ("story documents after the 08:30 pass") puts T5.4-INS (4.25 h) into the 08:30–10:30 window, which already holds T5.2, T5.4 and T5.5.
  - A1–A3 restate deterministic slices that the server already turns into briefs for skipped slices (§2).
  - The design's own sources say debate adds little at equal compute (§8), so the demo value is the audit trail.
- **Fix.** Decide now:
  - Server briefs for every slice, then C → K (2 calls) on the T3.4 runner (≈1.5–2 h), plus `/ekip/[run]` (1.5 h).
  - For insurance, a deterministic HTML print view of the trigger definition, the event evidence and K's decision with its review. Approval binds to `data_sha256` (≈2 h).
  - The analysts, W, Typst, the re-render and the B2B PDF move to after the freeze.
  - `B2B` stops being a run mode. §4 says "same run", and a separate mode in the cache key pays again.

  This saves about 3–5 h and 3–4 calls per run. It still needs M3 by 01:00; otherwise ship the core single call and the print view.

### 4. High: model failures are reported as missing evidence, and analysts decide what K sees
- **Break.**
  - K gets the briefs, not the slices (roster). An analyst that leaves out a triggered item hides it from K.
  - An `INVALID` analyst becomes the absence marker "kanıt mevcut değil".
  - Two `INVALID` K outputs print "kanıt yetersiz".
  - Both texts are false when the evidence exists and only the model failed.

  Chained with finding 6: one "bir" makes A1 `INVALID`. K then sees no price evidence for a fund whose D1–D4 fired. It cannot cite a triggered item for `MATERIAL`, so it proposes `NOT_MATERIAL` or `INSUFFICIENT_EVIDENCE`. Nobody can review that step.
- **Fix.**
  - K always receives the server slice: every item ID and its state.
  - An `INVALID` analyst is replaced by the server brief, flagged "analist çıktısı doğrulanamadı".
  - A cross-step check requires every TRIGGERED or CONFIRMED item to appear in a brief.
  - A failure reads "Yapay zekâ önerisi üretilemedi; insan incelemesi gerekli" and goes to the queue.

### 5. High: human review is bound neither across decision methods nor to documents
- **Break.**
  - A packet can hold a SINGLE row (from the 08:30 pass) and a TEAM row (run on demand). The design does not say which one is effective, or whether a TEAM row reopens a human override.
  - One review covers both materiality and `trigger_assessment`.
  - Approval binds only `pdf_sha256`. An admin can approve a PDF whose decision was later overridden or rejected, or whose packet has since gained an event. The PDF prints only the AI value.
- **Fix.**
  - The effective value is the latest human review on any decision for the current packet. A later AI row never displaces it; it is shown as "farklı yapay zekâ önerisi".
  - Each field gets its own review.
  - `ai.documents` stores `decision_id`, `review_id` and `packet_sha256`.
  - A document renders only after a human review, and approval returns 409 if any of those three has changed.
  - The PDF prints the AI value, the human value, the reviewer and the time.

### 6. High: the validator is both too strict and too loose for Turkish
- **Too strict.**
  - Plan §6 fails "any Turkish number word", and the integrity review lists "bir" among them (`plan-review-integrity.md:73`).
  - "Bir" is also the indefinite article, so the project's own copy fails: "ayrı bir arşiv kesitidir" and "bir güvenlik değerlendirmesi değildir" (`dated_contracts.py:51-53`).
  - With up to six text steps per run, runs fail closed in bulk, and the rushed fix will be to delete the check.
- **Too loose.** It misses:
  - magnitude claims without digits ("çok üzerinde", "olağanüstü");
  - a threshold placeholder used as if it were the value;
  - uppercase text: `str.lower()` leaves "MANİPÜLASYON" with a combining dot and turns "I" into "i", never "ı".
- **Fix.**
  - Fail number words only when they act as numerals, that is, before a unit, time or magnitude noun (gün, ay, yıl, kat, puan, yüzde, bin, milyon).
  - Render `{{ev:<id>}}` as a labelled value and threshold, plus a magnitude band computed on the server. Ban intensity adjectives.
  - Fold İ, I, ı and i together before matching.
  - The test corpus includes valid sentences with many "bir" and invalid sentences in capitals.
  - Gate the 08:30 pass on the `INVALID` rate of the 20 tuning calls.

### 7. Medium-high: SDK retries, timeouts and crashes break the "exact" reservations
- **Break.**
  - openai-python retries twice by default (connection errors, 408, 409, 429, ≥500) and times out after 10 minutes, so one logical call can become three attempts.
  - Unless the 60 s limit is set on the client itself, a hung call can outlive the 6-minute lease and be repeated by a second worker. A call that times out may still be billed [U].
  - A crash between reserving and settling leaves the mutable bucket row wrong.
  - Both models allow 128k output tokens. K's $0.056 reservation assumes a few thousand, and medium reasoning may use more [U]. The response then comes back incomplete, is marked `INVALID`, and gets a paid retry.
  - `INVALID` results are never cached, so every press of "Ekibi çalıştır" pays again.
- **Fix.**
  - Set `max_retries=0` and `timeout=60` on the client. The runner does the retries and reserves budget for each one.
  - Give every step an explicit `max_output_tokens` and price the reservation from it.
  - Store reservations as rows with `expires_at`. A timeout or expiry settles at the worst case and is never released.
  - After an `INVALID`, block reruns of the same packet and prompt.
  - Keep K at `low` unless tuning shows it needs more.
  - Size the 08:30 pass from the measured p90 cost, and put the demo funds first.

### 8. Medium-high: live-demo latency
- **Break.** A run is three to four model stages in sequence plus Typst, with K at `medium`. The limits are 60 s per call and 4 minutes per run, and on-demand jobs have no stated priority over batch jobs. A wait of tens of seconds or more [U] inside a pitch of about 5 minutes is likely.
- **Fix.**
  - Demo from runs stored after the 08:30 pass. Re-running a stored packet gives an instant cache hit, labelled as such.
  - For a live moment, run C → K only, with K at `low` and priority over batch jobs, and fall back to the stored run after 60 s.
  - The Fast tier costs 2× (how to select it is [U]).
  - Rate limits are not the constraint: sol gets 1M TPM on the lowest listed tier (this account's tier is [U]).

### 9. Medium: Turkish PDFs in Docker
- **Break.**
  - `typst` is not in `uv.lock`, and the fonts need an apt layer. Adding them on Sunday means re-locking and rebuilding the worker during the 08:30 pass, over venue Wi-Fi.
  - The slim image has no `tr_TR` locale, so `setlocale` raises an error and `%B` gives "September".
  - `document.date` defaults to the compile time, which makes the equal-hash test fragile.
  - The footer hardcodes `HISTORICAL_REPLAY`, but runs on current data are not replays.
  - A replay packet must not carry the 2026-10-06 TEFAS status, because it reveals the halt.
  - WeasyPrint needs Pango.
- **Fix.**
  - Add `typst` 0.15.0 and `fonts-dejavu-core` now, in T1.3 and T1.2.
  - Format dates with `MONTH_NAMES_TR`, imported read-only from the registered `dated_contracts.py:68`, and numbers with a hand-written formatter. Test both in the container.
  - Drop the determinism test: approval binds to the stored bytes.
  - Use no `upper()` in show rules.
  - Take the origin and cutoff from the document row, and require `available_at` ≤ cutoff.
  - Fall back to browser printing.

### 10. Low: licence obligations if TradingAgents code is copied
- **Break.** The clone is Apache-2.0, with no `NOTICE` file and no copyright lines in its Python files. Re-implementing its patterns carries no §4 duty. Copying code or comments (for example `tradingagents/agents/context.py:190-201`) into the pushed repository is redistribution [repository visibility U], which triggers:
  - §4(a): include a copy of the licence;
  - §4(b): add prominent change notices;
  - §4(c): keep the original notices.

  §6 allows the name only to describe where the code came from.
- **Fix.**
  - DEC-030 records that no code is copied.
  - If any is copied, add `LICENSES/Apache-2.0.txt`, `THIRD_PARTY_NOTICES.md` and the header "Adapted from TauricResearch/TradingAgents @1394a3f (Apache-2.0), modified".
  - Say "TradingAgents-inspired", and cite arXiv 2412.20138.

## What held up
- There is no debate loop: one round, at most 8 calls and a 4-minute deadline.
- Budget buckets and per-user caps block runs across all funds.
- Option (d) avoids the framework collision.
- The prices match OpenAI's pricing page.

## Sources (accessed 2026-10-10)
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/docs/models/gpt-6.1-sol and `/gpt-6-luna`
- https://github.com/openai/openai-python (README)
- https://pypi.org/project/typst/
- https://typst.app/docs/reference/model/document/
- The plan: `C:\Users\mirza\AppData\Local\Temp\claude\c--Users-mirza-Desktop-Hackathon-project-50k\fcb59ff2-d20e-4984-b01d-14d47f0bf736\scratchpad\app-lf\plans\2026-10-10-product-build-plan.md`
- Repository files under `C:\Users\mirza\Desktop\Hackathon\project-50k\`:
  - `docs\notes\research-2026-10-10\research-product.md`
  - `docs\notes\research-2026-10-10\plan-review-integrity.md`
  - `services\p50k\research_reviews\dated_contracts.py`
  - `uv.lock`
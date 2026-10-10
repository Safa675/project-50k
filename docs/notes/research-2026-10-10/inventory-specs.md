# Handoff v0.5 and DEC-024–029 mapped to the new direction

Status at 2026-10-10, about 12:45. Two new decisions were committed while I was working (`36cffaf`) and they settle several of the collisions in section 4:
- **DEC-028:** AI-native build on localhost, the product's own auth, PostgreSQL, OpenAI with a $25 limit.
- **DEC-029:** every downloaded fund is opened and there is no held-out test set.

Paths are relative to `C:\Users\mirza\Desktop\Hackathon\project-50k`. `docs/NN` means `docs/handoff-v0.5/docs/NN_*.md`.

**Data on disk (counts only):**
- **TEFAS prices:** 2,022 price files in `raw/tefas/prices` (5-year daily).
- **Forward snapshots:** `~/.local/share/project-50k/fund_snapshots_forward.sqlite3`. Its 2026-10-10 log reports 1,071 TEFAS-traded funds, 8 of them undated. I did not open the database.
- **KAP:** 1,342 PDFs and 101 monthly series under `raw/kap/`. The spike parsed 1,246 of 1,255 reports. KAP's report list reaches back only 365 days.
- **SPK:** one bulletin PDF in `raw/spk`.

## 1. Fund anomaly catalog against the team's data

Sources: `docs/12`, `config/anomaly_catalog.json` (every threshold is `PROVISIONAL_NOT_EMPIRICALLY_VALIDATED`) and `research/spikes/2026-10-06-tefas/REPORT.md`.

| Entry (phase) | Definition and threshold | Data needs | Implementable before the freeze? |
|---|---|---|---|
| AN-FND-001 NAV/category divergence (NEXT) | Fund return minus the median peer return on matched dates, as a robust residual. Needs at least 10 eligible peers. No fund-specific cut-off; the nearest is the generic robust z ≥ 4 in `config/detection_defaults.json` | Dated NAV, dated category membership, distributions | **Yes, with a disclosed deviation.** Prices cover about 2,000 funds, but only today's category exists, which brings survivorship bias. D1 and D2 are its preregistered one-sided variants |
| AN-FND-002 Net-flow estimate (CONDITIONAL) | flow = A_t − A_prev·(NAV_t/NAV_prev). Review when the absolute rate is ≥ 10%, only after baseline checks (≥ 20 observations) | Two aligned, dated AUM and NAV values; distribution and unit-change status | **Monthly arithmetic: yes, for about 100 funds** from KAP (`services/p50k/detectors/fund_flow.py`). The 11 monthly changes are under the 20-observation baseline, so the trigger stays ABSTAINED. **Daily: no.** Snapshots began on 2026-10-06 and the forward series on 2026-10-09, and TEFAS publishes no new date this weekend |
| AN-FND-003 Investor-count change (CONDITIONAL) | Change of ≥ 10% and ≥ 100 investors, judged against the past distribution | Dated counts with history | **No.** Counts exist only in daily snapshots (first run 2026-10-06), not in TEFAS history or KAP. Only the plumbing can be built now |
| AN-FND-004 Allocation shift (CORE) | D = 0.5·Σabs(w_t − w_prev) ≥ 0.20, or any one category moves ≥ 20 percentage points. Signed or leveraged weights are modelled separately | Two comparable, dated allocations | **Yes, monthly, for about 100 funds**, from the KAP monthly-average asset mix (`detectors/fund_allocation.py`, supported layouts only). The TEFAS allocation path is not admissible because it needs an Akamai bypass |
| AN-FND-005 Access/regulatory event (CORE) | Extract official notices and validate the fund identities: access restriction, liquidation, material prospectus change | The official decision, exact fund identities, publication and effective dates | **Partly.** The 17 September 2026 SPK case is covered (`raw/spk`, `liquidated_funds.json`). There is no live KAP/SPK fund-disclosure adapter. This is the best insurance trigger |
| AN-FND-006 Holding concentration (LATER) | Top-N share or HHI of verified security weights | Dated security-level holdings | **Descriptive only**, for about 100 funds (`research_reviews/concentration.py`). No alarm threshold is defined |
| AN-FND-007 Liquidity mismatch (LATER) | Illiquid exposure compared with the redemption horizon | Holdings, redemption terms, licensed liquidity data | **No** |

DEC-024 also keeps four data-quality and correction guards active:
- **AN-DQ-001, stale source:** yes, from the job logs and a weekday calendar. Holidays are not verified.
- **AN-DQ-002, placeholders:** yes. A zero price counts as missing, and a price that stops is surfaced as an event.
- **AN-DQ-003, baseline break:** partly; there is no fund corporate-action calendar.
- **AN-EVT-004, correction:** partly; it needs versioned disclosures.

D3 (returns too smooth), D4 (decoupled from peers) and D5 (fund younger than 730 days) have no catalog IDs. D5 is a fund attribute, not an anomaly.

**Leftover problem from DEC-029:** `price_detectors/results.json` stores thresholds for only 4 of the 12 top-100 categories for D1, D2 and D4, and 7 of 12 for D3. Widening the peer set also changes the D1/D2/D4 statistic. Unless a dated recalibration note is written, most funds will abstain.

## 2. The handoff's AI design and the rule "the LLM decides, a human can override"

**What each component was meant to do**
- **Investigator** (`prompts/RUNTIME_INVESTIGATOR.md`, `docs/17` sections 1–3):
  - For each event it classifies disclosures, resolves entities and gathers context. It also lists competing explanations and missing evidence.
  - Input follows `contracts/investigation_packet.schema.json`.
  - Output is claims with evidence IDs, support types, limitations and a *suggested* classification. The server decides publication and severity.
- **Evidence reviewer** (`prompts/RUNTIME_EVIDENCE_REVIEWER.md`): an optional second model, with no web access. It labels each claim SUPPORTED, UNSUPPORTED, CONTRADICTED or INTERPRETATION_WITH_LIMITS. The app blocks unsupported claims either way.
- **Asset chat** (`prompts/RUNTIME_ASSET_ASSISTANT.md`; FR-094–098; OpenAPI `POST /assets/{asset_id}/chat` and `GET /chat/threads/{thread_id}`): Turkish answers in `contracts/ai_answer.schema.json`. Every claim needs at least one evidence ID, and the server does the calculations (RATIO only).
- **Tools** (`docs/17` section 2): get_asset, get_observations, get_events, search_documents, web_research, calculate and get_methodology.
  - Limits per request: 6 calls, 2 searches, 8 sources, 45 s.
  - Limit per user: 10 chat turns a day (`config/notification_defaults.json`).

**Guardrails**
- **Evidence-bound claims.** Claims cite existing evidence, and numbers come only from deterministic calculations. No URL or ID is invented, and insufficient evidence is said plainly (FR-058, FR-061, NFR-027–029).
- **Validation before display.** In order: schema, identity and time eligibility, reference existence, arithmetic recomputation, sentence support, then an advice and allegation check. Output is held back until it passes (`docs/17` section 4, NFR-009, NFR-031).
- **Read-only tools, validated on the server.** Retrieved text is data, not instructions. No private data goes into queries. No SQL, shell, URLs, threshold or role changes, and no sending (`docs/17` sections 2 and 6, NFR-032).
- **No advice or allegations.** No buy, hold or sell, and an anomaly is not called fraud (FR-062, FR-071, NFR-071/072).
- **Deterministic scoring.**
  - Confidence is evidence strength: 100·(0.35Q+0.25F+0.25I+0.15C), with `calibrated_probability` set to null.
  - Severity comes from rules, never from the LLM (FR-066/067, NFR-030).
  - If the LLM times out, a metric-only event still shows (`docs/13` section 5, FR-074).
- **Gaps in the handoff.** There are no strict output schemas for the investigator or the reviewer, and the calculation contract covers RATIO only.

**How to adapt it (consistent with DEC-028's AI rules)**
1. **The LLM decides from fixed options and never outputs a number.**
   - `materiality`: MATERIAL, NOT_MATERIAL, DATA_ISSUE or INSUFFICIENT_EVIDENCE.
   - `classification`: explained by an official notice, or unexplained.
   - `disposition`: PUBLISH or HOLD_FOR_REVIEW.
   - For insurance, `trigger_assessment`: MET, NOT_MET or UNDETERMINED, judged against a machine-readable term sheet.
   - Every decision carries a Turkish rationale and the evidence IDs it relies on.
2. **Deterministic limits around the LLM.**
   - The detectors and the hard gates in `docs/13` section 2 run first, and the LLM chooses only among the actions they allow.
   - It never changes scores, severity or thresholds.
   - It never releases a CRITICAL event; that stays the admin's `POST /admin/events/{event_id}/release`.
   - It never authorizes a payment; the institution pays.
3. **Append-only tables**, modelled on `private.event_release_decisions` and `private.settings_versions`:
   - `ai_decisions` records the event and revision, type, value, rationale, evidence IDs, packet hash, model ID, prompt hash, validation result and time.
   - `decision_overrides` records the decision, who overrode it, the new value, a required reason and the time.
   - The latest human override is the value that counts. Re-running the AI on the same revision cannot displace it.
4. **Every decision type can be overridden**, with roles checked on the server (FR-011, NFR-012). The interface shows the AI value, the human value, and who changed it, when and why (UR-072, FR-106/107).
5. **Fail closed.** Invalid output, a timeout or an exhausted budget produces `UNDECIDED`, the deterministic view, and an entry in the human review queue.
6. **Cost controls.**
   - An admin `ai_paused` switch beside the existing `generation_paused`.
   - Each call reserves its cost in `private.budget_ledger` first.
   - The AI runs only on TRIGGERED events and on request.
   - Pricing, from the page fetched 2026-10-10 (verify before pinning a model): small models cost $0.05–0.25 per million input tokens and $0.40–2.00 per million output tokens.
   - A decision with 8,000 input and 1,000 output tokens costs about $0.004 at the top rates, so $25 covers roughly 6,000 decisions. The real budget risk is chat and tool loops.
7. **Chat stays read-only.** It explains data and decisions. A "re-evaluate" action creates a new decision, which can also be overridden. Web research stays off this weekend.
8. **Enforcement.** Use OpenAI Structured Outputs with a strict JSON schema, then re-validate on the server with Pydantic. Whether strict mode accepts the handoff schemas' `format`, `pattern` and `if/then` keywords is unverified.

## 3. Vertical slices

The registry has 284 IDs: 80 user (UR), 122 functional (FR) and 82 non-functional (NFR) requirements, all NOT_IMPLEMENTED. By legacy priority: 237 P0, 9 qualified P0, 34 P1 and 4 P2. The numbers in brackets count IDs per document area. In the last column, "Must" means needed before the Sunday freeze and "Should" means a thin version if time allows.

| Slice | Areas (IDs) | Key IDs | Freeze |
|---|---|---|---|
| Fund catalog | UR-001–005 (5); FR-001–005 (5) | FR-001, FR-003, FR-004, FR-031, UR-005, NFR-007 | Must |
| Fund detail | UR-034–039 (6); FR-031–038 (8); FR-076–080 (5) | FR-032, FR-033/034 (dated values only), FR-035, FR-075, FR-078, UR-035, NFR-024 | Must |
| Anomaly feed | UR-015–019 (5); UR-020–028 (9); FR-072–075 (4); FR-081–084 (4); watchlist UR-010–014 and FR-012–016 (10); feedback (6) | UR-019/FR-084 (quiet state), UR-022/023, UR-028, FR-072–074, FR-083. The watchlist becomes the customer's list of monitored funds | Must |
| Detector runs | FR-048–054 (7); FR-064–071 (8); NFR-035–040 (6); FR-108–111 (4); UR-078–080 (3) | FR-037, FR-048, FR-054, FR-064, FR-066–069, NFR-035–038, NFR-046, FR-109 | Must |
| Evidence and provenance | NFR-022–026 (5); FR-120–122 (3); NFR-001–005 (5) | NFR-001, NFR-022, NFR-023, FR-120, UR-025–027 | Must |
| AI decisions and override | FR-055–063 (9); NFR-027–034 (8) | FR-055–057, FR-061, FR-062, NFR-030, NFR-031, NFR-034, FR-122. Overrides need new IDs | Must |
| AI chat | UR-048–056 (9); FR-094–098 (5) | UR-048, UR-052, UR-054, UR-055, FR-094, FR-096–098, NFR-009, NFR-016 | Must |
| Auth | UR-006–009 (4); FR-006–011 (6); NFR-011–021 (11) | FR-009–011, NFR-012, NFR-013, NFR-015, NFR-020 | Must |
| Admin | UR-067–072 (6); FR-102–107 (6); NFR-041–045 (5) | FR-103–105, FR-107, NFR-017, NFR-044 | Should |
| B2B API | No IDs exist | Nearest: NFR-047, NFR-052, NFR-073/074 and `public_event.schema.json`. API keys, quotas and exports need new IDs | Should |
| Ingestion | FR-017–023 (7) | FR-017, FR-018, FR-020, FR-021, FR-023, NFR-025, NFR-049 | Must |
| Database | NFR-046–049 (4) | NFR-014, NFR-048, NFR-077; `contracts/domain_tables.json` lists 25 tables | Must |
| Deployment and operations | NFR-006–010 (5); NFR-050–055 (6); NFR-075–082 (8) | NFR-043, NFR-075, NFR-076, NFR-078 (the research app is the fallback demo), NFR-079 | Must |
| Design and accessibility | UR-073–077 (5); FR-112–119 (8); NFR-056–069 (14) | UR-073, UR-075, NFR-058, NFR-060, NFR-063, NFR-066/067 | Must (Barış) |

Out of scope before the freeze:
- **34 IDs for the markets DEC-024 postponed:** UR-029–033, UR-040–047, FR-024–030, FR-039–047, FR-049, FR-052, FR-077, FR-079 and FR-080.
- **17 e-mail and notification IDs behind release gate G06:** UR-057–063, FR-085–093 and FR-121.

## 4. Collisions

**Already settled by DEC-028 and DEC-029:**
- the development/test split;
- plain PostgreSQL instead of Supabase;
- email/password sign-in instead of Google-only, which affects FR-006, NFR-011, UR-006 and FR-116;
- the OpenAI key as the only service account, with its $25 counted toward the TRY 5,000 ceiling.

**Still open:**

| # | Collision | Proposed resolution | Who decides |
|---|---|---|---|
| 1 | D1–D5 stored thresholds vs. monitoring all funds (section 1) | Write a dated recalibration note on pre-2025-10-06 data covering all categories, labelled as a development result. Show ABSTAINED until then | Mirza |
| 2 | "The LLM decides" vs. "the server decides publication and severity" (`docs/17`, FR-066) | The limits in section 2, recorded in a new decision record. For the freeze, team analysts override globally. Per-customer overrides need tenant scoping, because events are shared (NFR-047) | Mirza |
| 3 | Insurance pricing vs. evidence strength not being a probability (DEC-002), no measured evaluation (G10), and only one labelled event cluster | Pitch triggers and event history, not premiums. A price stop is neither timely nor complete: 110 of the 131 ordered funds still showed a price on 2026-10-06. "Act of god" triggers have no catalog entry and no data | Team (Safa leads) |
| 4 | Designing policies vs. insurance licensing (Law 5684, regulator SEDDK; details unverified) | Act as a trigger-data provider to licensed insurers: never underwrite, sell or hold money. Get legal advice before any claim | Safa |
| 5 | Selling B2B signals vs. SPK licensing for investment advice (Law 6362; details unverified) and NFR-070/071 | Offer descriptive signals only, with no recommendations. Get a legal check | Safa |
| 6 | Selling or integrating data vs. unreviewed TEFAS, KAP and MKK data rights (DEC-025/027, NFR-074) | Keep real data on localhost. Put a `rights_status` on API records and keep external access off. No contact with institutions without authorization | Safa |
| 7 | Sending data and chats to OpenAI vs. model-processing rights (`docs/17` section 3) and Turkish data-protection (KVKK) review of transfers abroad (`docs/19` section 4, gate G07) | Team-only accounts. Send derived evidence packets with no personal data. Clear G07 before any public accounts. OpenAI says API data is not used for training by default and abuse logs are kept up to 30 days (from a search snippet) | Safa; Mirza for data minimization |
| 8 | New code vs. the files the live demo's sealed bundles depend on (`.claude/rules/registered-runtime.md`; hooks block edits; the main checkout must stay untouched while the demo runs) | Put new code in new modules that import those helpers read-only. Build in a worktree. Don't switch branches in the main checkout while the demo runs | Mirza |
| 9 | The frozen requirements registry vs. new requirements (B2B keys, quotas, overrides, organizations, own auth) | Create a new requirements file outside the handoff with its own ID namespace. Set statuses only after tests pass | Mirza |
| 10 | Anonymous public pages (UR-001, FR-005, FR-116) vs. B2B use and data rights | Real-data pages behind login; a public landing page with no real data | Team (Barış, Safa) |
| 11 | Chat web research marked P0 (UR-051, FR-060) vs. the $25 limit and prompt-injection risk | Keep it off until after the freeze | Mirza |
| 12 | The pitch vs. the do-not-claim list | No accuracy, lead-time, demand or SPK-motive claims. No flagged fund names on slides other than the eight targets | Barış, Safa |
| 13 | Designer approval (G09) vs. screens Barış won't design | Mirza applies `config/design_tokens.json`; Barış reviews before the freeze | Barış |
| 14 | "All funds" vs. KAP depth (about 100 funds, 365 days, roughly one request every 6 s) | Show which detectors cover each fund (DEC-013) | Mirza |

## 5. What stays binding and what can flex

**Binding integrity rules:**
- No fabricated or zero-filled data. TEFAS zero prices and borsapy placeholders count as missing (NFR-001, DEC-003).
- Fund NAV appears only at its published cadence (DEC-001, FR-032).
- Full provenance and point-in-time inputs, with no future data leaking into the past (NFR-022/023, NFR-038).
- Honest origin labels. Unknown or abstained is not normal, and no alert does not mean safe (DEC-011).
- Detectors are deterministic and versioned. The LLM never changes a number (FR-054, DEC-028).
- Evidence strength is not a probability, and severity stays separate (DEC-002, NFR-030).
- An anomaly is not fraud, and a liquidation is not a total loss (NFR-072, `docs/13` section 4).
- No buy, hold or sell advice (NFR-071).
- AI output is tied to evidence and checked against a schema, and its tools are read-only (NFR-027–032).
- Overrides are stored beside AI decisions, never in their place. Event revisions are immutable.
- Authorization happens on the server, and secrets live only in `.env`.
- No real values in git. Real data stays on localhost, and committed files name only the eight targets (DEC-027/029).
- Every detector figure is labelled a development result (DEC-029).
- The TRY 5,000 ceiling holds, with no unapproved spending or outside contact (DEC-020/028).
- Frozen protocols stay frozen, and merges are merge commits only.

**Product requirements that can flex:**
- Market scope.
- The retail (B2C) persona, core user loop and anonymous pages.
- Auth and hosting choices.
- E-mail.
- Chat web research.
- The AI's role and the event state machine, within the binding rules.
- Catalog phases and thresholds, changed through dated notes.
- The watchlist model.
- Feed ranking and quotas.
- Replay formalities (the DEC-026 exceptions).
- Brand and design tokens.
- The Impeccable design-review process (NFR-059).
- Performance targets.
- Legacy P0 labels.

## Web sources (accessed 2026-10-10)

- [OpenAI pricing](https://developers.openai.com/api/docs/pricing): read through a summarizing fetch. An aggregator ([CloudZero](https://www.cloudzero.com/blog/openai-api-pricing/)) names the models differently, so check model IDs before use.
- [OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- [OpenAI: your data](https://developers.openai.com/api/docs/guides/your-data)
- [Insurance Law 5684](https://www.tsb.org.tr/content/Legislations/1.5.5684.pdf): from a search snippet; SEDDK details are unverified.
- [SPK investment services guide](https://spk.gov.tr/duyurular/basin-duyurulari/2014/yatirim-hizmet-ve-faaliyetleri-ile-yatirim-kuruluslarina-iliskin-rehber): from a search snippet; unverified.
- TEFAS data-use terms: not found, so unverified.
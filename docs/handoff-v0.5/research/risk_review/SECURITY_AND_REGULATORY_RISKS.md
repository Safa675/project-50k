# Security and regulatory risk review

**Checked 2026-10-02.** Eight concrete risks are prioritized below for the proposed Project 50K runtime. These are implementation gaps, lab counterexamples and unresolved release classifications, **not findings of exploitable vulnerabilities in a deployed application**. No application, database authorization, LLM security, cache, concurrent worker or real-email test was performed for this review. No shared contracts were changed.

The current authority remains `AGENTS.md`, document 19, the corrected contracts and the owner decisions. Public-data rights, public onboarding/privacy, financial-language review and external-email gates remain intact. Research does not establish compliance, organizer permission, provider entitlement or authorization to deploy, provision accounts, spend or send messages. BIST, funds, crypto, US and meaningful on-chain remain the selected target.

## Prioritized risks and smallest acceptance tests

### SR-01 — Retrieved instructions reach privileged tools or unsafe fetches

**Trigger:** a filing, news page or chat citation tells the model to fetch a supplied URL, send private text elsewhere or change a setting. Read-only fetching can still disclose information or reach internal services. A URL with an HTTPS prefix can resolve or redirect to a private target; rendering attacker-selected images can also cause unwanted requests.

**Current boundary:** document 19 lines 15–16 and 21 already require injection containment, SSRF rejection and safe rendering. `contracts/evidence.schema.json:27` accepts a locator string; `contracts/public_event.schema.json:67` checks only an HTTP(S) prefix. Those are structural contracts, not destination authorization. The investigation lab has no real model/tool/fetch attack test. OWASP documents [indirect injection and least-privilege tool validation](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) and [redirect/DNS bypass considerations](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).

**Smallest real acceptance test:** run the actual tool router/fetch resolver and renderer against controlled hostile-source fixtures and a stub DNS/HTTP transport. Attempt a public-to-private redirect, IPv4/IPv6 private destination, DNS answer change and secret-bearing query. Assert no prohibited request reaches transport, no private context enters search parameters, no settings/email action exists in the runtime tool capability, and unsafe markup cannot execute or load exfiltration resources. Replay must never invoke current web retrieval. Pattern filters or a reviewer model alone do not constitute this boundary. **Refs:** NFR-014/015/032; FR-109.

### SR-02 — Poisoned or misattributed sources become “verified truth”

**Trigger:** a copied article, spoofed issuer page or internally consistent false source is cited by an existing evidence ID. Multiple copies inflate corroboration, or a stored hash is treated as proof of authenticity.

**Current boundary:** source IDs, versions, availability provenance and APPROVED rights in `contracts/evidence.schema.json:78–98` are records whose truth needs runtime checks. A rights-status label does not verify entitlement. The temporal lab detects content/hash mismatch but cannot authenticate a source; the evidence lab E06 accepts independently agreeing sources with a hidden world-false assertion. E05/E07/E21/E24/E28/E31 illustrate lineage, identity and support problems. These are supplied-fixture counterexamples, not source-authentication tests.

**Smallest real acceptance test:** ingest one genuine approved issuer document and a controlled lookalike/wrong-issuer/copy version through the real adapter; retain approved canonical issuer/source identity, exact revision/locator and allowed retention record. Alter content while reusing an evidence ID and test a same-identity conflicting revision. Require quarantine or explicit unverified state and claim-specific origin lineage; no “world verified” badge follows from hashes, URLs or agreement. Exact source support and authenticity remain separate. **Refs:** NFR-028/033; document 19 lines 24–26,41.

### SR-03 — User data leaks through bypass roles, stale sessions or shared caches

**Trigger:** an own-user API executes under a database role that bypasses RLS, an admin role is inferred from writable metadata, or a cached response/client retains another user's session or private chat context.

**Current boundary:** document 19 lines 12–14,36; document 15 lines 57–62; `contracts/domain_tables.json:242` explicitly disclaims applied migrations and verified RLS. OpenAPI bearer declarations are not server authentication. [Supabase RLS documentation](https://supabase.com/docs/guides/database/postgres/row-level-security) distinguishes grants, row policies and actual bypass roles; a request carrying a user's token can run under that user's policies even if client initialization used a secret key. Inspect the effective request/role, not just a variable name. Its [SSR guide](https://supabase.com/docs/guides/auth/server-side/advanced-guide) warns about cached Set-Cookie responses and shared clients, while [session documentation](https://supabase.com/docs/guides/auth/sessions) explains additional checks for sensitive post-sign-out access.

**Smallest real acceptance test:** use a disposable Supabase-compatible database plus the actual API with anonymous/A/B identities. Exercise own/cross-user watchlists and chats, private table grants and forged admin metadata; verify read/write denial without leaked content. Revoke admin membership and sign out before a sensitive operation using the former token. Alternate A/B requests through the actual SSR/cache path, including token refresh, and assert no cookie, content or session crosses users. No such integration test has run. **Refs:** NFR-012/013/017/021; FR-095.

### SR-04 — Revision changes race publication, approval or delivery

**Trigger:** a reorg, source correction, release revocation or policy change occurs after an intent is queued or a worker leases it. A worker sends using an old event/approval snapshot, or retries after uncertain provider acceptance.

**Current boundary:** `contracts/public_event.schema.json:20` says release approval in event text is informational; `contracts/domain_tables.json:229` calls for current revision/policy/consent checks. Document 15 lines 65–69 requires atomic publication/outbox creation and concurrency protection. Temporal C11–C16/C24–C29 demonstrates local stale/invalid-state suppression and correction-required transitions. It does not implement transactions, dependency invalidation, leases, crash recovery or an outbox.

**Smallest real acceptance test:** in real PostgreSQL with a deterministic provider stub, pause two workers after lease acquisition, invalidate/revise or revoke the event, then resume. Assert no stale provider call, one logical intent, immutable revision history and suppression audit. Inject a crash after stub acceptance but before recording it; verify conservative reconciliation and stable idempotency identity. For already accepted material errors, retain a correction record linked to the original. Actual provider delivery remains a separate authorized acceptance step; universal exactly-once email is not promised. **Refs:** FR-089/090; NFR-004; document 13 §5.

### SR-05 — Missing evidence or high heuristic score becomes a safety badge

**Trigger:** an empty RPC result, absent sources, failed parser or low detected anomaly becomes “safe,” “no risk” or confidence zero. A high evidence-strength score overrides an invalid premise, or free prose introduces an unsupported causal/fraud conclusion.

**Current boundary:** `contracts/ai_answer.schema.json:12,37` permits free answer text and an empty claim list; semantic correspondence needs server validation. The evidence lab E03/E14/E15/E25/E29 demonstrates unsupported cause, omitted prose and unbounded absence assertions; E06 shows a high score does not prove world truth. A transfer is not a sale; account/authority count is not beneficial-owner count. The lab's internal claim-role taxonomy is a research proposal distinct from shipped DIRECT/DERIVED/INTERPRETATION support values.

**Smallest real acceptance test:** send an unavailable/partial dataset, a source-supported but false-looking adversarial fixture, and a schema-valid answer with an uncited extra “safe”/causal sentence through the actual publisher and renderer. Assert UNKNOWN/INSUFFICIENT/PARTIAL or REVIEW_REQUIRED states, missing scores remain absent, and every material rendered assertion has approved scope/support. Verify a failed hard gate cannot be outweighed by a score. No UI/LLM runtime validation has run. **Refs:** NFR-001/029/030/031; document 19 line 41.

### SR-06 — Watchlists and chat escape the declared data lifecycle

**Trigger:** user-linked prompts/watchlists enter shared caches, analytics, raw logs, foreign model/search vendors or retained backups without a reviewed purpose, deletion path or processing arrangement. Users may type holdings or identifying details even though the application does not request them.

**Current boundary:** document 19 lines 29–31,36 requires minimization and actual controller/vendor review. Document 15's 7/30/90-day defaults are proposals, not statutory retention periods. The official [KVKK FAQ](https://www.kvkk.gov.tr/SharedFolderServer/CMSFiles/c148901d-cd7f-43ff-ae9a-978fb78fb43c.pdf?v=1.0.24) describes purpose limitation, proportionality and retention limited to legal/purpose needs. The official [overseas-transfer explanation](https://www.kvkk.gov.tr/Icerik/2053/Yurtdisina-Aktarim) describes the revised Article 9 hierarchy and narrowly incidental exceptions. Routine foreign processing cannot simply be presumed incidental. No actual provider region, subprocessor chain, lawful basis, retention necessity or transfer mechanism was verified; ordinary processing consent is not itself that review.

**Smallest real acceptance test:** follow one test user's identity/watchlist/chat through database, cache, logs, model/search request payloads and queued mail using the actual integration with stub vendors. Trigger deletion and expiry; assert removal/suppression in active stores and recorded backup handling, without indiscriminate destruction of justified minimal audit records. Produce the actual data-flow inventory and category/purpose-specific retention/transfer review for the existing privacy gate. This is not a determination that all watchlist information has a particular statutory special-data classification. **Refs:** NFR-018/019/020/021; FR-095; G07.

### SR-07 — Informational chat drifts into directive or personalized recommendations

**Trigger:** a user asks what to buy, when to exit or how much leverage to use; the answer uses their circumstances to recommend a security/position. A general event feed, sponsored content or notification also uses directive language despite an informational label.

**Current boundary:** document 19 lines 7,41 prohibits personalized Buy/Hold/Sell, entry/exit and sizing recommendations and preserves review before release/monetization. The current [SPK investment-services guide, updated 10 March 2026](https://spk.gov.tr/data/61e496a11b41c60d1404d6b2/Yat%C4%B1r%C4%B1m%20Hizmetleri%20ve%20Kurulu%C5%9Flar%C4%B1%20Rehberi%20%28i-SPK.37.8%29%2010%2003%202026.pdf) distinguishes nondirective financial information, general recommendations and customer-specific activities, and calls for case-specific evaluation. Its provisions concern defined entities/activities; this reading establishes neither the proposed service's classification nor a categorical license obligation/exemption. Watchlist filtering, a disclaimer or a “not advice” label does not settle the actual workflow.

**Smallest real acceptance test:** evaluate the actual Turkish answer/event/email templates on user-specific purchase, liquidation, leverage and portfolio prompts. Preserve supported observations while withholding directive personalization; inspect all rendered text, not only the claims array. Give qualified Turkish review the concrete interaction flows, personalization inputs, monetization/advertising and distribution templates before the existing release gate is cleared. Passing a refusal fixture is not a legal classification. **Refs:** document 19 §1/§6; NFR-031; current product language policy.

### SR-08 — Alert preferences are mistaken for every consent or sending authority

**Trigger:** following an asset authorizes global discovery email, unsubscribe is checked only at enqueue, or app preferences/KVKK consent are treated as commercial-message approval. A synthetic/replay event or unapproved revision reaches an external sender.

**Current boundary:** document 19 lines 18,33 and FR-087/089 already separate optional channels and send-time eligibility; email remains disabled/dry-run. The [Ticaret Ministry general-information page](https://ticaret.gov.tr/ic-ticaret/ticari-elektronik-iletiler/genel-bilgiler) explains prior approval for commercial electronic messages and exceptions/refusal rules. It is dated 31 December 2020 and is an explanatory page, not independently checked consolidated current legislation. It does not settle whether these concrete requested alerts or global discovery messages are commercial, nor exact IYS obligations. Do not infer exemption or applicability from message importance alone.

**Smallest real acceptance test:** queue personal and global intents with a stub sender, then withdraw the relevant category consent, invalidate the revision, activate the kill switch or switch origin to replay/synthetic before execution. Assert no send in each case; verify following an asset never enables global email. Record category, consent version/time, withdrawal and suppression reason. Classify actual message templates and IYS consequences under the existing G06 review; authorized provider delivery/unsubscribe tests remain separate from this offline review. **Refs:** FR-087/089/090; G06; document 15 line 69.

## Review scope and interpretation

Official sources were read at selected relevant sections on 2026-10-02; URLs, retrieval references and exact depth are in `security_regulatory_sources.json`. OWASP documents engineering guidance rather than tested project defenses. Supabase documentation describes platform semantics rather than this application's grants or cache configuration. SPK/KVKK/Ticaret sources frame questions requiring the actual service, controller, data flows and messages; no legal-compliance conclusion, blanket licensing claim or disclaimer-based fix is made.

Existing labs provide reproducible local counterexamples only. The temporal lab passes 29 synthetic checks and performs zero sends; evidence authenticity/semantic extraction is manually supplied, and agreeing sources can still be wrong. This review ran no additional security or legal acceptance tests. Only these two research artifacts were created; there are no migrations, runtime changes or externally observable actions. The next concrete work is a smallest integrated vertical slice that exercises SR-01/03/04 boundaries and produces the actual templates/data-flow inventory needed by the existing release reviews.

# Project 50K — Security, Privacy & Compliance Release Gates

**Version:** 0.3 · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 1. Scope
Engineering risk controls, not a legal opinion. Informational positioning and disclaimers do not automatically place a product outside regulation. Obtain qualified Turkish legal review before public release/monetization, particularly personalized content, notifications, advertising, data processing and cross-border vendors.

## 2. Threat model
| Threat | Control | Required negative test |
|---|---|---|
| User B reads user A watchlist/chat | Verified JWT + RLS + owner-scoped queries | Cross-user identifiers return 404/403; no content leakage. |
| Client grants itself ADMIN | Private role membership; reject metadata/body role | Forged email/role never authorizes admin. |
| Service secret reaches browser/logs | Server-only env, bundle scan and redacted logs | No key patterns in client artifacts or error pages. |
| Article injects instructions | Read-only tools, source/data separation, output validation | Embedded “ignore instructions” cannot mutate settings or reveal secrets. |
| Search/fetch SSRF | Hosted approved search or strict public URL resolver | Reject localhost, RFC1918, metadata endpoints and redirect chains to private targets. |
| Replay uses future news | Cutoff filters + frozen sources + no live web | Future source addition does not change past result. |
| Mass mail from false event | Opt-in, global CRITICAL release, caps, outbox | Unapproved or synthetic event never sends external mail. |
| Duplicate retries | Durable idempotency keys/leases | Crash/retry and concurrent workers do not create duplicate delivery intent. |
| Runaway LLM spend | Atomic quota reservation, tool/time/token limits | Over-budget request stops before provider call. |
| Malicious HTML/citation URL | Sanitized rendering, URL scheme allowlist | javascript/data links and injected HTML are not executable. |

## 3. Data-rights gates
For every feed review: access, analysis/non-display, display, derived outputs, caching, redistribution, retention and model-processing. Borsa İstanbul expressly addresses non-display investment-analysis/gözetim usage [S01]. Wrapper source licensing cannot grant upstream rights [S05]. No assumption that free, delayed or educational means unrestricted.

Financial chart attribution is separate from exchange data rights [S23]. News citations are separate from rights to store/reprint full stories. Do not bypass authentication, paywalls, WAF, CAPTCHAs or rate limits. If permitted access fails, record a blocker and use a clearly labeled authorized fixture.

## 4. Personal data
Collect only account identity needed for Google login, preferences, watchlists, chat and operational logs. No Gmail scopes, bank credentials, wallet signing, portfolio quantity or identity-document collection. OAuth needs minimal profile/email scopes only.

Publish a real privacy notice with actual controller/contact and retention policy before public onboarding; placeholders are release blockers. Vendors receiving IP, email, chat or identifiers need processing/transfer review. KVKK cross-border arrangements may be relevant to Supabase, hosting, LLM and email vendors [S29]. Explicit consent is not a universal substitute for this analysis.

Marketing consent is separate from user-requested service-alert preferences. Legal counsel must classify global asset-discovery email and applicable communications/IYS obligations. All optional alert categories must be controllable and unsubscribe honored before enqueue/send.

## 5. Operational controls
TLS validation remains enabled. Auth fail closed. Strict allowed origins and redirect URLs. Admin private role revocation effective promptly. Minimal audit trails without chat bodies. Rate limits persistent across processes. No raw chain private keys because the application has no transaction-signing feature.

Public launch and external email are separate release gates. A demo-safe deployment can have a public synthetic landing while real-data views remain restricted until rights are approved. Never use a production Google-auth bypass for jury convenience; use staging with authorized test accounts or an offline recording.

## 6. Financial-language controls
Statistical unusualness ≠ Ponzi ≠ fraud ≠ official manipulation finding. An existing regulatory action must include its exact subject, authority, date and subsequent changes. A large transfer does not imply sale; concentrated accounts do not imply common ownership. Keep event updates and correction history. No user-specific Buy/Hold/Sell, entry/exit price or leverage/sizing recommendation.

## 7. Competition integrity
Obtain organizer clarification about prior research/specs/reference code before using these materials in the event. The local form supplied by the user is the controlling unresolved evidence. Keep an honest pre-event versus in-event work log; do not backdate commits, conceal assets or claim early detection not actually demonstrated.

## 2026-10-03 risk review

Risk research identified unimplemented boundaries, not exploited deployed vulnerabilities. Actual flows/templates, current classifications and two-user/router/race/deletion tests remain open; see security/regulatory review. Current synthesis: reports/RISK_REVIEW.md; register: research/risk_review/RISK_REGISTER.json.

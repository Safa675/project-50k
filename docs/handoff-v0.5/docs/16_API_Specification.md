# Project 50K — API & Integration Contracts

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 1. Contract authority
`contracts/openapi.yaml` is the draft API contract; `contracts/event.schema.json` is the event payload schema. Neither describes an already running server. Backend Pydantic models should generate the final OpenAPI; CI checks breaking differences before regenerating TypeScript types. Never maintain conflicting handwritten web/API interfaces.

Prefix `/v1`; JSON UTF-8; UTC ISO 8601 timestamps; financial decimals as strings; machine enums English and UI copy Turkish. Correlation ID on every response. Cursor pagination, maximum page size 100, stable `(timestamp,id)` ordering. Public endpoints use `contracts/public_event.schema.json`: published lifecycle states and display-cleared evidence only, including correction/invalidation records for previously published events. Candidate/review-only events are internal. Return explicit capability limitations rather than empty invented data. Schema rights labels must be backed by entitlement checks; a label alone is not permission.

## 2. Endpoint groups
| Access | Routes | Behavior |
|---|---|---|
| Public | GET /assets, /assets/{asset_id}, /assets/{asset_id}/bars | Search/disambiguation, capability map and permitted observations; supplied interval must be supported. |
| Public | GET /events, /events/{event_id} | Published evidence-first events; explicit origin/freshness/cutoff. |
| User | GET /me; GET/PUT /me/preferences | Derived from verified identity; no user ID supplied for authorization. |
| User | GET /watchlist; PUT/DELETE /watchlist/{asset_id} | Idempotent ownership-scoped operations; no quantity/cost fields. |
| User | GET /notifications; PATCH /notifications/{notification_id} | Read own items, mark read only. |
| User | PUT /events/{event_id}/feedback | Useful/not relevant, one value per user/event. |
| User | POST /assets/{asset_id}/chat | Bounded source-backed answer; all cited evidence accessible under policy. |
| User | GET /chat/threads/{thread_id} | Own conversation only; thread origin and asset cannot change silently. |
| Admin | GET /admin/overview, /admin/providers, /admin/jobs | Safe operations metrics; no credentials or private conversations. |
| Admin | PATCH /admin/settings/{key} | Typed whitelist, expected_version and reason; audit trail. |
| Admin | POST /admin/events/{event_id}/release | Approve eligible global critical circulation, not bypass evidence checks. |
| Admin | POST /admin/replays | Run an authorized immutable fixture bundle; never triggers external mail. |
| Public | GET /health | Liveness only; no internal topology or secrets. |

## 3. Response semantics
Search response includes `coverage` by market/history/context/on-chain, not just symbol/name. Unsupported fund intraday interval returns 422 `UNSUPPORTED_CADENCE` with allowed `1d`/published cadence; never interpolates. Unpriced asset remains searchable with `price_status=UNAVAILABLE`.

Event confidence is an object: mode, evidence_score, calibrated_probability=null, method_version, components and reasons. Evidence entries specify type, origin, observed/published/available times, safe link or synthetic fixture locator, claim IDs and numeric derivation. Citation URLs come from fetched source metadata, never model-constructed strings.

Chat response: `ANSWERED`, `INSUFFICIENT_EVIDENCE` or `PARTIAL`; `answer_tr`, claim-to-source references, as-of timestamp, asset ID, origin, replay cutoff, limitations, tool usage summary and request ID. No private chain of thought. Input, stored thread, investigation packet, event and answer carry a nonnull cutoff and registered replay_bundle_id for HISTORICAL_REPLAY, and null replay fields otherwise. The server binds owner, route asset, origin, exact cutoff and immutable bundle; a follow-up mismatch returns 409 and cannot silently change context. The frontend buffers an unvalidated final answer rather than streaming unsupported citations. Streaming can be added later with a validated final event.

## 4. Errors
Problem JSON: `code`, `message_tr`, `request_id`, optional retry_after/field errors. Codes include UNAUTHENTICATED 401, FORBIDDEN 403, NOT_FOUND 404, CONFLICT 409, INVALID_INPUT/UNSUPPORTED_CADENCE 422, RATE_LIMITED/BUDGET_LIMIT 429, PROVIDER_UNAVAILABLE 503. A blocked source is not an empty result. Conceal ownership by returning 404 for another user's thread/notification.

## 5. Idempotency and optimistic concurrency
Client mutation `Idempotency-Key` required for chat execution and replay creation; scope keys by authenticated user and operation. Persist request hash and result reference; reuse same key with a different payload gives 409. Store pending state to prevent concurrent double model spending. Settings require expected version; stale update gives 409. Watchlist PUT/DELETE are naturally idempotent.

## 6. Authentication integration tests
No personal caching in shared CDNs. No trust in unsigned user IDs, roles or emails in request bodies. Restrict CORS to known web origin. The same-origin BFF validates CSRF/Origin for cookie mutations and forwards user identity without upgrading privileges. Test expired/mis-signed, anonymous, non-Google and service-role tokens. Ordinary locally validated access tokens may remain valid until expiry after logout; sensitive admin/global-release/deletion actions additionally check current session state and private role revocation. Do not claim immediate universal JWT revocation from signature validation alone.

## 7. Quotas — provisional implementation defaults
Authenticated chat: 10 requests/day and one concurrent investigation/user; public API search 30/min/IP with bounded cache; overall daily AI budget disables further model calls gracefully. These are configurable trial limits, not pricing promises. Admin can lower limits, not switch off auth/evidence guards. Avoid counting NAT-shared IP alone for logged-in limits.

## 8. Preference withdrawal and account deletion
`POST /email/unsubscribe` accepts an opaque scoped, non-enumerating token and returns a neutral acknowledgment. It suppresses queued optional mail at send time; no login is needed to withdraw an email category. The token cannot read user data or enable subscriptions. `POST /me/deletion` starts a verified own-account deletion job, clears/schedules personal-data deletion and suppresses pending mail under the reviewed retention policy. Invalid token handling must not reveal whether an address is registered.

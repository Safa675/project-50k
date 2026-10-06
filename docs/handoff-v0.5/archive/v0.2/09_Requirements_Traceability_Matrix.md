# Project 50K — Requirements Traceability Matrix

**Document status:** Draft v0.2  
**Date:** 2026-10-02  
**Purpose:** Map high-level user needs to implementation requirements and quality constraints.

---

## 1. Why This Exists

Project 50K will be developed heavily with agentic coding and under hackathon time pressure. Requirement IDs give the team and coding agents a stable vocabulary for discussing scope, implementation, tests, and changes.

This document does not replace the detailed requirement documents. It provides a compact map between them.

---

## 2. Core Traceability Matrix

| User requirement group | Key URs | Primary FRs | Critical NFRs | MVP |
|---|---|---|---|---|
| Public asset search/research | UR-001–005 | FR-001–005, FR-112–115 | NFR-006–009, NFR-066 | P0 |
| Google authentication | UR-006–009 | FR-006–011 | NFR-011–017 | P0 |
| Watchlist / My Assets | UR-010–014 | FR-012–016 | NFR-018–020 | P0 |
| Personal intelligence feed | UR-015–019 | FR-081–084 | NFR-039, NFR-046–047 | P0 |
| Event explanation/evidence | UR-020–028 | FR-064–075 | NFR-022–034 | P0 |
| BIST intelligence | UR-029–033 | FR-024–030, FR-049–053 | NFR-023–026, NFR-035–039 | P0/P1 |
| Turkish fund intelligence | UR-034–039 | FR-031–038 | NFR-001, NFR-024, NFR-049 | P0/P1/P2 |
| Crypto/on-chain | UR-040–044 | FR-039–044 | NFR-022–026, NFR-049 | P0/P1 |
| U.S. equities | UR-045–047 | FR-045–047 | NFR-022–026 | P0/P1 |
| AI asset assistant | UR-048–056 | FR-055–063, FR-094–098 | NFR-027–034 | P0/P1 |
| Notifications/e-mail | UR-057–063 | FR-085–093 | NFR-004, NFR-039, NFR-044 | P0/P1/P2 |
| User feedback | UR-064–066 | FR-099–101 | NFR-040 | P0/P1 |
| Admin operations | UR-067–072 | FR-102–107 | NFR-012–017, NFR-041–045 | P0/P1 |
| Turkish UX/design | UR-073–077 | FR-117–119 | NFR-056–069 | P0/P1 |
| Historical replay/live proof | UR-078–080 | FR-108–111 | NFR-005, NFR-035–038, NFR-078–080 | P0 |

---

## 3. P0 End-to-End Requirement Chain

The most important traceability chain for the Techstars MVP is:

```text
Anonymous Visitor
  ↓
UR-001 / UR-002 / UR-003
  ↓
FR-001–005
  ↓
Asset Page
  ↓
UR-020–027
  ↓
FR-048–075
  ↓
Evidence-backed Intelligence Event
  ↓
UR-048–055
  ↓
FR-055–063 + FR-094–098
  ↓
Sourced AI Explanation
  ↓
Google Sign-in
  ↓
UR-006–013
  ↓
FR-006–016
  ↓
Watchlist + Personal Feed
  ↓
UR-015–019
  ↓
FR-081–084
  ↓
Alert
  ↓
UR-057–059
  ↓
FR-085–090
```

If any link in this chain is broken, the jury cannot experience the complete product thesis.

---

## 4. P0 Test Traceability Skeleton

Detailed test cases will be defined later, but implementation should eventually use IDs such as:

| Test ID | Requirement coverage | Intent |
|---|---|---|
| T-AUTH-001 | UR-006, FR-006–008 | Google login creates/restores user and returns to intended page |
| T-AUTH-002 | UR-067, FR-009–011 | Non-admin cannot access admin route/API |
| T-WATCH-001 | UR-010–013, FR-012–016 | User can add/remove unique watchlist assets without cost basis |
| T-EVENT-001 | UR-020–027, FR-064–075 | Historical BIST event exposes severity, confidence, evidence, sources |
| T-CONF-001 | UR-022–023, FR-067–068 | Confidence derives from structured components, not LLM free-form output |
| T-AI-001 | UR-052–054, FR-057–061 | AI answer contains valid sources or returns insufficient-evidence state |
| T-NOTIF-001 | UR-057–059, FR-085–090 | Critical event creates only one eligible notification/e-mail |
| T-REPLAY-001 | UR-078–080, FR-108–111 | Replay does not use future evidence and produces normal event schema |
| T-FUND-001 | UR-036–037, FR-035–037 | Fund allocation/metric change creates expected fund event |
| T-ADMIN-001 | UR-068–071, FR-102–105 | Admin sees data freshness and can safely change approved threshold |

---

## 5. Scope-Change Rule

When a new feature is proposed during the hackathon, the team should answer:

1. Which existing `UR` does it satisfy?
2. If none, is a new user requirement justified?
3. Which `FR` must change or be added?
4. Does it introduce a new `NFR`, data source, licensing, or operational risk?
5. Is it more important than an unfinished P0 requirement?

If the feature cannot beat the value of completing the P0 chain, it should be deferred.

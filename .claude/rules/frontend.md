---
paths:
  - "frontend/**"
---

# Frontend conventions

- Private research data is fetched only in the browser through same-origin proxies (`/api/research/...` rewrite,
  `/api/research-dated/...` route handler); server components never fetch it and builds never embed it.
- Every response is validated at runtime with the strict Zod contracts (`research-contract.ts`,
  `dated-contract.ts`); a mismatch is an error state, never a partial render. Missing stays missing: no zeros.
- User-facing text is natural `tr-TR`. Dated pages use the protocol's exact sentences verbatim and the copy
  denylist; no fraud, safety, prediction, advice or lead-time wording.
- Tests use invented codes and values only. Browser tests need a production server on 127.0.0.1:3060; if a demo
  holds that port, use the spare-port config in `/p50k-verify` instead of stopping the demo.
- Keep isolation: the fixed-date pages and their tests change only in deliberate, reviewed commits.

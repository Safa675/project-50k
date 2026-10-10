# DEC-031 — Derived evidence only for OpenAI processing

**Date:** 2026-10-10 (Europe/Istanbul).
**Source:** Mirza's explicit D7 answer during the Codex takeover: "Approve derived evidence only".

## Decision

OpenAI may receive only detector values, thresholds and states; dates; categories;
public fund codes and names; SPK event metadata and short SPK quotes. All inputs
must pass through one typed egress allowlist before any API request.

Do not send raw price series, TEFAS size, units or investor counts, KAP text or
values extracted from KAP PDFs, or personal data. Chat tells users that their
questions go to OpenAI and must not contain personal information or secrets.

Every Responses API call sets `store: false`. This disables response storage for
later retrieval; it does not establish Zero Data Retention. OpenAI's default
abuse-monitoring logs may retain customer content for up to 30 days. Source:
[official data controls](https://developers.openai.com/api/docs/guides/your-data),
checked 2026-10-10.

Safa has not answered D7. His agreement remains in `docs/notes/team-asks.md`;
Mirza's explicit approval permits implementation of this scope.

Live calls also require the egress tests, output validator, cost reservations,
configured key, and the schedule gates in the build plan. Until those are ready,
AI is off for the real-data database; mock tests use only the development database.

## Other takeover answers

- D1: use `C:\Users\mirza\Desktop\Hackathon\project-50k-app`, branch `product/build`.
- D9: profiles, SPK bulletin PDFs for 2024–2026 and additional KAP report lists
  are authorized. Mirza confirmed the laptop will stay on and explicitly asked
  to start downloads immediately, rather than waiting for night. Outputs stay
  under the external overnight folder. Each host keeps its required pacing.
- T1.7a: Mirza confirmed the single closest-name identity. The ten exact-match
  human spot checks remain outstanding; events stay candidates until completed.
  Actual other-fund identities are kept out of this decision record.

## Unchanged

DEC-024 scope, DEC-028 deterministic numbers and human override, DEC-029
development-result labels, DEC-030 budget target and working agreements, and
the ban on publishing real data or placing it in git.

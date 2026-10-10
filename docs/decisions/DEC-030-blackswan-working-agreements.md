# DEC-030 — BlackSwan name, working agreements and plan confirmation

**Date:** 2026-10-10 (Europe/Istanbul)
**Source:** Mirza (technical lead), in chat on 2026-10-10 at about 14:05–14:30.

| Item | Decision |
|---|---|
| Product name | **BlackSwan.** Mirza will supply the logos and designs later. Until then the app shows the text "BlackSwan" and the existing research-app tokens; there is no placeholder logo |
| Build plan | Confirmed by delegation. Agents confirm items in `plans/2026-10-10-product-build-plan.md` that align with the team's interest, and ask Mirza only about problematic ones, with clear options, details and a recommendation. The questions still open are listed in `docs/notes/team-asks.md` |
| API budget | The $25 OpenAI budget is a target, not a hard cap. Do not waste API money. Raise it only with a valid reason and Mirza's OK. The internal $20 cap and its buckets (plan section 6) apply until then |
| No placeholders | The product never contains placeholder content: no lorem ipsum, fake or demo values, "coming soon" screens, blank template rows, mock AI output, or notes addressed to the team. Messages for Mirza go in chat, never into the product. If something cannot be built properly, tell Mirza instead of shipping a placeholder |
| What does not count as a placeholder | Required integrity labels (data mode, "geliştirme sonucu", "veri hakları incelenmedi", "yatırım tavsiyesi değildir"). Real empty, error and stale states. The text wordmark until the logo arrives. The current tokens until Barış's arrive |
| Persistent reminders | If Mirza misses something important, such as an unanswered question or unconfirmed information that affects everything, agents raise it again in every reply until he answers. This applies only to truly critical items |
| Downloads | Start downloads as soon as they can run. The all-fund TEFAS snapshot (2,136 funds) started at 14:30 into `~/.local/share/project-50k/overnight/2026-10-10/snapshots-all.sqlite3` |
| Handoff | Claude's usage limits are running out. Codex continues from `plans/2026-10-10-codex-handoff-prompt.md` |

## Still open (ask Mirza)

- **D7:** what data may go to OpenAI. Until it is answered, AI runs only in mock mode, in the development database.
- **The rest of D9:**
  - TEFAS fund profiles;
  - SPK bulletin PDFs for 2024–2026;
  - optional overnight KAP report lists.
- **D1:** whether to build in the separate worktree folder.
- **T1.7a:** a human check of one closest-name fund mapping in the 2026/61 list.

## Unchanged

DEC-024 to DEC-029 and the binding integrity rules.

# DEC-035 — Always-on agent team, Reporter dock and UI clean-up

**Date:** 2026-10-10 (Europe/Istanbul)
**Source:** Mirza, in chat at about 21:55, after Claude took the product back from Codex. His answers came through
the question tool.

## Why

The pitch is "7/24 çalışan, ajan tabanlı risk yönetimi ekibi ve anomali tespiti". The product must show that team
working, not hide it behind one chat box. A check of the code on 2026-10-10 found that the five-agent workflow in the
team's design did not exist:

- Detectors and human review existed.
- A single AI proposal per fund existed.
- No Hipotezci, Şüpheci, Doğrulayıcı or Raportör agents existed.

## Decisions

| Item | Decision |
|---|---|
| Agent team | Five roles, in this order: **Nöbetçi** (a statistical algorithm detects an anomaly and opens a case) → **Hipotezci** (plausible explanations) and **Şüpheci** (counter-explanations and refutation tests), in parallel → **Doğrulayıcı** (tests the hypotheses with sources and code-computed results) → **Raportör** (an evidence-based, auditable report) → **İnsan incelemesi ve nihai karar** (the existing human review and override) |
| Who talks to the user | Only the Raportör. Users watch every other agent's work but cannot talk to those agents. The Raportör orchestrates their work: it turns a user's request into queued work for the team |
| Always-on pacing | A budgeted queue (Mirza chose ~$3/day). Nöbetçi (deterministic and free) runs continuously and opens cases. The AI roles take queued cases within a **daily cap of $3**, and user requests jump the queue. When the day's cap is used, the team shows that it is waiting for the next day's budget. The overall $25 target stays a target (DEC-030); Mirza is told before it is exceeded |
| Scheduling UI | A visible todo list of queued, running and done work, with priority, origin (system or user), state and budget |
| Reporter conversations | One saved conversation per fund, plus one general conversation for other pages, reusing the persistent chat threads (`fund_code` NULL = general). Enter sends, Shift+Enter adds a newline, and IME composition is respected |
| Page awareness | On a fund page the Reporter shows a quiet note built from stored evidence at no AI cost, with any warning and 2–3 suggested questions. An open case for that fund moves up the queue. The AI runs only when the user asks or when the case's turn comes |
| Stocks | Funds first. On stock pages the Reporter answers about the stored prices. Nöbetçi's stock checks come next, using the official Borsa İstanbul daily files under a separately recorded v2 protocol |
| Dock | A mascot floating button at the bottom right of **every** page. It opens a wide horizontal panel that shows the team running, what each agent does, how they interact, the queue and the Raportör conversation, with a way into each agent's read-only workspace. The visual quality bar is very high |
| Mascot art | **A placeholder mascot is explicitly allowed** until Barış or Mirza supply the design. This is Mirza's exception to DEC-030's no-placeholder rule, and it covers the mascot art only |
| Removed | The "Fon hakkında sorularınız" chat section on asset pages, which the Raportör replaces. Meaningless status tags such as "Yayımlanmış veriler", along with similar chips that only restate the mode or the date shown in the navbar |

## Rules that still bind

- **Deterministic numbers.** Detectors and the Doğrulayıcı's code tests compute every number. No agent writes a
  number; text uses evidence placeholders that the server renders.
- **One validator.** Every agent text passes the existing validator: citations, wording lists, number rules. Failed
  text is never shown.
- **Egress (DEC-031).** Only derived evidence goes to OpenAI, with `store:false`. In historical mode, model input hides
  the fund's identity.
- **Human authority.** Every Raportör decision is an AI proposal that a human can accept, override or reject. Agent
  messages are append-only.
- **Read-only tools.** Agent tools are read-only, except one bounded, deduplicated, rate-limited action: queueing an
  investigation that a user asked for.
- **No hindsight.** Historical runs (12 September by default) use only data available before the cutoff. Nothing is
  tuned to known outcomes.

## Demo format (Mirza, 2026-10-10 about 22:10)

The pitch demo is a **screen recording of about 25 seconds**, not a live demo. So the priority is a polished,
recordable flow on real 12 September data, with agent cases already processed by the real pipeline. Live-demo
safeguards such as latency and on-stage fallbacks matter less. No mock or staged content appears in the recording
(DEC-030); the only exception is the mascot art.

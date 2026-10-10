---
name: p50k-meta
description: Do Project 50K meta work. Persist new context and decisions, and keep the agent instructions (CLAUDE.md, AGENTS.md), current state, team asks, plans, skills, hooks, rules and Claude memory consistent and tested. Use when the user shares new context, decisions, roles, deadlines, preferences or data sources; after a change of direction; when a procedure repeats often enough to deserve a skill or hook; or when asked for meta work.
---

# Meta work

Meta work keeps every later session correct without anyone re-explaining: Claude, Codex and the teammates. Do it as
soon as new context arrives, before product work continues.

## 1. Capture

- **Classify each new fact:**
  - a decision (record who decided and when);
  - a requirement or a preference;
  - a role or a deadline;
  - a data source;
  - an open question;
  - something needed from a person (a decision or an action).
- **Never drop earlier work.** When the direction changes, carry pending tasks into the new plan and say what each
  new item supersedes.

## 2. Persist in the right place (repository first, memory second)

| What | Where |
|---|---|
| A decision by Mirza, Safa or the team | A new `docs/decisions/DEC-NNN-*.md`. Earlier records are never rewritten; say what the new one supersedes |
| Where the project stands and what comes next | `docs/notes/current-state.md` |
| Product ideas and open product questions | `docs/notes/product-direction.md` |
| Something needed from Mirza, Safa, Barış or the team | `docs/notes/team-asks.md` (type, since, status) |
| Plans and todo lists | `plans/<date>-<topic>.md`, marked PROPOSED until the user confirms |
| How agents must behave | `CLAUDE.md` and `AGENTS.md`, changed together and kept consistent |
| Guidance for specific paths | `.claude/rules/*.md` |
| Repeatable procedures | `.claude/skills/<name>/SKILL.md` |
| Mechanical guardrails | `.claude/hooks/`, `.claude/settings.json` and `.claude/hooks/hooks.test.mjs` |
| Facts that belong to the user or the machine, not the repository (preferences, local paths) | Claude memory: one fact per file plus a line in `MEMORY.md` |

- Memory points to repository documents for project facts instead of copying them.
- Secrets, real TEFAS/KAP/MKK values and other private data go into none of these.

## 3. Keep everything consistent

- **Search for contradictions.** Grep for statements the new fact contradicts in:
  - `CLAUDE.md` and `AGENTS.md`;
  - `docs/notes/current-state.md` and `docs/notes/agent-tooling.md`;
  - `.claude/rules/`, `.claude/skills/` and the hook messages;
  - Claude memory.

  Update each one, or mark it superseded with a pointer to the decision record.
- **Frozen files are never edited:** `docs/handoff-v0.5/`, committed protocols and preregistrations, and the
  preregistered detectors. Record an override in a decision record instead.
- **Know who reads what:**
  - Codex reads `AGENTS.md` and what it links.
  - Claude Code reads `CLAUDE.md` with its imports, the rules, skills, hooks and memory.
  - Teammates read the README, `docs/notes/current-state.md` and `docs/notes/team-asks.md`.
- **Integrity rules stay binding even when product requirements flex:**
  - no real data in git;
  - no fraud claims;
  - provenance and point-in-time discipline;
  - no fabricated results;
  - no spending, accounts, deployment or external contact without authorization.

## 4. Tooling changes

- **Skills.** Add one when a procedure repeats or is easy to get wrong.
- **Hooks.**
  - Add one only for a mechanical mistake that is costly.
  - Keep hooks fast (under about 200 ms), failing open and covered by `hooks.test.mjs`.
  - Run `node --test .claude/hooks/hooks.test.mjs`.
- **MCP servers.** Add one only with a recorded need, a pinned and reviewed package, and a note in
  `docs/notes/agent-tooling.md`.

## 5. Verify and land

- **Checks:**
  - `git diff --check`;
  - no CRLF in changed files;
  - `/p50k-leak-scan` with zero hits;
  - the hook self-test when tooling changed.
- **Landing:**
  1. Commit on a branch in a separate clone.
  2. Push it.
  3. Merge into `main` with `git merge --no-ff` (DEC-027) and push `main`.
  4. Run `git pull --ff-only` in the main checkout and in the demo clone.
  5. Confirm the demo still answers.
- **Scope.** Meta commits change documentation and tooling only. No runtime file and no file bound into a sealed
  bundle.

## 6. Report

Tell the user:

- what was persisted, and where;
- which instructions changed;
- what is superseded;
- the open asks for each person, each marked as a decision or an action.

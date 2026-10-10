# Agent tooling

Added 2026-10-10. This note covers what `.claude/` provides for Claude Code sessions in this repository. Codex and
other agents read `AGENTS.md`; the hooks below do not run for them, so they follow the same rules by hand.
Change `CLAUDE.md` and `AGENTS.md` together so they never disagree.

## Skills (`.claude/skills/`)

| Skill | Use |
|---|---|
| `/p50k-verify` | Full verification, the Windows diagnostic variant and a spare-port browser config for when a demo holds port 3060 |
| `/p50k-leak-scan` | Pre-commit scan for real price values, real fund names and non-target codes; it prints locations, never values |
| `/p50k-demo` | Start, stop, restart or health-check the local demo, with PowerShell and Linux scripts |
| `/p50k-seal-dated` | Seal or verify the dated D1 index on a machine that holds the private archive |
| `/p50k-new-research-slice` | The protocol-first workflow for any new calculation on real data |

## Hooks (`.claude/settings.json`, scripts in `.claude/hooks/`)

| Event | Script | Effect |
|---|---|---|
| `SessionStart` | `session-orientation.mjs` | Adds branch, HEAD, uncommitted count, `core.autocrlf`, private-data presence, key rules and the skill list to the session context |
| `PreToolUse` on `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | `protect-paths.mjs` | Blocks edits to the frozen handoff, the frozen detectors and their results, committed protocols and preregistrations, `raw/` data, and files bound into sealed bundles |
| `PreToolUse` on `Bash`, `PowerShell` | `guard-git.mjs` | Blocks force pushes, remote branch deletion, squash and rebase merges, force-adds and staging `raw/` |

- **How they run:** the hooks start `node` directly, without a shell (exec form). They behave the same on Linux
  and Windows and need Node on `PATH`.
- **Limits:** they guard against mistakes and are not a security boundary. If Node is missing or a script fails,
  the action goes ahead.
- **Self-test:** `node --test .claude/hooks/hooks.test.mjs`.
- **Intended reseal:** create `.claude/allow-registered-edits.local`, then edit and commit. Reseal every affected
  bundle, record the new IDs, and delete the file.

## Path rules (`.claude/rules/`)

| File | Loaded for | Content |
|---|---|---|
| `registered-runtime.md` | sealed-bundle runtime and runners | What resealing involves and how to avoid it |
| `research-protocols.md` | `research/events/**`, `docs/decisions/**` | Protocol-first rules, the unopened-files rule, naming and data rules |
| `frontend.md` | `frontend/**` | Proxy-only data access, strict contracts, Turkish copy, synthetic test data |

## Local files (gitignored)

| File | Purpose |
|---|---|
| `.claude/settings.local.json` | Personal permissions |
| `.claude/p50k-demo.local.json` | The demo's bundle paths: `{"fixed_bundle": "<dir>", "dated_index": "<dir>"}` |
| `.claude/p50k-demo.pids.local.json`, `.claude/*.pid`, `.claude/demo-logs/` | Demo process state and logs |
| `.claude/allow-registered-edits.local` | The reseal override |

## Line endings

`.gitattributes` checks out every text file with LF, on Windows too. Sealed bundles, runner registration and the
handoff `MANIFEST.json` hash LF bytes.

A Windows checkout made before `.gitattributes` existed can still hold CRLF files. To convert it:

1. Commit or stash your work.
2. Run `git rm -r -q --cached .` and then `git reset --hard`. This rewrites the tracked files and leaves ignored
   files such as `raw/` alone.

## MCP servers: none (decided 2026-10-10)

The repository has no `.mcp.json`. The reasons:

- The shell already covers what the work needs: `gh` for GitHub, the project Python for SQLite and the local APIs,
  and Playwright for browsers.
- A project server runs third-party code in every team member's sessions. `npx`-based servers download it at
  start-up.
- On native Windows, `npx` servers need a `cmd /c` wrapper that Linux does not accept, so one committed file
  cannot serve both.

A project server needs all of the following, recorded here:

- a recorded need;
- a pinned and reviewed package;
- loopback-only or read-only access;
- no access to `raw/` or the snapshot databases.

For personal use, `claude mcp add --scope local` adds a server without affecting anyone else.

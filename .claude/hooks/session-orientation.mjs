#!/usr/bin/env node
// SessionStart: print a short orientation; stdout becomes session context. Must stay fast and never fail.
import {execFileSync} from 'node:child_process';
import {existsSync, readdirSync} from 'node:fs';
import {join, resolve} from 'node:path';

const root = resolve(process.env.CLAUDE_PROJECT_DIR || process.cwd());
const git = (...args) => {
  try { return execFileSync('git', ['-C', root, ...args], {encoding: 'utf8', timeout: 4000}).trim(); } catch { return ''; }
};
const count = (path) => { try { return readdirSync(join(root, path)).length; } catch { return 0; } };

const branch = git('rev-parse', '--abbrev-ref', 'HEAD') || '?';
const head = git('log', '-1', '--format=%h %s') || '?';
const dirty = git('status', '--porcelain').split('\n').filter(Boolean).length;
const eol = git('config', '--get', 'core.autocrlf') || 'unset';
const lines = [
  `Project 50K session context: branch ${branch} at ${head}; ${dirty} uncommitted path(s); core.autocrlf=${eol}.`,
  `Private data here: raw/ ${existsSync(join(root, 'raw')) ? 'present' : 'absent'}; sealed fixed-date bundles: ${count('raw/research/fund-review-app')}; dated indexes: ${count('raw/research/fund-review-dated/index')}.`,
  'Rules: Turkish funds only (DEC-024); real data never enters git; never edit docs/handoff-v0.5, committed protocols or files bound into sealed bundles; merge commits only, no squash or force-push; the owner only pulls (DEC-027).',
  'Skills: /p50k-verify, /p50k-leak-scan, /p50k-demo, /p50k-seal-dated, /p50k-new-research-slice. Current state: docs/notes/current-state.md.',
];
process.stdout.write(lines.join('\n') + '\n');

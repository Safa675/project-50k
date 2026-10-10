#!/usr/bin/env node
// PreToolUse guard for Edit/Write/MultiEdit/NotebookEdit. Exit 2 blocks the edit; stderr explains why.
// Frozen files and private data are never edited. Files bound into sealed research bundles are
// blocked by default because editing them makes every sealed bundle fail verification (API 503).
import {execFileSync} from 'node:child_process';
import {existsSync, readFileSync} from 'node:fs';
import {isAbsolute, join, relative, resolve} from 'node:path';

const root = resolve(process.env.CLAUDE_PROJECT_DIR || process.cwd());
let input = {};
try { input = JSON.parse(readFileSync(0, 'utf8') || '{}'); } catch { process.exit(0); }
const target = input?.tool_input?.file_path || input?.tool_input?.notebook_path;
if (typeof target !== 'string' || !target) process.exit(0);

const absolute = isAbsolute(target) ? resolve(target) : resolve(root, target);
const rel = relative(root, absolute).split('\\').join('/');
if (rel.startsWith('..') || isAbsolute(rel)) process.exit(0);

const block = (reason) => {
  process.stderr.write(`Blocked edit to ${rel}: ${reason}\n`);
  process.exit(2);
};
const committed = (path) => {
  try { execFileSync('git', ['-C', root, 'cat-file', '-e', `HEAD:${path}`], {stdio: 'ignore', timeout: 4000}); return true; } catch { return false; }
};

const EVENT = 'research/events/2026-09-17-spk-liquidations';
const frozen = [
  [/^docs\/handoff-v0\.5\//, 'The v0.5 handoff is frozen; its MANIFEST.json hashes verify it. Record changes in docs/decisions/ or docs/notes/.'],
  [new RegExp(`^${EVENT}/price_detectors/(detectors\\.py|PREREGISTRATION\\.md|results\\.json)$`), 'The preregistered detectors and their stored results are frozen. Write a v2 beside them with its own dated preregistration.'],
  [/^(raw|research\/(spikes|events)\/[^/]+\/raw)\//, 'raw/ holds private TEFAS/KAP data with unreviewed rights. Never edit it; outputs are written only by the registered runners.'],
];
for (const [pattern, reason] of frozen) if (pattern.test(rel)) block(reason);

// A protocol may be drafted freely; once committed it is frozen.
if (/^research\/events\/[^/]+\/[^/]+\/(PROTOCOL|PREREGISTRATION)\.md$/.test(rel) && committed(rel)) {
  block('Committed protocols and preregistrations are frozen. Add a new versioned protocol file instead.');
}

// Files whose bytes are re-hashed whenever a sealed bundle loads.
const registered = new Set([
  `${EVENT}/top100_funds.txt`,
  `${EVENT}/fund_review_app/run.py`, `${EVENT}/fund_concentration_app/run.py`, `${EVENT}/fund_review_dated/run.py`,
]);
try {
  const lock = JSON.parse(readFileSync(join(root, 'tests/unit/registered_sources.lock.json'), 'utf8'));
  for (const entry of Array.isArray(lock) ? lock : lock.entries || lock.files || []) {
    if (entry && typeof entry.path === 'string') registered.add(entry.path);
  }
} catch { /* lock file absent on old branches */ }
const registeredPattern = /^services\/p50k\/(research_reviews\/(__init__|bundle|bundle_v2|comments|concentration|contracts|dated_[a-z_]+)\.py|replay\.py|evidence_store\.py|detectors\/fund_flow\.py|providers\/(kap_report|security_holdings|thf_holdings)\.py)$/;
if ((registered.has(rel) || registeredPattern.test(rel)) && !existsSync(join(root, '.claude', 'allow-registered-edits.local'))) {
  block('sealed research bundles re-hash this file on every load, so editing it makes the running app refuse ' +
    'its bundles (503) until they are resealed. Prefer a new module beside it. If a reseal is intended, create ' +
    '.claude/allow-registered-edits.local (gitignored), make the edit, commit, reseal, then delete that file.');
}
process.exit(0);

// Shared path rules for the project hooks: which repository files must not change, and why.
import {execFileSync} from 'node:child_process';
import {existsSync, readFileSync} from 'node:fs';
import {isAbsolute, join, relative, resolve} from 'node:path';

export const root = resolve(process.env.CLAUDE_PROJECT_DIR || process.cwd());
const windows = process.platform === 'win32';
// Windows paths are case-insensitive, so compare folded spellings there.
const fold = (path) => (windows ? path.toLowerCase() : path);
const EVENT = 'research/events/2026-09-17-spk-liquidations';
const FROZEN_FILES = ['detectors.py', 'PREREGISTRATION.md', 'results.json'].map((name) => `${EVENT}/price_detectors/${name}`);
const STATIC_REGISTERED = [
  `${EVENT}/top100_funds.txt`,
  `${EVENT}/fund_review_app/run.py`, `${EVENT}/fund_concentration_app/run.py`, `${EVENT}/fund_review_dated/run.py`,
  ...['contracts', 'review', 'comments', 'bundle'].map((name) => `services/p50k/research_reviews/dated_${name}.py`),
];
const REGISTERED_PATTERN = /^services\/p50k\/(research_reviews\/(__init__|bundle|bundle_v2|comments|concentration|contracts)\.py|replay\.py|evidence_store\.py|detectors\/fund_flow\.py|providers\/(kap_report|security_holdings|thf_holdings)\.py)$/i;
const PROTOCOL_PATTERN = /^research\/events\/[^/]+\/[^/]+\/(PROTOCOL|PREREGISTRATION)\.md$/i;
const RAW_PATTERN = /^(raw|research\/(spikes|events)\/[^/]+\/raw)(\/|$)/i;

export const REASONS = {
  raw: 'raw/ holds private TEFAS/KAP data with unreviewed rights. Only the registered runners write there, and nothing may delete it.',
  handoff: 'The v0.5 handoff is frozen; its MANIFEST.json hashes verify it. Record changes in docs/decisions/ or docs/notes/.',
  frozen: 'The preregistered detectors and their stored results are frozen. Write a v2 beside them with its own dated preregistration.',
  protocol: 'Committed protocols and preregistrations are frozen. Add a new versioned protocol file instead.',
  registered: 'Sealed research bundles re-hash this file on every load, so changing it makes the running demo refuse its ' +
    'bundles (503) until they are resealed. Add a new module beside it instead. Only with the user\'s approval for a ' +
    'reseal: create .claude/allow-registered-edits.local, change and commit the file, reseal every affected bundle, ' +
    'then delete that file.',
  repository: 'This would delete protected repository content, including private raw/ data.',
};

export function readInput() {
  try { return JSON.parse(readFileSync(0, 'utf8') || '{}'); } catch { return null; }
}

// Repository-relative POSIX path for a path argument; '.' for the root; null outside the repository.
export function toRel(target, cwd = root) {
  if (typeof target !== 'string') return null;
  let path = target.trim();
  if (!path || path.startsWith('~') || path.includes('://') || path.startsWith('$')) return null;
  if (windows && /^\/[a-zA-Z](\/|$)/.test(path)) path = `${path[1]}:/${path.slice(3)}`;  // Git Bash /c/Users/...
  const rel = relative(root, isAbsolute(path) ? resolve(path) : resolve(cwd || root, path)).split('\\').join('/');
  if (rel === '') return '.';
  return rel.startsWith('..') || isAbsolute(rel) ? null : rel;
}

let registeredPaths;
function registered() {
  if (registeredPaths) return registeredPaths;
  const paths = new Set(STATIC_REGISTERED);
  try {
    const lock = JSON.parse(readFileSync(join(root, 'tests/unit/registered_sources.lock.json'), 'utf8'));
    for (const entry of Array.isArray(lock) ? lock : lock.files || lock.entries || []) {
      if (entry && typeof entry.path === 'string') paths.add(entry.path);
    }
  } catch { /* the lock file is absent on old branches */ }
  return (registeredPaths = [...paths]);
}
const registeredFolded = () => new Set(registered().map(fold));
export const isRegistered = (rel) => registeredFolded().has(fold(rel)) || REGISTERED_PATTERN.test(rel);
export const resealAllowed = () => existsSync(join(root, '.claude', 'allow-registered-edits.local'));

function git(args) {
  return execFileSync('git', ['-C', root, ...args], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 8000});
}
const committed = (rel) => { try { git(['cat-file', '-e', `HEAD:${rel}`]); return true; } catch { return false; } };
function committedProtocols() {
  try { return git(['ls-files', '--', 'research/events/*/*/PROTOCOL.md', 'research/events/*/*/PREREGISTRATION.md']).split('\n').filter(Boolean); } catch { return []; }
}

// Protected paths a shell glob could expand to; deletions also count every parent directory.
function globTargets(kind) {
  const files = ['raw', 'docs/handoff-v0.5', ...FROZEN_FILES, ...registered(), ...committedProtocols()];
  if (kind !== 'delete') return files;
  const all = new Set(files);
  for (const file of files) {
    const parts = file.split('/');
    for (let n = 1; n < parts.length; n++) all.add(parts.slice(0, n).join('/'));
  }
  return [...all];
}
const globPattern = (glob) => new RegExp(`^${[...glob].map((c) => (c === '*' ? '[^/]*' : c === '?' ? '[^/]'
  : /[\\^$.|+(){}]/.test(c) ? `\\${c}` : c)).join('')}$`, windows ? 'i' : '');

// Why `rel` must not be changed, or null. `kind` is 'edit' (create or overwrite) or 'delete'.
export function protection(rel, kind = 'edit') {
  if (rel === null || rel === undefined) return null;
  if (rel === '.') return kind === 'delete' ? REASONS.repository : null;
  if (RAW_PATTERN.test(rel)) return REASONS.raw;
  if (/^docs\/handoff-v0\.5(\/|$)/i.test(rel)) return REASONS.handoff;
  if (/[*?[]/.test(rel)) {
    let pattern;
    try { pattern = globPattern(rel); } catch { return null; }
    for (const target of globTargets(kind)) {
      if (pattern.test(target)) { const reason = protection(target, kind); if (reason) return reason; }
    }
    return null;
  }
  const folded = fold(rel);
  if (FROZEN_FILES.some((path) => fold(path) === folded)) return REASONS.frozen;
  if (PROTOCOL_PATTERN.test(rel) && committed(rel)) return REASONS.protocol;
  if (isRegistered(rel) && !resealAllowed()) return REASONS.registered;
  if (kind === 'delete') {
    // Deleting a directory deletes everything protected inside it.
    const inside = (path) => fold(path).startsWith(`${folded}/`);
    if (inside('raw/x') || inside('docs/handoff-v0.5/x') || FROZEN_FILES.some(inside) || committedProtocols().some(inside)) {
      return REASONS.repository;
    }
    if (!resealAllowed() && registered().some(inside)) return REASONS.registered;
  }
  return null;
}

// Protected tracked files that differ from HEAD, for the tripwire and the session summary.
export function drift() {
  const specs = ['docs/handoff-v0.5', ...FROZEN_FILES, ...registered(), ...committedProtocols(), 'services/p50k'];
  let changed;
  try { changed = git(['diff', '--name-only', 'HEAD', '--', ...specs]).split('\n').map((line) => line.trim()).filter(Boolean); } catch { return []; }
  return changed.filter((path) => {
    if (/^services\/p50k\//i.test(path) && !isRegistered(path)) return false;
    return !(isRegistered(path) && resealAllowed());
  });
}

// Self-test for the project hooks: node --test .claude/hooks/hooks.test.mjs (from the repository root).
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdirSync, mkdtempSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname, join, resolve} from 'node:path';
import {test} from 'node:test';
import {fileURLToPath} from 'node:url';

const hooks = dirname(fileURLToPath(import.meta.url));
const repo = resolve(hooks, '..', '..');
const run = (script, input, root = repo) => spawnSync(process.execPath, [join(hooks, script)], {
  input: typeof input === 'string' ? input : JSON.stringify(input),
  env: {...process.env, CLAUDE_PROJECT_DIR: root},
  encoding: 'utf8',
});
const edit = (path, root) => run('protect-paths.mjs', {tool_name: 'Edit', tool_input: {file_path: path}}, root).status;
const shell = (command) => run('guard-git.mjs', {tool_name: 'Bash', tool_input: {command}}).status;

const EVENT = 'research/events/2026-09-17-spk-liquidations';

test('frozen files and private data are blocked', () => {
  for (const path of [
    'docs/handoff-v0.5/START_HERE.md',
    `${EVENT}/price_detectors/detectors.py`,
    `${EVENT}/price_detectors/PREREGISTRATION.md`,
    `${EVENT}/fund_review_dated/PROTOCOL.md`,
    'raw/tefas/prices/XYZ.json',
    `${EVENT}/raw/notes.json`,
    join(repo, 'docs', 'handoff-v0.5', 'AGENTS.md'),
  ]) assert.equal(edit(path), 2, path);
});

test('registered bundle files are blocked unless a reseal is opted into', () => {
  for (const path of [
    'services/p50k/research_reviews/bundle.py',
    'services/p50k/research_reviews/dated_review.py',
    'services/p50k/replay.py',
    `${EVENT}/top100_funds.txt`,
    `${EVENT}/fund_review_dated/run.py`,
  ]) assert.equal(edit(path), 2, path);

  const root = mkdtempSync(join(tmpdir(), 'p50k-hooks-'));
  try {
    assert.equal(edit('services/p50k/replay.py', root), 2);
    mkdirSync(join(root, '.claude'));
    writeFileSync(join(root, '.claude', 'allow-registered-edits.local'), '');
    assert.equal(edit('services/p50k/replay.py', root), 0);
  } finally {
    rmSync(root, {recursive: true, force: true});
  }
});

test('ordinary and new files are allowed', () => {
  for (const path of [
    'services/p50k/jobs/fund_snapshots.py',
    'services/p50k/research_reviews/flow_v2.py',
    `${EVENT}/price_detectors/detectors_v2.py`,
    `${EVENT}/fund_review_flow_draft/PROTOCOL.md`,
    'docs/notes/current-state.md',
    'frontend/src/lib/raw.ts',
    resolve(repo, '..', 'elsewhere', 'file.txt'),
  ]) assert.equal(edit(path), 0, path);
  assert.equal(run('protect-paths.mjs', {tool_name: 'NotebookEdit', tool_input: {notebook_path: 'raw/x.ipynb'}}).status, 2);
  assert.equal(run('protect-paths.mjs', 'not json').status, 0);
});

test('history-rewriting and private-data git commands are blocked', () => {
  for (const command of [
    'git push --force origin main',
    'git push -f',
    'git push --force-with-lease origin claude/x',
    'git push origin +main',
    'git push origin --delete claude/x',
    'git push -d origin claude/x',
    'git push origin :claude/x',
    'git status && git push origin main --force',
    'git -C ../other push --force',
    'git merge --squash claude/x',
    'gh pr merge 7 --squash',
    'gh pr merge 7 -s',
    'gh pr merge 7 --rebase',
    'git add -f raw/tefas',
    'git add --force .claude/demo-logs',
    'git add raw/',
    'git add ./raw/tefas/prices/XYZ.json',
  ]) assert.equal(shell(command), 2, command);
});

test('ordinary git commands are allowed', () => {
  for (const command of [
    'git push origin main',
    'git push -u origin claude/agent-tooling',
    'git push origin HEAD:refs/heads/claude/x',
    'git push --follow-tags origin main',
    'git merge --no-ff claude/x',
    'gh pr merge 7 --merge',
    'git add -A',
    'git add docs/notes/raw-data-layout.md frontend/src/lib/raw.ts',
    'git commit -m "Never force-push or squash"',
    'git log --oneline -5',
  ]) assert.equal(shell(command), 0, command);
  assert.equal(run('guard-git.mjs', {tool_name: 'Bash', tool_input: {}}).status, 0);
});

test('session orientation prints context and exits 0', () => {
  const result = run('session-orientation.mjs', {hook_event_name: 'SessionStart', source: 'startup'});
  assert.equal(result.status, 0);
  assert.match(result.stdout, /^Project 50K session context: branch /);
  assert.match(result.stdout, /docs\/notes\/current-state\.md/);
});

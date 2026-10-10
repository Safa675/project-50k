// Self-test for the project hooks: node --test .claude/hooks/hooks.test.mjs (from the repository root).
import assert from 'node:assert/strict';
import {execFileSync, spawnSync} from 'node:child_process';
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
const edit = (path, root) => run('protect-paths.mjs', {tool_name: 'Edit', tool_input: {file_path: path}, cwd: root || repo}, root).status;
const shell = (command, cwd = repo) => run('guard-shell.mjs', {tool_name: 'Bash', tool_input: {command}, cwd}).status;
const EVENT = 'research/events/2026-09-17-spk-liquidations';

function tempRepo(files) {
  const root = mkdtempSync(join(tmpdir(), 'p50k-hooks-'));
  const git = (...args) => execFileSync('git', ['-C', root, ...args], {stdio: 'ignore'});
  git('init', '-q');
  git('config', 'core.autocrlf', 'false');
  for (const [path, text] of Object.entries(files)) {
    mkdirSync(dirname(join(root, path)), {recursive: true});
    writeFileSync(join(root, path), text);
  }
  git('add', '-A');
  git('-c', 'user.name=test', '-c', 'user.email=test@example.invalid', 'commit', '-q', '-m', 'fixture');
  return root;
}

test('file tools: frozen files and private data are blocked', () => {
  for (const path of [
    'docs/handoff-v0.5/START_HERE.md',
    `${EVENT}/price_detectors/detectors.py`,
    `${EVENT}/price_detectors/PREREGISTRATION.md`,
    `${EVENT}/fund_review_dated/PROTOCOL.md`,
    `${EVENT}/fund_futures_divergence/PREREGISTRATION.md`,
    'raw/tefas/prices/XYZ.json',
    `${EVENT}/raw/notes.json`,
    join(repo, 'docs', 'handoff-v0.5', 'AGENTS.md'),
  ]) assert.equal(edit(path), 2, path);
  if (process.platform === 'win32') {
    assert.equal(edit('Docs/Handoff-v0.5/X.md'), 2);
    assert.equal(edit('RAW/x.json'), 2);
    assert.equal(edit('Services/P50K/Replay.py'), 2);
  }
});

test('file tools: registered bundle files are blocked unless a reseal is opted into', () => {
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
    assert.equal(edit('raw/x.json', root), 2);
  } finally {
    rmSync(root, {recursive: true, force: true});
  }
});

test('file tools: ordinary and new files are allowed', () => {
  for (const path of [
    'services/p50k/jobs/fund_snapshots.py',
    'services/p50k/research_reviews/dated_flow.py',
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

test('shell: history rewrites, squash merges and private-data staging are blocked', () => {
  for (const command of [
    'git push --force origin main',
    'git push -f',
    'git push -uf origin main',
    'git push -fu origin main',
    'git push -qf',
    'git push --force-with-lease origin claude/x',
    'git push --mirror origin',
    'git push --prune origin',
    'git push origin +main',
    'git push origin "+main"',
    'git push origin --delete claude/x',
    'git push -d origin claude/x',
    "git push origin ':claude/x'",
    'git push origin main \\\n  --force',
    'git push origin main `\n  --force',
    'git status && git push origin main --force',
    'git -C ../other push --force',
    'git merge --squash claude/x',
    'git pull --squash origin claude/x',
    'gh pr merge 7 --squash',
    'gh pr merge 7 -s',
    'gh pr merge 7 --rebase',
    'gh api -X PUT repos/o/r/pulls/7/merge -f merge_method=squash',
    'gh api --method DELETE repos/o/r/git/refs/heads/claude/x',
    'gh api -X PATCH repos/o/r/git/refs/heads/main -F sha=abc -F force=true',
    'git add -f raw/tefas',
    'git add -Af',
    'git add -fA .',
    'git add --force .claude/demo-logs',
    'git add raw/',
    'git add ./raw/tefas/prices/XYZ.json',
    'git clean -fdx',
    'git clean -xfd',
    'git clean -X -f',
    'git stash -a',
    'git stash push --all',
  ]) assert.equal(shell(command), 2, command);
});

test('shell: writes and deletions that hit protected files are blocked', () => {
  for (const command of [
    'rm -rf raw',
    'rm -rf ./raw/',
    'rm -rf *',
    'rm -rf .',
    'Remove-Item -Recurse -Force raw',
    `rm -r ${EVENT}/raw`,
    'rm -rf docs',
    'rm services/p50k/research_reviews/*.py',
    'cd frontend && rm -rf ../raw',
    `rm -rf "${join(repo, 'raw')}"`,
    "sed -i 's/a/b/' services/p50k/replay.py",
    "perl -pi -e 's/a/b/' docs/handoff-v0.5/START_HERE.md",
    "cat > services/p50k/evidence_store.py <<'EOF'\nx = 1\nEOF",
    `echo x >> ${EVENT}/price_detectors/results.json`,
    'Set-Content -Path services/p50k/replay.py -Value x',
    'cp /tmp/x services/p50k/research_reviews/bundle.py',
    'Copy-Item C:/tmp/x -Destination services/p50k/replay.py',
    'mv services/p50k/replay.py /tmp/x',
    'tee docs/handoff-v0.5/x.md',
    `git rm ${EVENT}/price_detectors/detectors.py`,
  ]) assert.equal(shell(command), 2, command);
  assert.equal(shell('rm -rf ../raw', join(repo, 'frontend')), 2);
});

test('shell: ordinary commands are allowed', () => {
  for (const command of [
    'git push origin main',
    'git push -u origin claude/agent-tooling',
    'git push origin HEAD:refs/heads/claude/x',
    'git push --follow-tags origin main',
    'git merge --no-ff claude/x',
    'gh pr merge 7 --merge',
    'gh pr merge 7 --merge --body "do not use -s"',
    'gh api repos/o/r/pulls/7',
    'git add -A',
    'git add docs/notes/raw-data-layout.md frontend/src/lib/raw.ts',
    'git commit -m "docs: never git push --force"',
    "git commit -F - <<'EOF'\nNever git push --force or git add -f raw/\nEOF",
    'git log --grep "push -f"',
    'git log --oneline -5',
    'git remote add -f upstream https://example.invalid/repo.git',
    'git worktree add -f ../wt main',
    'git clean -fd',
    'git clean -nx',
    'git stash -u',
    'git stash apply',
    'grep -rn "git push --force" .claude/',
    'Select-String -Pattern "push --force" -Path AGENTS.md',
    'sed -n 1,10p services/p50k/replay.py',
    'cat services/p50k/replay.py > /tmp/copy.py',
    'cp services/p50k/replay.py /tmp/x',
    'rm frontend/src/lib/raw.ts',
    'rm -rf frontend/.next node_modules',
    'rm -rf /tmp/scratch/*',
    `python ${EVENT}/fund_review_dated/run.py --v1-bundle raw/research/x --snapshot-db raw/snapshots/s.sqlite3`,
    'npm run build 2>&1 | tail -5',
    'echo ok > /dev/null',
  ]) assert.equal(shell(command), 0, command);
  assert.equal(run('guard-shell.mjs', {tool_name: 'Bash', tool_input: {}}).status, 0);
});

test('tripwire reports protected files that differ from HEAD', () => {
  const root = tempRepo({
    'services/p50k/replay.py': 'x = 1\n',
    'services/p50k/jobs/other.py': 'y = 1\n',
    'docs/handoff-v0.5/START_HERE.md': 'frozen\n',
  });
  const trip = () => run('tripwire.mjs', {tool_name: 'Bash'}, root);
  try {
    assert.equal(trip().status, 0);
    writeFileSync(join(root, 'services/p50k/jobs/other.py'), 'y = 2\n');
    assert.equal(trip().status, 0);
    writeFileSync(join(root, 'services/p50k/replay.py'), 'x = 2\n');
    const result = trip();
    assert.equal(result.status, 2);
    assert.match(result.stderr, /services\/p50k\/replay\.py/);
    mkdirSync(join(root, '.claude'));
    writeFileSync(join(root, '.claude', 'allow-registered-edits.local'), '');
    assert.equal(trip().status, 0);
    writeFileSync(join(root, 'docs/handoff-v0.5/START_HERE.md'), 'changed\n');
    assert.equal(trip().status, 2);
    const orientation = run('session-orientation.mjs', {source: 'startup'}, root);
    assert.equal(orientation.status, 0);
    assert.match(orientation.stdout, /WARNING: protected files differ from HEAD: docs\/handoff-v0\.5\/START_HERE\.md/);
  } finally {
    rmSync(root, {recursive: true, force: true});
  }
});

test('session orientation prints context and exits 0', () => {
  const result = run('session-orientation.mjs', {hook_event_name: 'SessionStart', source: 'startup'});
  assert.equal(result.status, 0);
  assert.match(result.stdout, /^Project 50K session context: branch /);
  assert.match(result.stdout, /docs\/notes\/current-state\.md/);
});

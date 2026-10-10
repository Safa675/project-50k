#!/usr/bin/env node
// PreToolUse guard for shell commands (Bash and PowerShell). Exit 2 blocks the command; stderr explains why.
// It recognises the usual spellings of history rewrites, private-data staging, and shell writes or deletions
// that hit protected files. It is a heuristic: tripwire.mjs reports protected files that changed anyway.
import {basename, resolve} from 'node:path';
import {REASONS, protection, readInput, root, toRel} from './lib/protected.mjs';

const input = readInput();
const command = input?.tool_input?.command;
if (typeof command !== 'string' || !command.trim()) process.exit(0);
// Updated by cd, Set-Location and pushd inside the command so later relative paths resolve correctly.
let cwd = typeof input.cwd === 'string' && input.cwd ? input.cwd : root;

function block(reason) {
  process.stderr.write(`Blocked command: ${reason}\n`);
  process.exit(2);
}

// Drop heredoc and here-string bodies (commit messages, file contents) and join continued lines.
function normalize(text) {
  return text.replace(/\r\n/g, '\n')
    .replace(/@(['"])[ \t]*\n[\s\S]*?\n\1@/g, '@@')
    .replace(/(<<-?[ \t]*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\2[^\n]*)\n[\s\S]*?\n[ \t]*\3[ \t]*(?=\n|$)/g, '$1')
    .replace(/\\\n/g, ' ')
    .replace(/`\n/g, ' ');
}

// Simple commands as token lists, split at newlines, ;, &&, ||, |, parentheses and braces outside quotes.
function commands(text) {
  const result = [];
  let tokens = [];
  let current = '';
  let active = false;
  let quote = null;
  const endToken = () => { if (active) tokens.push(current); current = ''; active = false; };
  const endCommand = () => { endToken(); if (tokens.length) result.push(tokens); tokens = []; };
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quote) {
      if (ch === quote) quote = null;
      else if (ch === '\\' && quote === '"' && '"\\$`'.includes(text[i + 1] ?? '')) current += text[++i];
      else current += ch;
      continue;
    }
    if (ch === '"' || ch === "'") { quote = ch; active = true; continue; }
    if ('\n;(){}'.includes(ch)) { endCommand(); continue; }
    if (ch === '|' || (ch === '&' && text[i + 1] === '&')) {
      if (text[i + 1] === ch) i++;
      endCommand();
      continue;
    }
    if (ch === ' ' || ch === '\t') { endToken(); continue; }
    current += ch;
    active = true;
  }
  endCommand();
  return result;
}

const WRAPPERS = new Set(['sudo', 'env', 'command', 'exec', 'nohup', 'time', '&', '.', '$', 'call', 'start']);
const DELETE = new Set(['rm', 'rmdir', 'del', 'erase', 'rd', 'remove-item', 'ri', 'unlink', 'shred']);
const MOVE = new Set(['mv', 'move', 'move-item', 'mi', 'ren', 'rename', 'rename-item', 'rni']);
const COPY = new Set(['cp', 'copy', 'copy-item', 'cpi', 'install', 'rsync', 'robocopy', 'xcopy']);
const WRITE = new Set(['tee', 'set-content', 'sc', 'add-content', 'ac', 'out-file', 'truncate', 'new-item', 'ni', 'clear-content', 'clc']);
// PowerShell parameters whose value is not a path.
const VALUE_PARAMETERS = new Set(['-value', '-encoding', '-inputobject', '-filter', '-include', '-exclude', '-itemtype', '-type', '-width', '-stream', '-s', '-size']);
const REDIRECT = /^(?:\d|&|\*)?>>?(.*)$/;

function operandsOf(args) {
  const operands = [];
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (REDIRECT.test(arg)) { if (!REDIRECT.exec(arg)[1]) i++; continue; }
    if (arg.startsWith('-')) { if (VALUE_PARAMETERS.has(arg.toLowerCase())) i++; continue; }
    operands.push(arg);
  }
  return operands;
}

function check(path, kind) {
  const reason = protection(toRel(path, cwd), kind);
  if (reason) block(`${reason} (${path})`);
}

function checkGit(args) {
  let i = 0;
  while (i < args.length && args[i].startsWith('-')) {
    i += ['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env'].includes(args[i]) ? 2 : 1;
  }
  const sub = args[i];
  const rest = args.slice(i + 1);
  const options = rest.filter((arg) => arg.startsWith('-'));
  const operands = operandsOf(rest);
  const short = (letters) => options.some((o) => /^-[A-Za-z0-9]+$/.test(o) && [...letters].some((l) => o.includes(l)));
  const long = (...names) => options.some((o) => names.some((n) => o === n || o.startsWith(`${n}=`)));
  if (sub === 'push' && (long('--force', '--force-with-lease', '--mirror', '--prune', '--delete') || short('fd')
      || operands.some((o) => o.startsWith('+') || o.startsWith(':')))) {
    block('Pushes that force, mirror, prune or delete rewrite or drop published history; the owner pulls this ' +
      'repository (DEC-027). Push new commits instead.');
  }
  if ((sub === 'merge' || sub === 'pull') && long('--squash')) {
    block('Squash merges drop protocol commits from main (DEC-026/027). Use a merge commit: git merge --no-ff.');
  }
  if (sub === 'add' || sub === 'stage') {
    if (long('--force') || short('f')) block('Force-adding ignored files can stage private raw/ data. Stage explicit paths only.');
    for (const operand of operands) if (protection(toRel(operand, cwd)) === REASONS.raw) block(REASONS.raw);
  }
  if (sub === 'clean' && short('xX') && !(short('n') || long('--dry-run'))) {
    block('git clean -x/-X deletes ignored files, including private raw/ data and sealed bundles.');
  }
  if (sub === 'stash' && (long('--all') || short('a'))) {
    block('git stash --all moves ignored files, including private raw/ data, out of the working tree.');
  }
  if (sub === 'rm' || sub === 'mv') operands.forEach((operand) => check(operand, 'delete'));
}

function checkGh(args) {
  const text = args.join(' ');
  if (args[0] === 'pr' && args[1] === 'merge' && args.some((a) => ['--squash', '-s', '--rebase', '-r'].includes(a))) {
    block('Merge pull requests with a merge commit (gh pr merge --merge); squash or rebase merges drop protocol commits.');
  }
  if (args[0] === 'repo' && args[1] === 'delete') block('Deleting a repository is not an agent action.');
  if (args[0] !== 'api') return;
  let method = '';
  args.forEach((a, i) => {
    if (a === '-X' || a === '--method') method = args[i + 1] || '';
    else if (/^-X[A-Za-z]+$/.test(a)) method = a.slice(2);
    else if (a.startsWith('--method=')) method = a.slice(9);
  });
  method = method.toUpperCase();
  if (/merge_method=(squash|rebase)/i.test(text)) {
    block('Merge pull requests with a merge commit; squash or rebase merges drop protocol commits.');
  }
  if (/(^|\s)\/?repos\/\S+\/(git\/refs|branches)\//.test(text) && (method === 'DELETE' || /\bforce=true\b/i.test(text))) {
    block('Deleting or force-updating branches through the API rewrites published history (DEC-027).');
  }
  if (method === 'DELETE' && /(^|\s)\/?repos\/[^/\s]+\/[^/\s]+\/?(\s|$)/.test(text)) block('Deleting a repository is not an agent action.');
}

function checkFiles(name, args) {
  const operands = operandsOf(args);
  if (DELETE.has(name) || MOVE.has(name)) operands.forEach((path) => check(path, 'delete'));
  if (WRITE.has(name)) operands.forEach((path) => check(path, 'edit'));
  if (COPY.has(name)) {
    const named = args.findIndex((a) => /^-dest(ination)?$/i.test(a));
    if (named >= 0) check(args[named + 1], 'edit');
    else if (operands.length > 1) check(operands[operands.length - 1], 'edit');
  }
  if ((name === 'sed' || name === 'perl') && args.some((a) => /^-[A-Za-z]*i/.test(a) || a.startsWith('--in-place'))) {
    operands.forEach((path) => check(path, 'edit'));
  }
  if (name === 'dd') args.filter((a) => a.startsWith('of=')).forEach((a) => check(a.slice(3), 'edit'));
  for (let i = 0; i < args.length; i++) {
    const match = REDIRECT.exec(args[i]);
    if (!match) continue;
    const target = match[1] || args[i + 1];
    if (target && !target.startsWith('&') && !/^(\/dev\/null|\$null|nul)$/i.test(target)) check(target, 'edit');
  }
}

for (let tokens of commands(normalize(command))) {
  while (tokens.length && (/^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[0]) || WRAPPERS.has(tokens[0].toLowerCase()))) tokens = tokens.slice(1);
  if (!tokens.length) continue;
  const name = basename(tokens[0].replace(/\\/g, '/')).toLowerCase().replace(/\.exe$/, '');
  const args = tokens.slice(1);
  if (['cd', 'chdir', 'pushd', 'set-location', 'sl'].includes(name)) {
    const target = operandsOf(args)[0];
    if (target && !target.startsWith('~') && !target.startsWith('$')) cwd = resolve(cwd, target);
    continue;
  }
  if (name === 'git') checkGit(args);
  if (name === 'gh') checkGh(args);
  checkFiles(name, args);
}
process.exit(0);

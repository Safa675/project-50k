#!/usr/bin/env node
// PreToolUse guard for shell commands (Bash and PowerShell). Exit 2 blocks the command.
// The owner only pulls (DEC-027): published history must never be rewritten, protocol commits must stay
// reachable from main, and private raw data must never be staged.
import {readFileSync} from 'node:fs';

let input = {};
try { input = JSON.parse(readFileSync(0, 'utf8') || '{}'); } catch { process.exit(0); }
const command = input?.tool_input?.command;
if (typeof command !== 'string' || !command) process.exit(0);

const rules = [
  [/\bgit\b[^\n;&|]*\bpush\b[^\n;&|]*(\s--force(-with-lease)?\b|\s-f\b|\s\+[^\s]+)/,
    'Force pushes rewrite published history; the owner pulls this repository (DEC-027). Push new commits instead.'],
  [/\bgit\b[^\n;&|]*\bpush\b[^\n;&|]*(\s--delete\b|\s-d\b|\s:[A-Za-z0-9._\/-]+)/,
    'Deleting remote branches can drop protocol-before-calculation evidence. Merge their history first and ask the user.'],
  [/\bgit\b[^\n;&|]*\bmerge\b[^\n;&|]*\s--squash\b/,
    'Squash merges drop protocol commits from main (DEC-026/027). Use a merge commit: git merge --no-ff.'],
  [/\bgh\s+pr\s+merge\b[^\n;&|]*\s(--squash|-s|--rebase|-r)\b/,
    'Merge pull requests with a merge commit (gh pr merge --merge); squash or rebase merges drop protocol commits.'],
  [/\bgit\b[^\n;&|]*\badd\b[^\n;&|]*\s(-f|--force)\b/,
    'Force-adding ignored files can stage private raw data. Stage explicit paths only.'],
  [/\bgit\b[^\n;&|]*\badd\b[^\n;&|]*\s["']?(\.\/)?raw(\/|["'\s]|$)/,
    'raw/ holds private TEFAS/KAP data and must never be committed.'],
];
for (const [pattern, reason] of rules) {
  if (pattern.test(command)) {
    process.stderr.write(`Blocked command: ${reason}\n`);
    process.exit(2);
  }
}
process.exit(0);

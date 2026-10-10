#!/usr/bin/env node
// PreToolUse guard for Edit/Write/MultiEdit/NotebookEdit. Exit 2 blocks the edit; stderr explains why.
// Frozen files and private data are never edited. Files bound into sealed research bundles are
// blocked by default because editing them makes every sealed bundle fail verification (API 503).
import {protection, readInput, toRel} from './lib/protected.mjs';

const input = readInput();
const target = input?.tool_input?.file_path || input?.tool_input?.notebook_path;
const rel = toRel(target, input?.cwd);
const reason = protection(rel, 'edit');
if (reason) {
  process.stderr.write(`Blocked edit to ${rel}: ${reason}\n`);
  process.exit(2);
}
process.exit(0);

#!/usr/bin/env node
// PostToolUse tripwire for shell commands: reports protected tracked files that now differ from HEAD.
// guard-shell.mjs is a heuristic; this catches writes it missed (python -c, unusual redirects) right after
// they happen. Exit 2 shows the message to Claude; the command has already run.
import {drift, readInput} from './lib/protected.mjs';

readInput();
const changed = drift();
if (changed.length) {
  process.stderr.write(
    `Protected files now differ from HEAD: ${changed.slice(0, 8).join(', ')}${changed.length > 8 ? ', ...' : ''}. ` +
    'Unless the user approved this exact change, restore each one with `git checkout HEAD -- <file>` and tell the ' +
    'user. A changed file bound into a sealed bundle makes the running demo answer 503.\n');
  process.exit(2);
}
process.exit(0);

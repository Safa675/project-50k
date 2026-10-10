// Claude Read/Grep/Glob guard. Codex must enforce the same boundary by hand.
import fs from 'node:fs';

export function isSecretPath(value) {
  if (typeof value !== 'string') return false;
  return value.replaceAll('\\', '/').split('/').some(
    part => part.toLowerCase() === 'secrets' || part.toLowerCase().startsWith('.env'),
  );
}

if (process.argv[1]?.endsWith('protect-secret-reads.mjs')) {
  const input = JSON.parse(fs.readFileSync(0, 'utf8') || '{}');
  const args = input.tool_input || {};
  if ([args.file_path, args.path, args.pattern, args.glob].some(isSecretPath)) {
    process.stderr.write('Blocked secret read: agents must not read .env files or secrets/.\n');
    process.exit(2);
  }
}

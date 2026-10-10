import assert from 'node:assert/strict';
import test from 'node:test';
import {isSecretPath} from './protect-secret-reads.mjs';

test('blocks Windows and POSIX secret file paths', () => {
  for (const path of ['secrets/openai_api_key', 'C:\\app\\secrets\\key', '.env', '/app/.env.local']) {
    assert.equal(isSecretPath(path), true);
  }
});

test('ordinary source paths remain readable', () => {
  for (const path of ['services/p50k/product/settings.py', 'db/migrations', undefined]) {
    assert.equal(isSecretPath(path), false);
  }
});

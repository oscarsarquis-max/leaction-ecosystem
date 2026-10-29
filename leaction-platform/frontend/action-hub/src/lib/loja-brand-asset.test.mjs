import assert from 'node:assert/strict';
import { existsSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = join(dirname(fileURLToPath(import.meta.url)), '../..');
const asset = join(root, 'public/brands/lojadepaes.png');

test('logo oficial da Loja está no public do Hub', () => {
  assert.equal(existsSync(asset), true);
  assert.ok(statSync(asset).size > 10000);
});

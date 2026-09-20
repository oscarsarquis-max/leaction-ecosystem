import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { collectEvidenceRefs, validateDocumentationContent } from '../src/console/documentation/validate.js';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const spiderRoot = resolve(frontendRoot, '..');

const structural = validateDocumentationContent();
const missing = [];
const seen = new Set();

for (const ref of collectEvidenceRefs()) {
  if (seen.has(ref.path)) continue;
  seen.add(ref.path);
  if (/^https?:/i.test(ref.path) || ref.path.startsWith('ausência')) continue;
  const full = resolve(spiderRoot, ref.path);
  if (!existsSync(full)) missing.push(`${ref.owner}: ${ref.path}`);
}

if (!structural.ok || missing.length) {
  for (const error of structural.errors) console.error(`content: ${error}`);
  for (const error of missing) console.error(`missing: ${error}`);
  process.exit(1);
}

console.log(`documentation snapshot ok (${seen.size} evidence paths)`);

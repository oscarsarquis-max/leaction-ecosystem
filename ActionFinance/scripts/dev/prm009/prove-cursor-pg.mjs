import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { listOrderSql } = require('../../../../leaction-platform/services/gateway-api/domain/spider-pay-lookup.js');

const evidenceDir = join(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  '..',
  'documents',
  'reviews',
  'evidence',
  'prm-009-cor-001',
);
mkdirSync(evidenceDir, { recursive: true });

const name = 'prm009-cursor-pg';
const port = '55434';

function psql(sql) {
  return execFileSync(
    'docker',
    ['exec', '-e', 'PGPASSWORD=prm009', name, 'psql', '-U', 'prm009', '-d', 'cursor_proof', '-v', 'ON_ERROR_STOP=1', '-t', '-A', '-c', sql],
    { encoding: 'utf8' },
  ).trim();
}

function ensureDb() {
  const existing = execFileSync('docker', ['ps', '-a', '--filter', `name=^/${name}$`, '--format', '{{.Names}}'], {
    encoding: 'utf8',
  }).trim();
  if (existing === name) {
    execFileSync('docker', ['start', name], { encoding: 'utf8' });
  } else {
    execFileSync(
      'docker',
      [
        'run',
        '-d',
        '--name',
        name,
        '--label',
        'prm009=1',
        '-e',
        'POSTGRES_USER=prm009',
        '-e',
        'POSTGRES_PASSWORD=prm009',
        '-e',
        'POSTGRES_DB=cursor_proof',
        '-p',
        `127.0.0.1:${port}:5432`,
        'postgres:17.6',
      ],
      { encoding: 'utf8' },
    );
  }
  for (let i = 0; i < 40; i += 1) {
    try {
      execFileSync('docker', ['exec', name, 'pg_isready', '-U', 'prm009', '-d', 'cursor_proof'], { encoding: 'utf8' });
      return;
    } catch {
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 500);
    }
  }
  throw new Error('cursor proof db not ready');
}

function walkAll(limit = 2) {
  const seen = [];
  let cursor = null;
  let pages = 0;
  while (pages < 20) {
    pages += 1;
    const params = ["'homolog-padaria'"];
    let sql = `SELECT id::text, date_trunc('milliseconds', updated_at) AS cursor_ts
      FROM orders
      WHERE gateway_ref LIKE ('hub:' || 'homolog-padaria' || ':%')`;
    if (cursor) {
      params.push(`'${cursor.updatedAt}'::timestamptz`, `'${cursor.id}'`);
      sql += ` AND (date_trunc('milliseconds', updated_at), id::text) > (${params[1]}, ${params[2]})`;
    }
    sql += ` ${listOrderSql()} LIMIT ${limit + 1}`;
    const rows = psql(sql)
      .split('\n')
      .filter(Boolean)
      .map((line) => {
        const [id, cursorTs] = line.split('|');
        return { id, cursorTs };
      });
    const page = rows.slice(0, limit);
    if (page.length === 0) break;
    for (const row of page) seen.push(row.id);
    if (rows.length <= limit) break;
    const last = page[page.length - 1];
    cursor = { updatedAt: last.cursorTs, id: last.id };
  }
  return seen;
}

ensureDb();
psql(`
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  gateway_ref TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
INSERT INTO orders (id, gateway_ref, updated_at) VALUES
  ('20000000-0000-4000-8000-000000000001', 'hub:homolog-padaria:a', TIMESTAMPTZ '2026-10-01 12:00:00.123456+00'),
  ('20000000-0000-4000-8000-000000000002', 'hub:homolog-padaria:b', TIMESTAMPTZ '2026-10-01 12:00:00.123999+00'),
  ('20000000-0000-4000-8000-000000000003', 'hub:homolog-padaria:c', TIMESTAMPTZ '2026-10-01 12:00:00.123000+00'),
  ('20000000-0000-4000-8000-000000000004', 'hub:homolog-padaria:d', TIMESTAMPTZ '2026-10-01 12:00:01.000000+00'),
  ('20000000-0000-4000-8000-000000000005', 'hub:homolog-padaria:e', TIMESTAMPTZ '2026-10-01 12:00:01.000000+00');
`);

const first = walkAll(2);
const expected = [
  '20000000-0000-4000-8000-000000000001',
  '20000000-0000-4000-8000-000000000002',
  '20000000-0000-4000-8000-000000000003',
  '20000000-0000-4000-8000-000000000004',
  '20000000-0000-4000-8000-000000000005',
];
if (first.length !== 5 || expected.some((id) => !first.includes(id))) {
  throw new Error(`perda no limite: ${JSON.stringify(first)}`);
}

psql(`UPDATE orders SET updated_at = TIMESTAMPTZ '2026-10-01 12:00:02.500123+00' WHERE id = '20000000-0000-4000-8000-000000000001'`);
const second = walkAll(2);
if (!second.includes('20000000-0000-4000-8000-000000000001') || second.length !== 5) {
  throw new Error(`item atualizado perdido: ${JSON.stringify(second)}`);
}

const report = {
  orderSql: listOrderSql(),
  firstWalk: first,
  afterUpdate: second,
  sameMillisecondDistinctMicros: true,
  sameTimestampDistinctIds: true,
  updatedRowReappears: true,
  loss: false,
};
writeFileSync(join(evidenceDir, 'cursor-pg-proof.json'), JSON.stringify(report, null, 2));
process.stdout.write(`CURSOR_PG_OK count=${first.length} updatedReappears=true\n`);

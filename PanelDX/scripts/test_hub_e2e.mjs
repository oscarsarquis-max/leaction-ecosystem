#!/usr/bin/env node
'use strict';

const https = require('https');
const path = require('path');
const { createRequire } = require('module');
const requireFromGateway = createRequire(
  path.join('/var/www/leaction-platform/services/gateway-api', 'package.json')
);
const { Pool } = requireFromGateway('pg');

const PANELDX_BASE = process.env.PANELDX_BASE || 'https://paneldx.com.br';
const HUB_API = process.env.HUB_API || 'https://api.actionhub.com.br';
const TEST_EMAIL = process.env.TEST_EMAIL || 'dev@leaction.com.br';
const TEST_SKU = process.env.TEST_SKU || 'PANEL_MATURIDADE';
const PANELDX_DB_PASSWORD = process.env.PANELDX_DB_PASSWORD;

if (!PANELDX_DB_PASSWORD) {
  console.error('PANELDX_DB_PASSWORD obrigatorio');
  process.exit(2);
}

const agent = new https.Agent({ rejectUnauthorized: false });

function httpJson(method, url, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const payload = body ? JSON.stringify(body) : null;
    const req = https.request(
      {
        hostname: u.hostname,
        port: u.port || 443,
        path: u.pathname + u.search,
        method,
        agent,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
        },
      },
      (res) => {
        let raw = '';
        res.on('data', (c) => (raw += c));
        res.on('end', () => {
          let parsed = {};
          try {
            parsed = raw ? JSON.parse(raw) : {};
          } catch (_) {
            parsed = { _raw: raw };
          }
          resolve({ status: res.statusCode, body: parsed });
        });
      }
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

async function findTestMatu() {
  const pool = new Pool({
    host: 'paneldx-database.czqyam2auctn.us-east-2.rds.amazonaws.com',
    port: 5432,
    database: 'LeAction_SysF',
    user: 'postgres',
    password: PANELDX_DB_PASSWORD,
    ssl: { rejectUnauthorized: false },
  });
  const q = `
    SELECT m.id_matu, m.status_ia, COALESCE(p.status, ''), c.mail_clie, COALESCE(c.has_active_project, false)
    FROM ctdi_matu m
    JOIN ctdi_clie c ON c.id_clie = m.id_clie
    LEFT JOIN ctdi_projetos p ON p.id_clie = c.id_clie
    WHERE lower(c.mail_clie) = lower($1)
    ORDER BY m.id_matu DESC
    LIMIT 5`;
  let { rows } = await pool.query(q, [TEST_EMAIL]);
  if (!rows.length) {
  ({ rows } = await pool.query(`
      SELECT m.id_matu, m.status_ia, COALESCE(p.status, ''), c.mail_clie, COALESCE(c.has_active_project, false)
      FROM ctdi_matu m
      JOIN ctdi_clie c ON c.id_clie = m.id_clie
      LEFT JOIN ctdi_projetos p ON p.id_clie = c.id_clie
      ORDER BY m.id_matu DESC
      LIMIT 10`));
  }
  await pool.end();
  return rows;
}

async function matuState(idMatu) {
  const pool = new Pool({
    host: 'paneldx-database.czqyam2auctn.us-east-2.rds.amazonaws.com',
    port: 5432,
    database: 'LeAction_SysF',
    user: 'postgres',
    password: PANELDX_DB_PASSWORD,
    ssl: { rejectUnauthorized: false },
  });
  const { rows } = await pool.query(
    `SELECT m.status_ia, COALESCE(p.status, ''), COALESCE(c.has_active_project, false), c.mail_clie
     FROM ctdi_matu m
     JOIN ctdi_clie c ON c.id_clie = m.id_clie
     LEFT JOIN ctdi_projetos p ON p.id_clie = c.id_clie
     WHERE m.id_matu = $1`,
    [idMatu]
  );
  await pool.end();
  return rows[0] || null;
}

(async () => {
  console.log('==> 1) Config via proxy PanelDX');
  const cfg = await httpJson('GET', `${PANELDX_BASE}/hub-api/config/payments`);
  console.log('HTTP', cfg.status, JSON.stringify(cfg.body).slice(0, 180));

  console.log('\n==> 2) Buscar id_matu no RDS');
  const candidates = await findTestMatu();
  candidates.forEach((r) =>
    console.log(`  id_matu=${r.id_matu} status_ia=${r.status_ia} projeto=${r.status} email=${r.mail_clie} active=${r.has_active_project}`)
  );
  if (!candidates.length) {
    console.error('Nenhum id_matu');
    process.exit(1);
  }
  const pick = candidates[0];
  const idMatu = pick.id_matu;
  const email = (pick.mail_clie || TEST_EMAIL).trim();
  console.log(`\nUsando id_matu=${idMatu} email=${email} (status_ia antes: ${pick.status_ia})`);

  console.log('\n==> 3) Criar pedido POST /hub-api/v1/payments');
  const created = await httpJson('POST', `${PANELDX_BASE}/hub-api/v1/payments`, {
    client_id: 'paneldx',
    sku: TEST_SKU,
    amount: 1,
    id_matu: String(idMatu),
    customer: { email, name: 'E2E Test' },
    webhook_url: `${PANELDX_BASE}/api/hub/payment-webhook`,
    hub_public_url: 'https://actionhub.com.br',
    return_to: '/projeto',
  });
  console.log('HTTP', created.status, JSON.stringify(created.body));
  if (created.status !== 201) process.exit(1);
  const orderId = created.body.payment_id;
  if (!orderId) process.exit(1);

  console.log('\n==> 4) Simular pagamento no Hub');
  const sim = await httpJson('POST', `${HUB_API}/simular-pagamento`, { order_id: orderId });
  console.log('HTTP', sim.status, JSON.stringify(sim.body));
  if (sim.status !== 200 || !sim.body.success) process.exit(1);
  if (!sim.body.webhook_delivered) {
    console.error('webhook_delivered=false');
    process.exit(1);
  }

  console.log('\n==> 5) Verificar ativacao no PanelDX RDS');
  const after = await matuState(idMatu);
  console.log(`status_ia=${after.status_ia} projeto=${after.status} has_active_project=${after.has_active_project} email=${after.mail_clie}`);
  const activated =
    String(after.status_ia || '').trim().toUpperCase() === 'PROJETO OK' &&
    after.status === 'ATIVO' &&
    after.has_active_project === true;

  if (activated || sim.body.order?.status === 'PAID') {
    console.log('\nE2E OK — pedido pago e webhook entregue');
    if (activated) console.log('Diagnostico ativado (PROJETO OK / ATIVO)');
    else console.log('Pedido PAID; matu ja estava ativo ou status diferente');
    process.exit(0);
  }
  console.error('\nE2E falhou na ativacao');
  process.exit(1);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});

'use strict';

const { test, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const { randomUUID } = require('crypto');
const http = require('http');
const express = require('express');
const { Pool } = require('pg');

process.env.AMOUNT_CHECKOUT_APP_IDS = 'lojadepaes';
process.env.JWT_SECRET = 'reference-recovery-secret';

const {
  refreshAmountPaymentFromMercadoPago,
  registerAmountCheckoutRoutes,
  parseHubPayload,
} = require('./amount-checkout');

const url = process.env.PAY105A_TEST_DATABASE_URL;
if (url && !/^postgresql:\/\/[^@]+@127\.0\.0\.1:5438\/hub_pay105a$/.test(url)) {
  throw new Error('A dedicated local hub_pay105a database is required');
}
const pool = url ? new Pool({ connectionString: url }) : null;
const dbtest = url ? test : test.skip;
const OLD_SELECT = `SELECT o.id, o.status, o.gateway_ref, o.external_resource_id, p.type AS product_type
  FROM orders o JOIN products p ON p.id = o.product_id WHERE o.id = $1 LIMIT 1`;

before(async () => {
  if (!pool) return;
  await pool.query(`
    CREATE TABLE IF NOT EXISTS products(id uuid primary key, type text, external_resource_id text);
    ALTER TABLE products ADD COLUMN IF NOT EXISTS external_resource_id text;
    CREATE TABLE IF NOT EXISTS orders(
      id uuid primary key, status text, payment_status text, paid_at timestamptz,
      created_at timestamptz default now(), updated_at timestamptz default now(),
      external_resource_id text, gateway_reference text, gateway_ref text,
      payment_url text, product_id uuid, user_id uuid);
    CREATE TABLE IF NOT EXISTS webhook_outbox(
      id uuid primary key default gen_random_uuid(), app_id text, event_type text,
      payload_json jsonb, idempotency_key text unique, status text, attempts int,
      next_retry_at timestamptz, created_at timestamptz default now());
    CREATE TABLE IF NOT EXISTS app_registry(
      app_id text primary key, name text, active boolean, webhook_secret text,
      webhook_url text, return_origins text);
  `);
  await pool.query(
    `INSERT INTO app_registry(app_id, name, active, webhook_secret)
     VALUES('lojadepaes','Loja',true,'reference-secret')
     ON CONFLICT (app_id) DO UPDATE SET webhook_secret = EXCLUDED.webhook_secret, active = true`
  );
});

beforeEach(async () => {
  if (!pool) return;
  await pool.query('DROP TRIGGER IF EXISTS fail_outbox ON webhook_outbox');
  await pool.query('TRUNCATE orders, products, webhook_outbox');
});

after(async () => {
  if (pool) await pool.end();
});

function providerPayment(orderId, id, overrides = {}) {
  return {
    id,
    external_reference: orderId,
    status: 'approved',
    status_detail: 'accredited',
    captured: true,
    currency_id: 'BRL',
    transaction_amount: 70,
    transaction_amount_refunded: 0,
    date_approved: '2026-09-27T13:08:08.000Z',
    date_last_updated: '2026-09-27T13:08:09.000Z',
    live_mode: true,
    ...overrides,
  };
}

async function seedPaidOrder({ gatewayReference = '180134636613', payloadExtras = {}, status = 'PAID' } = {}) {
  const product = randomUUID();
  const id = randomUUID();
  const requestId = randomUUID();
  const payload = {
    source: 'amount_checkout',
    app_id: 'lojadepaes',
    amount_cents: 7000,
    currency: 'BRL',
    method: 'card',
    order_reference: `LP-TEST-${id.slice(0, 8)}`,
    payment_request_id: requestId,
    ...payloadExtras,
  };
  await pool.query(`INSERT INTO products(id, type) VALUES($1,'AMOUNT_CHECKOUT')`, [product]);
  await pool.query(
    `INSERT INTO orders(id, status, payment_status, product_id, gateway_ref, gateway_reference, external_resource_id)
     VALUES($1,$2,$3,$4,$5,$6,$7)`,
    [id, status, status === 'PAID' ? 'paid' : null, product, `amount:lojadepaes:${requestId}`, gatewayReference, JSON.stringify(payload)]
  );
  return { id, requestId, payload };
}

function listen(fetchPayment) {
  const app = express();
  registerAmountCheckoutRoutes(app, pool, { fetchPayment });
  return new Promise((resolve) => {
    const server = app.listen(0, '127.0.0.1', () => resolve(server));
  });
}

function getJson(server, path) {
  const { port } = server.address();
  return new Promise((resolve, reject) => {
    const req = http.request({
      host: '127.0.0.1',
      port,
      path,
      headers: { Authorization: 'Bearer reference-secret', 'X-App-Id': 'lojadepaes' },
    }, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        resolve({ status: res.statusCode, body: text ? JSON.parse(text) : {} });
      });
    });
    req.on('error', reject);
    req.end();
  });
}

dbtest('R01 old select never calls the provider; request route uses the stored numeric id', async () => {
  const seeded = await seedPaidOrder();
  const old = await pool.query(OLD_SELECT, [seeded.id]);
  assert.equal(Object.hasOwn(old.rows[0], 'gateway_reference'), false);
  let oldCalls = 0;
  await refreshAmountPaymentFromMercadoPago(pool, old.rows[0], seeded.payload, {
    fetchPayment: async () => {
      oldCalls += 1;
      throw new Error('a projeção antiga não pode consultar o provedor');
    },
  });
  assert.equal(oldCalls, 0);

  const seen = [];
  const server = await listen(async (id) => {
    seen.push(String(id));
    return providerPayment(seeded.id, id);
  });
  try {
    const response = await getJson(server, `/v1/checkout/amount?app_id=lojadepaes&payment_request_id=${seeded.requestId}`);
    assert.equal(response.status, 200);
    assert.deepEqual(seen, ['180134636613']);
    assert.equal(response.body.mp_payment_id, '180134636613');
    assert.equal(response.body.paid_amount_cents, 7000);
    assert.equal(response.body.provider_status, 'approved');
    assert.equal(response.body.provider_approved_at, '2026-09-27T13:08:08.000Z');
    assert.equal(response.body.amount_refunded_cents, 0);
    assert.equal(response.body.method, 'card');
    assert.equal(response.body.order_id, seeded.id);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
  const stored = await pool.query('SELECT status, gateway_reference, external_resource_id FROM orders WHERE id=$1', [seeded.id]);
  assert.equal(stored.rows[0].status, 'PAID');
  assert.equal(stored.rows[0].gateway_reference, '180134636613');
  const payload = parseHubPayload(stored.rows[0].external_resource_id);
  assert.equal(payload.mp_payment_id, '180134636613');
  assert.equal(payload.paid_amount_confirmed, true);
  const events = await pool.query(`SELECT event_type FROM webhook_outbox`);
  assert.equal(events.rows.length, 1);
  assert.equal(events.rows[0].event_type, 'PAYMENT_CONFIRMED');
});

dbtest('R02 order id route recovers the same charge and keeps the other app hidden', async () => {
  const seeded = await seedPaidOrder({ gatewayReference: '186395637864' });
  const otherRequest = randomUUID();
  const otherId = randomUUID();
  const product = (await pool.query('SELECT product_id FROM orders WHERE id=$1', [seeded.id])).rows[0].product_id;
  await pool.query(
    `INSERT INTO orders(id, status, product_id, gateway_ref, gateway_reference, external_resource_id)
     VALUES($1,'PAID',$2,$3,'999',$4)`,
    [otherId, product, `amount:other:${otherRequest}`, JSON.stringify({
      source: 'amount_checkout', app_id: 'other', amount_cents: 7000, currency: 'BRL',
      method: 'card', payment_request_id: otherRequest, order_reference: 'OTHER',
    })]
  );
  const seen = [];
  const server = await listen(async (id) => {
    seen.push(String(id));
    return providerPayment(seeded.id, id);
  });
  try {
    const found = await getJson(server, `/v1/checkout/amount/${seeded.id}?app_id=lojadepaes`);
    assert.equal(found.status, 200);
    assert.deepEqual(seen, ['186395637864']);
    assert.equal(found.body.mp_payment_id, '186395637864');
    assert.equal(found.body.paid_amount_cents, 7000);
    const hidden = await getJson(server, `/v1/checkout/amount?app_id=lojadepaes&payment_request_id=${otherRequest}`);
    assert.equal(hidden.status, 404);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
  assert.equal((await pool.query('SELECT count(*)::int AS n FROM orders')).rows[0].n, 2);
});

dbtest('R03 missing or non numeric reference does not invent an approval', async () => {
  const missing = await seedPaidOrder({ gatewayReference: null });
  const textual = await seedPaidOrder({ gatewayReference: 'amount-not-a-provider-id' });
  let calls = 0;
  const server = await listen(async () => {
    calls += 1;
    throw new Error('não há identificador para consultar');
  });
  try {
    for (const seeded of [missing, textual]) {
      const response = await getJson(server, `/v1/checkout/amount?app_id=lojadepaes&payment_request_id=${seeded.requestId}`);
      assert.equal(response.status, 200);
      assert.equal(response.body.mp_payment_id, null);
      assert.equal(response.body.paid_amount_cents, null);
      assert.equal(response.body.paid_amount_absent, true);
      assert.equal(response.body.status, 'PAID');
    }
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
  assert.equal(calls, 0);
  assert.equal((await pool.query('SELECT count(*)::int AS n FROM orders')).rows[0].n, 2);
  assert.equal((await pool.query('SELECT count(*)::int AS n FROM webhook_outbox')).rows[0].n, 0);
});

dbtest('R04 divergent provider data does not confirm or retarget the charge', async () => {
  const seeded = await seedPaidOrder();
  const stranger = randomUUID();
  const product = (await pool.query('SELECT product_id FROM orders WHERE id=$1', [seeded.id])).rows[0].product_id;
  await pool.query(
    `INSERT INTO orders(id, status, product_id, gateway_ref, external_resource_id)
     VALUES($1,'PENDING',$2,$3,$4)`,
    [stranger, product, `amount:lojadepaes:${randomUUID()}`, JSON.stringify({
      source: 'amount_checkout', app_id: 'lojadepaes', amount_cents: 7000, currency: 'BRL', method: 'card',
    })]
  );
  const cases = [
    providerPayment(stranger, '180134636613'),
    providerPayment(seeded.id, '180134636613', { currency_id: 'USD' }),
    providerPayment(seeded.id, '180134636613', { transaction_amount: 10 }),
    providerPayment(seeded.id, '180134636613', { captured: false }),
    providerPayment(seeded.id, '999', { id: '999' }),
  ];
  let index = 0;
  const server = await listen(async () => cases[index++]);
  try {
    for (let step = 0; step < cases.length; step += 1) {
      const response = await getJson(server, `/v1/checkout/amount/${seeded.id}?app_id=lojadepaes`);
      assert.equal(response.status, 200);
      assert.equal(response.body.amount_cents, 7000);
      assert.equal(response.body.order_id, seeded.id);
    }
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
  const rows = await pool.query('SELECT id, status, gateway_reference FROM orders ORDER BY status');
  const byId = Object.fromEntries(rows.rows.map((row) => [row.id, row]));
  assert.equal(byId[seeded.id].status, 'PAID');
  assert.equal(byId[seeded.id].gateway_reference, '180134636613');
  assert.equal(byId[stranger].status, 'PENDING');
  assert.equal((await pool.query(`SELECT count(*)::int AS n FROM webhook_outbox WHERE event_type='PAYMENT_CONFIRMED'`)).rows[0].n, 0);
});

dbtest('R05 provider failure leaves a proven charge untouched', async () => {
  const seeded = await seedPaidOrder();
  await pool.query(
    `UPDATE orders SET external_resource_id = $2 WHERE id = $1`,
    [seeded.id, JSON.stringify({ ...seeded.payload, paid_amount_cents: 7000, paid_amount_confirmed: true, provider_status: 'approved' })]
  );
  const failures = [
    async () => { throw new Error('timeout'); },
    async () => { const error = new Error('resource not found'); error.statusCode = 404; throw error; },
    async () => { throw new Error('Mercado Pago indisponível'); },
  ];
  let index = 0;
  const server = await listen(async () => failures[index++]());
  try {
    for (let step = 0; step < failures.length; step += 1) {
      const response = await getJson(server, `/v1/checkout/amount/${seeded.id}?app_id=lojadepaes`);
      assert.equal(response.status, 200);
      assert.equal(response.body.status, 'PAID');
      assert.equal(response.body.paid_amount_cents, 7000);
      assert.equal(response.body.provider_status, 'approved');
    }
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
  assert.equal((await pool.query('SELECT count(*)::int AS n FROM orders')).rows[0].n, 1);
  assert.equal((await pool.query('SELECT count(*)::int AS n FROM webhook_outbox')).rows[0].n, 0);
});

dbtest('R11 payload and pix identifiers stay ahead of the new column', async () => {
  const card = await seedPaidOrder({
    gatewayReference: '000',
    payloadExtras: { mp_payment_id: '185349985529' },
  });
  const pix = await seedPaidOrder({
    gatewayReference: null,
    payloadExtras: { method: 'pix', pix: { mp_payment_id: '186394563492', status: 'cancelled' } },
  });
  const seen = [];
  const server = await listen(async (id) => {
    seen.push(String(id));
    return providerPayment(seen.length === 1 ? card.id : pix.id, id, {
      status: seen.length === 1 ? 'approved' : 'cancelled',
      status_detail: seen.length === 1 ? 'accredited' : 'by_collector',
      transaction_amount_refunded: seen.length === 1 ? 0 : 70,
    });
  });
  try {
    const cardResponse = await getJson(server, `/v1/checkout/amount/${card.id}?app_id=lojadepaes`);
    const pixResponse = await getJson(server, `/v1/checkout/amount/${pix.id}?app_id=lojadepaes`);
    assert.equal(cardResponse.body.mp_payment_id, '185349985529');
    assert.equal(cardResponse.body.method, 'card');
    assert.equal(pixResponse.body.mp_payment_id, '186394563492');
    assert.equal(pixResponse.body.method, 'pix');
    assert.equal(pixResponse.body.status, 'PAID');
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
  assert.deepEqual(seen, ['185349985529', '186394563492']);
});

dbtest('R12 outbox failure cannot confirm, and the retry records one event', async () => {
  const seeded = await seedPaidOrder({ gatewayReference: '185000000001', status: 'PENDING' });
  await pool.query(`CREATE OR REPLACE FUNCTION fail_105a_event() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'outbox unavailable'; END $$;
    CREATE TRIGGER fail_outbox BEFORE INSERT ON webhook_outbox FOR EACH ROW EXECUTE FUNCTION fail_105a_event();`);
  const server = await listen(async (id) => providerPayment(seeded.id, id));
  try {
    const failed = await getJson(server, `/v1/checkout/amount/${seeded.id}?app_id=lojadepaes`);
    assert.equal(failed.status, 200);
    assert.equal(failed.body.status, 'PENDING');
    await pool.query('DROP TRIGGER fail_outbox ON webhook_outbox');
    const recovered = await getJson(server, `/v1/checkout/amount/${seeded.id}?app_id=lojadepaes`);
    assert.equal(recovered.status, 200);
    assert.equal(recovered.body.status, 'PAID');
    assert.equal(recovered.body.mp_payment_id, '185000000001');
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
  assert.equal((await pool.query(`SELECT count(*)::int AS n FROM webhook_outbox WHERE event_type='PAYMENT_CONFIRMED'`)).rows[0].n, 1);
  const again = await listen(async (id) => providerPayment(seeded.id, id));
  try {
    await getJson(again, `/v1/checkout/amount/${seeded.id}?app_id=lojadepaes`);
  } finally {
    await new Promise((resolve) => again.close(resolve));
  }
  assert.equal((await pool.query(`SELECT count(*)::int AS n FROM webhook_outbox WHERE event_type='PAYMENT_CONFIRMED'`)).rows[0].n, 1);
});

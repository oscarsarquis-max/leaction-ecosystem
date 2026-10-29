'use strict';

/**
 * Provas direcionadas 91C no Hub local (leaction_hub :5433).
 * Sem cobrança, sem produção, sem checkout na Loja.
 */

const { Pool } = require('pg');
const {
  mergeEntitlement,
  viewCredits,
  ensureCreditOperationsTable,
  reserveCredits,
  confirmCredits,
  releaseCredits,
} = require('../domain/credits-ops');
require('dotenv').config({ path: '../../../.env', override: true });

const APP = 'lojadepaes';
const SUBJECT = 'biblioteca.91c.sandbox@test.local';
const PRINCIPAL_SKU = 'LOJADEPAES_BIBLIOTECA_MENSAL';
const COMP_SKU = 'LOJADEPAES_BIBLIOTECA_CREDITOS';

const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 5433),
  database: process.env.DB_NAME || 'leaction_hub',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASS || 'password123',
});

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function writeSnapshot(payload, validUntil) {
  await pool.query(
    `INSERT INTO entitlement_snapshots (app_id, subject_id, payload_json, valid_until, updated_at)
     VALUES ($1, $2, $3::jsonb, $4, CURRENT_TIMESTAMP)
     ON CONFLICT (app_id, subject_id) DO UPDATE SET
       payload_json = EXCLUDED.payload_json,
       valid_until = EXCLUDED.valid_until,
       updated_at = CURRENT_TIMESTAMP`,
    [APP, SUBJECT, JSON.stringify(payload), validUntil]
  );
}

async function withTx(fn) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const out = await fn(client);
    await client.query('COMMIT');
    return out;
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

(async () => {
  const report = { env: 'local-hub-sandbox', charged: false, suite: '91c-targeted' };
  const principalUntil = new Date(Date.now() + 28 * 24 * 3600 * 1000).toISOString();
  const complementaryUntil = new Date(Date.now() + 12 * 24 * 3600 * 1000).toISOString();
  const run = `91c-${Date.now()}`;

  await ensureCreditOperationsTable(pool);
  await pool.query(`DELETE FROM credit_operations WHERE subject_id = $1`, [SUBJECT]);
  await pool.query(`DELETE FROM entitlement_snapshots WHERE app_id = $1 AND subject_id = $2`, [APP, SUBJECT]);

  const principalOnly = mergeEntitlement(
    {},
    [{ item_type: 'plan', sku: PRINCIPAL_SKU, meta_json: { periodicidade: 'mensal' } }],
    { credits: 20, direitos: { biblioteca: true } },
    principalUntil
  );
  assert(principalOnly.payload.credits === 20, 'principal sozinho concede 20');
  const principalRenew = mergeEntitlement(
    { ...principalOnly.payload, principal_credits: 4, credits: 4 },
    [{ item_type: 'plan', sku: PRINCIPAL_SKU, meta_json: { periodicidade: 'mensal' } }],
    { credits: 20, direitos: { biblioteca: true } },
    principalUntil
  );
  assert(principalRenew.payload.credits === 20, 'principal sem complementar: renovação = 20');
  assert(principalRenew.payload.complementary == null, 'principal sozinho não inventa complementar');
  report.principal_only_renew = 20;

  const leftoverComplementary = mergeEntitlement(
    {
      credits: 10,
      principal_credits: 7,
      complementary_credits: 3,
      complementary: { sku: COMP_SKU, remaining: 3, cycle_ends_at: complementaryUntil },
      plan: { sku: PRINCIPAL_SKU, franchise: 20 },
      premium: true,
    },
    [{ item_type: 'plan', sku: PRINCIPAL_SKU, meta_json: { periodicidade: 'mensal' } }],
    { credits: 20, direitos: { biblioteca: true } },
    principalUntil
  );
  assert(leftoverComplementary.payload.principal_credits === 20, 'renovação do principal define 20');
  assert(leftoverComplementary.payload.complementary_credits === 3, 'sobra do complementar permanece no próprio ciclo');
  report.principal_renew_keeps_complementary = leftoverComplementary.payload.credits;

  const bothRenewed = mergeEntitlement(
    leftoverComplementary.payload,
    [
      {
        item_type: 'plan',
        sku: COMP_SKU,
        quantity: 10,
        meta_json: { direitos: { papel: 'complementar' } },
      },
    ],
    { credits: 10, direitos: { papel: 'complementar', creditos: 10 } },
    complementaryUntil
  );
  assert(bothRenewed.payload.principal_credits === 20, 'ambos renovados: principal 20');
  assert(bothRenewed.payload.complementary_credits === 10, 'ambos renovados: complementar 10 novos, sem sobra');
  assert(bothRenewed.payload.credits === 30, 'ambos renovados no mesmo instante: 20+10');
  report.both_renewed = 30;

  const cancelledView = viewCredits(
    {
      ...bothRenewed.payload,
      complementary: { ...bothRenewed.payload.complementary, cycle_ends_at: '2000-01-01T00:00:00.000Z' },
    },
    Date.now(),
    principalUntil
  );
  assert(cancelledView.principalActive === true, 'principal segue após o complementar vencer');
  assert(cancelledView.complementaryActive === false, 'complementar encerra no próprio ciclo');
  assert(cancelledView.available === 20, 'após o complementar vencer, gastam-se só os 20 do principal');
  report.complementary_cancelled_at_period_end = { available: 20, complementary_active: false };

  const expiredView = viewCredits(bothRenewed.payload, Date.parse('2099-01-01T00:00:00.000Z'), principalUntil);
  assert(expiredView.available === 0 && expiredView.principalActive === false, 'expiração do principal bloqueia o gasto');
  report.expiration = true;

  const dup = mergeEntitlement(
    bothRenewed.payload,
    [{ item_type: 'plan', sku: PRINCIPAL_SKU, meta_json: { periodicidade: 'mensal' } }],
    { credits: 20, direitos: { biblioteca: true } },
    principalUntil
  );
  assert(dup.payload.principal_credits === 20, 'evento duplicado do principal não concede 40');
  assert(dup.payload.complementary_credits === 10, 'evento duplicado não zera o complementar vigente');
  report.duplicate_event = { principal: 20, complementary: 10 };

  await writeSnapshot(bothRenewed.payload, principalUntil);
  const reserved = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: SUBJECT, amount: 1, operationId: `${run}-consult` })
  );
  assert(reserved.ok && reserved.credits === 29, `consulta deveria deixar 29, veio ${reserved.credits}`);
  const confirmed = await withTx((client) =>
    confirmCredits(client, { appId: APP, subjectId: SUBJECT, operationId: `${run}-consult` })
  );
  assert(confirmed.ok && confirmed.status === 'confirmed', 'confirm da consulta');
  const recovered = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: SUBJECT, amount: 1, operationId: `${run}-consult` })
  );
  assert(recovered.idempotent && recovered.status === 'confirmed' && recovered.credits === 29, 'recuperação sem segundo débito');
  const releasedFail = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: SUBJECT, amount: 1, operationId: `${run}-fail` })
  );
  assert(releasedFail.ok && releasedFail.credits === 28, 'reserva da falha');
  const released = await withTx((client) =>
    releaseCredits(client, { appId: APP, subjectId: SUBJECT, operationId: `${run}-fail` })
  );
  assert(released.ok && released.credits === 29, `liberação deveria devolver, veio ${released.credits}`);
  report.consume_recover = { credits: 29, recovered: true, released: true };

  await pool.query(`DELETE FROM credit_operations WHERE subject_id = $1`, [SUBJECT]);
  await pool.query(`DELETE FROM entitlement_snapshots WHERE app_id = $1 AND subject_id = $2`, [APP, SUBJECT]);

  console.log(JSON.stringify({ ok: true, ...report }, null, 2));
  await pool.end();
})().catch(async (err) => {
  console.error('FAIL', err.message);
  try {
    await pool.end();
  } catch {
    /* ignore */
  }
  process.exit(1);
});

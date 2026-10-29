'use strict';

/**
 * Sandbox 91B no Hub local (leaction_hub :5433).
 * Não cobra, não fala com produção, não abre checkout na Loja.
 */

const { Pool } = require('pg');
const {
  classifyCatalogItemType,
  mergeEntitlement,
  ensureCreditOperationsTable,
  reserveCredits,
  confirmCredits,
  releaseCredits,
} = require('../domain/credits-ops');
require('dotenv').config({ path: '../../../.env', override: true });

const APP = 'lojadepaes';
const SUBJECT = 'biblioteca.91b.sandbox@test.local';
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

async function upsertPlan(sku, name, price, credits, complementary) {
  const meta = {
    creditos: credits,
    credits,
    periodicidade: 'mensal',
    period_months: 1,
    direitos: {
      assinatura: true,
      biblioteca: true,
      creditos: credits,
      ...(complementary ? { papel: 'complementar' } : {}),
    },
  };
  const features = complementary
    ? ['10 créditos adicionais no ciclo', 'Opcional', 'Mensal — não é compra avulsa']
    : ['20 créditos por ciclo', '1 crédito = 1 consulta', 'Não acumulam'];
  const existing = await pool.query(
    `SELECT id FROM catalog_plans WHERE app_id = $1 AND sku = $2 LIMIT 1`,
    [APP, sku]
  );
  if (existing.rows[0]) {
    const updated = await pool.query(
      `UPDATE catalog_plans
       SET name = $2, type = 'plan', price = $3, currency = 'BRL',
           features = $4::jsonb, meta_json = $5::jsonb, active = TRUE,
           updated_at = CURRENT_TIMESTAMP
       WHERE id = $1
       RETURNING id, sku, price, active`,
      [existing.rows[0].id, name, price, JSON.stringify(features), JSON.stringify(meta)]
    );
    return updated.rows[0];
  }
  const inserted = await pool.query(
    `INSERT INTO catalog_plans (app_id, name, type, sku, price, currency, features, meta_json, active)
     VALUES ($1, $2, 'plan', $3, $4, 'BRL', $5::jsonb, $6::jsonb, TRUE)
     RETURNING id, sku, price, active`,
    [APP, name, sku, price, JSON.stringify(features), JSON.stringify(meta)]
  );
  return inserted.rows[0];
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
  const report = { env: 'local-hub-sandbox', charged: false };

  await pool.query(
    `INSERT INTO app_registry (app_id, name, webhook_secret, return_origins, active)
     VALUES ($1, 'Loja de Pães', 'dev-hub-app-secret-lojadepaes',
             ARRAY['https://lojadepaes.com.br','http://127.0.0.1:5175']::TEXT[], TRUE)
     ON CONFLICT (app_id) DO UPDATE SET active = TRUE`,
    [APP]
  );

  assert(classifyCatalogItemType('plan', PRINCIPAL_SKU, 20) === 'plan', 'plano com 20 créditos não pode virar pack');

  const principal = await upsertPlan(PRINCIPAL_SKU, 'Principal da Biblioteca', 19, 20, false);
  const complementary = await upsertPlan(COMP_SKU, 'Complementar de créditos', 10, 10, true);
  report.plan_ids = { principal: principal.id, complementary: complementary.id };
  console.log('plan_ids', JSON.stringify(report.plan_ids));

  const ends = new Date(Date.now() + 28 * 24 * 3600 * 1000).toISOString();
  const granted = mergeEntitlement(
    {},
    [{ item_type: 'plan', sku: PRINCIPAL_SKU, meta_json: { plano_nome: 'Principal da Biblioteca', periodicidade: 'mensal' } }],
    { credits: 20, direitos: { biblioteca: true, assinatura: true } }
  );
  assert(granted.payload.credits === 20, 'concessão inicial deve ser 20');
  await writeSnapshot(granted.payload, ends);
  report.grant_20 = granted.payload.credits;

  const plus = mergeEntitlement(
    granted.payload,
    [
      {
        item_type: 'plan',
        sku: COMP_SKU,
        quantity: 10,
        meta_json: { direitos: { papel: 'complementar' } },
      },
    ],
    { credits: 10, direitos: { papel: 'complementar', creditos: 10 } }
  );
  assert(plus.payload.credits === 30, `complementar deve somar 10, veio ${plus.payload.credits}`);
  assert(plus.payload.plan.sku === PRINCIPAL_SKU, 'complementar não troca o plano');
  assert(plus.replaceValidUntil === false, 'complementar não redefine o ciclo');
  await writeSnapshot(plus.payload, ends);
  report.complementary_10 = plus.payload.credits;

  await ensureCreditOperationsTable(pool);
  await pool.query(`DELETE FROM credit_operations WHERE subject_id = $1`, [SUBJECT]);
  const run = `91b-${Date.now()}`;

  const reserved = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: SUBJECT, amount: 1, operationId: `${run}-single` })
  );
  assert(reserved.ok && reserved.credits === 29, `consulta única deveria deixar 29, veio ${reserved.credits}`);
  const confirmed = await withTx((client) =>
    confirmCredits(client, { appId: APP, subjectId: SUBJECT, operationId: `${run}-single` })
  );
  assert(confirmed.ok && confirmed.status === 'confirmed', 'confirm da consulta única');
  const again = await withTx((client) =>
    confirmCredits(client, { appId: APP, subjectId: SUBJECT, operationId: `${run}-single` })
  );
  assert(again.idempotent && again.credits === 29, 'débito idempotente não tira de novo');
  report.single_consult = { credits: again.credits, idempotent: true };

  const held = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: SUBJECT, amount: 1, operationId: `${run}-fail` })
  );
  assert(held.ok && held.credits === 28, 'reserva da falha');
  const released = await withTx((client) =>
    releaseCredits(client, { appId: APP, subjectId: SUBJECT, operationId: `${run}-fail` })
  );
  assert(released.ok && released.credits === 29, `liberação deveria devolver, veio ${released.credits}`);
  report.fail_release = { credits: released.credits };

  const recovered = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: SUBJECT, amount: 1, operationId: `${run}-single` })
  );
  assert(recovered.idempotent && recovered.status === 'confirmed', 'recuperação da mesma operação não reserva de novo');
  report.recover = { status: recovered.status, credits: recovered.credits };

  await writeSnapshot({ credits: 1, premium: true, plan: { sku: PRINCIPAL_SKU, franchise: 20 } }, ends);
  async function race(operationId) {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      const result = await reserveCredits(client, {
        appId: APP,
        subjectId: SUBJECT,
        amount: 1,
        operationId,
      });
      if (result.ok) await client.query('COMMIT');
      else await client.query('ROLLBACK');
      return result;
    } catch (err) {
      await client.query('ROLLBACK').catch(() => {});
      throw err;
    } finally {
      client.release();
    }
  }
  const raced = await Promise.all([race(`${run}-race-a`), race(`${run}-race-b`)]);
  const oks = raced.filter((row) => row.ok).length;
  const denied = raced.find((row) => !row.ok);
  assert(oks === 1, `concorrência deveria aprovar 1, aprovou ${oks}`);
  assert(denied && denied.error === 'insufficient_credits', 'a segunda reserva concorrente deve falhar por saldo');
  report.concurrent = { approved: oks, denied: denied.error };

  const leftover = mergeEntitlement(
    {
      credits: 12,
      principal_credits: 12,
      complementary_credits: 0,
      premium: true,
      plan: { sku: PRINCIPAL_SKU },
    },
    [{ item_type: 'plan', sku: PRINCIPAL_SKU, meta_json: { periodicidade: 'mensal' } }],
    { credits: 20, direitos: { biblioteca: true } }
  );
  assert(leftover.payload.credits === 20, 'somente o principal: renovação define 20');
  assert(leftover.payload.complementary == null, 'sem complementar ativo o snapshot não inventa um');
  report.renewal_no_accumulate = leftover.payload.credits;

  const dup = mergeEntitlement(
    leftover.payload,
    [{ item_type: 'plan', sku: PRINCIPAL_SKU, meta_json: { periodicidade: 'mensal' } }],
    { credits: 20, direitos: { biblioteca: true } }
  );
  assert(dup.payload.credits === 20, 'evento repetido de plano não concede 40');
  report.duplicate_event = dup.payload.credits;

  await pool.query(`DELETE FROM credit_operations WHERE subject_id = $1`, [SUBJECT]);
  await writeSnapshot({ credits: 5, premium: true }, '2000-01-01T00:00:00.000Z');
  const expired = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: SUBJECT, amount: 1, operationId: `op-91b-expired-${Date.now()}` })
  );
  assert(!expired.ok && expired.error === 'expired', 'crédito expirado não pode ser usado');
  report.expired_blocked = true;

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

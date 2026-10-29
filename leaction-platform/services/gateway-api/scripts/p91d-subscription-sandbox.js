'use strict';

/**
 * Provas 91D isoladas: recorrência, idempotência e dependência.
 * Sem Mercado Pago, sem e-mail, sem produção.
 */

const { Pool } = require('pg');
const {
  isRecurringCatalogPlan,
  recurringReady,
  assertCatalogSubscriptionAllowed,
  ensureSubscriptionCyclesTable,
  processAuthorizedInvoice,
  processPreapprovalLifecycle,
} = require('../domain/catalog-subscription');
require('dotenv').config({ path: '../../../.env', override: true });

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

(async () => {
  const report = { env: 'local-hub-sandbox', charged: false, suite: '91d-recurring' };
  const plan = {
    sku: 'LOJADEPAES_BIBLIOTECA_MENSAL',
    type: 'plan',
    price: 19,
    meta_json: { periodicidade: 'mensal', checkout_mode: 'subscription', direitos: { papel: 'principal' } },
  };
  assert(isRecurringCatalogPlan(plan) && recurringReady(plan), 'principal deve ser recorrente');
  assert(
    !recurringReady({ ...plan, meta_json: { ...plan.meta_json, recurring_ready: false } }),
    'pausa bloqueia contratação'
  );

  await ensureSubscriptionCyclesTable(pool);
  const denied = await assertCatalogSubscriptionAllowed(pool, {
    appId: 'lojadepaes',
    subjectId: 'biblioteca.91d.sandbox@test.local',
    plan: {
      sku: 'LOJADEPAES_BIBLIOTECA_CREDITOS',
      meta_json: { direitos: { papel: 'complementar' } },
    },
    hubPayload: { direitos: { papel: 'complementar' } },
  });
  assert(!denied.ok, 'complementar sem principal deve ser recusado no servidor');
  report.complementary_requires_principal = true;

  const failed = await processAuthorizedInvoice(pool, {
    id: 'inv-fail-91d',
    payment: { id: 'pay-fail-91d', status: 'rejected' },
    preapproval_id: 'pre-missing',
  });
  assert(failed.granted === false, 'falha de renovação não concede crédito');
  report.failed_renewal_no_grant = true;

  const cancelled = await processPreapprovalLifecycle(pool, {
    id: 'pre-not-stored-91d',
    status: 'cancelled',
  });
  assert(cancelled.status === 'cancelled', 'cancelamento não apaga ciclo — só interrompe renovação');
  report.cancel_does_not_wipe = true;

  const first = await processAuthorizedInvoice(pool, {
    id: 'pay-dup-91d',
    payment: { id: 'pay-dup-91d', status: 'approved' },
    preapproval_id: 'pre-missing',
  });
  const again = await processAuthorizedInvoice(pool, {
    id: 'pay-dup-91d',
    payment: { id: 'pay-dup-91d', status: 'approved' },
    preapproval_id: 'pre-missing',
  });
  assert(first.reason === 'subscription_not_found', 'sem assinatura persistida não inventa concessão');
  assert(again.reason === 'subscription_not_found', 'evento repetido sem assinatura continua sem concessão');
  report.duplicate_without_sub = true;

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

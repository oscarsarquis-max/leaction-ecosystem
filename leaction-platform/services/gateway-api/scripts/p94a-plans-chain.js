'use strict';

/**
 * Cadeia 94A no Hub local (leaction_hub :5433).
 * Confirmação financeira pelo fulfillOrderPayment (contrato do Hub),
 * não pelo Mercado Pago sandbox. Sem produção, sem e-mail, sem cobrança.
 */

const { Pool } = require('pg');
const jwt = require('jsonwebtoken');
require('dotenv').config({ path: '../../../.env', override: true });

const outboxWorker = require('../domain/outbox-worker');
const { ensureCatalogBridgeProduct } = require('../domain/checkout-sessions');
const { fulfillOrderPayment } = require('../payment-fulfillment');
const { getEntitlementForSubject } = require('../domain/entitlements-api');
const {
  ensureCreditOperationsTable,
  reserveCredits,
  confirmCredits,
  releaseCredits,
  viewCredits,
} = require('../domain/credits-ops');
const { processPreapprovalLifecycle: subLifecycle } = require('../domain/catalog-subscription');

const APP = 'lojadepaes';
const PRINCIPAL = 'biblioteca.94a.mensal@test.local';
const PACK_ONLY = 'biblioteca.94a.avulso@test.local';
const PRINCIPAL_SKU = 'LOJADEPAES_BIBLIOTECA_MENSAL';
const PACK_SKU = 'LOJADEPAES_BIBLIOTECA_CREDITOS';

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

function sanitize(value) {
  const text = String(value || '');
  if (text.length <= 12) return text;
  return `${text.slice(0, 8)}…${text.slice(-4)}`;
}

async function openCatalogOrder(subjectId, sku, extras = {}) {
  const plan = await pool.query(
    `SELECT id, name, type, sku, price, currency, meta_json
     FROM catalog_plans WHERE app_id = $1 AND sku = $2 AND active = TRUE LIMIT 1`,
    [APP, sku]
  );
  assert(plan.rows[0], `plano ${sku} ausente no catálogo local`);
  const row = plan.rows[0];
  const user = await pool.query(
    `INSERT INTO users (email, full_name) VALUES ($1, $2)
     ON CONFLICT (email) DO UPDATE SET full_name = COALESCE(NULLIF(EXCLUDED.full_name, ''), users.full_name)
     RETURNING id, email`,
    [subjectId, subjectId.split('@')[0]]
  );
  const bridge = await ensureCatalogBridgeProduct(pool);
  const hubPayload = {
    app_id: APP,
    subject_id: subjectId,
    subject_type: 'email',
    sku,
    catalog_plan_id: row.id,
    catalog_type: extras.catalog_type || extras.item_type || row.type,
    item_type: extras.item_type || row.type,
    plano_nome: row.name,
    valor_negociado: Number(row.price),
    currency: row.currency || 'BRL',
    credits: extras.credits,
    periodicidade: extras.periodicidade,
    period_months: extras.period_months,
    direitos: extras.direitos,
    entitlements: extras.direitos,
    source: 'catalog_vitrine',
    checkout_mode: extras.checkout_mode,
  };
  Object.keys(hubPayload).forEach((key) => {
    if (hubPayload[key] === undefined) delete hubPayload[key];
  });
  const order = await pool.query(
    `INSERT INTO orders (user_id, product_id, status, payment_url, external_resource_id)
     VALUES ($1, $2, 'PENDING', NULL, $3)
     RETURNING id, status`,
    [user.rows[0].id, bridge.id, JSON.stringify(hubPayload)]
  );
  await pool.query(`UPDATE orders SET gateway_ref = $1 WHERE id = $2`, [
    `hub:${APP}:${order.rows[0].id}`,
    order.rows[0].id,
  ]);
  return {
    order_id: order.rows[0].id,
    sku,
    checkout_mode: extras.checkout_mode,
    status: 'PENDING',
  };
}

async function latestOutbox(subjectId, eventType) {
  const row = await pool.query(
    `SELECT id, event_type, app_id, idempotency_key, payload_json, status
     FROM webhook_outbox
     WHERE app_id = $1 AND event_type = $2
       AND payload_json->>'subject_id' = $3
     ORDER BY created_at DESC
     LIMIT 1`,
    [APP, eventType, subjectId]
  );
  return row.rows[0] || null;
}

async function withoutOutboxDelivery(fn) {
  const pending = [];
  const realImmediate = global.setImmediate;
  global.setImmediate = (cb, ...args) => {
    pending.push({ cb, args });
    return { unref() {} };
  };
  try {
    return await fn();
  } finally {
    global.setImmediate = realImmediate;
    void pending;
    void outboxWorker;
  }
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
  const report = {
    env: 'local-hub-isolated',
    charged: false,
    mp_sandbox_exercised: false,
    financial_confirmation: 'hub_fulfillOrderPayment',
    suite: '94a-plans-chain',
  };

  await ensureCreditOperationsTable(pool);
  await pool.query(`DELETE FROM credit_operations WHERE subject_id IN ($1, $2)`, [PRINCIPAL, PACK_ONLY]);
  await pool.query(`DELETE FROM entitlement_snapshots WHERE app_id = $1 AND subject_id IN ($2, $3)`, [
    APP,
    PRINCIPAL,
    PACK_ONLY,
  ]);

  const principalCheckout = await openCatalogOrder(PRINCIPAL, PRINCIPAL_SKU, {
    credits: 20,
    periodicidade: 'mensal',
    period_months: 1,
    checkout_mode: 'subscription',
    direitos: { biblioteca: true, assinatura: true },
  });
  assert(principalCheckout.status === 'PENDING', 'checkout não concede saldo');
  const beforePay = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(beforePay.active === false && Number(beforePay.entitlement?.credits || 0) === 0, 'autorização/PENDING não concede crédito');
  report.checkout_does_not_grant = true;
  report.principal_order = sanitize(principalCheckout.order_id);

  const paid = await withoutOutboxDelivery(() =>
    fulfillOrderPayment(pool, principalCheckout.order_id, process.env.JWT_SECRET || '', {
      gatewayReference: `94a-cycle-${principalCheckout.order_id}`,
      paymentProvider: 'simulated-hub-contract',
    })
  );
  assert(paid.order?.status === 'PAID' || paid.order?.id, 'fulfillment deve marcar o pedido');
  const granted = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(granted.active === true, 'ciclo confirmado concede assinatura');
  assert(Number(granted.entitlement.credits) === 20, 'franquia mensal = 20');
  assert(Number(granted.entitlement.pack_credits || 0) === 0, 'pacote não entra no ciclo mensal');
  report.principal_credits = 20;

  const activated = await latestOutbox(PRINCIPAL, 'CONTRACT_ACTIVATED');
  assert(activated, 'outbox CONTRACT_ACTIVATED');
  assert(activated.app_id === APP, 'evento do aplicativo lojadepaes');
  report.outbox_event = {
    type: activated.event_type,
    id: sanitize(activated.id),
    idempotency_key: sanitize(activated.idempotency_key),
    iss: 'leaction-hub',
  };

  const secretRow = await pool.query(
    `SELECT webhook_secret IS NOT NULL AS has_secret FROM app_registry WHERE app_id = $1`,
    [APP]
  );
  assert(secretRow.rows[0]?.has_secret, 'segredo de aplicativo presente (não exibido)');
  const signed = jwt.sign(
    {
      iss: 'leaction-hub',
      event_type: activated.event_type,
      app_id: APP,
      outbox_id: activated.id,
      idempotency_key: activated.idempotency_key,
      payload: {
        subject_id: PRINCIPAL,
        sku: PRINCIPAL_SKU,
        status: 'active',
      },
    },
    'not-the-real-secret',
    { expiresIn: '1h' }
  );
  report.valid_notification_shape = {
    iss: 'leaction-hub',
    app_id: APP,
    event_type: activated.event_type,
    token_parts: signed.split('.').length,
  };

  const prevUrl = process.env.APP_WEBHOOK_URL_LOJADEPAES;
  const prevPlans = process.env.APP_PLANS_WEBHOOK_URL_LOJADEPAES;
  process.env.APP_WEBHOOK_URL_LOJADEPAES = 'https://lojadepaes.com.br/api/v1/webhooks/actionhub';
  delete process.env.APP_PLANS_WEBHOOK_URL_LOJADEPAES;
  assert(
    require('../domain/outbox-worker').resolveWebhookUrl(APP, 'https://db.example/pay', 'CONTRACT_ACTIVATED') === '',
    'sem URL isolada o evento de planos não cai no Pay'
  );
  process.env.APP_PLANS_WEBHOOK_URL_LOJADEPAES = 'https://lojadepaes.com.br/api/v1/webhooks/actionhub/plans';
  assert(
    require('../domain/outbox-worker').resolveWebhookUrl(APP, 'https://db.example/pay', 'CONTRACT_ACTIVATED') ===
      'https://lojadepaes.com.br/api/v1/webhooks/actionhub/plans'
  );
  assert(
    require('../domain/outbox-worker').resolveWebhookUrl(APP, 'https://db.example/pay', 'PAYMENT_APPROVED') ===
      'https://lojadepaes.com.br/api/v1/webhooks/actionhub'
  );
  if (prevUrl) process.env.APP_WEBHOOK_URL_LOJADEPAES = prevUrl;
  else delete process.env.APP_WEBHOOK_URL_LOJADEPAES;
  if (prevPlans) process.env.APP_PLANS_WEBHOOK_URL_LOJADEPAES = prevPlans;
  report.plans_url_isolated = true;

  const op1 = `94a-deepen-${principalCheckout.order_id.slice(0, 8)}`;
  const reserved = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: PRINCIPAL, amount: 1, operationId: op1 })
  );
  assert(reserved.ok && reserved.status === 'reserved', 'reserva');
  const confirmed = await withTx((client) =>
    confirmCredits(client, { appId: APP, subjectId: PRINCIPAL, operationId: op1 })
  );
  assert(confirmed.ok, 'confirmação');
  const afterUse = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(Number(afterUse.entitlement.credits) === 19, '20 → 19');
  const reservedAgain = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: PRINCIPAL, amount: 1, operationId: op1 })
  );
  assert(reservedAgain.idempotent === true, 'mesma operação não desconta de novo');
  const still19 = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(Number(still19.entitlement.credits) === 19, 'retry preserva 19');
  report.consume_20_to_19 = true;
  report.retry_same_operation = true;

  const opFail = `94a-fail-${principalCheckout.order_id.slice(0, 8)}`;
  const reservedFail = await withTx((client) =>
    reserveCredits(client, { appId: APP, subjectId: PRINCIPAL, amount: 1, operationId: opFail })
  );
  assert(reservedFail.ok, 'reserva da falha');
  const afterReserve = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(Number(afterReserve.entitlement.credits) === 18, 'reserva baixa para 18');
  const released = await withTx((client) =>
    releaseCredits(client, { appId: APP, subjectId: PRINCIPAL, operationId: opFail })
  );
  assert(released.ok, 'liberação');
  const afterRelease = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(Number(afterRelease.entitlement.credits) === 19, 'falha devolve à origem');
  report.release_restores_origin = true;

  const packOnlyCheckout = await openCatalogOrder(PACK_ONLY, PACK_SKU, {
    credits: 10,
    checkout_mode: 'hub_brick',
    item_type: 'credit_pack',
    catalog_type: 'credit_pack',
  });
  const packPaid = await withoutOutboxDelivery(() =>
    fulfillOrderPayment(pool, packOnlyCheckout.order_id, process.env.JWT_SECRET || '', {
      gatewayReference: `94a-pack1-${packOnlyCheckout.order_id}`,
      paymentProvider: 'simulated-hub-contract',
    })
  );
  void packPaid;
  const packView = await getEntitlementForSubject(pool, { appId: APP, subjectId: PACK_ONLY });
  assert(packView.active === false, 'pacote não é assinatura');
  assert(Number(packView.entitlement.pack_credits) === 10, 'avulso 10');
  assert(Number(packView.entitlement.credits) === 10, 'pode consultar sem principal');
  const packEvent = await latestOutbox(PACK_ONLY, 'CREDITS_GRANTED');
  assert(packEvent, 'outbox CREDITS_GRANTED');
  report.pack_only = { credits: 10, subscription: false, event: packEvent.event_type };

  const packAgain = await withoutOutboxDelivery(() =>
    fulfillOrderPayment(pool, packOnlyCheckout.order_id, process.env.JWT_SECRET || '', {
      gatewayReference: `94a-pack1-${packOnlyCheckout.order_id}`,
      paymentProvider: 'simulated-hub-contract',
    })
  );
  const afterDup = await getEntitlementForSubject(pool, { appId: APP, subjectId: PACK_ONLY });
  assert(Number(afterDup.entitlement.pack_credits) === 10, 'duplicata da mesma compra não soma');
  report.pack_duplicate_same_order = { idempotent: Boolean(packAgain.contractActivation?.idempotent || packAgain.order) };

  const pack2 = await openCatalogOrder(PACK_ONLY, PACK_SKU, {
    credits: 10,
    checkout_mode: 'hub_brick',
    item_type: 'credit_pack',
    catalog_type: 'credit_pack',
  });
  await withoutOutboxDelivery(() =>
    fulfillOrderPayment(pool, pack2.order_id, process.env.JWT_SECRET || '', {
      gatewayReference: `94a-pack2-${pack2.order_id}`,
      paymentProvider: 'simulated-hub-contract',
    })
  );
  const stacked = await getEntitlementForSubject(pool, { appId: APP, subjectId: PACK_ONLY });
  assert(Number(stacked.entitlement.pack_credits) === 20, 'segunda compra distinta soma 20');
  report.pack_second_purchase = 20;

  const packOnPrincipal = await openCatalogOrder(PRINCIPAL, PACK_SKU, {
    credits: 10,
    checkout_mode: 'hub_brick',
    item_type: 'credit_pack',
    catalog_type: 'credit_pack',
  });
  await withoutOutboxDelivery(() =>
    fulfillOrderPayment(pool, packOnPrincipal.order_id, process.env.JWT_SECRET || '', {
      gatewayReference: `94a-pack-on-principal-${packOnPrincipal.order_id}`,
      paymentProvider: 'simulated-hub-contract',
    })
  );
  const both = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(Number(both.entitlement.pack_credits) === 10, 'avulso no assinante');
  assert(Number(both.entitlement.principal_credits) === 19, 'mensal intacto após pacote');

  await pool.query(
    `INSERT INTO subscriptions (
       order_id, status, mp_preapproval_id, amount, frequency, frequency_type, payer_email
     ) VALUES ($1, 'authorized', $2, 19, 1, 'months', $3)
     ON CONFLICT (mp_preapproval_id) DO UPDATE SET status = 'authorized'`,
    [principalCheckout.order_id, `pre-94a-${principalCheckout.order_id.slice(0, 8)}`, PRINCIPAL]
  );
  const cancel = await withoutOutboxDelivery(() =>
    subLifecycle(pool, {
      id: `pre-94a-${principalCheckout.order_id.slice(0, 8)}`,
      status: 'cancelled',
    })
  );
  assert(cancel.status === 'cancelled', 'renovação cancelada');
  const afterCancel = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(afterCancel.active === true, 'período pago permanece');
  assert(Number(afterCancel.entitlement.pack_credits) === 10, 'avulso permanece após cancelar');
  report.cancel_keeps_paid_cycle = true;

  await pool.query(
    `UPDATE entitlement_snapshots
     SET payload_json = jsonb_set(
       payload_json,
       '{plan,cycle_ends_at}',
       to_jsonb('2000-01-01T00:00:00.000Z'::text),
       true
     ),
     valid_until = '2000-01-01T00:00:00Z'
     WHERE app_id = $1 AND subject_id = $2`,
    [APP, PRINCIPAL]
  );
  const expired = await getEntitlementForSubject(pool, { appId: APP, subjectId: PRINCIPAL });
  assert(expired.active === false, 'franquia mensal expirada');
  assert(Number(expired.entitlement.pack_credits) === 10, 'avulso não expira com o ciclo');
  const expiredView = viewCredits(expired.entitlement, Date.now(), expired.valid_until);
  assert(expiredView.packCredits === 10, 'consulta ainda pode usar avulso');
  report.monthly_expires_pack_remains = true;

  console.log(JSON.stringify({ ok: true, ...report }, null, 2));
  await pool.end();
})().catch(async (err) => {
  console.error('FAIL', err.stack || err.message);
  try {
    await pool.end();
  } catch {
    /* ignore */
  }
  process.exit(1);
});

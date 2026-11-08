'use strict';

/**
 * Assinatura mensal do catálogo via preapproval do Mercado Pago.
 * Créditos só após pagamento confirmado do ciclo — autorização da recorrência não concede saldo.
 */

const { createContractService } = require('./contract-service');
const { isComplementaryItem, isOneShotAiPack } = require('./credits-ops');

const BIBLIOTECA_SKUS = new Set([
  'LOJADEPAES_BIBLIOTECA_MENSAL',
  'LOJADEPAES_BIBLIOTECA_CREDITOS',
]);

const TABLE_SQL = `
CREATE TABLE IF NOT EXISTS subscription_cycles (
  payment_id TEXT PRIMARY KEY,
  preapproval_id TEXT,
  order_id UUID,
  kind TEXT NOT NULL,
  granted BOOLEAN NOT NULL DEFAULT FALSE,
  payload_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;

function normalizeMeta(value) {
  if (value == null) return {};
  if (typeof value === 'object' && !Array.isArray(value)) return value;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
    } catch {
      return {};
    }
  }
  return {};
}

function parseHubPayload(raw) {
  if (!raw) return {};
  if (typeof raw === 'object') return raw;
  try {
    const parsed = JSON.parse(String(raw));
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function isBibliotecaSku(sku) {
  return BIBLIOTECA_SKUS.has(String(sku || '').trim());
}

function isMonthlyPlan(plan) {
  const meta = normalizeMeta(plan?.meta_json);
  const period = String(meta.periodicidade || '').toLowerCase();
  const months = Number(meta.period_months || meta.meses || 0);
  const type = String(plan?.type || '').toLowerCase();
  return type === 'plan' && (period.includes('mensal') || period === 'monthly' || months === 1);
}

function isRecurringCatalogPlan(plan) {
  if (isOneShotAiPack(plan, plan?.meta_json)) return false;
  const meta = normalizeMeta(plan?.meta_json);
  if (String(meta.checkout_mode || '').toLowerCase() === 'subscription') return true;
  if (isBibliotecaSku(plan?.sku) && isMonthlyPlan(plan)) return true;
  return false;
}

function recurringReady(plan) {
  const meta = normalizeMeta(plan?.meta_json);
  return isRecurringCatalogPlan(plan) && meta.recurring_ready !== false && Number(plan?.price) > 0;
}

async function ensureSubscriptionCyclesTable(pool) {
  await pool.query(TABLE_SQL);
}

async function findPendingCatalogOrder(client, { userId, sku }) {
  const r = await client.query(
    `SELECT o.id, o.status, o.external_resource_id, o.created_at
     FROM orders o
     WHERE o.user_id = $1
       AND o.status = 'PENDING'
       AND o.external_resource_id::text LIKE $2
     ORDER BY o.created_at DESC
     LIMIT 1`,
    [userId, `%"sku":"${sku}"%`]
  );
  return r.rows[0] || null;
}

async function findActiveCatalogSubscription(client, { appId, subjectId, sku }) {
  const r = await client.query(
    `SELECT s.id, s.status, s.mp_preapproval_id, s.order_id, s.amount, o.external_resource_id
     FROM subscriptions s
     JOIN orders o ON o.id = s.order_id
     WHERE LOWER(s.status) IN ('authorized', 'pending', 'paused')
       AND o.external_resource_id::text LIKE $1
       AND o.external_resource_id::text LIKE $2
     ORDER BY s.created_at DESC
     LIMIT 1`,
    [`%"app_id":"${appId}"%`, `%"sku":"${sku}"%`]
  );
  if (!r.rows[0]) return null;
  const payload = parseHubPayload(r.rows[0].external_resource_id);
  if (String(payload.subject_id || '').toLowerCase() !== String(subjectId || '').toLowerCase()) {
    return null;
  }
  return r.rows[0];
}

async function principalAllowsComplementary(client, { appId, subjectId }) {
  const snap = await client.query(
    `SELECT payload_json, valid_until
     FROM entitlement_snapshots
     WHERE app_id = $1 AND subject_id = $2
     LIMIT 1`,
    [appId, subjectId]
  );
  if (!snap.rows[0]) return { ok: false, error: 'o complementar só abre depois da assinatura mensal principal' };
  const payload = snap.rows[0].payload_json && typeof snap.rows[0].payload_json === 'object'
    ? snap.rows[0].payload_json
    : {};
  const until = payload.plan?.cycle_ends_at || snap.rows[0].valid_until;
  if (until && new Date(until).getTime() <= Date.now()) {
    return { ok: false, error: 'o complementar só abre com o plano principal vigente' };
  }
  if (!payload.premium && !payload.plan) {
    return { ok: false, error: 'o complementar só abre depois da assinatura mensal principal' };
  }
  return { ok: true };
}

async function assertCatalogSubscriptionAllowed(client, { appId, subjectId, plan, hubPayload }) {
  const sku = String(plan.sku || '');
  const complementary = isComplementaryItem({ sku, meta_json: plan.meta_json }, hubPayload);
  const existing = await findActiveCatalogSubscription(client, { appId, subjectId, sku });
  if (existing) {
    return {
      ok: false,
      statusCode: 409,
      error: complementary
        ? 'já existe uma assinatura complementar vigente ou pendente para esta conta'
        : 'já existe uma assinatura principal vigente ou pendente para esta conta',
      existing_order_id: existing.order_id,
    };
  }
  if (complementary) {
    const principal = await principalAllowsComplementary(client, { appId, subjectId });
    if (!principal.ok) {
      return { ok: false, statusCode: 409, error: principal.error };
    }
  }
  return { ok: true };
}

function subscriptionCopy(plan) {
  if (isOneShotAiPack(plan, plan?.meta_json)) {
    return 'Pacote avulso de R$ 10,00 com 10 consultas de IA. Não é assinatura e não renova sozinho. Não concede desconto de assinante.';
  }
  return 'Assinatura mensal de R$ 19,00 com 20 consultas de IA por ciclo e 10% de desconto nos produtos vendidos pela Loja enquanto o direito estiver vigente. A renovação automática é autorizada na contratação. Créditos entram após o pagamento confirmado do ciclo. Cancele no ActionHub; o período já pago continua até o vencimento.';
}

async function recordCycle(client, row) {
  await client.query(
    `INSERT INTO subscription_cycles (payment_id, preapproval_id, order_id, kind, granted, payload_json)
     VALUES ($1, $2, $3, $4, $5, $6::jsonb)
     ON CONFLICT (payment_id) DO NOTHING`,
    [
      row.payment_id,
      row.preapproval_id || null,
      row.order_id || null,
      row.kind,
      Boolean(row.granted),
      JSON.stringify(row.payload || {}),
    ]
  );
}

async function cycleExists(client, paymentId) {
  const r = await client.query(
    `SELECT payment_id, granted, order_id FROM subscription_cycles WHERE payment_id = $1`,
    [paymentId]
  );
  return r.rows[0] || null;
}

async function grantCatalogCycleFromConfirmedPayment(pool, { orderId, paymentId, preapprovalId, kind }) {
  await ensureSubscriptionCyclesTable(pool);
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const existing = await cycleExists(client, paymentId);
    if (existing && existing.granted) {
      await client.query('COMMIT');
      return { ok: true, idempotent: true, order_id: existing.order_id, kind };
    }
    await recordCycle(client, {
      payment_id: paymentId,
      preapproval_id: preapprovalId,
      order_id: orderId,
      kind: kind || 'first',
      granted: false,
      payload: { status: 'received' },
    });
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }

  const contractService = createContractService(pool);
  const { fulfillOrderPayment } = require('../payment-fulfillment');
  const jwtSecret = process.env.JWT_SECRET || '';
  const result = await fulfillOrderPayment(pool, orderId, jwtSecret, {
    gatewayReference: paymentId,
    paymentProvider: 'mercadopago',
    mpPreapprovalId: preapprovalId,
  });
  const grantClient = await pool.connect();
  try {
    await grantClient.query(
      `UPDATE subscription_cycles
       SET granted = TRUE, order_id = $2, payload_json = $3::jsonb
       WHERE payment_id = $1`,
      [paymentId, orderId, JSON.stringify({ kind: kind || 'first', contract: result.contract || null })]
    );
  } finally {
    grantClient.release();
  }
  return { ok: true, idempotent: false, order_id: orderId, contract: result.contract, kind: kind || 'first' };
}

async function openRenewalOrder(pool, originalOrderId, paymentId) {
  const original = await pool.query(
    `SELECT user_id, product_id, payment_url, external_resource_id, gateway_ref
     FROM orders WHERE id = $1`,
    [originalOrderId]
  );
  if (!original.rows[0]) {
    const err = new Error('pedido original da assinatura não encontrado');
    err.statusCode = 404;
    throw err;
  }
  const row = original.rows[0];
  const payload = parseHubPayload(row.external_resource_id);
  payload.renewal_of = originalOrderId;
  payload.cycle_payment_id = paymentId;
  const inserted = await pool.query(
    `INSERT INTO orders (user_id, product_id, status, payment_url, external_resource_id, gateway_ref)
     VALUES ($1, $2, 'PENDING', $3, $4, $5)
     RETURNING id`,
    [
      row.user_id,
      row.product_id,
      row.payment_url,
      JSON.stringify(payload),
      `renewal:${paymentId}`,
    ]
  );
  return inserted.rows[0].id;
}

function complementarySkuFromPayload(payload) {
  return isComplementaryItem({ sku: payload.sku, meta_json: payload }, payload);
}

async function findComplementarySubscriptionsToStop(client, { appId, subjectId }) {
  const r = await client.query(
    `SELECT s.id, s.mp_preapproval_id, s.status, o.external_resource_id
     FROM subscriptions s
     JOIN orders o ON o.id = s.order_id
     WHERE LOWER(s.status) IN ('authorized', 'pending')
       AND o.external_resource_id::text LIKE $1`,
    [`%"app_id":"${appId}"%`]
  );
  return r.rows.filter((row) => {
    const payload = parseHubPayload(row.external_resource_id);
    return (
      String(payload.subject_id || '').toLowerCase() === String(subjectId || '').toLowerCase() &&
      complementarySkuFromPayload(payload)
    );
  });
}

async function processAuthorizedInvoice(pool, invoice, deps) {
  const paymentId = String(invoice?.payment?.id || invoice?.id || '').trim();
  const preapprovalId = String(invoice?.preapproval_id || invoice?.preapprovalId || '').trim();
  const status = String(invoice?.payment?.status || invoice?.status || '').toLowerCase();
  if (!paymentId) {
    return { handled: false, reason: 'missing_payment_id' };
  }
  if (!['approved', 'accredited'].includes(status)) {
    await ensureSubscriptionCyclesTable(pool);
    const skipClient = await pool.connect();
    try {
      await recordCycle(skipClient, {
        payment_id: `skip:${paymentId}`,
        preapproval_id: preapprovalId,
        order_id: null,
        kind: 'failed',
        granted: false,
        payload: { status },
      });
    } finally {
      skipClient.release();
    }
    return { handled: true, granted: false, reason: 'payment_not_approved', status };
  }
  const sub = await pool.query(
    `SELECT s.id, s.order_id, o.status AS order_status, o.external_resource_id
     FROM subscriptions s
     LEFT JOIN orders o ON o.id = s.order_id
     WHERE s.mp_preapproval_id = $1
     LIMIT 1`,
    [preapprovalId]
  );
  if (!sub.rows[0]?.order_id) {
    return { handled: false, reason: 'subscription_not_found', preapproval_id: preapprovalId };
  }
  const existing = await pool.query(
    `SELECT payment_id, granted FROM subscription_cycles WHERE payment_id = $1`,
    [paymentId]
  );
  if (existing.rows[0]?.granted) {
    return { handled: true, idempotent: true, order_id: sub.rows[0].order_id };
  }
  let orderId = sub.rows[0].order_id;
  const kind = String(sub.rows[0].order_status || '').toUpperCase() === 'PAID' ? 'renewal' : 'first';
  if (kind === 'renewal') {
    orderId = await openRenewalOrder(pool, sub.rows[0].order_id, paymentId);
  }
  const granted = await grantCatalogCycleFromConfirmedPayment(pool, {
    orderId,
    paymentId,
    preapprovalId,
    kind,
  });
  if (deps && typeof deps.afterGrant === 'function') {
    await deps.afterGrant({ kind, payload: parseHubPayload(sub.rows[0].external_resource_id) });
  }
  return { handled: true, ...granted };
}

async function processPreapprovalLifecycle(pool, preapproval, deps) {
  const id = String(preapproval?.id || '').trim();
  const status = String(preapproval?.status || '').toLowerCase();
  if (!id) return { handled: false, reason: 'missing_preapproval' };
  await pool.query(
    `UPDATE subscriptions
     SET status = $2, raw_response = $3::jsonb, updated_at = CURRENT_TIMESTAMP
     WHERE mp_preapproval_id = $1`,
    [id, status || 'unknown', JSON.stringify(preapproval)]
  );
  const notifyRow = await pool.query(
    `SELECT o.external_resource_id
     FROM subscriptions s
     JOIN orders o ON o.id = s.order_id
     WHERE s.mp_preapproval_id = $1
     LIMIT 1`,
    [id]
  );
  const notifyPayload = parseHubPayload(notifyRow.rows[0]?.external_resource_id);
  if (String(notifyPayload.app_id || '').toLowerCase() === 'lojadepaes') {
    const { enqueueLojaPlansEvent } = require('./loja-plans-notify');
    await enqueueLojaPlansEvent(pool, {
      eventType: 'SUBSCRIPTION_STATUS',
      idempotencyKey: `loja-plans-sub-${id}-${status || 'unknown'}`,
      payload: {
        subject_id: notifyPayload.subject_id || null,
        sku: notifyPayload.sku || null,
        status: status || 'unknown',
        commercial_status: status || 'unknown',
        financial_status: 'not_applicable',
      },
    });
  }
  if (status !== 'cancelled' && status !== 'canceled') {
    return { handled: true, status, cancelled_dependents: [] };
  }
  const row = await pool.query(
    `SELECT o.external_resource_id
     FROM subscriptions s
     JOIN orders o ON o.id = s.order_id
     WHERE s.mp_preapproval_id = $1
     LIMIT 1`,
    [id]
  );
  const payload = parseHubPayload(row.rows[0]?.external_resource_id);
  if (complementarySkuFromPayload(payload)) {
    return { handled: true, status, cancelled_dependents: [] };
  }
  const dependents = await findComplementarySubscriptionsToStop(pool, {
    appId: payload.app_id,
    subjectId: payload.subject_id,
  });
  const cancelled = [];
  for (const dep of dependents) {
    if (!dep.mp_preapproval_id || dep.mp_preapproval_id === id) continue;
    if (deps && typeof deps.cancelPreapproval === 'function') {
      await deps.cancelPreapproval(dep.mp_preapproval_id, 'cancelled');
    }
    await pool.query(
      `UPDATE subscriptions SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
       WHERE mp_preapproval_id = $1`,
      [dep.mp_preapproval_id]
    );
    cancelled.push(dep.mp_preapproval_id);
  }
  return { handled: true, status, cancelled_dependents: cancelled };
}

module.exports = {
  BIBLIOTECA_SKUS,
  isBibliotecaSku,
  isRecurringCatalogPlan,
  recurringReady,
  parseHubPayload,
  normalizeMeta,
  subscriptionCopy,
  ensureSubscriptionCyclesTable,
  findPendingCatalogOrder,
  findActiveCatalogSubscription,
  assertCatalogSubscriptionAllowed,
  grantCatalogCycleFromConfirmedPayment,
  openRenewalOrder,
  findComplementarySubscriptionsToStop,
  cycleExists,
  processAuthorizedInvoice,
  processPreapprovalLifecycle,
  registerCatalogSubscriptionRoutes,
};

function registerCatalogSubscriptionRoutes(app, pool, deps) {
  const { authenticateApp, extractCallerSecret } = require('./entitlements-api');
  const cancelFn =
    deps && typeof deps.cancelPreapproval === 'function'
      ? deps.cancelPreapproval
      : async () => {
          const err = new Error('cancelamento de assinatura indisponível');
          err.statusCode = 503;
          throw err;
        };

  app.get('/v1/subscriptions', async (req, res) => {
    try {
      const appId = String(req.query.app_id || '').trim().toLowerCase();
      const subjectId = String(req.query.subject_id || '').trim();
      if (!appId || !subjectId) {
        return res.status(400).json({ error: 'Parâmetros obrigatórios: app_id e subject_id' });
      }
      const secret = extractCallerSecret(req);
      if (!secret) return res.status(401).json({ error: 'Credencial ausente' });
      const auth = await authenticateApp(pool, appId, secret);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      const rows = await pool.query(
        `SELECT s.id, s.status, s.mp_preapproval_id, s.amount, s.frequency, s.frequency_type,
                s.order_id, o.external_resource_id
         FROM subscriptions s
         JOIN orders o ON o.id = s.order_id
         WHERE o.external_resource_id::text LIKE $1
         ORDER BY s.created_at DESC`,
        [`%"app_id":"${appId}"%`]
      );
      const items = rows.rows
        .map((row) => {
          const payload = parseHubPayload(row.external_resource_id);
          if (String(payload.subject_id || '').toLowerCase() !== subjectId.toLowerCase()) return null;
          return {
            id: row.id,
            sku: payload.sku,
            status: row.status,
            amount: Number(row.amount),
            frequency: row.frequency,
            frequency_type: row.frequency_type,
            cancelable: ['authorized', 'pending', 'paused'].includes(String(row.status || '').toLowerCase()),
          };
        })
        .filter(Boolean);
      return res.status(200).json({
        app_id: appId,
        subject_id: subjectId,
        subscriptions: items,
        cancel_policy:
          'O cancelamento interrompe a renovação automática. O período já pago e os créditos daquele ciclo continuam até o vencimento. Sem pró-rata.',
      });
    } catch (err) {
      console.error('❌ GET /v1/subscriptions', err.message);
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  });

  app.post('/v1/subscriptions/cancel', async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const appId = String(body.app_id || '').trim().toLowerCase();
      const subjectId = String(body.subject_id || '').trim();
      const sku = String(body.sku || '').trim();
      if (!appId || !subjectId) {
        return res.status(400).json({ error: 'Campos obrigatórios: app_id, subject_id' });
      }
      const secret = extractCallerSecret(req);
      if (!secret) return res.status(401).json({ error: 'Credencial ausente' });
      const auth = await authenticateApp(pool, appId, secret);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      const active = await findActiveCatalogSubscription(pool, {
        appId,
        subjectId,
        sku: sku || 'LOJADEPAES_BIBLIOTECA_MENSAL',
      });
      if (!active?.mp_preapproval_id) {
        return res.status(404).json({ error: 'assinatura vigente não encontrada' });
      }
      await cancelFn(active.mp_preapproval_id, 'cancelled');
      const lifecycle = await processPreapprovalLifecycle(
        pool,
        { id: active.mp_preapproval_id, status: 'cancelled' },
        { cancelPreapproval: cancelFn }
      );
      return res.status(200).json({
        ok: true,
        status: 'cancelled',
        sku: sku || active.order_id,
        cancelled_dependents: lifecycle.cancelled_dependents || [],
        message:
          'A renovação automática foi cancelada. O período já pago continua até o vencimento. Não há reembolso proporcional.',
      });
    } catch (err) {
      const status = err.statusCode || 500;
      console.error('❌ POST /v1/subscriptions/cancel', err.message);
      return res.status(status).json({ error: status >= 500 ? 'Erro interno no servidor' : err.message });
    }
  });
}

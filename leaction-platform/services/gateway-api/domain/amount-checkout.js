'use strict';

/**
 * POST /v1/checkout/amount — cobrança avulsa por valor.
 * Isolado de /v1/checkout/sessions (SKU/plano Inove) e /v1/payments (PanelDX).
 * Sem créditos, entitlement, catálogo de planos ou webhook_url no corpo.
 */

const { authenticateApp, extractCallerSecret } = require('./entitlements-api');
const {
  isMercadoPagoConfigured,
  createPixPayment,
  extractPixTransactionData,
  cancelMercadoPagoPayment,
  fetchMercadoPagoPayment,
} = require('../mercadopago');
const { buildHubBrickCheckoutUrl } = require('./checkout-sessions');
const {
  MIN_CENTS,
  MAX_CENTS,
  assertCents,
  centsToMercadoPagoAmount,
  mercadoPagoAmountToCents,
} = require('../lib/money-cents');

const AMOUNT_CHECKOUT_SKU = 'AMOUNT_CHECKOUT';
const AMOUNT_CHECKOUT_TYPE = 'AMOUNT_CHECKOUT';
const SOURCE = 'amount_checkout';
const MAX_DESC = 120;
const MAX_REF = 80;
const MAX_REQUEST_ID = 120;
const MAX_NAME = 160;
const MAX_EMAIL = 254;

function amountCheckoutAppIds() {
  return String(process.env.AMOUNT_CHECKOUT_APP_IDS || '')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function isAmountCheckoutAllowed(appId) {
  const id = String(appId || '').trim().toLowerCase();
  if (!id) return false;
  return amountCheckoutAppIds().includes(id);
}

function parseHubPayload(raw) {
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) return raw;
  const text = raw == null ? '' : String(raw).trim();
  if (!text.startsWith('{')) return null;
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
  } catch {
    return null;
  }
  return null;
}

function isAmountCheckoutPayload(payload) {
  return Boolean(payload && payload.source === SOURCE);
}

function isAmountCheckoutOrder(orderRow) {
  if (!orderRow) return false;
  if (String(orderRow.product_type || '').toUpperCase() === AMOUNT_CHECKOUT_TYPE) {
    return true;
  }
  return isAmountCheckoutPayload(parseHubPayload(orderRow.external_resource_id));
}

function normalizeMethod(value) {
  const method = String(value || 'card').trim().toLowerCase();
  return method === 'pix' || method === 'card' ? method : null;
}

function canonicalAmountRequest({
  appId,
  orderReference,
  paymentRequestId,
  amountCents,
  currency,
  customerEmail,
  method,
}) {
  return {
    app_id: String(appId || '').trim().toLowerCase(),
    order_reference: String(orderReference || '').trim(),
    payment_request_id: String(paymentRequestId || '').trim(),
    amount_cents: amountCents,
    currency: String(currency || 'BRL').trim().toUpperCase(),
    customer_email: String(customerEmail || '').trim().toLowerCase(),
    method: normalizeMethod(method) || 'card',
  };
}

function payloadsConflict(stored, next) {
  if (!stored || !next) return true;
  return (
    stored.app_id !== next.app_id ||
    stored.order_reference !== next.order_reference ||
    stored.payment_request_id !== next.payment_request_id ||
    stored.amount_cents !== next.amount_cents ||
    stored.currency !== next.currency ||
    stored.customer_email !== next.customer_email ||
    stored.method !== next.method
  );
}

function originOf(raw) {
  const text = String(raw || '').trim();
  if (!text) return '';
  try {
    const parsed = new URL(text.includes('://') ? text : `https://${text}`);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
    return parsed.origin;
  } catch {
    return '';
  }
}

function returnOriginAllowed(returnOrigin, allowedOrigins) {
  const origin = originOf(returnOrigin);
  if (!origin) return { ok: false, error: 'return_origin inválido' };
  const allowed = Array.isArray(allowedOrigins)
    ? allowedOrigins.map((item) => originOf(item)).filter(Boolean)
    : [];
  if (allowed.length === 0) {
    return { ok: false, error: 'app sem return_origins cadastradas para checkout avulso' };
  }
  if (!allowed.includes(origin)) {
    return { ok: false, error: 'return_origin não autorizado para este aplicativo' };
  }
  return { ok: true, origin };
}

function returnPathAllowed(returnTo) {
  const path = String(returnTo || '').trim() || '/';
  if (!path.startsWith('/') || path.startsWith('//')) {
    return { ok: false, error: 'return_to deve ser um caminho absoluto da Loja' };
  }
  return { ok: true, path };
}

function mapMpStatusToFinancial(status, statusDetail) {
  const value = String(status || '').trim().toLowerCase();
  const detail = String(statusDetail || '').trim().toLowerCase();
  if (value === 'approved' || value === 'authorized') return 'paid';
  if (value === 'rejected') return 'failed';
  if (value === 'cancelled' || value === 'expired' || detail === 'expired') return 'cancelled';
  if (value === 'refunded') return 'refunded';
  if (value === 'charged_back') return 'refunded';
  if (value === 'in_process' || value === 'pending' || value === 'in_mediation') {
    return 'pending';
  }
  return 'unknown';
}

async function ensureAmountCheckoutProduct(pool) {
  const existing = await pool.query(
    `SELECT id, sku, name, type FROM products WHERE sku = $1 LIMIT 1`,
    [AMOUNT_CHECKOUT_SKU]
  );
  if (existing.rows[0]) return existing.rows[0];
  const inserted = await pool.query(
    `INSERT INTO products (sku, name, type, external_resource_id)
     VALUES ($1, $2, $3, $4)
     ON CONFLICT (sku) DO UPDATE SET
       name = EXCLUDED.name,
       type = EXCLUDED.type
     RETURNING id, sku, name, type`,
    [AMOUNT_CHECKOUT_SKU, 'Checkout avulso por valor', AMOUNT_CHECKOUT_TYPE, SOURCE]
  );
  return inserted.rows[0];
}

function idempotencyGatewayRef(appId, idempotencyKey) {
  return `amount:${appId}:idk:${idempotencyKey}`;
}

function requestGatewayRef(appId, paymentRequestId) {
  return `amount:${appId}:req:${paymentRequestId}`;
}

async function enqueueAmountPaymentEvent(pool, { appId, eventType, payload, idempotencyKey }) {
  await pool.query(
    `INSERT INTO webhook_outbox (
       app_id, event_type, payload_json, idempotency_key,
       status, attempts, next_retry_at, created_at
     ) VALUES (
       $1, $2, $3::jsonb, $4,
       'pending', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
     )
     ON CONFLICT (idempotency_key) DO NOTHING`,
    [appId, eventType, JSON.stringify(payload), idempotencyKey]
  );
}

function brickCheckoutUrl(order, payload, hubPublicBase) {
  const method = String(payload.method || 'card').toLowerCase();
  if (method === 'pix') return null;
  return buildHubBrickCheckoutUrl({
    orderId: order.id,
    customerEmail: payload.customer_email,
    appId: payload.app_id,
    hubPublicBase,
    returnTo: payload.return_to,
    returnOrigin: payload.return_origin,
  });
}

function publicPix(payload) {
  if (String(payload.method || 'card').toLowerCase() !== 'pix') return null;
  const pix = payload.pix && typeof payload.pix === 'object' ? payload.pix : {};
  return {
    qr_code: pix.qr_code || null,
    qr_code_base64: pix.qr_code_base64 || null,
    ticket_url: pix.ticket_url || null,
    date_of_expiration: pix.date_of_expiration || null,
    mp_payment_id: payload.mp_payment_id || pix.mp_payment_id || null,
  };
}

function publicAmountOrder(order, payload, extras = {}) {
  const method = String(payload.method || 'card').toLowerCase();
  return {
    order_id: order.id,
    status: String(order.status || '').toUpperCase(),
    checkout_mode: method === 'pix' ? 'pix' : 'hub_brick',
    method,
    amount_cents: payload.amount_cents,
    currency: payload.currency || 'BRL',
    order_reference: payload.order_reference,
    payment_request_id: payload.payment_request_id,
    checkout_url: extras.checkoutUrl !== undefined ? extras.checkoutUrl : brickCheckoutUrl(order, payload),
    pix: publicPix(payload),
  };
}

async function persistHubPayload(pool, orderId, payload) {
  await pool.query(`UPDATE orders SET external_resource_id = $1 WHERE id = $2`, [
    JSON.stringify(payload),
    orderId,
  ]);
}

async function ensurePixCharge(pool, order, payload) {
  if (payload.pix && payload.pix.qr_code) {
    return payload;
  }
  const mpPayment = await createPixPayment({
    payerEmail: payload.customer_email,
    amountCents: payload.amount_cents,
    externalReference: String(order.id),
    description: payload.description,
  });
  const pix = extractPixTransactionData(mpPayment);
  if (!pix.qr_code) {
    const err = new Error('Mercado Pago não devolveu o QR Pix');
    err.statusCode = 502;
    throw err;
  }
  payload.method = 'pix';
  payload.mp_payment_id = pix.mp_payment_id;
  payload.pix = {
    qr_code: pix.qr_code,
    qr_code_base64: pix.qr_code_base64,
    ticket_url: pix.ticket_url,
    date_of_expiration: pix.date_of_expiration,
    mp_payment_id: pix.mp_payment_id,
    status: pix.status,
    status_detail: pix.status_detail,
  };
  await persistHubPayload(pool, order.id, payload);
  return payload;
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 */
async function refreshAmountPaymentFromMercadoPago(pool, row, payload) {
  if (!row || !payload) return { row, payload };
  if (String(row.status || '').toUpperCase() === 'PAID') return { row, payload };
  const mpPaymentId = payload.mp_payment_id || (payload.pix && payload.pix.mp_payment_id);
  if (!mpPaymentId) return { row, payload };
  let payment;
  try {
    payment = await fetchMercadoPagoPayment(mpPaymentId);
  } catch (err) {
    console.error('[amount-checkout] consulta Mercado Pago falhou:', err.message);
    return { row, payload };
  }
  if (String(payment && payment.status || '').toLowerCase() !== 'approved') {
    return { row, payload };
  }
  try {
    const { fulfillFromApprovedPayment } = require('./mp-webhooks');
    await fulfillFromApprovedPayment(pool, process.env.JWT_SECRET, payment);
  } catch (err) {
    console.error('[amount-checkout] confirmação do Pix aprovado falhou:', err.message);
    return { row, payload };
  }
  const reloaded = await pool.query(`SELECT * FROM orders WHERE id = $1 LIMIT 1`, [row.id]);
  const next = reloaded.rows[0] || row;
  return { row: next, payload: parseHubPayload(next.external_resource_id) || payload };
}

function registerAmountCheckoutRoutes(app, pool) {
  app.post('/v1/checkout/amount', async (req, res) => {
    try {
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const claimedAppId = String(body.app_id || '').trim().toLowerCase();
      const secret = extractCallerSecret(req);
      if (!secret) {
        return res.status(401).json({
          error:
            'Credencial ausente. Envie Authorization: Bearer <secret> ou header X-App-Secret.',
        });
      }
      if (!claimedAppId) {
        return res.status(400).json({ error: 'Campo obrigatório: app_id' });
      }

      const auth = await authenticateApp(pool, claimedAppId, secret);
      if (!auth.ok) {
        return res.status(auth.status).json({ error: auth.error });
      }
      const appId = String(auth.app.app_id).trim().toLowerCase();
      if (appId !== claimedAppId) {
        return res.status(401).json({ error: 'app_id não corresponde à credencial' });
      }
      if (!isAmountCheckoutAllowed(appId)) {
        return res.status(403).json({
          error: 'aplicativo não autorizado para cobrança avulsa por valor',
        });
      }

      const idempotencyKey = String(
        req.headers['idempotency-key'] || body.idempotency_key || ''
      ).trim();
      if (!idempotencyKey || idempotencyKey.length > 120) {
        return res.status(400).json({ error: 'Idempotency-Key obrigatória (até 120 caracteres)' });
      }

      const orderReference = String(body.order_reference || '').trim();
      const paymentRequestId = String(body.payment_request_id || '').trim();
      const amountCents = body.amount_cents;
      const currency = String(body.currency || 'BRL').trim().toUpperCase();
      const description = String(body.description || '').trim();
      const method = normalizeMethod(body.method || 'card');
      const customer = body.customer && typeof body.customer === 'object' ? body.customer : {};
      const customerEmail = String(customer.email || body.email || '').trim().toLowerCase();
      const customerName = String(customer.name || '').trim() || customerEmail.split('@')[0];
      if (!method) {
        return res.status(400).json({ error: 'method deve ser pix ou card' });
      }

      if (!orderReference || orderReference.length > MAX_REF) {
        return res.status(400).json({ error: 'order_reference obrigatória (até 80 caracteres)' });
      }
      if (!paymentRequestId || paymentRequestId.length > MAX_REQUEST_ID) {
        return res.status(400).json({
          error: 'payment_request_id obrigatório (até 120 caracteres)',
        });
      }
      if (currency !== 'BRL') {
        return res.status(400).json({ error: 'currency deve ser BRL' });
      }
      try {
        assertCents(amountCents);
      } catch (err) {
        return res.status(400).json({ error: err.message });
      }
      if (!description || description.length > MAX_DESC) {
        return res.status(400).json({ error: 'description obrigatória (até 120 caracteres)' });
      }
      if (!customerEmail.includes('@') || customerEmail.length > MAX_EMAIL) {
        return res.status(400).json({ error: 'customer.email inválido' });
      }
      if (customerName.length > MAX_NAME) {
        return res.status(400).json({ error: 'customer.name excede o tamanho permitido' });
      }
      if (/\b(plano|sku|cr[eé]dito|entitlement|assinatura)\b/i.test(description)) {
        return res.status(400).json({
          error: 'description não pode referir plano, SKU, crédito ou assinatura',
        });
      }

      const origins = auth.app.return_origins;
      const originCheck = returnOriginAllowed(body.return_origin, origins);
      if (!originCheck.ok) {
        return res.status(400).json({ error: originCheck.error });
      }
      const pathCheck = returnPathAllowed(body.return_to);
      if (!pathCheck.ok) {
        return res.status(400).json({ error: pathCheck.error });
      }

      if (!isMercadoPagoConfigured()) {
        return res.status(503).json({
          error: 'Mercado Pago não configurado (MP_ACCESS_TOKEN)',
        });
      }

      const canonical = canonicalAmountRequest({
        appId,
        orderReference,
        paymentRequestId,
        amountCents,
        currency,
        customerEmail,
        method,
      });
      const idkRef = idempotencyGatewayRef(appId, idempotencyKey);
      const reqRef = requestGatewayRef(appId, paymentRequestId);

      const existing = await pool.query(
        `SELECT id, status, gateway_ref, external_resource_id, payment_url
         FROM orders
         WHERE gateway_ref = $1 OR gateway_ref = $2
         ORDER BY created_at ASC`,
        [idkRef, reqRef]
      );

      if (existing.rows.length > 0) {
        const row = existing.rows[0];
        const stored = parseHubPayload(row.external_resource_id) || {};
        const storedCanonical = canonicalAmountRequest({
          appId: stored.app_id,
          orderReference: stored.order_reference,
          paymentRequestId: stored.payment_request_id,
          amountCents: stored.amount_cents,
          currency: stored.currency,
          customerEmail: stored.customer_email,
          method: stored.method,
        });
        if (payloadsConflict(storedCanonical, canonical)) {
          return res.status(409).json({
            error: 'Idempotency-Key ou payment_request_id já usados com payload diferente',
          });
        }
        let payload = stored;
        if (method === 'pix') {
          payload = await ensurePixCharge(pool, row, stored);
        }
        const checkoutUrl = brickCheckoutUrl(row, payload, body.hub_public_url);
        return res.status(200).json({
          ...publicAmountOrder(row, payload, { checkoutUrl }),
          reused: true,
        });
      }

      const product = await ensureAmountCheckoutProduct(pool);
      const storedEmail = `${appId}.${Buffer.from(customerEmail).toString('base64url').slice(0, 48)}@amount.hub.local`;
      const userResult = await pool.query(
        `INSERT INTO users (email, full_name)
         VALUES ($1, $2)
         ON CONFLICT (email)
         DO UPDATE SET full_name = COALESCE(NULLIF(EXCLUDED.full_name, ''), users.full_name)
         RETURNING id, email`,
        [storedEmail, customerName]
      );
      const user = userResult.rows[0];

      const hubPayload = {
        source: SOURCE,
        app_id: appId,
        order_reference: orderReference,
        payment_request_id: paymentRequestId,
        amount_cents: amountCents,
        currency,
        description,
        method,
        customer_email: customerEmail,
        customer_name: customerName,
        subject_id: `${appId}:${customerEmail}`,
        subject_type: 'email',
        return_origin: originCheck.origin,
        return_to: pathCheck.path,
      };

      const checkoutPlaceholder = '';
      const orderResult = await pool.query(
        `INSERT INTO orders (user_id, product_id, status, payment_url, external_resource_id, gateway_ref)
         VALUES ($1, $2, 'PENDING', $3, $4, $5)
         RETURNING id, status, created_at, gateway_ref`,
        [user.id, product.id, checkoutPlaceholder, JSON.stringify(hubPayload), idkRef]
      );
      const order = orderResult.rows[0];

      let payload = hubPayload;
      if (method === 'pix') {
        payload = await ensurePixCharge(pool, order, hubPayload);
      }

      const checkoutUrl = brickCheckoutUrl(order, payload, body.hub_public_url);
      console.log(
        `📥 [AMOUNT CHECKOUT] app=${appId} method=${method} cents=${amountCents} order=${order.id} ref=${orderReference}`
      );

      return res.status(201).json({
        ...publicAmountOrder(order, payload, { checkoutUrl }),
        reused: false,
      });
    } catch (err) {
      console.error('❌ Erro em POST /v1/checkout/amount:', err.message);
      const status =
        err.statusCode && err.statusCode >= 400 && err.statusCode < 600 ? err.statusCode : 500;
      return res.status(status).json({
        error: status >= 500 ? 'Erro interno no servidor' : err.message,
      });
    }
  });

  async function loadOwnedAmountOrder(pool, appId, { orderId, paymentRequestId }) {
    if (orderId) {
      const result = await pool.query(
        `SELECT o.id, o.status, o.gateway_ref, o.external_resource_id, p.type AS product_type
         FROM orders o
         JOIN products p ON p.id = o.product_id
         WHERE o.id = $1
         LIMIT 1`,
        [orderId]
      );
      return result.rows[0] || null;
    }
    const result = await pool.query(
      `SELECT o.id, o.status, o.gateway_ref, o.external_resource_id, p.type AS product_type
       FROM orders o
       JOIN products p ON p.id = o.product_id
       WHERE o.gateway_ref LIKE $1
       ORDER BY o.created_at DESC`,
      [`amount:${appId}:%`]
    );
    return (
      result.rows.find((row) => {
        const payload = parseHubPayload(row.external_resource_id);
        return payload && payload.payment_request_id === paymentRequestId;
      }) || null
    );
  }

  async function authenticateAmountApp(req, res) {
    const secret = extractCallerSecret(req);
    const claimedAppId = String(req.query.app_id || req.headers['x-app-id'] || '').trim().toLowerCase();
    if (!secret) {
      res.status(401).json({
        error: 'Credencial ausente. Envie Authorization: Bearer <secret> ou header X-App-Secret.',
      });
      return null;
    }
    if (!claimedAppId) {
      res.status(400).json({ error: 'Informe app_id na query ou header X-App-Id' });
      return null;
    }
    const auth = await authenticateApp(pool, claimedAppId, secret);
    if (!auth.ok) {
      res.status(auth.status).json({ error: auth.error });
      return null;
    }
    if (!isAmountCheckoutAllowed(claimedAppId)) {
      res.status(403).json({ error: 'aplicativo não autorizado para cobrança avulsa por valor' });
      return null;
    }
    return claimedAppId;
  }

  app.get('/v1/checkout/amount/:orderId', async (req, res) => {
    try {
      const appId = await authenticateAmountApp(req, res);
      if (!appId) return;
      const row = await loadOwnedAmountOrder(pool, appId, { orderId: req.params.orderId });
      if (!row || !isAmountCheckoutOrder(row)) {
        return res.status(404).json({ error: 'cobrança avulsa não encontrada' });
      }
      const payload = parseHubPayload(row.external_resource_id);
      if (!payload || payload.app_id !== appId) {
        return res.status(404).json({ error: 'cobrança avulsa não encontrada' });
      }
      const fresh = await refreshAmountPaymentFromMercadoPago(pool, row, payload);
      return res.status(200).json(publicAmountOrder(fresh.row, fresh.payload));
    } catch (err) {
      console.error('❌ Erro em GET /v1/checkout/amount/:id:', err.message);
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  });

  app.post('/v1/checkout/amount/:orderId/cancel', async (req, res) => {
    try {
      const appId = await authenticateAmountApp(req, res);
      if (!appId) return;
      const row = await loadOwnedAmountOrder(pool, appId, { orderId: req.params.orderId });
      if (!row || !isAmountCheckoutOrder(row)) {
        return res.status(404).json({ error: 'cobrança avulsa não encontrada' });
      }
      const payload = parseHubPayload(row.external_resource_id);
      if (!payload || payload.app_id !== appId) {
        return res.status(404).json({ error: 'cobrança avulsa não encontrada' });
      }
      if (String(row.status || '').toUpperCase() === 'PAID') {
        return res.status(409).json({ error: 'cobrança já paga; não é possível cancelar' });
      }
      if (payload.cancelled) {
        return res.status(200).json({ ...publicAmountOrder(row, payload), cancelled: true });
      }
      const mpPaymentId = payload.mp_payment_id || payload.pix?.mp_payment_id;
      if (String(payload.method || '') === 'pix' && mpPaymentId) {
        try {
          const cancelled = await cancelMercadoPagoPayment(mpPaymentId);
          const cancelledStatus = String(cancelled?.status || '').toLowerCase();
          if (cancelledStatus === 'approved') {
            return res.status(409).json({ error: 'Pix já foi pago' });
          }
        } catch (err) {
          const message = String(err.message || '').toLowerCase();
          if (message.includes('approved') || err.statusCode === 409) {
            return res.status(409).json({ error: 'Pix já foi pago' });
          }
          throw err;
        }
      }
      payload.cancelled = true;
      await persistHubPayload(pool, row.id, payload);
      await pool.query(`UPDATE orders SET status = 'CANCELLED' WHERE id = $1 AND status <> 'PAID'`, [
        row.id,
      ]);
      return res.status(200).json({
        ...publicAmountOrder({ ...row, status: 'CANCELLED' }, payload),
        cancelled: true,
      });
    } catch (err) {
      console.error('❌ Erro em POST /v1/checkout/amount/:id/cancel:', err.message);
      const status =
        err.statusCode && err.statusCode >= 400 && err.statusCode < 600 ? err.statusCode : 500;
      return res.status(status).json({
        error: status >= 500 ? 'Erro interno no servidor' : err.message,
      });
    }
  });

  app.get('/v1/checkout/amount', async (req, res) => {
    try {
      const appId = await authenticateAmountApp(req, res);
      if (!appId) return;
      const paymentRequestId = String(req.query.payment_request_id || '').trim();
      if (!paymentRequestId) {
        return res.status(400).json({ error: 'payment_request_id é obrigatório' });
      }
      const row = await loadOwnedAmountOrder(pool, appId, { paymentRequestId });
      if (!row) {
        return res.status(404).json({ error: 'cobrança avulsa não encontrada' });
      }
      const payload = parseHubPayload(row.external_resource_id);
      if (!payload || payload.app_id !== appId) {
        return res.status(404).json({ error: 'cobrança avulsa não encontrada' });
      }
      const fresh = await refreshAmountPaymentFromMercadoPago(pool, row, payload);
      return res.status(200).json(publicAmountOrder(fresh.row, fresh.payload));
    } catch (err) {
      console.error('❌ Erro em GET /v1/checkout/amount:', err.message);
      return res.status(500).json({ error: 'Erro interno no servidor' });
    }
  });
}

module.exports = {
  SOURCE,
  AMOUNT_CHECKOUT_SKU,
  AMOUNT_CHECKOUT_TYPE,
  MIN_CENTS,
  MAX_CENTS,
  registerAmountCheckoutRoutes,
  ensureAmountCheckoutProduct,
  isAmountCheckoutAllowed,
  isAmountCheckoutPayload,
  isAmountCheckoutOrder,
  parseHubPayload,
  canonicalAmountRequest,
  normalizeMethod,
  payloadsConflict,
  returnOriginAllowed,
  returnPathAllowed,
  mapMpStatusToFinancial,
  enqueueAmountPaymentEvent,
  centsToMercadoPagoAmount,
  mercadoPagoAmountToCents,
};

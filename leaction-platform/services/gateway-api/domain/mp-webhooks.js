'use strict';

/**
 * Webhooks Mercado Pago → fulfill order → ContractService.activateFromOrder
 *
 * Rotas:
 *   POST /webhooks/mercadopago
 *   GET  /webhooks/mercadopago  (IPN clássico ?topic=&id=)
 *
 * Formatos aceitos:
 *   - Query IPN: ?topic=payment|merchant_order&id=
 *   - Body v1:  { type/action: payment.*, data: { id } }
 */

const crypto = require('crypto');
const {
  fetchMercadoPagoPayment,
  fetchMercadoPagoMerchantOrder,
  fetchAuthorizedPayment,
  fetchPreapproval,
  updatePreapprovalStatus,
  isMercadoPagoConfigured,
} = require('../mercadopago');
const { processAuthorizedInvoice, processPreapprovalLifecycle } = require('./catalog-subscription');
const { fulfillOrderPayment } = require('../payment-fulfillment');
const {
  isAmountCheckoutPayload,
  parseHubPayload,
  mapMpStatusToFinancial,
  enqueueAmountPaymentEvent,
  mercadoPagoAmountToCents,
  persistAmountProviderObservation,
  isProviderPaidConfirmed,
} = require('./amount-checkout');

const LOG = '[MP Webhook]';

function extractNotification(req) {
  const q = req.query || {};
  const body = req.body && typeof req.body === 'object' ? req.body : {};

  const topic = String(
    q.topic || q.type || body.type || body.topic || ''
  )
    .trim()
    .toLowerCase();

  const action = String(body.action || '').trim().toLowerCase();

  const id = String(
    q.id || q['data.id'] || body?.data?.id || body.id || ''
  ).trim();

  return { topic, action, id, body };
}

function parseSignatureHeader(raw) {
  const parts = String(raw || '')
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean);
  const values = {};
  for (const part of parts) {
    const eq = part.indexOf('=');
    if (eq <= 0) continue;
    values[part.slice(0, eq)] = part.slice(eq + 1);
  }
  return values;
}

function webhookDataId(req) {
  const q = req.query || {};
  const body = req.body && typeof req.body === 'object' ? req.body : {};
  return String(q['data.id'] || q.id || body?.data?.id || body.id || '').trim().toLowerCase();
}

function buildMercadoPagoManifest(req, ts) {
  const dataId = webhookDataId(req);
  const requestId = String(req.get && req.get('x-request-id') || req.headers?.['x-request-id'] || '').trim();
  const pieces = [];
  if (dataId) pieces.push(`id:${dataId}`);
  if (requestId) pieces.push(`request-id:${requestId}`);
  pieces.push(`ts:${ts}`);
  return pieces.join(';') + ';';
}

function verifyMercadoPagoWebhookSignature(req, secret) {
  const configured = String(secret || process.env.MP_WEBHOOK_SECRET || '').trim();
  const header = req.get ? req.get('x-signature') : req.headers?.['x-signature'];
  if (!configured) {
    return { ok: true, mode: 'secret_absent', reason: 'MP_WEBHOOK_SECRET ausente; validação HMAC não aplicada' };
  }
  if (!header) {
    const method = String(req.method || 'GET').toUpperCase();
    if (method === 'GET') {
      return { ok: true, mode: 'ipn_without_signature', reason: 'IPN clássico sem x-signature; consulta autenticada ao recurso continua obrigatória' };
    }
    return { ok: false, mode: 'signature_missing', reason: 'notificação Webhooks sem x-signature' };
  }
  const parsed = parseSignatureHeader(header);
  if (!parsed.ts || !parsed.v1) {
    return { ok: false, mode: 'signature_malformed', reason: 'x-signature sem ts/v1' };
  }
  const manifest = buildMercadoPagoManifest(req, parsed.ts);
  const expected = crypto.createHmac('sha256', configured).update(manifest).digest('hex');
  const given = Buffer.from(String(parsed.v1), 'utf8');
  const want = Buffer.from(expected, 'utf8');
  if (given.length !== want.length || !crypto.timingSafeEqual(given, want)) {
    return { ok: false, mode: 'signature_mismatch', reason: 'assinatura Mercado Pago inválida' };
  }
  return { ok: true, mode: 'hmac_sha256', reason: 'x-signature válida' };
}

function isPaymentNotification({ topic, action }) {
  if (topic === 'payment' || topic === 'payments') return true;
  if (action.startsWith('payment.')) return true;
  return false;
}

function isMerchantOrderNotification({ topic, action }) {
  if (topic === 'merchant_order' || topic === 'merchant_orders') return true;
  if (action.startsWith('merchant_order.')) return true;
  return false;
}

function isAuthorizedPaymentNotification({ topic, action }) {
  if (topic === 'subscription_authorized_payment' || topic === 'subscription-authorized-payment') {
    return true;
  }
  return action.includes('authorized_payment') || action.includes('subscription_authorized_payment');
}

function isPreapprovalNotification({ topic, action }) {
  if (topic === 'subscription_preapproval' || topic === 'subscription-preapproval') return true;
  return action.includes('subscription_preapproval') || action.startsWith('preapproval.');
}

async function notifyAmountCheckout(pool, orderRow, payment, financialStatus, extra = {}) {
  const payload = parseHubPayload(orderRow.external_resource_id) || {};
  const appId = String(payload.app_id || '').trim().toLowerCase();
  if (!appId) {
    return { handled: false, reason: 'amount_checkout_missing_app' };
  }
  const paymentId = payment?.id != null ? String(payment.id) : null;
  const eventType =
    financialStatus === 'paid'
      ? 'PAYMENT_CONFIRMED'
      : financialStatus === 'unknown'
        ? 'PAYMENT_INCONSISTENT'
        : 'PAYMENT_UPDATED';
  const outboxPayload = {
    source: 'amount_checkout',
    event_type: eventType,
    financial_status: financialStatus,
    order_id: orderRow.id,
    order_reference: payload.order_reference,
    payment_request_id: payload.payment_request_id,
    amount_cents: payload.amount_cents,
    currency: payload.currency || 'BRL',
    mp_payment_id: paymentId,
    mp_status: payment?.status || null,
    mp_status_detail: payment?.status_detail || null,
    method: payload.method || null,
    paid_amount_cents: extra.paidAmountCents ?? null,
    amount_refunded_cents: payment?.transaction_amount_refunded != null
      ? mercadoPagoAmountToCents(payment.transaction_amount_refunded) : null,
    provider_observed_at: payment?.date_last_updated || null,
    provider_approved_at: payment?.date_approved || null,
    subject_id: payload.subject_id,
    customer_email: payload.customer_email,
  };
  await enqueueAmountPaymentEvent(pool, {
    appId,
    eventType,
    payload: outboxPayload,
    idempotencyKey: `amount_${orderRow.id}_${paymentId || 'none'}_${eventType}_${financialStatus}`,
  });
  return {
    handled: true,
    amount_checkout: true,
    financial_status: financialStatus,
    order_id: orderRow.id,
    payment_id: paymentId,
    event_type: eventType,
  };
}

/**
 * @param {import('pg').Pool} pool
 * @param {string} jwtSecret
 * @param {object} payment — resposta GET /v1/payments/:id
 */
async function fulfillFromApprovedPayment(pool, jwtSecret, payment) {
  const status = String(payment?.status || '').toLowerCase();
  const paymentId = payment?.id != null ? String(payment.id) : null;
  const orderId = String(payment?.external_reference || '').trim();

  if (!orderId) {
    if (status !== 'approved') {
      console.log(
        `${LOG} Pagamento ${paymentId || '—'} status=${status || '—'} — ignorado (só approved dispara fulfill)`
      );
      return { handled: false, reason: 'not_approved', status, payment_id: paymentId };
    }
    console.warn(
      `${LOG} Pagamento ${paymentId} aprovado sem external_reference — não é possível mapear order`
    );
    return { handled: false, reason: 'missing_external_reference', payment_id: paymentId };
  }

  const existing = await pool.query(
    `SELECT id, status, external_resource_id FROM orders WHERE id = $1 LIMIT 1`,
    [orderId]
  );
  if (existing.rows.length === 0) {
    if (status !== 'approved') {
      return { handled: false, reason: 'not_approved', status, payment_id: paymentId };
    }
    console.warn(`${LOG} Order não encontrada para external_reference=${orderId}`);
    return {
      handled: false,
      reason: 'order_not_found',
      order_id: orderId,
      payment_id: paymentId,
    };
  }

  const order = existing.rows[0];
  const hubPayload = parseHubPayload(order.external_resource_id);

  if (isAmountCheckoutPayload(hubPayload)) {
    const financialStatus = mapMpStatusToFinancial(status, payment?.status_detail);
    let paidAmountCents = null;
    try {
      if (payment?.transaction_amount != null) {
        paidAmountCents = mercadoPagoAmountToCents(payment.transaction_amount);
      }
    } catch (err) {
      await persistAmountProviderObservation(pool, orderId, payment, {
        mismatchReason: 'amount_unreadable',
      });
      await notifyAmountCheckout(pool, order, payment, 'unknown', {});
      return {
        handled: true,
        amount_checkout: true,
        reason: 'amount_unreadable',
        order_id: orderId,
        payment_id: paymentId,
      };
    }

    const storedPaymentId = hubPayload.mp_payment_id != null ? String(hubPayload.mp_payment_id) : '';
    if (storedPaymentId && paymentId && storedPaymentId !== paymentId) {
      await persistAmountProviderObservation(pool, orderId, payment, {
        paidAmountCents: paidAmountCents == null ? undefined : paidAmountCents,
        mismatchReason: 'unauthorized_payment_reference',
      });
      await notifyAmountCheckout(pool, order, payment, 'unknown', { paidAmountCents });
      return {
        handled: true,
        amount_checkout: true,
        reason: 'unauthorized_payment_reference',
        order_id: orderId,
        payment_id: paymentId,
        stored_payment_id: storedPaymentId,
        order_confirmed: false,
      };
    }

    if (isProviderPaidConfirmed(payment)) {
      if (paidAmountCents !== hubPayload.amount_cents) {
        await persistAmountProviderObservation(pool, orderId, payment, {
          paidAmountCents,
          mismatchReason: 'amount_mismatch',
        });
        await notifyAmountCheckout(pool, order, payment, 'unknown', { paidAmountCents });
        return {
          handled: true,
          amount_checkout: true,
          reason: 'amount_mismatch',
          order_id: orderId,
          payment_id: paymentId,
          expected_cents: hubPayload.amount_cents,
          paid_amount_cents: paidAmountCents,
          order_confirmed: false,
        };
      }
      await persistAmountProviderObservation(pool, orderId, payment, {
        paidAmountCents,
        markPaid: true,
        gatewayReference: paymentId,
        onPersist: (client, _row, observedPayload) => notifyAmountCheckout(
          client, { ...order, external_resource_id: observedPayload }, payment, 'paid', { paidAmountCents }
        ),
      });
      const result = await fulfillOrderPayment(pool, orderId, jwtSecret, {
        gatewayReference: paymentId,
        paymentProvider: 'mercadopago',
        skipContract: true,
        amountCheckout: true,
      });
      return {
        handled: true,
        amount_checkout: true,
        already_paid: Boolean(result.alreadyPaid),
        order_id: orderId,
        payment_id: paymentId,
        contract: null,
      };
    }

    await persistAmountProviderObservation(pool, orderId, payment, {
      paidAmountCents: paidAmountCents == null ? undefined : paidAmountCents,
    });
    return notifyAmountCheckout(pool, order, payment, financialStatus, { paidAmountCents });
  }

  if (status !== 'approved') {
    console.log(
      `${LOG} Pagamento ${paymentId || '—'} status=${status || '—'} — ignorado (só approved dispara fulfill)`
    );
    return { handled: false, reason: 'not_approved', status, payment_id: paymentId };
  }

  console.log('📦 Order ID recebida:', orderId);
  console.log('🔍 Buscando ordem no banco de dados...');

  if (String(order.status || '').toUpperCase() === 'PAID') {
    if (String(hubPayload.checkout_mode || '') === 'subscription') {
      const sub = await pool.query(
        `SELECT mp_preapproval_id FROM subscriptions WHERE order_id = $1 LIMIT 1`,
        [orderId]
      );
      return processAuthorizedInvoice(pool, {
        id: paymentId,
        payment: { id: paymentId, status },
        preapproval_id: payment.preapproval_id || sub.rows[0]?.mp_preapproval_id,
      });
    }
    console.log('⚠️ Ordem já estava paga. Ignorando para evitar duplicidade.');
    const result = await fulfillOrderPayment(pool, orderId, jwtSecret, {
      gatewayReference: paymentId,
      paymentProvider: 'mercadopago',
    });
    return {
      handled: true,
      already_paid: true,
      order_id: orderId,
      payment_id: paymentId,
      contract: result.contract,
    };
  }

  console.log('✅ Pagamento Aprovado! Acionando ContractService.activateFromOrder...');

  const result = await fulfillOrderPayment(pool, orderId, jwtSecret, {
    gatewayReference: paymentId,
    paymentProvider: 'mercadopago',
  });

  if (result.contract) {
    console.log('🎉 Contrato criado e evento de Outbox gerado com sucesso!');
  } else {
    console.warn(
      `${LOG} Fulfill OK order=${orderId} mas ContractService sem retorno — ver logs anteriores`
    );
  }

  console.log(
    `${LOG} Fulfill OK order=${orderId} contract=${result.contract?.contract_id || '—'} alreadyPaid=${Boolean(result.alreadyPaid)}`
  );

  return {
    handled: true,
    already_paid: Boolean(result.alreadyPaid),
    order_id: orderId,
    payment_id: paymentId,
    contract: result.contract,
  };
}

// The synchronous card response follows the same verified path as the MP webhook.
async function fulfillVerifiedCardPayment(pool, orderRow, payment, jwtSecret) {
  const payload = parseHubPayload(orderRow.external_resource_id);
  if (!isAmountCheckoutPayload(payload) && String(orderRow.product_type || '').toUpperCase() !== 'AMOUNT_CHECKOUT') {
    return fulfillOrderPayment(pool, orderRow.id, jwtSecret, {
      gatewayReference: payment.id != null ? String(payment.id) : null,
      paymentProvider: 'mercadopago',
    });
  }
  if (String(payment.external_reference || '') !== String(orderRow.id)
      || payment.currency_id !== (payload.currency || 'BRL')
      || !isProviderPaidConfirmed(payment)) {
    const error = new Error('Confirmação financeira divergente; não refaça o pagamento.');
    error.statusCode = 409;
    throw error;
  }
  const result = await fulfillFromApprovedPayment(pool, jwtSecret, payment);
  if (!result.handled || result.reason || result.order_id !== String(orderRow.id)) {
    const error = new Error('Pagamento requer verificação financeira; não refaça o pagamento.');
    error.statusCode = 409;
    throw error;
  }
  return {
    order: { id: orderRow.id, status: 'PAID' },
    alreadyPaid: Boolean(result.already_paid),
    webhookDelivered: false,
    confirmationQueued: true,
  };
}

async function processMpNotification(pool, jwtSecret, notification) {
  if (!isMercadoPagoConfigured()) {
    const err = new Error('Mercado Pago não configurado');
    err.statusCode = 503;
    throw err;
  }

  const { topic, action, id } = notification;

  if (!id) {
    console.log(`${LOG} Notificação sem id — ack sem processar`, { topic, action });
    return { handled: false, reason: 'missing_id' };
  }

  if (isAuthorizedPaymentNotification(notification)) {
    const invoice = await fetchAuthorizedPayment(id);
    return processAuthorizedInvoice(pool, invoice, {});
  }

  if (isPreapprovalNotification(notification)) {
    const preapproval = await fetchPreapproval(id);
    return processPreapprovalLifecycle(pool, preapproval, {
      cancelPreapproval: (preapprovalId, status) => updatePreapprovalStatus(preapprovalId, status),
    });
  }

  if (isPaymentNotification(notification)) {
    console.log(`${LOG} Recebido payment id=${id} topic=${topic || action || '—'}`);
    const payment = await fetchMercadoPagoPayment(id);
    console.log('💳 Detalhe do pagamento (API MP):', {
      id: payment?.id,
      status: payment?.status,
      external_reference: payment?.external_reference,
      transaction_amount: payment?.transaction_amount,
    });
    return fulfillFromApprovedPayment(pool, jwtSecret, payment);
  }

  if (isMerchantOrderNotification(notification)) {
    console.log(`${LOG} Recebido merchant_order id=${id}`);
    const merchantOrder = await fetchMercadoPagoMerchantOrder(id);
    const payments = Array.isArray(merchantOrder?.payments) ? merchantOrder.payments : [];
    const approved = payments.filter(
      (p) => String(p?.status || '').toLowerCase() === 'approved'
    );

    if (approved.length === 0) {
      console.log(
        `${LOG} merchant_order ${id} sem pagamentos approved (${payments.length} payment(s))`
      );
      return { handled: false, reason: 'merchant_order_no_approved', merchant_order_id: id };
    }

    const results = [];
    for (const p of approved) {
      const payId = p.id != null ? String(p.id) : '';
      if (!payId) continue;
      const payment = await fetchMercadoPagoPayment(payId);
      console.log('💳 Detalhe do pagamento (API MP):', {
        id: payment?.id,
        status: payment?.status,
        external_reference: payment?.external_reference,
        transaction_amount: payment?.transaction_amount,
      });
      results.push(await fulfillFromApprovedPayment(pool, jwtSecret, payment));
    }
    return {
      handled: results.some((r) => r.handled),
      merchant_order_id: id,
      results,
    };
  }

  console.log(
    `${LOG} Tópico ignorado topic=${topic || '—'} action=${action || '—'} id=${id}`
  );
  return { handled: false, reason: 'ignored_topic', topic, action, id };
}

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ jwtSecret: string }} options
 */
function registerMpWebhookRoutes(app, pool, { jwtSecret }) {
  const handler = async (req, res) => {
    console.log('\n\n=== 🚨 INÍCIO WEBHOOK MERCADO PAGO 🚨 ===');
    console.log('📥 method:', req.method);
    console.log('📥 query:', JSON.stringify(req.query || {}, null, 2));
    console.log('📥 body (payload):', JSON.stringify(req.body || {}, null, 2));
    console.log('📥 headers (x-request-id / user-agent):', {
      'user-agent': req.headers['user-agent'],
      'x-request-id': req.headers['x-request-id'],
      'content-type': req.headers['content-type'],
    });

    try {
      const signature = verifyMercadoPagoWebhookSignature(req);
      if (!signature.ok) {
        console.warn(`${LOG} assinatura recusada mode=${signature.mode}`);
        return res.status(401).json({ ok: false, error: 'assinatura inválida' });
      }
      const notification = extractNotification(req);
      console.log(
        `${LOG} Incoming topic=${notification.topic || '—'} action=${notification.action || '—'} id=${notification.id || '—'} sig=${signature.mode}`
      );

      const result = await processMpNotification(pool, jwtSecret, notification);

      console.log('📤 resultado:', JSON.stringify(result, null, 2));
      console.log('=== 🏁 FIM WEBHOOK MERCADO PAGO 🏁 ===\n\n');

      // MP espera 200/201 para não reenviar em loop; erros de negócio ainda 200
      return res.status(200).json({ ok: true, ...result });
    } catch (err) {
      console.error(`${LOG} Erro:`, err.message);
      if (err.mpResponse) {
        console.error(`${LOG} mpResponse:`, JSON.stringify(err.mpResponse, null, 2));
      }
      console.log('=== 🏁 FIM WEBHOOK MERCADO PAGO 🏁 ===\n\n');

      const status = err.statusCode && err.statusCode >= 400 && err.statusCode < 600 ? err.statusCode : 500;
      // 5xx faz o MP reintentar — útil se a API MP estiver instável
      if (status >= 500) {
        return res.status(status).json({ ok: false, error: err.message });
      }
      return res.status(200).json({ ok: false, error: err.message });
    }
  };

  app.post('/webhooks/mercadopago', handler);
  app.get('/webhooks/mercadopago', handler);
  // Alias legado / tipografia comum
  app.post('/webhook/mercadopago', handler);
  app.get('/webhook/mercadopago', handler);
}

// Return build that keeps the durable card confirmation. The pre-outbox Hub is not a return version.
const FINANCIAL_RETURN_VERSION = 'hub-confirm-durable-20261028';

module.exports = {
  FINANCIAL_RETURN_VERSION,
  registerMpWebhookRoutes,
  processMpNotification,
  fulfillFromApprovedPayment,
  fulfillVerifiedCardPayment,
  extractNotification,
  verifyMercadoPagoWebhookSignature,
  buildMercadoPagoManifest,
};

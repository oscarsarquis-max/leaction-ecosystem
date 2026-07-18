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

const {
  fetchMercadoPagoPayment,
  fetchMercadoPagoMerchantOrder,
  isMercadoPagoConfigured,
} = require('../mercadopago');
const { fulfillOrderPayment } = require('../payment-fulfillment');

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

/**
 * @param {import('pg').Pool} pool
 * @param {string} jwtSecret
 * @param {object} payment — resposta GET /v1/payments/:id
 */
async function fulfillFromApprovedPayment(pool, jwtSecret, payment) {
  const status = String(payment?.status || '').toLowerCase();
  const paymentId = payment?.id != null ? String(payment.id) : null;
  const orderId = String(payment?.external_reference || '').trim();

  if (status !== 'approved') {
    console.log(
      `${LOG} Pagamento ${paymentId || '—'} status=${status || '—'} — ignorado (só approved dispara fulfill)`
    );
    return { handled: false, reason: 'not_approved', status, payment_id: paymentId };
  }

  if (!orderId) {
    console.warn(
      `${LOG} Pagamento ${paymentId} aprovado sem external_reference — não é possível mapear order`
    );
    return { handled: false, reason: 'missing_external_reference', payment_id: paymentId };
  }

  const existing = await pool.query(
    `SELECT id, status FROM orders WHERE id = $1 LIMIT 1`,
    [orderId]
  );
  if (existing.rows.length === 0) {
    console.warn(`${LOG} Order não encontrada para external_reference=${orderId}`);
    return {
      handled: false,
      reason: 'order_not_found',
      order_id: orderId,
      payment_id: paymentId,
    };
  }

  const order = existing.rows[0];
  if (String(order.status || '').toUpperCase() === 'PAID') {
    console.log(
      `${LOG} Order ${orderId} já está PAID — idempotência (payment=${paymentId})`
    );
    // Garante activateFromOrder caso fulfill anterior tenha falhado no contrato
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

  console.log(
    `${LOG} Pagamento aprovado para a order ${orderId}. Acionando ContractService...`
  );

  const result = await fulfillOrderPayment(pool, orderId, jwtSecret, {
    gatewayReference: paymentId,
    paymentProvider: 'mercadopago',
  });

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

  if (isPaymentNotification(notification)) {
    console.log(`${LOG} Recebido payment id=${id} topic=${topic || action || '—'}`);
    const payment = await fetchMercadoPagoPayment(id);
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

    // Processa cada payment approved (busca detalhe para external_reference)
    const results = [];
    for (const p of approved) {
      const payId = p.id != null ? String(p.id) : '';
      if (!payId) continue;
      const payment = await fetchMercadoPagoPayment(payId);
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
    try {
      const notification = extractNotification(req);
      console.log(
        `${LOG} Incoming ${req.method} topic=${notification.topic || '—'} action=${notification.action || '—'} id=${notification.id || '—'}`
      );

      const result = await processMpNotification(pool, jwtSecret, notification);

      // MP espera 200/201 para não reenviar em loop; erros de negócio ainda 200
      return res.status(200).json({ ok: true, ...result });
    } catch (err) {
      console.error(`${LOG} Erro:`, err.message);
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

module.exports = {
  registerMpWebhookRoutes,
  processMpNotification,
  fulfillFromApprovedPayment,
  extractNotification,
};

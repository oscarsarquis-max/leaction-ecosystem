'use strict';

/**
 * Cobranças na conta MP do parceiro. Axios direto com o token do recebedor.
 * Não importa mercadopago.js.
 */

const axios = require('axios');
const {
  sellerPaymentsEnabled,
  authSellerApp,
  getSellerAccount,
  ensureSellerAccessToken,
  returnToAllowed,
  signChargeToken,
  verifyChargeToken,
} = require('./sellers-oauth');
const { assertCents, centsToMercadoPagoAmount, mercadoPagoAmountToCents } = require('../lib/money-cents');

const MP_PAYMENTS_URL = 'https://api.mercadopago.com/v1/payments';
const PUBLIC_ORIGIN = () =>
  String(process.env.ACTION_HUB_PUBLIC_URL || 'https://actionhub.com.br').replace(/\/$/, '');
const API_ORIGIN = () =>
  String(process.env.HUB_GATEWAY_PUBLIC_URL || 'https://api.actionhub.com.br').replace(/\/$/, '');
const SELLER_WEBHOOK = () => `${API_ORIGIN()}/webhook/sellers`;
const OBSERVE_MIN_MS = 30_000;

function disabled404(res) {
  return res.status(404).json({ error: 'não encontrado' });
}

function mapMpToChargeStatus(status, detail) {
  const value = String(status || '').toLowerCase();
  const d = String(detail || '').toLowerCase();
  if (value === 'approved') return 'PAID';
  if (value === 'rejected') return 'REJECTED';
  if (value === 'cancelled') return 'CANCELLED';
  if (value === 'expired' || d === 'expired') return 'EXPIRED';
  if (value === 'refunded' || value === 'charged_back') return 'REFUNDED';
  return 'PENDING';
}

function extractPix(payment) {
  const data =
    payment?.point_of_interaction?.transaction_data &&
    typeof payment.point_of_interaction.transaction_data === 'object'
      ? payment.point_of_interaction.transaction_data
      : {};
  return {
    qr_code: data.qr_code ? String(data.qr_code) : null,
    qr_code_base64: data.qr_code_base64 ? String(data.qr_code_base64) : null,
    ticket_url: data.ticket_url ? String(data.ticket_url) : null,
    date_of_expiration: payment?.date_of_expiration
      ? String(payment.date_of_expiration)
      : null,
  };
}

async function mpRequest(deps, { method, url, token, body, idempotencyKey }) {
  const http = deps.http || axios;
  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  if (idempotencyKey) headers['X-Idempotency-Key'] = String(idempotencyKey).slice(0, 120);
  try {
    const res = await http({ method, url, data: body, headers, timeout: 20000 });
    return res.data;
  } catch (err) {
    const wrapped = new Error(
      err.response?.data?.message ||
        err.response?.data?.error ||
        err.message ||
        'falha Mercado Pago'
    );
    wrapped.statusCode = err.response?.status || 502;
    wrapped.mpResponse = err.response?.data;
    throw wrapped;
  }
}

async function createPixWithSellerToken(token, charge, deps) {
  const amount = centsToMercadoPagoAmount(charge.amount_cents);
  const payload = {
    transaction_amount: amount,
    description: String(charge.description).slice(0, 120),
    payment_method_id: 'pix',
    payer: { email: charge.payer_email },
    external_reference: String(charge.id),
    notification_url: SELLER_WEBHOOK(),
  };
  return mpRequest(deps, {
    method: 'post',
    url: MP_PAYMENTS_URL,
    token,
    body: payload,
    idempotencyKey: `seller-pix-${charge.id}`,
  });
}

async function createCardWithSellerToken(token, charge, cardBody, deps) {
  const amount = centsToMercadoPagoAmount(charge.amount_cents);
  const payer = cardBody.payer && typeof cardBody.payer === 'object' ? cardBody.payer : {};
  const identification =
    payer.identification && typeof payer.identification === 'object'
      ? payer.identification
      : {};
  const payload = {
    transaction_amount: amount,
    description: String(charge.description).slice(0, 120),
    token: String(cardBody.token || ''),
    payment_method_id: String(cardBody.payment_method_id || ''),
    installments: Number(cardBody.installments) || 1,
    issuer_id: cardBody.issuer_id != null ? String(cardBody.issuer_id) : undefined,
    payer: {
      email: String(payer.email || charge.payer_email).trim().toLowerCase(),
      identification: {
        type: String(identification.type || 'CPF'),
        number: String(identification.number || '').replace(/\D/g, ''),
      },
    },
    external_reference: String(charge.id),
    notification_url: SELLER_WEBHOOK(),
  };
  if (!payload.token || !payload.payment_method_id) {
    const err = new Error('token e payment_method_id obrigatórios');
    err.statusCode = 400;
    throw err;
  }
  if (!payload.payer.identification.number || payload.payer.identification.number.length < 11) {
    const err = new Error('CPF obrigatório');
    err.statusCode = 400;
    throw err;
  }
  return mpRequest(deps, {
    method: 'post',
    url: MP_PAYMENTS_URL,
    token,
    body: payload,
    idempotencyKey: `seller-card-${charge.id}`,
  });
}

async function fetchPaymentWithSellerToken(token, paymentId, deps) {
  return mpRequest(deps, {
    method: 'get',
    url: `${MP_PAYMENTS_URL}/${encodeURIComponent(paymentId)}`,
    token,
  });
}

async function applyPaymentObservation(pool, charge, payment) {
  const status = mapMpToChargeStatus(payment.status, payment.status_detail);
  let paidAmountCents = null;
  try {
    if (payment.transaction_amount != null) {
      paidAmountCents = mercadoPagoAmountToCents(payment.transaction_amount);
    }
  } catch {
    paidAmountCents = null;
  }

  let mismatch = null;
  let finalStatus = status;
  if (status === 'PAID') {
    if (paidAmountCents !== charge.amount_cents) {
      mismatch = 'amount_mismatch';
      finalStatus = 'PENDING';
    }
  }

  const pix = extractPix(payment);
  const refunded =
    payment.transaction_amount_refunded != null
      ? mercadoPagoAmountToCents(payment.transaction_amount_refunded)
      : null;

  const r = await pool.query(
    `UPDATE seller_charges SET
       mp_payment_id = COALESCE($2, mp_payment_id),
       status = $3,
       mp_status = $4,
       mp_status_detail = $5,
       method = COALESCE(method, $6),
       pix_qr_code = COALESCE($7, pix_qr_code),
       pix_qr_code_base64 = COALESCE($8, pix_qr_code_base64),
       pix_ticket_url = COALESCE($9, pix_ticket_url),
       pix_expires_at = COALESCE($10::timestamptz, pix_expires_at),
       paid_amount_cents = CASE WHEN $3 = 'PAID' THEN $11 ELSE paid_amount_cents END,
       refunded_amount_cents = COALESCE($12, refunded_amount_cents),
       paid_at = CASE WHEN $3 = 'PAID' AND paid_at IS NULL THEN now() ELSE paid_at END,
       mismatch_reason = $13,
       last_observed_at = now(),
       updated_at = now()
     WHERE id = $1
     RETURNING *`,
    [
      charge.id,
      payment.id != null ? String(payment.id) : null,
      finalStatus,
      payment.status != null ? String(payment.status) : null,
      payment.status_detail != null ? String(payment.status_detail) : null,
      payment.payment_type_id === 'credit_card' || payment.payment_method_id === 'pix'
        ? payment.payment_method_id === 'pix'
          ? 'pix'
          : 'card'
        : null,
      pix.qr_code,
      pix.qr_code_base64,
      pix.ticket_url,
      pix.date_of_expiration,
      paidAmountCents,
      refunded,
      mismatch,
    ]
  );
  return r.rows[0];
}

function publicChargeView(charge, account) {
  return {
    charge_id: charge.id,
    amount_cents: charge.amount_cents,
    description: charge.description,
    payer_email: charge.payer_email || null,
    seller_nickname: account?.mp_nickname || null,
    public_key: account?.public_key || null,
    status: charge.status,
    method: charge.method,
    pix:
      charge.method === 'pix' || charge.pix_qr_code
        ? {
            qr_code: charge.pix_qr_code,
            qr_code_base64: charge.pix_qr_code_base64,
            ticket_url: charge.pix_ticket_url,
            date_of_expiration: charge.pix_expires_at,
          }
        : null,
    return_to: charge.return_to,
  };
}

function checkoutUrlFor(chargeId) {
  const t = signChargeToken(chargeId);
  return `${PUBLIC_ORIGIN()}/checkout/seller?charge=${encodeURIComponent(chargeId)}&t=${encodeURIComponent(t)}`;
}

async function loadCharge(pool, id) {
  const r = await pool.query(`SELECT * FROM seller_charges WHERE id = $1 LIMIT 1`, [id]);
  return r.rows[0] || null;
}

async function maybeRefreshPending(pool, charge, account, deps) {
  if (charge.status !== 'PENDING' || !charge.mp_payment_id) return charge;
  const last = charge.last_observed_at ? new Date(charge.last_observed_at).getTime() : 0;
  if (Date.now() - last < OBSERVE_MIN_MS) return charge;
  const token = await ensureSellerAccessToken(pool, account, deps);
  const payment = await fetchPaymentWithSellerToken(token, charge.mp_payment_id, deps);
  return applyPaymentObservation(pool, charge, payment);
}

function registerSellerChargeRoutes(app, pool, deps = {}) {
  app.post('/v1/sellers/:ref/charges', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const auth = await authSellerApp(req, pool);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      const sellerRef = String(req.params.ref || '').trim();
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const idempotencyKey = String(
        req.headers['idempotency-key'] || body.idempotency_key || ''
      ).trim();
      if (!idempotencyKey || idempotencyKey.length > 120) {
        return res.status(400).json({ error: 'idempotency_key obrigatória (até 120)' });
      }
      const existing = await pool.query(
        `SELECT * FROM seller_charges WHERE app_id = $1 AND idempotency_key = $2 LIMIT 1`,
        [auth.appId, idempotencyKey]
      );
      if (existing.rows[0]) {
        const charge = existing.rows[0];
        return res.status(200).json({
          charge_id: charge.id,
          status: charge.status,
          amount_cents: charge.amount_cents,
          pix: {
            qr_code: charge.pix_qr_code,
            qr_code_base64: charge.pix_qr_code_base64,
            ticket_url: charge.pix_ticket_url,
            date_of_expiration: charge.pix_expires_at,
          },
          checkout_url: checkoutUrlFor(charge.id),
        });
      }

      const account = await getSellerAccount(pool, auth.appId, sellerRef);
      if (!account || account.status !== 'connected') {
        return res.status(409).json({ error: 'Reconecte sua conta' });
      }

      const externalReference = String(body.external_reference || '').trim();
      const description = String(body.description || '').trim();
      const payerEmail = String(body.payer_email || '').trim().toLowerCase();
      const amountCents = body.amount_cents;
      try {
        assertCents(amountCents);
      } catch (err) {
        return res.status(400).json({ error: err.message });
      }
      if (!externalReference || externalReference.length > 120) {
        return res.status(400).json({ error: 'external_reference obrigatória' });
      }
      if (!description || description.length > 120) {
        return res.status(400).json({ error: 'description obrigatória (até 120)' });
      }
      if (!payerEmail.includes('@') || payerEmail.length > 254) {
        return res.status(400).json({ error: 'payer_email inválido' });
      }
      let returnTo = null;
      if (body.return_to) {
        const check = returnToAllowed(body.return_to, auth.app.return_origins);
        if (!check.ok) return res.status(400).json({ error: check.error });
        returnTo = check.url;
      }

      const inserted = await pool.query(
        `INSERT INTO seller_charges (
           app_id, seller_ref, seller_account_id, idempotency_key, external_reference,
           description, payer_email, amount_cents, currency, status, return_to, method
         ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'BRL','PENDING',$9,'pix')
         RETURNING *`,
        [
          auth.appId,
          sellerRef,
          account.id,
          idempotencyKey,
          externalReference,
          description,
          payerEmail,
          amountCents,
          returnTo,
        ]
      );
      let charge = inserted.rows[0];
      const token = await ensureSellerAccessToken(pool, account, deps);
      const payment = await createPixWithSellerToken(token, charge, deps);
      charge = await applyPaymentObservation(pool, charge, payment);

      return res.status(201).json({
        charge_id: charge.id,
        status: charge.status,
        amount_cents: charge.amount_cents,
        pix: {
          qr_code: charge.pix_qr_code,
          qr_code_base64: charge.pix_qr_code_base64,
          ticket_url: charge.pix_ticket_url,
          date_of_expiration: charge.pix_expires_at,
        },
        checkout_url: checkoutUrlFor(charge.id),
      });
    } catch (err) {
      console.error('[seller-charges] create', err.message);
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });

  app.get('/v1/sellers/charges/:id', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const auth = await authSellerApp(req, pool);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      let charge = await loadCharge(pool, String(req.params.id || '').trim());
      if (!charge || charge.app_id !== auth.appId) {
        return res.status(404).json({ error: 'cobrança não encontrada' });
      }
      const account = await getSellerAccount(pool, charge.app_id, charge.seller_ref);
      charge = await maybeRefreshPending(pool, charge, account, deps);
      return res.status(200).json({
        charge_id: charge.id,
        status: charge.status,
        amount_cents: charge.amount_cents,
        paid_amount_cents: charge.paid_amount_cents,
        method: charge.method,
        mp_payment_id: charge.mp_payment_id,
        mismatch_reason: charge.mismatch_reason,
      });
    } catch (err) {
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });

  app.post('/v1/sellers/charges/:id/cancel', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const auth = await authSellerApp(req, pool);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      const charge = await loadCharge(pool, String(req.params.id || '').trim());
      if (!charge || charge.app_id !== auth.appId) {
        return res.status(404).json({ error: 'cobrança não encontrada' });
      }
      if (charge.status !== 'PENDING') {
        return res.status(409).json({ error: 'só cobranças PENDING podem ser canceladas' });
      }
      const account = await getSellerAccount(pool, charge.app_id, charge.seller_ref);
      const token = await ensureSellerAccessToken(pool, account, deps);
      if (charge.mp_payment_id) {
        await mpRequest(deps, {
          method: 'put',
          url: `${MP_PAYMENTS_URL}/${encodeURIComponent(charge.mp_payment_id)}`,
          token,
          body: { status: 'cancelled' },
        });
      }
      const r = await pool.query(
        `UPDATE seller_charges SET status = 'CANCELLED', updated_at = now() WHERE id = $1 RETURNING status`,
        [charge.id]
      );
      return res.status(200).json({ status: r.rows[0].status });
    } catch (err) {
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });

  app.post('/v1/sellers/charges/:id/refund', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const auth = await authSellerApp(req, pool);
      if (!auth.ok) return res.status(auth.status).json({ error: auth.error });
      const charge = await loadCharge(pool, String(req.params.id || '').trim());
      if (!charge || charge.app_id !== auth.appId) {
        return res.status(404).json({ error: 'cobrança não encontrada' });
      }
      if (charge.status !== 'PAID') {
        return res.status(409).json({ error: 'só cobranças PAID podem ser estornadas' });
      }
      const account = await getSellerAccount(pool, charge.app_id, charge.seller_ref);
      const token = await ensureSellerAccessToken(pool, account, deps);
      await mpRequest(deps, {
        method: 'post',
        url: `${MP_PAYMENTS_URL}/${encodeURIComponent(charge.mp_payment_id)}/refunds`,
        token,
        body: {},
        idempotencyKey: `seller-refund-${charge.id}`,
      });
      const r = await pool.query(
        `UPDATE seller_charges SET status = 'REFUNDED', refunded_amount_cents = amount_cents, updated_at = now()
         WHERE id = $1 RETURNING status, refunded_amount_cents`,
        [charge.id]
      );
      return res.status(200).json(r.rows[0]);
    } catch (err) {
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });

  app.get('/v1/sellers/charges/:id/public', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const id = String(req.params.id || '').trim();
      const t = String(req.query.t || '').trim();
      if (!verifyChargeToken(id, t)) {
        return res.status(401).json({ error: 'token inválido' });
      }
      let charge = await loadCharge(pool, id);
      if (!charge) return res.status(404).json({ error: 'cobrança não encontrada' });
      const account = await getSellerAccount(pool, charge.app_id, charge.seller_ref);
      charge = await maybeRefreshPending(pool, charge, account, deps);
      return res.status(200).json(publicChargeView(charge, account));
    } catch (err) {
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });

  app.post('/v1/sellers/charges/:id/card', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const id = String(req.params.id || '').trim();
      const t = String(req.query.t || req.body?.t || '').trim();
      if (!verifyChargeToken(id, t)) {
        return res.status(401).json({ error: 'token inválido' });
      }
      let charge = await loadCharge(pool, id);
      if (!charge) return res.status(404).json({ error: 'cobrança não encontrada' });
      if (charge.status === 'PAID') {
        return res.status(200).json({ status: 'PAID', charge_id: charge.id });
      }
      if (charge.status !== 'PENDING') {
        return res.status(409).json({ error: 'cobrança não aceita cartão' });
      }
      const account = await getSellerAccount(pool, charge.app_id, charge.seller_ref);
      const token = await ensureSellerAccessToken(pool, account, deps);
      await pool.query(`UPDATE seller_charges SET method = 'card', updated_at = now() WHERE id = $1`, [
        charge.id,
      ]);
      const payment = await createCardWithSellerToken(token, charge, req.body || {}, deps);
      charge = await applyPaymentObservation(pool, { ...charge, method: 'card' }, payment);
      return res.status(200).json({
        status: charge.status,
        charge_id: charge.id,
        mp_payment_id: charge.mp_payment_id,
      });
    } catch (err) {
      console.error('[seller-charges] card', err.message);
      return res.status(err.statusCode || 500).json({ error: err.message });
    }
  });

  app.post('/webhook/sellers', async (req, res) => {
    if (!sellerPaymentsEnabled()) return disabled404(res);
    try {
      const q = req.query || {};
      const body = req.body && typeof req.body === 'object' ? req.body : {};
      const paymentId = String(
        q.id || q['data.id'] || body?.data?.id || body.id || ''
      ).trim();
      if (!paymentId) {
        return res.status(200).json({ ok: true, reason: 'missing_id' });
      }

      let charge = (
        await pool.query(
          `SELECT * FROM seller_charges WHERE mp_payment_id = $1 LIMIT 1`,
          [paymentId]
        )
      ).rows[0];
      if (!charge) {
        // tenta por external_reference = charge.id (quando o MP notifica antes do UPDATE local)
        const byRef = await pool.query(
          `SELECT * FROM seller_charges WHERE id::text = $1 LIMIT 1`,
          [String(body?.data?.external_reference || body.external_reference || '')]
        );
        charge = byRef.rows[0];
      }
      if (!charge) {
        return res.status(200).json({ ok: true, reason: 'charge_not_found' });
      }

      const account = await getSellerAccount(pool, charge.app_id, charge.seller_ref);
      if (!account) {
        return res.status(200).json({ ok: true, reason: 'account_missing' });
      }
      const token = await ensureSellerAccessToken(pool, account, deps);
      const payment = await fetchPaymentWithSellerToken(token, paymentId, deps);
      const updated = await applyPaymentObservation(pool, charge, payment);
      return res.status(200).json({
        ok: true,
        charge_id: updated.id,
        status: updated.status,
        mismatch_reason: updated.mismatch_reason,
      });
    } catch (err) {
      console.error('[seller-charges] webhook', err.message);
      return res.status(200).json({ ok: false, error: err.message });
    }
  });
}

module.exports = {
  registerSellerChargeRoutes,
  applyPaymentObservation,
  mapMpToChargeStatus,
  extractPix,
  createPixWithSellerToken,
  createCardWithSellerToken,
  fetchPaymentWithSellerToken,
  checkoutUrlFor,
  publicChargeView,
  SELLER_WEBHOOK,
};

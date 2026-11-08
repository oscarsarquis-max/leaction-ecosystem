'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  applyProviderObservation,
  publicAmountOrder,
  mapMpStatusToFinancial,
  isAmountCheckoutPayload,
  isProviderPaidConfirmed,
} = require('./amount-checkout');
const { fulfillFromApprovedPayment, extractNotification, verifyMercadoPagoWebhookSignature } = require('./mp-webhooks');
const { isCardPaymentSuccess, isCardPaymentPending, isPreapprovalSuccess } = require('../mercadopago');
const { publicListItem, classifyOrderDetail } = require('./spider-pay-lookup');
const { chargedCentsFromHub, paidCentsFromHub, serializePaymentRow } = require('../admin/payments');
const { mercadoPagoAmountToCents } = require('../lib/money-cents');
const { parsePanelDxIdMatu } = require('../payment-fulfillment');

function amountPayload(overrides = {}) {
  return {
    source: 'amount_checkout',
    app_id: 'lojadepaes',
    amount_cents: 7000,
    currency: 'BRL',
    method: 'pix',
    customer_email: 'cliente@example.test',
    subject_id: 'subject-1',
    order_reference: 'ref-1',
    payment_request_id: 'req-1',
    mp_payment_id: '111',
    pix: { status: 'pending', mp_payment_id: '111', qr_code: 'qr' },
    ...overrides,
  };
}

function sessionPayload() {
  return {
    source: 'catalog_checkout',
    app_id: 'inove4us',
    sku: 'PLANO_PRO',
    plano_nome: 'Pro',
    valor_negociado: 99.5,
    credits: 100,
    subject_id: 'escola-1',
  };
}

test('mapeamento approved/pending/cancelled não inventa literal do pedido', () => {
  assert.equal(mapMpStatusToFinancial('approved'), 'paid');
  assert.equal(mapMpStatusToFinancial('authorized'), 'authorized');
  assert.notEqual(mapMpStatusToFinancial('authorized'), 'paid');
  assert.equal(mapMpStatusToFinancial('pending'), 'pending');
  assert.equal(mapMpStatusToFinancial('cancelled'), 'cancelled');
  assert.equal(mapMpStatusToFinancial('rejected'), 'failed');
  assert.equal(mapMpStatusToFinancial('in_process'), 'pending');
  assert.notEqual(mapMpStatusToFinancial('approved'), 'PAID');
  assert.notEqual(mapMpStatusToFinancial('approved'), 'approved');
});

test('checkout avulso: Pix aprovado, pendente, cancelado, divergente e cartão', () => {
  const approved = applyProviderObservation(amountPayload(), {
    id: 111,
    status: 'approved',
    live_mode: true,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 7000 });
  const approvedPublic = publicAmountOrder({ id: 'o1', status: 'PAID' }, approved.payload);
  assert.equal(approvedPublic.amount_cents, 7000);
  assert.equal(approvedPublic.paid_amount_cents, 7000);
  assert.equal(approvedPublic.pix.status, 'approved');
  assert.equal(approvedPublic.live_mode, true);

  const pending = publicAmountOrder({ id: 'o2', status: 'PENDING' }, amountPayload());
  assert.equal(pending.paid_amount_absent, true);
  assert.equal(pending.paid_amount_cents, null);
  assert.equal(pending.pix.status, 'pending');

  const cancelled = applyProviderObservation(amountPayload(), {
    id: 111,
    status: 'cancelled',
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, {});
  const cancelledPublic = publicAmountOrder({ id: 'o3', status: 'CANCELLED' }, cancelled.payload);
  assert.equal(cancelledPublic.status, 'CANCELLED');
  assert.equal(cancelledPublic.pix.status, 'cancelled');
  assert.equal(cancelledPublic.amount_cents, 7000);
  assert.equal(cancelledPublic.paid_amount_absent, true);
  assert.equal(cancelledPublic.paid_amount_cents, null);
  assert.equal(cancelled.payload.observed_amount_cents, undefined);

  const mismatch = applyProviderObservation(amountPayload(), {
    id: 222,
    status: 'approved',
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 6500, mismatchReason: 'amount_mismatch' });
  assert.equal(mismatch.payload.amount_cents, 7000);
  assert.equal(mismatch.payload.paid_amount_cents, 6500);
  assert.equal(mismatch.payload.amount_mismatch.reason, 'amount_mismatch');
  assert.equal(publicAmountOrder({ id: 'o4', status: 'PENDING' }, mismatch.payload).status, 'PENDING');

  const card = publicAmountOrder(
    { id: 'o5', status: 'PENDING' },
    amountPayload({ method: 'card', pix: undefined })
  );
  assert.equal(card.method, 'card');
  assert.equal(card.pix, null);
  assert.equal(card.amount_cents, 7000);

  const authorized = applyProviderObservation(amountPayload({ method: 'card', pix: undefined }), {
    id: 333,
    status: 'authorized',
    status_detail: 'pending_capture',
    captured: false,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 7000 });
  const authorizedPublic = publicAmountOrder({ id: 'o6', status: 'PENDING' }, authorized.payload);
  assert.equal(authorizedPublic.status, 'PENDING');
  assert.equal(authorizedPublic.paid_amount_absent, true);
  assert.equal(authorizedPublic.paid_amount_cents, null);
  assert.equal(authorizedPublic.observed_amount_cents, 7000);
  assert.equal(authorized.payload.paid_amount_confirmed, false);

  const cancelledWithAmount = applyProviderObservation(amountPayload(), {
    id: 111,
    status: 'cancelled',
    transaction_amount: 70,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 7000 });
  const cancelledObserved = publicAmountOrder({ id: 'o7', status: 'CANCELLED' }, cancelledWithAmount.payload);
  assert.equal(cancelledObserved.paid_amount_absent, true);
  assert.equal(cancelledObserved.paid_amount_cents, null);
  assert.equal(cancelledObserved.observed_amount_cents, 7000);
  assert.equal(cancelledWithAmount.payload.paid_amount_confirmed, false);

  assert.equal(isProviderPaidConfirmed({ status: 'approved', captured: true }), true);
  assert.equal(isProviderPaidConfirmed({ status: 'approved' }), true);
  assert.equal(isProviderPaidConfirmed({ status: 'approved', captured: false }), false);
  assert.equal(isProviderPaidConfirmed({ status: 'authorized', captured: false }), false);
});

test('sessão/plano continua em valor_negociado e não é confundida com checkout avulso', () => {
  const session = sessionPayload();
  assert.equal(isAmountCheckoutPayload(session), false);
  const charged = chargedCentsFromHub(session);
  assert.equal(charged, 9950);
  assert.equal(paidCentsFromHub(session), null);
  const item = publicListItem({
    id: 'sess-1',
    status: 'PAID',
    external_resource_id: JSON.stringify(session),
    created_at: '2026-10-01T12:00:00.000Z',
    updated_at: '2026-10-01T12:00:00.000Z',
  });
  assert.equal(item.amountSource, 'valor_negociado_brl');
  assert.equal(item.chargedAmountMinor, '9950');
  assert.equal(item.paidAmountAbsent, true);
});

test('PanelDX id_matu permanece numérico e fulfill compartilhado reconhece skip só no avulso', () => {
  assert.equal(parsePanelDxIdMatu('12345'), '12345');
  assert.equal(parsePanelDxIdMatu('abc'), null);
  assert.equal(parsePanelDxIdMatu('0'), null);
  assert.equal(isAmountCheckoutPayload({ source: 'amount_checkout', amount_cents: 100 }), true);
  assert.equal(isAmountCheckoutPayload({ source: 'catalog_checkout', valor_negociado: 10 }), false);
});

test('observação preserva metadados e recusa callback antigo', () => {
  const first = applyProviderObservation(amountPayload({ extra_note: 'keep-me' }), {
    id: 111,
    status: 'approved',
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 7000 });
  assert.equal(first.payload.extra_note, 'keep-me');
  assert.equal(first.payload.customer_email, 'cliente@example.test');
  const stale = applyProviderObservation(first.payload, {
    id: 111,
    status: 'pending',
    date_last_updated: '2026-10-02T11:00:00.000Z',
  }, { paidAmountCents: 1 });
  assert.equal(stale.applied, false);
  assert.equal(stale.payload.paid_amount_cents, 7000);
  assert.equal(stale.payload.pix.status, 'approved');
});

test('live_mode só vem do pagamento e token de processo não é gravado', () => {
  const none = applyProviderObservation(amountPayload(), {
    id: 1,
    status: 'approved',
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 7000 });
  assert.equal(none.payload.live_mode, undefined);
  const live = applyProviderObservation(amountPayload(), {
    id: 1,
    status: 'approved',
    live_mode: true,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 7000 });
  assert.equal(live.payload.live_mode, true);
  assert.equal(live.payload.live_mode_source, 'mp_payment.live_mode');
  const testMode = applyProviderObservation(amountPayload(), {
    id: 1,
    status: 'approved',
    live_mode: false,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 7000 });
  assert.equal(testMode.payload.live_mode, false);
});

test('admin distingue cobrado, pago ausente e nunca inventa zero', () => {
  const checkout = serializePaymentRow({
    id: 'adm-1',
    status: 'PAID',
    created_at: '2026-10-01T12:00:00.000Z',
    external_resource_id: JSON.stringify(amountPayload()),
  });
  assert.equal(checkout.charged_amount_cents, 7000);
  assert.equal(checkout.paid_amount_cents, null);
  assert.equal(checkout.paid_amount_absent, true);
  assert.equal(checkout.amount, 70);
  const paid = serializePaymentRow({
    id: 'adm-2',
    status: 'PAID',
    created_at: '2026-10-01T12:00:00.000Z',
    external_resource_id:     JSON.stringify({
      ...amountPayload(),
      paid_amount_cents: 7000,
      paid_amount_confirmed: true,
      provider_status: 'approved',
    }),
  });
  assert.equal(paid.paid_amount_cents, 7000);
  assert.equal(paid.provider_status, 'approved');
  assert.equal(serializePaymentRow({
    id: 'adm-3',
    status: 'PENDING',
    created_at: '2026-10-01T12:00:00.000Z',
    external_resource_id: '{}',
  }).charged_amount_cents, null);
});

test('classificação REAL exige live_mode no payload, não no token', () => {
  const indeterminate = classifyOrderDetail({
    status: 'PAID',
    external_resource_id: JSON.stringify(amountPayload()),
  });
  assert.equal(indeterminate.classification, 'INDETERMINATE');
  const real = classifyOrderDetail({
    status: 'PAID',
    external_resource_id: JSON.stringify({ ...amountPayload(), live_mode: true }),
  });
  assert.equal(real.classification, 'REAL');
  const labeledTest = classifyOrderDetail({
    status: 'PAID',
    external_resource_id: JSON.stringify({ ...amountPayload(), sandbox: true }),
  });
  assert.equal(labeledTest.classification, 'TEST');
});

test('cartão autorizado não é sucesso de captura', () => {
  assert.equal(isCardPaymentSuccess({ status: 'approved' }), true);
  assert.equal(isCardPaymentSuccess({ status: 'authorized' }), false);
  assert.equal(isCardPaymentPending({ status: 'authorized' }), true);
});

test('HMAC Mercado Pago aceita assinatura oficial e recusa POST sem header quando o secret existe', () => {
  const crypto = require('crypto');
  const secret = 'webhook-secret-test';
  const req = {
    method: 'POST',
    query: { 'data.id': '999' },
    body: { data: { id: '999' } },
    headers: { 'x-request-id': 'req-1' },
    get(name) {
      return this.headers[String(name).toLowerCase()];
    },
  };
  const manifest = 'id:999;request-id:req-1;ts:1704908010;';
  req.headers['x-signature'] =
    'ts=1704908010,v1=' + crypto.createHmac('sha256', secret).update(manifest).digest('hex');
  assert.equal(verifyMercadoPagoWebhookSignature(req, secret).ok, true);
  assert.equal(verifyMercadoPagoWebhookSignature(req, secret).mode, 'hmac_sha256');
  delete req.headers['x-signature'];
  assert.equal(verifyMercadoPagoWebhookSignature(req, secret).ok, false);
  assert.equal(verifyMercadoPagoWebhookSignature({ method: 'GET', query: { id: '1' }, headers: {}, get() { return undefined; } }, secret).mode, 'ipn_without_signature');
  assert.equal(verifyMercadoPagoWebhookSignature(req, '').mode, 'secret_absent');
});

test('webhook extrai id de IPN e body sem inventar tópico', () => {
  const ipn = extractNotification({ query: { topic: 'payment', id: '99' }, body: {} });
  assert.equal(ipn.topic, 'payment');
  assert.equal(ipn.id, '99');
  const body = extractNotification({
    query: {},
    body: { type: 'payment', action: 'payment.updated', data: { id: '88' } },
  });
  assert.equal(body.id, '88');
  const missing = extractNotification({ query: {}, body: {} });
  assert.equal(missing.id, '');
});

test('rota de preapproval existe e authorized de assinatura não é pagamento capturado', () => {
  const server = fs.readFileSync(path.join(__dirname, '..', 'server.js'), 'utf8');
  assert.match(server, /app\.post\('\/subscriptions\/preapproval'/);
  assert.equal(isPreapprovalSuccess({ status: 'authorized' }), true);
  assert.equal(isCardPaymentSuccess({ status: 'authorized' }), false);
  assert.equal(mapMpStatusToFinancial('authorized'), 'authorized');
});

test('referência de pagamento não autorizada e replay HMAC inválido não confirmam o pedido', async () => {
  const payload = amountPayload({ mp_payment_id: '111' });
  const updates = [];
  const pool = {
    query: async (sql, params) => {
      if (String(sql).includes('SELECT id, status, external_resource_id FROM orders WHERE id')) {
        return { rows: [{ id: params[0], status: 'PENDING', external_resource_id: JSON.stringify(payload) }] };
      }
      if (String(sql).includes('FOR UPDATE') || String(sql).includes('external_resource_id')) {
        if (params && params[1]) updates.push(typeof params[1] === 'string' ? JSON.parse(params[1]) : params[1]);
        return { rows: [{ id: 'ord-1', status: 'PENDING', external_resource_id: JSON.stringify(payload) }] };
      }
      if (String(sql).includes("SET status = 'PAID'")) {
        throw new Error('fulfill não deveria marcar PAID em referência não autorizada');
      }
      return { rows: [] };
    },
    connect: async () => ({
      query: async (sql, params) => pool.query(sql, params),
      release() {},
    }),
  };
  const result = await fulfillFromApprovedPayment(pool, 'secret', {
    id: 999,
    status: 'approved',
    external_reference: 'ord-1',
    transaction_amount: 70,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  });
  assert.equal(result.reason, 'unauthorized_payment_reference');
  assert.equal(result.order_confirmed, false);
  const replay = {
    method: 'POST',
    query: { 'data.id': '111' },
    body: { data: { id: '111' } },
    headers: { 'x-request-id': 'req-1', 'x-signature': 'ts=1,v1=deadbeef' },
    get(name) {
      return this.headers[String(name).toLowerCase()];
    },
  };
  assert.equal(verifyMercadoPagoWebhookSignature(replay, 'webhook-secret-test').ok, false);
});

test('precisão monetária recusa terceira casa e aceita centavos exactos', () => {
  assert.equal(mercadoPagoAmountToCents('70.00'), 7000);
  assert.equal(mercadoPagoAmountToCents(70), 7000);
  assert.throws(() => mercadoPagoAmountToCents('70.001'));
});

test('mismatch aprovado não confirma o pedido e não chama fulfill de status', async () => {
  const updates = [];
  const payload = amountPayload();
  const pool = {
    query: async (sql, params) => {
      if (String(sql).includes('SELECT id, status, external_resource_id FROM orders WHERE id')) {
        return { rows: [{ id: params[0], status: 'PENDING', external_resource_id: JSON.stringify(payload) }] };
      }
      if (String(sql).includes('FOR UPDATE') || String(sql).includes('external_resource_id')) {
        if (params && params[1]) updates.push(typeof params[1] === 'string' ? JSON.parse(params[1]) : params[1]);
        return { rows: [{ id: 'ord-1', status: 'PENDING', external_resource_id: JSON.stringify(payload) }] };
      }
      if (String(sql).includes("SET status = 'PAID'") && !String(sql).includes('external_resource_id')) {
        throw new Error('fulfill não deveria marcar PAID em mismatch');
      }
      return { rows: [] };
    },
    connect: async () => ({
      query: async (sql, params) => pool.query(sql, params),
      release() {},
    }),
  };
  const result = await fulfillFromApprovedPayment(pool, 'secret', {
    id: 111,
    status: 'approved',
    external_reference: 'ord-1',
    transaction_amount: 65,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  });
  assert.equal(result.reason, 'amount_mismatch');
  assert.equal(result.order_confirmed, false);
  assert.equal(updates.some((row) => row && row.paid_amount_cents === 6500), true);
});

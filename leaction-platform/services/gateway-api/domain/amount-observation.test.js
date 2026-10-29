const test = require('node:test');
const assert = require('node:assert/strict');
const { fulfillFromApprovedPayment, FINANCIAL_RETURN_VERSION } = require('./mp-webhooks');
const {
  applyProviderObservation,
  publicAmountOrder,
  paidCentsFromPayment,
} = require('./amount-checkout');

function basePayload() {
  return {
    source: 'amount_checkout',
    app_id: 'lojadepaes',
    amount_cents: 7000,
    currency: 'BRL',
    method: 'pix',
    mp_payment_id: '111',
    pix: { status: 'pending', mp_payment_id: '111', qr_code: 'x' },
  };
}

test('observação do provedor grava pago e estado do Pix sem alterar o cobrado', () => {
  const result = applyProviderObservation(basePayload(), {
    id: 111,
    status: 'approved',
    transaction_amount: 70,
    live_mode: true,
    date_last_updated: '2026-10-02T11:00:00.000Z',
  }, { paidAmountCents: 7000 });
  assert.equal(result.applied, true);
  assert.equal(result.payload.amount_cents, 7000);
  assert.equal(result.payload.paid_amount_cents, 7000);
  assert.equal(result.payload.pix.status, 'approved');
  assert.equal(result.payload.live_mode, true);
  assert.equal(result.payload.live_mode_source, 'mp_payment.live_mode');
});

test('callback antigo não sobrescreve observação mais recente', () => {
  const first = applyProviderObservation(basePayload(), {
    id: 111,
    status: 'approved',
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 7000 });
  const second = applyProviderObservation(first.payload, {
    id: 111,
    status: 'pending',
    date_last_updated: '2026-10-02T11:00:00.000Z',
  }, { paidAmountCents: 100 });
  assert.equal(second.applied, false);
  assert.equal(second.payload.pix.status, 'approved');
  assert.equal(second.payload.paid_amount_cents, 7000);
});

test('mismatch preserva valor observado e não inventa quitação no payload', () => {
  const result = applyProviderObservation(basePayload(), {
    id: 222,
    status: 'approved',
    date_last_updated: '2026-10-02T12:00:00.000Z',
  }, { paidAmountCents: 6500, mismatchReason: 'amount_mismatch' });
  assert.equal(result.payload.amount_cents, 7000);
  assert.equal(result.payload.paid_amount_cents, 6500);
  assert.equal(result.payload.amount_mismatch.reason, 'amount_mismatch');
  assert.equal(result.payload.amount_mismatch.observed_paid_amount_cents, 6500);
});

test('GET público distingue cobrado, pago ausente e Pix actualizado', () => {
  const pending = publicAmountOrder({ id: 'o1', status: 'PENDING' }, basePayload());
  assert.equal(pending.amount_cents, 7000);
  assert.equal(pending.paid_amount_cents, null);
  assert.equal(pending.paid_amount_absent, true);
  const paid = publicAmountOrder(
    { id: 'o1', status: 'PAID' },
    applyProviderObservation(basePayload(), {
      id: 111,
      status: 'approved',
      date_last_updated: '2026-10-02T12:00:00.000Z',
    }, { paidAmountCents: 7000 }).payload
  );
  assert.equal(paid.status, 'PAID');
  assert.equal(paid.paid_amount_cents, 7000);
  assert.equal(paid.pix.status, 'approved');
  const fromGateway = publicAmountOrder(
    { id: 'o1', status: 'PAID', gateway_reference: '185349985529' },
    { ...basePayload(), mp_payment_id: null, pix: {} }
  );
  assert.equal(fromGateway.mp_payment_id, '185349985529');
});

test('conversão MP recusa precisão inválida e aceita 70 reais', () => {
  assert.equal(paidCentsFromPayment({ transaction_amount: 70 }).cents, 7000);
  assert.equal(paidCentsFromPayment({ transaction_amount: '70.00' }).cents, 7000);
  assert.equal(paidCentsFromPayment({ transaction_amount: '70.001' }).ok, false);
  assert.equal(paidCentsFromPayment({}).ok, false);
});

test('fulfill amount_checkout não marca PAID em mismatch e não chama contrato', async () => {
  const updates = [];
  const payload = basePayload();
  const pool = {
    query: async (sql, params) => {
      if (String(sql).includes('SELECT id, status, external_resource_id FROM orders WHERE id')) {
        return { rows: [{ id: params[0], status: 'PENDING', external_resource_id: JSON.stringify(payload) }] };
      }
      if (String(sql).includes('FOR UPDATE')) {
        return { rows: [{ id: 'ord-1', status: 'PENDING', external_resource_id: JSON.stringify(payload) }] };
      }
      if (String(sql).includes('UPDATE orders SET external_resource_id') || String(sql).includes('external_resource_id = $2')) {
        updates.push(JSON.parse(params[1]));
        return { rows: [] };
      }
      if (String(sql).includes('INSERT INTO webhook_outbox')) {
        return { rows: [] };
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
  assert.equal(updates[0].amount_cents, 7000);
  assert.equal(updates[0].paid_amount_cents, 6500);
  assert.equal(updates[0].amount_mismatch.reason, 'amount_mismatch');
});

test('fulfill duplicado do checkout avulso não quebra e actualiza observação', async () => {
  const payload = applyProviderObservation(basePayload(), {
    id: 111,
    status: 'approved',
    date_last_updated: '2026-10-02T10:00:00.000Z',
  }, { paidAmountCents: 7000 }).payload;
  let fulfillUpdates = 0;
  const pool = {
    query: async (sql, params) => {
      if (String(sql).includes('SELECT id, status, external_resource_id FROM orders WHERE id = $1 LIMIT 1')) {
        return { rows: [{ id: params[0], status: 'PAID', external_resource_id: JSON.stringify(payload) }] };
      }
      if (String(sql).includes('FOR UPDATE')) {
        return { rows: [{ id: params[0], status: 'PAID', external_resource_id: JSON.stringify(payload) }] };
      }
      if (String(sql).includes('JOIN products')) {
        return {
          rows: [{
            id: params[0],
            status: 'PAID',
            product_type: 'AMOUNT_CHECKOUT',
            external_resource_id: JSON.stringify(payload),
            id_matu: JSON.stringify(payload),
          }],
        };
      }
      if (String(sql).includes("SET status = 'PAID'") && !String(sql).includes('external_resource_id')) {
        fulfillUpdates += 1;
        return { rows: [{ id: params[0], status: 'PAID' }] };
      }
      if (String(sql).includes('INSERT INTO webhook_outbox')) {
        return { rows: [] };
      }
      if (String(sql).includes('UPDATE orders SET external_resource_id')) {
        return { rows: [] };
      }
      return { rows: [] };
    },
    connect: async () => ({
      query: async (sql, params) => pool.query(sql, params),
      release() {},
    }),
  };
  const first = await fulfillFromApprovedPayment(pool, 'secret', {
    id: 111,
    status: 'approved',
    external_reference: 'ord-paid',
    transaction_amount: 70,
    live_mode: true,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  });
  const second = await fulfillFromApprovedPayment(pool, 'secret', {
    id: 111,
    status: 'approved',
    external_reference: 'ord-paid',
    transaction_amount: 70,
    live_mode: true,
    date_last_updated: '2026-10-02T12:00:00.000Z',
  });
  assert.equal(first.already_paid, true);
  assert.equal(second.already_paid, true);
  assert.equal(fulfillUpdates, 0);
});

test('versão de retorno do Hub é a confirmação durável', () => {
  assert.equal(FINANCIAL_RETURN_VERSION, 'hub-confirm-durable-20261028');
});

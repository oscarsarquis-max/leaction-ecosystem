const test = require('node:test');
const assert = require('node:assert/strict');
const {
  isRecurringCatalogPlan,
  recurringReady,
  isBibliotecaSku,
  subscriptionCopy,
} = require('./catalog-subscription');

const principal = {
  sku: 'LOJADEPAES_BIBLIOTECA_MENSAL',
  type: 'plan',
  price: 19,
  meta_json: {
    periodicidade: 'mensal',
    period_months: 1,
    checkout_mode: 'subscription',
    direitos: { assinatura: true, biblioteca: true, creditos: 20 },
  },
};

test('planos da Biblioteca são recorrentes mensais', () => {
  assert.equal(isBibliotecaSku(principal.sku), true);
  assert.equal(isRecurringCatalogPlan(principal), true);
  assert.equal(recurringReady(principal), true);
});

test('oferta inconsistente (sem recorrência pronta) não fica contratável', () => {
  const paused = {
    ...principal,
    meta_json: { ...principal.meta_json, recurring_ready: false },
  };
  assert.equal(recurringReady(paused), false);
});

test('pacote Inove não vira assinatura da Biblioteca', () => {
  assert.equal(
    isRecurringCatalogPlan({
      sku: 'INOVE4US_CREDITOS_100',
      type: 'credit_pack',
      price: 99,
      meta_json: { creditos: 100 },
    }),
    false
  );
});

test('SKU de créditos da Biblioteca não é recorrente mesmo com meta antiga', () => {
  assert.equal(
    isRecurringCatalogPlan({
      sku: 'LOJADEPAES_BIBLIOTECA_CREDITOS',
      type: 'plan',
      price: 10,
      meta_json: { checkout_mode: 'subscription', periodicidade: 'mensal', creditos: 10 },
    }),
    false
  );
  assert.equal(
    isRecurringCatalogPlan({
      sku: 'LOJADEPAES_BIBLIOTECA_CREDITOS',
      type: 'credit_pack',
      price: 10,
      meta_json: { creditos: 10 },
    }),
    false
  );
});

test('texto não trata ciclo único como assinatura', () => {
  const copy = subscriptionCopy(principal);
  assert.match(copy, /renovação automática/i);
  assert.match(copy, /pagamento confirmado/i);
  assert.match(copy, /Cancele/);
});

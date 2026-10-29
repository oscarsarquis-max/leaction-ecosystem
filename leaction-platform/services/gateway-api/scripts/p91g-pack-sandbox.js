'use strict';

const assert = require('node:assert/strict');
const { mergeEntitlement, viewCredits, isOneShotAiPack } = require('../domain/credits-ops');
const { isRecurringCatalogPlan } = require('../domain/catalog-subscription');

const PACK = {
  sku: 'LOJADEPAES_BIBLIOTECA_CREDITOS',
  type: 'credit_pack',
  price: 10,
  meta_json: { creditos: 10, checkout_mode: 'hub_brick' },
};

assert.equal(isOneShotAiPack(PACK, PACK.meta_json), true);
assert.equal(isRecurringCatalogPlan(PACK), false);

const first = mergeEntitlement({}, [{ item_type: 'credit_pack', sku: PACK.sku, quantity: 10 }], {
  sku: PACK.sku,
  credits: 10,
});
const view = viewCredits(first.payload, Date.now(), null);
assert.equal(first.payload.premium, false);
assert.equal(view.available, 10);
assert.equal(view.principalActive, false);
console.log(JSON.stringify({ ok: true, pack_credits: view.packCredits, premium: first.payload.premium }));

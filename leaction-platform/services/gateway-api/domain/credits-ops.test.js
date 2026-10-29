const test = require('node:test');
const assert = require('node:assert/strict');
const {
  classifyCatalogItemType,
  mergeEntitlement,
  viewCredits,
  nextOperationStatus,
} = require('./credits-ops');

const PRINCIPAL = 'LOJADEPAES_BIBLIOTECA_MENSAL';
const COMP = 'LOJADEPAES_BIBLIOTECA_CREDITOS';
const LEGACY = 'LOJADEPAES_BIBLIOTECA_COMPLEMENTAR';
const later = new Date(Date.now() + 20 * 24 * 3600 * 1000).toISOString();
const sooner = new Date(Date.now() + 10 * 24 * 3600 * 1000).toISOString();
const past = '2000-01-01T00:00:00.000Z';

test('plano mensal com 20 créditos não vira credit_pack', () => {
  assert.equal(classifyCatalogItemType('plan', PRINCIPAL, 20), 'plan');
  assert.equal(classifyCatalogItemType('credit_pack', 'INOVE4US_CREDITOS_100', 100), 'credit_pack');
  assert.equal(classifyCatalogItemType('', 'INOVE4US_CREDITOS_50', 50), 'credit_pack');
});

test('somente o principal ativo: renovação define 20', () => {
  const { payload, replaceValidUntil } = mergeEntitlement(
    {
      credits: 7,
      principal_credits: 7,
      complementary_credits: 0,
      premium: true,
      plan: { sku: PRINCIPAL, franchise: 20 },
    },
    [
      {
        item_type: 'plan',
        sku: PRINCIPAL,
        meta_json: { plano_nome: 'Biblioteca', periodicidade: 'mensal' },
      },
    ],
    { credits: 20, direitos: { biblioteca: true, assinatura: true } },
    later
  );
  assert.equal(payload.principal_credits, 20);
  assert.equal(payload.complementary_credits, 0);
  assert.equal(payload.credits, 20);
  assert.equal(payload.complementary, null);
  assert.equal(payload.plan.franchise, 20);
  assert.equal(payload.plan.cycle_ends_at, later);
  assert.equal(replaceValidUntil, true);
});

test('ambos ativos e só o principal renova: 20 novos + sobra do complementar', () => {
  const { payload } = mergeEntitlement(
    {
      credits: 10,
      principal_credits: 7,
      complementary_credits: 3,
      complementary: { sku: LEGACY, credits_granted: 10, remaining: 3, cycle_ends_at: sooner },
      premium: true,
      plan: { sku: PRINCIPAL, franchise: 20, cycle_ends_at: past },
    },
    [
      {
        item_type: 'plan',
        sku: PRINCIPAL,
        meta_json: { plano_nome: 'Biblioteca', periodicidade: 'mensal' },
      },
    ],
    { credits: 20, direitos: { biblioteca: true, assinatura: true } },
    later
  );
  assert.equal(payload.principal_credits, 20);
  assert.equal(payload.complementary_credits, 3);
  assert.equal(payload.credits, 23);
  assert.equal(payload.complementary.sku, LEGACY);
  assert.equal(payload.complementary.cycle_ends_at, sooner);
  assert.equal(payload.plan.cycle_ends_at, later);
});

test('ambos ativos e ambos renovados: 20 + 10 novos, sem sobras', () => {
  const prev = {
    credits: 10,
    principal_credits: 7,
    complementary_credits: 3,
    complementary: { sku: LEGACY, credits_granted: 10, remaining: 3, cycle_ends_at: sooner },
    premium: true,
    plan: { sku: PRINCIPAL, franchise: 20, cycle_ends_at: past },
  };
  const afterPrincipal = mergeEntitlement(
    prev,
    [
      {
        item_type: 'plan',
        sku: PRINCIPAL,
        meta_json: { plano_nome: 'Biblioteca', periodicidade: 'mensal' },
      },
    ],
    { credits: 20, direitos: { biblioteca: true, assinatura: true } },
    later
  );
  const afterBoth = mergeEntitlement(
    afterPrincipal.payload,
    [
      {
        item_type: 'plan',
        sku: LEGACY,
        quantity: 10,
        meta_json: { direitos: { papel: 'complementar' } },
      },
    ],
    { credits: 10, direitos: { papel: 'complementar', creditos: 10 } },
    sooner
  );
  assert.equal(afterBoth.payload.principal_credits, 20);
  assert.equal(afterBoth.payload.complementary_credits, 10);
  assert.equal(afterBoth.payload.credits, 30);
  assert.equal(afterBoth.replaceValidUntil, false);
  assert.equal(afterBoth.payload.complementary.cycle_ends_at, sooner);
});

test('complementar soma 10 sem trocar o plano nem o ciclo do principal', () => {
  const { payload, replaceValidUntil } = mergeEntitlement(
    {
      credits: 4,
      principal_credits: 4,
      complementary_credits: 0,
      premium: true,
      plan: { sku: PRINCIPAL, franchise: 20, cycle_ends_at: later },
    },
    [
      {
        item_type: 'plan',
        sku: LEGACY,
        quantity: 10,
        meta_json: { direitos: { papel: 'complementar' } },
      },
    ],
    { credits: 10, direitos: { papel: 'complementar', creditos: 10 } },
    sooner
  );
  assert.equal(payload.credits, 14);
  assert.equal(payload.principal_credits, 4);
  assert.equal(payload.complementary_credits, 10);
  assert.equal(payload.plan.sku, PRINCIPAL);
  assert.equal(payload.plan.cycle_ends_at, later);
  assert.equal(payload.complementary.sku, LEGACY);
  assert.equal(payload.complementary.credits_granted, 10);
  assert.equal(payload.complementary.cycle_ends_at, sooner);
  assert.equal(replaceValidUntil, false);
});

test('vencimentos distintos não exigem saldo 30 em qualquer instante', () => {
  const payload = {
    credits: 23,
    principal_credits: 20,
    complementary_credits: 3,
    plan: { sku: PRINCIPAL, cycle_ends_at: later },
    complementary: { sku: LEGACY, remaining: 3, cycle_ends_at: sooner },
  };
  const bothOpen = viewCredits(payload, Date.now(), later);
  assert.equal(bothOpen.available, 23);
  const afterComplementary = viewCredits(payload, new Date(sooner).getTime() + 1000, later);
  assert.equal(afterComplementary.available, 20);
  assert.equal(afterComplementary.complementaryActive, false);
  assert.equal(afterComplementary.principalActive, true);
  const afterPrincipal = viewCredits(payload, new Date(later).getTime() + 1000, later);
  assert.equal(afterPrincipal.available, 0);
  assert.equal(afterPrincipal.principalActive, false);
});

test('complementar expirado não gasta; sobra não some até o próprio ciclo', () => {
  const payload = {
    credits: 25,
    principal_credits: 20,
    complementary_credits: 5,
    plan: { sku: PRINCIPAL, cycle_ends_at: later },
    complementary: { sku: LEGACY, remaining: 5, cycle_ends_at: past },
  };
  const view = viewCredits(payload, Date.now(), later);
  assert.equal(view.available, 20);
  assert.equal(view.complementaryCredits, 0);
  assert.equal(payload.complementary_credits, 5);
});

test('pacote avulso da Biblioteca soma sem virar ciclo complementar', () => {
  const { payload, replaceValidUntil } = mergeEntitlement(
    {
      credits: 4,
      principal_credits: 4,
      complementary_credits: 0,
      premium: true,
      plan: { sku: PRINCIPAL, franchise: 20, cycle_ends_at: later },
    },
    [{ item_type: 'credit_pack', sku: COMP, quantity: 10 }],
    { credits: 10, sku: COMP }
  );
  assert.equal(payload.credits, 14);
  assert.equal(payload.principal_credits, 4);
  assert.equal(payload.pack_credits, 10);
  assert.equal(payload.complementary, null);
  assert.equal(payload.premium, true);
  assert.equal(replaceValidUntil, false);
  assert.equal(payload.plan.cycle_ends_at, later);
});

test('segunda compra consciente do pacote soma de novo, sem expiração inventada', () => {
  const first = mergeEntitlement(
    { credits: 0 },
    [{ item_type: 'credit_pack', sku: COMP, quantity: 10 }],
    { credits: 10, sku: COMP }
  );
  const second = mergeEntitlement(
    first.payload,
    [{ item_type: 'credit_pack', sku: COMP, quantity: 10 }],
    { credits: 10, sku: COMP }
  );
  assert.equal(second.payload.pack_credits, 20);
  assert.equal(second.payload.credits, 20);
  assert.equal(second.payload.premium, false);
  assert.equal(second.replaceValidUntil, false);
});

test('reserva do pacote avulso não exige assinatura vigente', () => {
  const { payload } = mergeEntitlement(
    {},
    [{ item_type: 'credit_pack', sku: COMP, quantity: 10 }],
    { credits: 10, sku: COMP }
  );
  const view = viewCredits(payload, Date.now(), null);
  const { canReserveCredits } = require('./credits-ops');
  assert.equal(canReserveCredits(view, 1).ok, true);
  assert.equal(canReserveCredits(view, 11).error, 'insufficient_credits');
  const empty = viewCredits({ plan: { sku: PRINCIPAL, cycle_ends_at: '2020-01-01T00:00:00Z' } }, Date.now(), '2020-01-01T00:00:00Z');
  assert.equal(canReserveCredits(empty, 1).error, 'expired');
});

test('pacote isolado não concede assinatura e continua visível sem principal', () => {
  const { payload } = mergeEntitlement(
    {},
    [{ item_type: 'credit_pack', sku: COMP, quantity: 10 }],
    { credits: 10, sku: COMP }
  );
  const view = viewCredits(payload, Date.now(), null);
  assert.equal(payload.premium, false);
  assert.equal(view.principalActive, false);
  assert.equal(view.packCredits, 10);
  assert.equal(view.available, 10);
});

test('pacote Inove continua somando', () => {
  const { payload } = mergeEntitlement(
    { credits: 5 },
    [{ item_type: 'credit_pack', sku: 'INOVE4US_CREDITOS_100', quantity: 100 }],
    { credits: 100 }
  );
  assert.equal(payload.credits, 105);
  assert.equal(payload.principal_credits, undefined);
});

test('reserva e confirmação são idempotentes; confirmado não libera', () => {
  assert.deepEqual(nextOperationStatus(null, 'reserve'), {
    ok: true,
    status: 'reserved',
    apply: true,
  });
  assert.equal(nextOperationStatus('reserved', 'reserve').idempotent, true);
  assert.equal(nextOperationStatus('confirmed', 'confirm').idempotent, true);
  assert.equal(nextOperationStatus('confirmed', 'release').ok, false);
  assert.equal(nextOperationStatus('released', 'confirm').ok, false);
});

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  extractAppId,
  sanitizeStatus,
  timingSafeEqual,
  lookupEnabled,
  isIsolatedLookup,
  ordersRelation,
  isProvenSandbox,
  ISOLATED_ORDERS_SCHEMA,
  publicLookup,
  publicListItem,
  amountMinorForList,
  currencyOf,
  encodeListCursor,
  decodeListCursor,
  normalizeListEnvironment,
  parseListLimit,
  listOrderSql,
  MAX_LIST_LIMIT,
} = require('./spider-pay-lookup');

test('rota permanece desligada por padrão mesmo com secret', () => {
  assert.equal(lookupEnabled({ ACTIONHUB_PAY_PROVIDER_SECRET: 'x' }), false);
  assert.equal(lookupEnabled({ ACTIONHUB_PAY_LOOKUP_ENABLED: 'true' }), false);
  assert.equal(
    lookupEnabled({ ACTIONHUB_PAY_LOOKUP_ENABLED: 'true', ACTIONHUB_PAY_LOOKUP_ISOLATED: 'true' }),
    true
  );
  assert.equal(
    lookupEnabled({ ACTIONHUB_PAY_LOOKUP_ENABLED: 'true', ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST: 'true' }),
    true
  );
});

test('não extrai aplicativo pelo nome comercial', () => {
  assert.equal(extractAppId({ gateway_ref: 'hub:homolog-padaria:abc', external_resource_id: '{}' }), 'homolog-padaria');
  assert.equal(extractAppId({ gateway_ref: '', external_resource_id: '{"app_id":"homolog-padaria"}' }), 'homolog-padaria');
  assert.equal(extractAppId({ gateway_ref: 'outro', external_resource_id: 'Loja de Pães' }), null);
});

test('sandbox só com metadado confiável ou schema isolado declarado', () => {
  assert.equal(isProvenSandbox({ external_resource_id: '{}' }, {}), false);
  assert.equal(isProvenSandbox({ external_resource_id: '{"sandbox":true}' }, {}), true);
  assert.equal(
    isProvenSandbox({ external_resource_id: '{}' }, { ACTIONHUB_PAY_LOOKUP_ISOLATED: 'true' }),
    true
  );
  assert.equal(isIsolatedLookup({}), false);
  assert.equal(isIsolatedLookup({ ACTIONHUB_PAY_LOOKUP_ISOLATED: 'true' }), true);
  assert.equal(ordersRelation({}), 'public.orders');
  assert.equal(ordersRelation({ ACTIONHUB_PAY_LOOKUP_ISOLATED: 'true' }), `${ISOLATED_ORDERS_SCHEMA}.orders`);
  assert.notEqual(ordersRelation({ ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST: 'true' }), `${ISOLATED_ORDERS_SCHEMA}.orders`);
});

test('publicLookup não marca sandbox sem prova', () => {
  const body = publicLookup({ id: 'o1', status: 'PAID', external_resource_id: '{"amount_cents":12550}' });
  assert.equal(body.result.sandbox, false);
  assert.equal(body.result.amountMinor, '12550');
  assert.equal(sanitizeStatus({ status: 'REFUNDED' }).externalStatus, 'REFUNDED');
});

test('compara segredo em tempo constante e recusa vazio', () => {
  assert.equal(timingSafeEqual('abc', 'abc'), true);
  assert.equal(timingSafeEqual('abc', 'abd'), false);
  assert.equal(timingSafeEqual('', 'abc'), false);
});

test('listagem usa amount_cents do checkout avulso e não inventa zero', () => {
  const checkout = amountMinorForList({
    external_resource_id: '{"amount_cents":12550,"app_id":"homolog-padaria"}',
  });
  assert.equal(checkout.amountMinor, '12550');
  assert.equal(checkout.amountSource, 'amount_cents');
  assert.equal(checkout.reviewRequired, false);
});

test('listagem converte valor_negociado em reais só com precisão de centavos', () => {
  const subscription = amountMinorForList({ external_resource_id: '{"valor_negociado":99.5}' });
  assert.equal(subscription.amountMinor, '9950');
  assert.equal(subscription.amountSource, 'valor_negociado_brl');
  const absent = amountMinorForList({ external_resource_id: '{}' });
  assert.equal(absent.amountMinor, null);
  assert.equal(absent.reviewRequired, true);
  const imprecise = amountMinorForList({ external_resource_id: '{"valor_negociado":10.001}' });
  assert.equal(imprecise.amountMinor, null);
  assert.equal(imprecise.reviewRequired, true);
});

test('listagem não inventa moeda BRL nem timestamp', () => {
  const item = publicListItem({
    id: 'o2',
    status: 'PAID',
    gateway_reference: 'mp-abc',
    external_resource_id: '{"amount_cents":100}',
    created_at: null,
    updated_at: null,
  });
  assert.equal(item.currency, null);
  assert.equal(item.createdAt, null);
  assert.equal(item.updatedAt, null);
  assert.equal(item.processorReference, 'mp-abc');
  assert.equal(item.orderReference, 'o2');
  assert.equal(item.amountAbsent, false);
  assert.equal(currencyOf({ external_resource_id: '{"currency_id":"brl"}' }), 'BRL');
});

test('cursor opaco rejeita outro aplicativo ou ambiente', () => {
  const cursor = encodeListCursor({
    appId: 'homolog-padaria',
    environment: 'HOMOLOG',
    updatedAt: '2026-10-01T12:00:00.000Z',
    id: '11111111-1111-4111-a111-111111111111',
  });
  assert.equal(decodeListCursor(cursor, 'homolog-padaria', 'HOMOLOG').ok, true);
  assert.equal(decodeListCursor(cursor, 'outro-app', 'HOMOLOG').ok, false);
  assert.equal(decodeListCursor(cursor, 'homolog-padaria', 'SANDBOX').ok, false);
  assert.equal(normalizeListEnvironment('sandbox'), 'SANDBOX');
  assert.equal(normalizeListEnvironment('prod'), null);
  assert.equal(parseListLimit('51'), null);
  assert.equal(parseListLimit('10'), 10);
  assert.equal(MAX_LIST_LIMIT, 50);
});

test('ORDER BY e cursor usam o mesmo date_trunc de milissegundo', () => {
  assert.match(listOrderSql(), /date_trunc\('milliseconds', updated_at\) ASC/);
  assert.match(listOrderSql(), /id::text ASC/);
});

test('cursor compara timestamp no milissegundo para não repetir a página', () => {
  const cursor = encodeListCursor({
    appId: 'homolog-padaria',
    environment: 'HOMOLOG',
    updatedAt: '2026-10-01T18:23:51.774Z',
    id: '20000000-0000-4000-8000-000000030025',
  });
  const decoded = decodeListCursor(cursor, 'homolog-padaria', 'HOMOLOG');
  assert.equal(decoded.ok, true);
  assert.equal(decoded.cursor.id, '20000000-0000-4000-8000-000000030025');
  assert.equal(decoded.cursor.updatedAt.toISOString(), '2026-10-01T18:23:51.774Z');
});

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  extractAppId,
  sanitizeStatus,
  timingSafeEqual,
  lookupEnabled,
  isIsolatedLookup,
  isOperationalApp,
  classifyOrder,
  classifyOrderDetail,
  queryPaymentList,
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
  providedProviderSecret,
  validateProviderListEnvelope,
  completedProviderList,
  registerSpiderPayLookupRoutes,
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
  assert.equal(
    lookupEnabled({ ACTIONHUB_PAY_LOOKUP_ENABLED: 'true', ACTIONHUB_PAY_LOOKUP_OPERATIONAL: 'true' }),
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
  assert.equal(
    ordersRelation(
      {
        ACTIONHUB_PAY_LOOKUP_ISOLATED: 'true',
        ACTIONHUB_PAY_LOOKUP_OPERATIONAL: 'true',
        ACTIONHUB_PAY_OPERATIONAL_APP_IDS: 'lojadepaes',
      },
      'lojadepaes'
    ),
    'public.orders'
  );
  assert.equal(
    ordersRelation(
      {
        ACTIONHUB_PAY_LOOKUP_ISOLATED: 'true',
        ACTIONHUB_PAY_LOOKUP_OPERATIONAL: 'true',
        ACTIONHUB_PAY_OPERATIONAL_APP_IDS: 'lojadepaes',
      },
      'af-public-test-padaria'
    ),
    `${ISOLATED_ORDERS_SCHEMA}.orders`
  );
  assert.equal(
    isOperationalApp({ ACTIONHUB_PAY_LOOKUP_OPERATIONAL: 'true', ACTIONHUB_PAY_OPERATIONAL_APP_IDS: 'lojadepaes' }, 'lojadepaes'),
    true
  );
  assert.equal(
    classifyOrder({ gateway_ref: 'amount:lojadepaes:1', external_resource_id: '{"app_id":"lojadepaes"}' }),
    'INDETERMINATE'
  );
  assert.equal(
    classifyOrder({
      gateway_ref: 'amount:lojadepaes:1',
      external_resource_id: '{"app_id":"lojadepaes","mp_payment_id":"123","payment_request_id":"pr-1"}',
    }),
    'INDETERMINATE'
  );
  assert.equal(
    classifyOrder({
      gateway_ref: 'amount:lojadepaes:1',
      external_resource_id: '{"app_id":"lojadepaes","live_mode":true}',
    }),
    'REAL'
  );
  assert.equal(
    classifyOrder({ gateway_ref: 'hub:x:1', external_resource_id: '{"app_id":"x","sandbox":true}' }),
    'TEST'
  );
  assert.equal(
    classifyOrderDetail({
      gateway_ref: 'amount:lojadepaes:1',
      external_resource_id: '{"app_id":"lojadepaes"}',
    }).reason.includes('não comprovam ambiente'),
    true
  );
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

test('listagem expõe pagador, aplicação e método persistidos sem inventar pago', () => {
  const item = publicListItem({
    id: 'o-90',
    status: 'PAID',
    payer_email: 'cliente@exemplo.test',
    product_name: 'Consulta avulsa',
    gateway_reference: '1234567890',
    external_resource_id: JSON.stringify({
      amount_cents: 9000,
      paid_amount_cents: 9000,
      paid_amount_confirmed: true,
      method: 'pix',
      app_id: 'lojadepaes',
      plano_nome: 'Consulta avulsa',
      live_mode: true,
      mp_payment_id: 'mp-1',
      provider_status: 'approved',
    }),
    created_at: '2026-10-06T12:00:00.000Z',
    updated_at: '2026-10-06T12:00:00.000Z',
  });
  assert.equal(item.transactionId, 'o-90');
  assert.equal(item.amountMinor, '9000');
  assert.equal(item.paidAmountMinor, '9000');
  assert.equal(item.paidAmountAbsent, false);
  assert.equal(item.payerKind, 'EMAIL');
  assert.equal(item.payerLabel, 'cliente@exemplo.test');
  assert.equal(item.payerProvenance, 'ACTIONHUB_PAY');
  assert.equal(item.commercialApplication, 'lojadepaes');
  assert.equal(item.commercialDescription, 'Consulta avulsa');
  assert.equal(item.paymentMethod, 'pix');
  assert.equal(item.processorName, 'Mercado Pago');
  assert.equal(item.providerStatus, 'approved');
  const unconfirmed = publicListItem({
    id: 'o-pending',
    status: 'PENDING',
    external_resource_id: '{"amount_cents":9000,"paid_amount_cents":9000,"method":"pix"}',
    created_at: '2026-10-06T12:00:00.000Z',
    updated_at: '2026-10-06T12:00:00.000Z',
  });
  assert.equal(unconfirmed.paidAmountMinor, undefined);
  assert.equal(Object.hasOwn(unconfirmed, 'paidAmountAbsent'), false);
  assert.equal(unconfirmed.amountMinor, '9000');
});

test('listagem não substitui valor cobrado pelo pago', () => {
  const item = publicListItem({
    id: 'o-paid-only',
    status: 'PAID',
    external_resource_id: '{"paid_amount_cents":6500,"paid_amount_confirmed":true,"method":"pix"}',
    created_at: '2026-10-01T12:00:00.000Z',
    updated_at: '2026-10-01T12:00:00.000Z',
  });
  assert.equal(item.amountMinor, null);
  assert.equal(item.chargedAmountMinor, null);
  assert.equal(item.amountAbsent, true);
  assert.equal(item.paidAmountMinor, '6500');
  assert.equal(item.paidAmountAbsent, false);
  const both = publicListItem({
    id: 'o-both',
    status: 'PAID',
    external_resource_id: '{"amount_cents":7000,"paid_amount_cents":6500,"paid_amount_confirmed":true}',
    created_at: '2026-10-01T12:00:00.000Z',
    updated_at: '2026-10-01T12:00:00.000Z',
  });
  assert.equal(both.chargedAmountMinor, '7000');
  assert.equal(both.paidAmountMinor, '6500');
  assert.equal(both.amountMinor, '7000');
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
  assert.equal(normalizeListEnvironment('production'), 'PRODUCTION');
  assert.equal(normalizeListEnvironment('prod'), null);
  assert.equal(parseListLimit('51'), null);
  assert.equal(parseListLimit('10'), 10);
  assert.equal(MAX_LIST_LIMIT, 50);
});

test('ORDER BY e cursor usam o mesmo date_trunc de milissegundo', () => {
  assert.match(listOrderSql(), /date_trunc\('milliseconds', updated_at\) ASC/);
  assert.match(listOrderSql(), /id::text ASC/);
});

test('envelope do provedor 1.4 recusa contrato ou capacidade errada', () => {
  assert.equal(validateProviderListEnvelope(null), 'payload inválido');
  assert.equal(
    validateProviderListEnvelope({
      contractVersion: '1.3',
      capabilityId: 'LIST_PAYMENT_TRANSACTIONS',
      requestId: 'r1',
      correlationId: 'c1',
      inputs: { payAppId: 'af-public-test-padaria', companyId: 'co', environment: 'HOMOLOG' },
    }),
    'contrato 1.4 obrigatório'
  );
  assert.equal(
    validateProviderListEnvelope({
      contractVersion: '1.4',
      capabilityId: 'LIST_PAYMENT_TRANSACTIONS',
      requestId: 'r1',
      correlationId: 'c1',
      inputs: { payAppId: 'af-public-test-padaria', companyId: 'co', environment: 'HOMOLOG' },
    }),
    null
  );
  assert.equal(
    validateProviderListEnvelope({
      contractVersion: '1.4',
      capabilityId: 'LIST_PAYMENT_TRANSACTIONS',
      requestId: 'r1',
      correlationId: 'c1',
      inputs: { payAppId: 'lojadepaes', companyId: 'co', environment: 'PRODUCTION' },
    }),
    null
  );
});

test('aceita a credencial da Spider no header da borda ou do Hub', () => {
  assert.equal(
    providedProviderSecret({ get: (name) => (name === 'X-ActionHub-Pay-Credential' ? 'edge-secret' : '') }),
    'edge-secret'
  );
  assert.equal(
    providedProviderSecret({ get: (name) => (name === 'X-Spider-Provider-Key' ? 'hub-secret' : '') }),
    'hub-secret'
  );
});

test('completedProviderList preserva identidade e não inventa READY', () => {
  const body = {
    requestId: 'req-1',
    correlationId: 'afp-1',
    inputs: {
      companyId: '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c',
      payAppId: 'af-public-test-padaria',
      environment: 'HOMOLOG',
    },
  };
  const listed = completedProviderList(body, {
    origin: 'ACTIONHUB_PAY',
    testLabeled: true,
    items: [{ transactionId: '9c2e0a10-4f11-4b8a-9c2e-0a104f110101', amountMinor: '12550' }],
    nextCursor: null,
  });
  assert.equal(listed.status, 'COMPLETED');
  assert.equal(listed.providerId, 'actionhub-pay');
  assert.equal(listed.capabilityId, 'LIST_PAYMENT_TRANSACTIONS');
  assert.equal(listed.result.itemCount, 1);
  assert.equal(listed.result.items[0].transactionId, '9c2e0a10-4f11-4b8a-9c2e-0a104f110101');
});

test('POST da capability devolve a listagem isolada e recusa sem credencial', async () => {
  const express = require('express');
  const http = require('http');
  const rows = [
    {
      id: '9c2e0a10-4f11-4b8a-9c2e-0a104f110101',
      status: 'PAID',
      gateway_ref: 'hub:af-public-test-padaria:001',
      gateway_reference: 'prm009-synthetic-001',
      external_resource_id: '{"app_id":"af-public-test-padaria","amount_cents":12550,"currency":"BRL"}',
      created_at: new Date('2026-10-01T15:00:00Z'),
      updated_at: new Date('2026-10-01T15:00:01Z'),
    },
  ];
  const app = express();
  app.use(express.json());
  registerSpiderPayLookupRoutes(app, { query: async () => ({ rows }) }, {
    env: {
      ACTIONHUB_PAY_LOOKUP_ENABLED: 'true',
      ACTIONHUB_PAY_LOOKUP_ISOLATED: 'true',
      ACTIONHUB_PAY_PROVIDER_SECRET: 'hub-secret',
    },
    providerSecret: 'hub-secret',
  });
  const server = await new Promise((resolve) => {
    const started = app.listen(0, '127.0.0.1', () => resolve(started));
  });
  const port = server.address().port;
  const payload = JSON.stringify({
    contractVersion: '1.4',
    requestId: 'req-1',
    correlationId: 'afp-1',
    capabilityId: 'LIST_PAYMENT_TRANSACTIONS',
    inputs: {
      payAppId: 'af-public-test-padaria',
      companyId: '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c',
      environment: 'HOMOLOG',
      limit: 10,
    },
  });
  const call = (headers) =>
    new Promise((resolve, reject) => {
      const req = http.request(
        {
          hostname: '127.0.0.1',
          port,
          path: '/v1/provider/capabilities/LIST_PAYMENT_TRANSACTIONS/executions',
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload), ...headers },
        },
        (res) => {
          const chunks = [];
          res.on('data', (chunk) => chunks.push(chunk));
          res.on('end', () =>
            resolve({ status: res.statusCode, body: JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}') })
          );
        }
      );
      req.on('error', reject);
      req.end(payload);
    });
  try {
    const denied = await call({});
    assert.equal(denied.status, 401);
    const allowed = await call({ 'X-ActionHub-Pay-Credential': 'hub-secret' });
    assert.equal(allowed.status, 200);
    assert.equal(allowed.body.status, 'COMPLETED');
    assert.equal(allowed.body.result.itemCount, 1);
    assert.equal(allowed.body.result.items[0].transactionId, '9c2e0a10-4f11-4b8a-9c2e-0a104f110101');
    assert.equal(allowed.body.result.payAppId, 'af-public-test-padaria');
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test('listagem operacional não encerra após excluídos e devolve revisão fora dos totais', async () => {
  const rows = [
    {
      id: '10000000-0000-4000-8000-000000000001',
      status: 'PAID',
      gateway_ref: 'amount:lojadepaes:1',
      gateway_reference: null,
      external_resource_id: '{"app_id":"lojadepaes","sandbox":true,"amount_cents":100}',
      created_at: new Date('2026-10-01T10:00:00.000Z'),
      updated_at: new Date('2026-10-01T10:00:00.000Z'),
    },
    {
      id: '10000000-0000-4000-8000-000000000002',
      status: 'PENDING',
      gateway_ref: 'amount:lojadepaes:2',
      gateway_reference: null,
      external_resource_id: '{"app_id":"lojadepaes","amount_cents":200,"mp_payment_id":"mp-2"}',
      created_at: new Date('2026-10-01T10:00:01.000Z'),
      updated_at: new Date('2026-10-01T10:00:01.000Z'),
    },
    {
      id: '10000000-0000-4000-8000-000000000003',
      status: 'CANCELLED',
      gateway_ref: 'amount:lojadepaes:3',
      gateway_reference: null,
      external_resource_id: '{"app_id":"lojadepaes","amount_cents":300,"live_mode":true}',
      created_at: new Date('2026-10-01T10:00:02.000Z'),
      updated_at: new Date('2026-10-01T10:00:02.000Z'),
    },
    {
      id: '10000000-0000-4000-8000-000000000004',
      status: 'PAID',
      gateway_ref: 'amount:lojadepaes:4',
      gateway_reference: null,
      external_resource_id: '{"app_id":"lojadepaes","amount_cents":400,"live_mode":true}',
      created_at: new Date('2026-10-01T10:00:03.000Z'),
      updated_at: new Date('2026-10-01T10:00:03.000Z'),
    },
  ];
  const pool = {
    query: async (sql, params) => {
      const match = sql.match(/LIMIT (\d+)/);
      const take = match ? Number(match[1]) : rows.length;
      let start = 0;
      if (params && params.length >= 3) {
        const cursorId = String(params[2]);
        const index = rows.findIndex((row) => String(row.id) === cursorId);
        start = index >= 0 ? index + 1 : 0;
      }
      return { rows: rows.slice(start, start + take) };
    },
  };
  const env = {
    ACTIONHUB_PAY_LOOKUP_OPERATIONAL: 'true',
    ACTIONHUB_PAY_OPERATIONAL_APP_IDS: 'lojadepaes',
  };
  const listed = await queryPaymentList(pool, env, 'lojadepaes', 'PRODUCTION', 1, null);
  assert.equal(listed.httpStatus, 200);
  assert.equal(listed.items.length, 1);
  assert.equal(listed.items[0].transactionId, '10000000-0000-4000-8000-000000000003');
  assert.equal(listed.items[0].classification, 'REAL');
  assert.equal(listed.items[0].originalStatus, 'CANCELLED');
  assert.equal(listed.reviews.length, 2);
  assert.equal(listed.reviews[0].classification, 'TEST');
  assert.equal(listed.reviews[1].classification, 'INDETERMINATE');
  assert.equal(listed.reviews[1].originalStatus, 'PENDING');
  assert.ok(listed.nextCursor);
  const second = await queryPaymentList(pool, env, 'lojadepaes', 'PRODUCTION', 1, listed.nextCursor);
  assert.equal(second.items.length, 1);
  assert.equal(second.items[0].transactionId, '10000000-0000-4000-8000-000000000004');
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

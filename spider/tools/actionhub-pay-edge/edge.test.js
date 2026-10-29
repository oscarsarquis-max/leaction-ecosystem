const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const { EventEmitter } = require('events');
const { resolveMode, validateEnvelope, handleExecution, completed } = require('./edge');

test('SIMULATOR e FORWARD são exclusivos', () => {
  assert.equal(resolveMode({}).mode, 'SIMULATOR');
  assert.throws(() => resolveMode({ ACTIONHUB_PAY_EDGE_MODE: 'SIMULATOR', ACTIONHUB_PAY_BASE_URL: 'https://pay.example' }));
  assert.throws(() => resolveMode({ ACTIONHUB_PAY_BASE_URL: 'https://pay.example' }));
  assert.equal(resolveMode({ ACTIONHUB_PAY_EDGE_MODE: 'FORWARD', ACTIONHUB_PAY_BASE_URL: 'https://pay.example' }).mode, 'FORWARD');
});

test('listagem 1.4 exige ambiente e recusa simulador no lugar do Hub', async () => {
  assert.equal(
    validateEnvelope({
      contractVersion: '1.4',
      requestId: 'preq-list',
      correlationId: 'afc-list',
      capabilityId: 'LIST_PAYMENT_TRANSACTIONS',
      inputs: {
        payAppId: 'homolog-padaria',
        companyId: '11111111-1111-4111-a111-111111111111',
        environment: 'HOMOLOG',
      },
    }),
    null
  );
  const env = { ACTIONHUB_PAY_EDGE_MODE: 'SIMULATOR', SPIDER_ACTIONHUB_PAY_EDGE_SECRET: 'segredo' };
  const outcome = await handleExecution(env, requestList('segredo'), new Map());
  assert.equal(outcome.httpStatus, 404);
  assert.match(String(outcome.body.error || ''), /Hub|listagem/i);
});

test('envelope exige contrato, correlação e binding', () => {
  assert.match(validateEnvelope({}), /1\.3/);
  assert.equal(
    validateEnvelope({
      contractVersion: '1.3',
      requestId: 'preq-1',
      correlationId: 'afc-1',
      capabilityId: 'LOOKUP_ACTIONHUB_PAYMENT',
      inputs: { payAppId: 'homolog-padaria', companyId: '11111111-1111-4111-a111-111111111111', externalReference: 'pay-homolog-0001' },
    }),
    null
  );
});

test('SIMULATOR identifica origem e não confirma referência desconhecida', async () => {
  const env = { ACTIONHUB_PAY_EDGE_MODE: 'SIMULATOR', SPIDER_ACTIONHUB_PAY_EDGE_SECRET: 'segredo' };
  const counts = new Map();
  const found = await handleExecution(env, requestFor('pay-homolog-0001', 'segredo'), counts);
  assert.equal(found.httpStatus, 200);
  assert.equal(found.body.result.origin, 'SIMULATOR');
  assert.equal(found.body.result.sandbox, true);
  assert.equal(found.body.correlationId, 'afc-corr-1');
  const missing = await handleExecution(env, requestFor('pay-ausente-xxxx', 'segredo'), counts);
  assert.equal(missing.httpStatus, 404);
  assert.notEqual(missing.body.result && missing.body.result.externalStatus, 'CONFIRMED');
});

test('FORWARD 404/401/500/corpo inválido/timeout não usa fixture', async () => {
  const upstream = await listenStub((req, res) => {
    if (req.url.endsWith('/missing')) {
      res.writeHead(404);
      res.end('{}');
      return;
    }
    if (req.url.endsWith('/denied')) {
      res.writeHead(401);
      res.end('{}');
      return;
    }
    if (req.url.endsWith('/boom')) {
      res.writeHead(500);
      res.end('{}');
      return;
    }
    if (req.url.endsWith('/bad')) {
      res.writeHead(200);
      res.end('{not-json');
      return;
    }
    if (req.url.endsWith('/slow')) {
      return;
    }
  });
  try {
    const env = {
      ACTIONHUB_PAY_EDGE_MODE: 'FORWARD',
      ACTIONHUB_PAY_BASE_URL: upstream.url,
      ACTIONHUB_PAY_PROVIDER_SECRET: 'pay',
      SPIDER_ACTIONHUB_PAY_EDGE_SECRET: 'segredo',
    };
    for (const [ref, code] of [
      ['missing', 404],
      ['denied', 401],
      ['boom', 502],
      ['bad', 502],
    ]) {
      const outcome = await handleExecution(env, requestFor(ref, 'segredo'), new Map());
      assert.equal(outcome.httpStatus, code, ref);
      assert.notEqual(outcome.body.result && outcome.body.result.origin, 'SIMULATOR');
      assert.notEqual(outcome.body.status, 'COMPLETED');
    }
    const timed = await handleExecution(env, requestFor('slow', 'segredo'), new Map());
    assert.equal(timed.body.errorCode, 'TIMEOUT');
    assert.notEqual(timed.body.result && timed.body.result.externalStatus, 'CONFIRMED');
  } finally {
    await upstream.close();
  }
});

test('FORWARD só marca ACTIONHUB_PAY com resposta válida de sandbox', async () => {
  const upstream = await listenStub((req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'COMPLETED',
      providerId: 'actionhub-pay',
      result: {
        providerReference: 'pay-homolog-0001',
        externalStatus: 'CONFIRMED',
        deliveryStatus: 'DELIVERED',
        amountMinor: '12550',
        currency: 'BRL',
        sandbox: true,
      },
    }));
  });
  try {
    const env = {
      ACTIONHUB_PAY_EDGE_MODE: 'FORWARD',
      ACTIONHUB_PAY_BASE_URL: upstream.url,
      ACTIONHUB_PAY_PROVIDER_SECRET: 'pay',
      SPIDER_ACTIONHUB_PAY_EDGE_SECRET: 'segredo',
    };
    const outcome = await handleExecution(env, requestFor('pay-homolog-0001', 'segredo'), new Map());
    assert.equal(outcome.httpStatus, 200);
    assert.equal(outcome.body.result.origin, 'ACTIONHUB_PAY');
    assert.equal(outcome.body.correlationId, 'afc-corr-1');
    assert.equal(outcome.body.requestId, 'preq-1');
  } finally {
    await upstream.close();
  }
});

test('FORWARD remoto em HTTP é recusado; HTTPS usa o módulo TLS e falha tipada', async () => {
  const envHttp = {
    ACTIONHUB_PAY_EDGE_MODE: 'FORWARD',
    ACTIONHUB_PAY_BASE_URL: 'http://example.test',
    ACTIONHUB_PAY_PROVIDER_SECRET: 'pay',
    SPIDER_ACTIONHUB_PAY_EDGE_SECRET: 'segredo',
  };
  const insecure = await handleExecution(envHttp, requestFor('pay-homolog-0001', 'segredo'), new Map());
  assert.equal(insecure.body.errorCode, 'INSECURE_TARGET');
  assert.notEqual(insecure.body.status, 'COMPLETED');

  const envTls = {
    ACTIONHUB_PAY_EDGE_MODE: 'FORWARD',
    ACTIONHUB_PAY_BASE_URL: 'https://127.0.0.1:1',
    ACTIONHUB_PAY_PROVIDER_SECRET: 'pay',
    SPIDER_ACTIONHUB_PAY_EDGE_SECRET: 'segredo',
  };
  const outcome = await handleExecution(envTls, requestFor('pay-homolog-0001', 'segredo'), new Map());
  assert.notEqual(outcome.body.status, 'COMPLETED');
  assert.notEqual(outcome.body.result && outcome.body.result.origin, 'SIMULATOR');
  assert.ok(outcome.body.errorCode === 'UPSTREAM_ERROR' || outcome.body.errorCode === 'TIMEOUT');
});

test('completed preserva correlação e não inventa origem', () => {
  const body = {
    requestId: 'preq-1',
    correlationId: 'afc-9',
    inputs: { externalReference: 'pay-homolog-0001', payAppId: 'homolog-padaria', companyId: 'c1' },
  };
  const payload = completed(body, FIXTURE_CONFIRMED(), 'SIMULATOR', true);
  assert.equal(payload.correlationId, 'afc-9');
  assert.equal(payload.result.origin, 'SIMULATOR');
  assert.equal(payload.result.amountMinor, '12550');
});

function FIXTURE_CONFIRMED() {
  return { externalStatus: 'CONFIRMED', deliveryStatus: 'DELIVERED', amountMinor: '12550', currency: 'BRL' };
}

function requestList(secret) {
  const req = new EventEmitter();
  req.headers = { 'x-actionhub-pay-credential': secret };
  req.destroy = () => {};
  process.nextTick(() => {
    req.emit(
      'data',
      Buffer.from(JSON.stringify({
        contractVersion: '1.4',
        requestId: 'preq-list',
        correlationId: 'afc-list',
        capabilityId: 'LIST_PAYMENT_TRANSACTIONS',
        inputs: {
          payAppId: 'homolog-padaria',
          companyId: '11111111-1111-4111-a111-111111111111',
          environment: 'HOMOLOG',
        },
      }))
    );
    req.emit('end');
  });
  return req;
}

function requestFor(reference, secret) {
  const req = new EventEmitter();
  req.headers = { 'x-actionhub-pay-credential': secret };
  req.destroy = () => {};
  process.nextTick(() => {
    req.emit(
      'data',
      Buffer.from(JSON.stringify({
        contractVersion: '1.3',
        requestId: 'preq-1',
        correlationId: 'afc-corr-1',
        capabilityId: 'LOOKUP_ACTIONHUB_PAYMENT',
        inputs: {
          payAppId: 'homolog-padaria',
          companyId: '11111111-1111-4111-a111-111111111111',
          externalReference: reference,
        },
      }))
    );
    req.emit('end');
  });
  return req;
}

function listenStub(handler) {
  return new Promise((resolve) => {
    const server = http.createServer(handler);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve({
        url: `http://127.0.0.1:${port}`,
        close: () => new Promise((done) => server.close(done)),
      });
    });
  });
}

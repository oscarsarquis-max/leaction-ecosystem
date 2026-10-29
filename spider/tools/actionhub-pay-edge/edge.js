/**
 * Borda PROVIDER isolada. Modos SIMULATOR e FORWARD são exclusivos.
 * FORWARD nunca cai em fixture. HTTPS valida certificado. Sem desligar TLS.
 */
const http = require('http');
const https = require('https');
const { timingSafeEqual } = require('crypto');

const MAX_BODY = 8192;
const LIST_MAX_BODY = 65536;
const FORWARD_TIMEOUT_MS = 3000;

const FIXTURES = {
  'pay-homolog-0001': {
    externalStatus: 'CONFIRMED',
    deliveryStatus: 'DELIVERED',
    amountMinor: '12550',
    currency: 'BRL',
    sandbox: true,
  },
  'pay-homolog-pending': {
    externalStatus: 'IN_PROGRESS',
    deliveryStatus: 'DELIVERED',
    amountMinor: '8900',
    currency: 'BRL',
    sandbox: true,
  },
  'pay-homolog-refunded': {
    externalStatus: 'REFUNDED',
    deliveryStatus: 'DELIVERED',
    amountMinor: '12550',
    currency: 'BRL',
    sandbox: true,
  },
};

function resolveMode(env) {
  const explicit = String(env.ACTIONHUB_PAY_EDGE_MODE || '').toUpperCase();
  const payBase = String(env.ACTIONHUB_PAY_BASE_URL || '').replace(/\/$/, '');
  if (explicit === 'FORWARD') {
    if (!payBase) {
      throw new Error('FORWARD exige ACTIONHUB_PAY_BASE_URL');
    }
    return { mode: 'FORWARD', payBase };
  }
  if (explicit === 'SIMULATOR') {
    if (payBase) {
      throw new Error('SIMULATOR não admite ACTIONHUB_PAY_BASE_URL');
    }
    return { mode: 'SIMULATOR', payBase: '' };
  }
  if (payBase) {
    throw new Error('defina ACTIONHUB_PAY_EDGE_MODE=FORWARD ou remova ACTIONHUB_PAY_BASE_URL');
  }
  return { mode: 'SIMULATOR', payBase: '' };
}

function equal(expected, provided) {
  if (!expected || !provided) return false;
  const a = Buffer.from(String(expected));
  const b = Buffer.from(String(provided));
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

function readLimitedBody(req, maxBytes) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > maxBytes) {
        reject(Object.assign(new Error('payload excedido'), { code: 'PAYLOAD_TOO_LARGE' }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}'));
      } catch (error) {
        reject(error);
      }
    });
    req.on('error', reject);
  });
}

function validateEnvelope(body) {
  if (!body || typeof body !== 'object') {
    return 'payload inválido';
  }
  const inputs = body.inputs || {};
  if (body.capabilityId === 'LIST_PAYMENT_TRANSACTIONS') {
    if (body.contractVersion !== '1.4') {
      return 'contrato 1.4 obrigatório';
    }
    if (!inputs.payAppId || !inputs.companyId || !inputs.environment) {
      return 'empresa, aplicativo ou ambiente não autorizados pela Spider';
    }
    if (!body.requestId || !body.correlationId) {
      return 'requestId e correlationId obrigatórios';
    }
    if (inputs.environment !== 'HOMOLOG' && inputs.environment !== 'SANDBOX' && inputs.environment !== 'PRODUCTION') {
      return 'ambiente incompatível';
    }
    return null;
  }
  if (body.contractVersion !== '1.3') {
    return 'contrato 1.3 obrigatório';
  }
  if (!body.requestId || !body.correlationId) {
    return 'requestId e correlationId obrigatórios';
  }
  if (body.capabilityId !== 'LOOKUP_ACTIONHUB_PAYMENT') {
    return 'capacidade não autorizada';
  }
  if (!inputs.payAppId || !inputs.companyId || !inputs.externalReference) {
    return 'empresa ou aplicativo não autorizados pela Spider';
  }
  return null;
}

function completed(body, result, origin, sandbox) {
  return {
    status: 'COMPLETED',
    providerId: 'actionhub-pay',
    requestId: body.requestId,
    correlationId: body.correlationId,
    capabilityId: 'LOOKUP_ACTIONHUB_PAYMENT',
    result: {
      providerReference: String(body.inputs.externalReference),
      payAppId: String(body.inputs.payAppId),
      companyId: String(body.inputs.companyId),
      externalStatus: result.externalStatus,
      deliveryStatus: result.deliveryStatus,
      amountMinor: result.amountMinor == null ? null : String(result.amountMinor),
      currency: result.currency || 'BRL',
      sandbox: sandbox === true,
      origin,
      providerObservedAt: result.providerObservedAt || null,
    },
  };
}

function typedFailure(code, httpStatus, detail) {
  return {
    httpStatus,
    body: {
      status: 'FAILED',
      providerId: 'actionhub-pay',
      errorCode: code,
      error: detail,
    },
  };
}

function completedList(body, result) {
  return {
    status: 'COMPLETED',
    providerId: 'actionhub-pay',
    requestId: body.requestId,
    correlationId: body.correlationId,
    capabilityId: 'LIST_PAYMENT_TRANSACTIONS',
    result: {
      companyId: String(body.inputs.companyId),
      payAppId: String(body.inputs.payAppId),
      environment: String(body.inputs.environment),
      origin: result.origin || 'ACTIONHUB_PAY',
      testLabeled: result.testLabeled === true,
      itemCount: Array.isArray(result.items) ? result.items.length : 0,
      reviewCount: Array.isArray(result.reviews) ? result.reviews.length : 0,
      nextCursor: result.nextCursor || null,
      items: Array.isArray(result.items) ? result.items : [],
      reviews: Array.isArray(result.reviews) ? result.reviews : [],
    },
  };
}

function listPay(env, inputs, correlationId) {
  const { payBase } = resolveMode(env);
  const secret = env.ACTIONHUB_PAY_PROVIDER_SECRET || '';
  return new Promise((resolve) => {
    let url;
    try {
      url = new URL('/v1/integration/payments', payBase);
      url.searchParams.set('environment', inputs.environment || 'HOMOLOG');
      if (inputs.limit) url.searchParams.set('limit', String(inputs.limit));
      if (inputs.cursor) url.searchParams.set('cursor', String(inputs.cursor));
    } catch {
      resolve({ ok: false, failure: typedFailure('INVALID_TARGET', 503, 'URL de encaminhamento inválida') });
      return;
    }
    if (url.protocol !== 'https:' && url.protocol !== 'http:') {
      resolve({ ok: false, failure: typedFailure('INVALID_TARGET', 503, 'protocolo não suportado') });
      return;
    }
    if (url.protocol === 'http:' && url.hostname !== '127.0.0.1' && url.hostname !== 'localhost') {
      resolve({ ok: false, failure: typedFailure('INSECURE_TARGET', 503, 'FORWARD remoto exige HTTPS') });
      return;
    }
    const transport = url.protocol === 'https:' ? https : http;
    const req = transport.request(
      url,
      {
        method: 'GET',
        rejectUnauthorized: true,
        headers: {
          'X-Spider-Provider-Key': secret,
          'X-Pay-App-Id': inputs.payAppId || '',
          'X-Correlation-ID': correlationId || '',
        },
      },
      (res) => {
        const chunks = [];
        let size = 0;
        res.on('data', (chunk) => {
          size += chunk.length;
          if (size > LIST_MAX_BODY) {
            req.destroy();
            resolve({ ok: false, failure: typedFailure('PAYLOAD_TOO_LARGE', 502, 'resposta do Pay excedeu o limite') });
          }
          chunks.push(chunk);
        });
        res.on('end', () => {
          if (res.statusCode === 401 || res.statusCode === 403) {
            resolve({ ok: false, failure: typedFailure('FORBIDDEN', res.statusCode, 'Pay recusou o escopo') });
            return;
          }
          if (res.statusCode >= 500) {
            resolve({ ok: false, failure: typedFailure('UPSTREAM', 502, 'Pay indisponível') });
            return;
          }
          try {
            const payload = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
            if (!payload || payload.status !== 'COMPLETED' || !Array.isArray(payload.items)) {
              resolve({ ok: false, failure: typedFailure('IDENTITY_MISMATCH', 502, 'listagem do Pay não confere') });
              return;
            }
            resolve({ ok: true, payload });
          } catch {
            resolve({ ok: false, failure: typedFailure('IDENTITY_MISMATCH', 502, 'resposta do Pay inválida') });
          }
        });
      }
    );
    req.on('error', () => resolve({ ok: false, failure: typedFailure('UPSTREAM', 502, 'Pay indisponível') }));
    req.setTimeout(FORWARD_TIMEOUT_MS, () => {
      req.destroy();
      resolve({ ok: false, failure: typedFailure('TIMEOUT', 504, 'Pay não respondeu') });
    });
    req.end();
  });
}

function lookupPay(env, inputs, correlationId) {
  const { payBase } = resolveMode(env);
  const secret = env.ACTIONHUB_PAY_PROVIDER_SECRET || '';
  return new Promise((resolve) => {
    let url;
    try {
      url = new URL(`/v1/integration/payments/${encodeURIComponent(inputs.externalReference)}`, payBase);
    } catch {
      resolve({ ok: false, failure: typedFailure('INVALID_TARGET', 503, 'URL de encaminhamento inválida') });
      return;
    }
    if (url.protocol !== 'https:' && url.protocol !== 'http:') {
      resolve({ ok: false, failure: typedFailure('INVALID_TARGET', 503, 'protocolo não suportado') });
      return;
    }
    if (url.protocol === 'http:' && url.hostname !== '127.0.0.1' && url.hostname !== 'localhost') {
      resolve({ ok: false, failure: typedFailure('INSECURE_TARGET', 503, 'FORWARD remoto exige HTTPS') });
      return;
    }
    const transport = url.protocol === 'https:' ? https : http;
    const req = transport.request(
      url,
      {
        method: 'GET',
        rejectUnauthorized: true,
        headers: {
          'X-Spider-Provider-Key': secret,
          'X-Pay-App-Id': inputs.payAppId || '',
          'X-Correlation-ID': correlationId || '',
        },
      },
      (res) => {
        const chunks = [];
        let size = 0;
        res.on('data', (chunk) => {
          size += chunk.length;
          if (size > MAX_BODY) {
            req.destroy();
            resolve({ ok: false, failure: typedFailure('PAYLOAD_TOO_LARGE', 502, 'corpo do Pay excedido') });
          } else {
            chunks.push(chunk);
          }
        });
        res.on('end', () => {
          if (res.statusCode === 404) {
            resolve({ ok: false, failure: typedFailure('NOT_FOUND', 404, 'pagamento de teste não encontrado') });
            return;
          }
          if (res.statusCode === 401 || res.statusCode === 403) {
            resolve({ ok: false, failure: typedFailure('UNAUTHORIZED', res.statusCode, 'Pay recusou a credencial') });
            return;
          }
          if (res.statusCode !== 200) {
            resolve({ ok: false, failure: typedFailure('UPSTREAM_ERROR', 502, 'Pay não devolveu resultado utilizável') });
            return;
          }
          try {
            const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8'));
            if (!parsed || parsed.status !== 'COMPLETED' || !parsed.result) {
              resolve({ ok: false, failure: typedFailure('INVALID_BODY', 502, 'corpo do Pay inválido') });
              return;
            }
            resolve({ ok: true, payload: parsed });
          } catch {
            resolve({ ok: false, failure: typedFailure('INVALID_BODY', 502, 'corpo do Pay inválido') });
          }
        });
      }
    );
    req.setTimeout(FORWARD_TIMEOUT_MS, () => {
      req.destroy();
      resolve({ ok: false, failure: typedFailure('TIMEOUT', 504, 'timeout no encaminhamento ao Pay') });
    });
    req.on('error', () => {
      resolve({ ok: false, failure: typedFailure('UPSTREAM_ERROR', 502, 'falha de transporte no encaminhamento') });
    });
    req.end();
  });
}

function handleHealth(env, counts) {
  const resolved = resolveMode(env);
  return { status: 'UP', mode: resolved.mode, counts: Object.fromEntries(counts) };
}

function runtimeMaps(env, runtime) {
  const overrides =
      runtime && runtime.overrides instanceof Map
          ? runtime.overrides
          : env.__overrides instanceof Map
            ? env.__overrides
            : new Map();
  const failures =
      runtime && runtime.failures instanceof Map
          ? runtime.failures
          : env.__failures instanceof Map
            ? env.__failures
            : new Map();
  return { overrides, failures };
}

async function handleExecution(env, req, counts, runtime) {
  const secret = env.SPIDER_ACTIONHUB_PAY_EDGE_SECRET || '';
  if (!equal(secret, req.headers['x-actionhub-pay-credential'])) {
    return { httpStatus: 401, body: { error: 'credencial de provedor inválida' } };
  }
  let body;
  try {
    body = await readLimitedBody(req, MAX_BODY);
  } catch (error) {
    if (error.code === 'PAYLOAD_TOO_LARGE') {
      return { httpStatus: 413, body: { error: 'payload excedido' } };
    }
    return { httpStatus: 400, body: { error: 'payload inválido' } };
  }
  const invalid = validateEnvelope(body);
  if (invalid) {
    return { httpStatus: invalid.includes('autorizad') || invalid.includes('ambiente') ? 403 : 400, body: { error: invalid } };
  }
  const resolved = resolveMode(env);
  const inputs = body.inputs;
  if (body.capabilityId === 'LIST_PAYMENT_TRANSACTIONS') {
    const listKey = `${inputs.payAppId}:list:${inputs.environment}`;
    counts.set(listKey, (counts.get(listKey) || 0) + 1);
    if (runtime.listFailAfter != null && counts.get(listKey) > runtime.listFailAfter) {
      return typedFailure('UPSTREAM', 503, 'Pay indisponível');
    }
    if (env.ACTIONHUB_PAY_EDGE_DROP_FIRST === '1' && !env.__dropped) {
      env.__dropped = true;
      return { drop: true };
    }
    if (resolved.mode === 'FORWARD') {
      const forwarded = await listPay(env, inputs, body.correlationId);
      if (!forwarded.ok) {
        return forwarded.failure;
      }
      return { httpStatus: 200, body: completedList(body, forwarded.payload) };
    }
    return typedFailure('NOT_FOUND', 404, 'listagem simulada não substitui o Hub');
  }
  const key = `${inputs.payAppId}:${inputs.externalReference}`;
  counts.set(key, (counts.get(key) || 0) + 1);
  if (env.ACTIONHUB_PAY_EDGE_DROP_FIRST === '1' && !env.__dropped) {
    env.__dropped = true;
    return { drop: true };
  }
  if (resolved.mode === 'FORWARD') {
    const forwarded = await lookupPay(env, { ...inputs, correlationId: body.correlationId }, body.correlationId);
    if (!forwarded.ok) {
      return forwarded.failure;
    }
    const result = forwarded.payload.result;
    if (result.sandbox !== true) {
      return typedFailure('NOT_SANDBOX', 403, 'consulta bloqueada: ambiente de teste não comprovado');
    }
    if (String(result.providerReference) !== String(inputs.externalReference)) {
      return typedFailure('IDENTITY_MISMATCH', 502, 'referência do Pay não confere');
    }
    return {
      httpStatus: 200,
      body: completed(body, result, 'ACTIONHUB_PAY', true),
    };
  }
  const { overrides, failures } = runtimeMaps(env, runtime);
  const failure = failures.get(inputs.externalReference);
  if (failure) {
    return typedFailure(failure.code || 'UNAVAILABLE', failure.httpStatus || 503, failure.detail || 'simulador indisponível');
  }
  const fixture = overrides.get(inputs.externalReference) || FIXTURES[inputs.externalReference];
  if (!fixture) {
    return typedFailure('NOT_FOUND', 404, 'pagamento de demonstração não encontrado');
  }
  return {
    httpStatus: 200,
    body: completed(body, fixture, 'SIMULATOR', true),
  };
}

function testControlEnabled(env, req) {
  if (env.ACTIONHUB_PAY_EDGE_TEST_CONTROL !== '1') {
    return false;
  }
  const host = String(req.socket && req.socket.remoteAddress || '');
  return host === '127.0.0.1' || host === '::1' || host === ':ffff:127.0.0.1';
}

function createServer(env) {
  resolveMode(env);
  const runtime = { overrides: new Map(), failures: new Map(), listFailAfter: null };
  const counts = new Map();
  return http.createServer(async (req, res) => {
    const json = (status, payload) => {
      const raw = JSON.stringify(payload);
      res.writeHead(status, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(raw) });
      res.end(raw);
    };
    try {
      if (req.method === 'GET' && req.url === '/health') {
        json(200, handleHealth(env, counts));
        return;
      }
      if (testControlEnabled(env, req) && req.method === 'GET' && req.url === '/__test/counts') {
        json(200, { counts: Object.fromEntries(counts), mode: resolveMode(env).mode });
        return;
      }
      if (testControlEnabled(env, req) && req.method === 'POST' && req.url === '/__test/reset-counts') {
        counts.clear();
        runtime.listFailAfter = null;
        json(200, { reset: true, mode: resolveMode(env).mode });
        return;
      }
      if (testControlEnabled(env, req) && req.method === 'PUT' && req.url === '/__test/list-fail-after') {
        const payload = await readLimitedBody(req, MAX_BODY);
        runtime.listFailAfter =
          payload && payload.after == null ? null : Number(payload && payload.after);
        if (runtime.listFailAfter != null && !Number.isInteger(runtime.listFailAfter)) {
          json(400, { error: 'after inválido' });
          return;
        }
        json(200, { listFailAfter: runtime.listFailAfter, mode: resolveMode(env).mode });
        return;
      }
      if (testControlEnabled(env, req) && req.method === 'PUT' && req.url && req.url.startsWith('/__test/fixtures/')) {
        const ref = decodeURIComponent(req.url.slice('/__test/fixtures/'.length));
        const payload = await readLimitedBody(req, MAX_BODY);
        if (payload.fail) {
          runtime.failures.set(
            ref,
            typeof payload.fail === 'string'
              ? { code: payload.fail, httpStatus: 503, detail: 'simulador indisponível' }
              : payload.fail
          );
          runtime.overrides.delete(ref);
        } else {
          runtime.failures.delete(ref);
          runtime.overrides.set(ref, payload);
        }
        json(200, { reference: ref, applied: true });
        return;
      }
      const listPath = '/v1/provider/capabilities/LIST_PAYMENT_TRANSACTIONS/executions';
      const lookupPath = '/v1/provider/capabilities/LOOKUP_ACTIONHUB_PAYMENT/executions';
      if (req.method !== 'POST' || (req.url !== lookupPath && req.url !== listPath)) {
        json(404, { error: 'not found' });
        return;
      }
      const outcome = await handleExecution(env, req, counts, runtime);
      if (outcome.drop) {
        req.socket.destroy();
        return;
      }
      json(outcome.httpStatus, outcome.body);
    } catch (error) {
      json(500, { error: 'borda indisponível', detail: error.message });
    }
  });
}

module.exports = {
  FIXTURES,
  resolveMode,
  validateEnvelope,
  completed,
  completedList,
  typedFailure,
  handleExecution,
  handleHealth,
  createServer,
  MAX_BODY,
  LIST_MAX_BODY,
};

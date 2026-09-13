import { createHash, timingSafeEqual } from 'node:crypto';

const WATERMARK =
  'DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO';
export const MAX_BYTES = 8192;
const PROVIDER_ID = 'insurance-provider-mock';
const LEGACY_PROVIDER_ID = 'SEGSENSE_PROVIDER_MOCK';
const ORIGIN = 'ILLUSTRATIVE_NOT_ICATU_CONTRACT';
const SUPPORTED = 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO';

export async function handleRequest(req, res, options) {
  const url = new URL(req.url || '/', 'http://127.0.0.1');
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString('utf8');
  const result = processDemoRequest({
    method: req.method,
    path: url.pathname,
    headers: req.headers,
    raw,
  }, options);
  if (result.delayMs) {
    await new Promise((resolve) => setTimeout(resolve, result.delayMs));
  }
  res.statusCode = result.status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(result.body));
}

export function processDemoRequest(input, options) {
  if (input.method === 'GET' && input.path === '/health') {
    return {
      status: 200,
      body: { status: 'ok', providerId: LEGACY_PROVIDER_ID, testDouble: true, satelliteRole: 'PROVIDER_TEST_DOUBLE' },
    };
  }
  const capabilityMatch = input.path.match(/^\/v1\/provider\/capabilities\/([^/]+)\/executions$/);
  if (input.method === 'POST' && capabilityMatch) {
    return processProviderContract(input, options, capabilityMatch[1]);
  }
  if (input.method !== 'POST' || input.path !== '/v1/illustrative-protection-items') {
    return { status: 404, body: { code: 'NOT_FOUND', message: 'Recurso inexistente.' } };
  }
  return processLegacy(input, options);
}

function processProviderContract(input, options, capabilityId) {
  const auth = authenticate(input, options);
  if (auth) {
    return auth;
  }
  const forced = force(input);
  if (forced) {
    return forced;
  }
  if ((input.raw || '').length > MAX_BYTES) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Payload excede o limite.', retryable: false } };
  }
  let body;
  try {
    body = JSON.parse(input.raw || '{}');
  } catch {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'JSON inválido.', retryable: false } };
  }
  if (capabilityId !== SUPPORTED) {
    return { status: 400, body: { errorCode: 'CAPABILITY_NOT_AVAILABLE', message: 'Capability não suportada.', retryable: false } };
  }
  if (
    body.contractVersion !== '1.0' ||
    body.capabilityId !== SUPPORTED ||
    body.purpose !== 'INSURANCE_PROTECTION_ASSESSMENT' ||
    !body.inputs ||
    body.inputs.scenarioKey !== 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1' ||
    typeof body.requestId !== 'string' ||
    typeof body.correlationId !== 'string' ||
    typeof body.decisionId !== 'string'
  ) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Pedido de capability inválido.', retryable: false } };
  }
  if (body.originSnapshot || body.objective || body.intent || body.executionPlan) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Payload excede a minimização da capability.', retryable: false } };
  }
  return {
    status: 200,
    body: {
      requestId: body.requestId,
      correlationId: body.correlationId,
      capabilityId: SUPPORTED,
      providerId: PROVIDER_ID,
      status: 'COMPLETED',
      result: illustrativeResult(),
      reasonCodes: [],
      executedAt: '2026-09-13T12:00:00Z',
      providerReference: `ill-${crypto.randomUUID()}`,
    },
  };
}

function processLegacy(input, options) {
  const auth = authenticate(input, options);
  if (auth) {
    return auth;
  }
  const forced = force(input);
  if (forced) {
    return forced;
  }
  if ((input.raw || '').length > MAX_BYTES) {
    return { status: 400, body: { code: 'VALIDATION_ERROR', message: 'Payload excede o limite.' } };
  }
  let body;
  try {
    body = JSON.parse(input.raw || '{}');
  } catch {
    return { status: 400, body: { code: 'VALIDATION_ERROR', message: 'JSON inválido.' } };
  }
  if (
    body.contractVersion !== 'segsense-mock-contract-v1' ||
    body.scenarioKey !== 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1' ||
    body.declaredObjective !== 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS' ||
    typeof body.decisionId !== 'string' ||
    typeof body.correlationId !== 'string'
  ) {
    return { status: 400, body: { code: 'VALIDATION_ERROR', message: 'Pedido ilustrativo inválido.' } };
  }
  const result = illustrativeResult();
  return {
    status: 200,
    body: {
      providerId: LEGACY_PROVIDER_ID,
      origin: ORIGIN,
      resultId: `ill-${crypto.randomUUID()}`,
      watermark: WATERMARK,
      items: result.items,
      pendingForBroker: result.pendingForHumanReview,
    },
  };
}

function illustrativeResult() {
  return {
    kind: 'ILLUSTRATIVE_PROTECTION_SCENARIO',
    origin: ORIGIN,
    testDouble: true,
    watermark: WATERMARK,
    items: [
      {
        code: 'ILLUSTRATIVE_FAMILY_CONTEXT_REVIEW',
        title: 'Revisar o contexto familiar declarado no cenário sintético',
        kind: 'JOURNEY_STEP',
        notOfferable: true,
      },
      {
        code: 'ILLUSTRATIVE_BROKER_HANDOFF',
        title: 'Encaminhar pendências à corretora e à seguradora autorizadas',
        kind: 'JOURNEY_STEP',
        notOfferable: true,
      },
    ],
    pendingForHumanReview: [
      'Confirmar com a seguradora autorizada se existe produto adequado.',
      'Não há cotação, capital, prêmio ou emissão neste artefato.',
    ],
  };
}

function authenticate(input, options) {
  const provided = header(input.headers, 'x-segsense-mock-credential');
  if (!secretsEqual(provided, options.credential)) {
    return { status: 401, body: { errorCode: 'UNAUTHENTICATED', code: 'AUTHENTICATION_REQUIRED', message: 'Autenticação de serviço necessária.', retryable: false } };
  }
  return null;
}

function force(input) {
  const forceHeader = header(input.headers, 'x-segsense-mock-force');
  if (forceHeader === 'timeout') {
    return { status: 200, delayMs: 4000, body: { code: 'TIMEOUT' } };
  }
  if (forceHeader === 'unavailable') {
    return { status: 503, body: { errorCode: 'PROVIDER_UNAVAILABLE', code: 'UNAVAILABLE', message: 'Provedor ilustrativo indisponível.', retryable: true } };
  }
  return null;
}

function secretsEqual(provided, expected) {
  const left = createHash('sha256').update(String(provided ?? ''), 'utf8').digest();
  const right = createHash('sha256').update(String(expected ?? ''), 'utf8').digest();
  return timingSafeEqual(left, right);
}

function header(headers, name) {
  const value = headers[name];
  return Array.isArray(value) ? value[0] : value;
}

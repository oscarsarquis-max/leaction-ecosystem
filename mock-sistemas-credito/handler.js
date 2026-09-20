import { createHash, timingSafeEqual } from 'node:crypto';

export const CAPABILITY = 'SIMULATE_WORKING_CAPITAL';
export const VERSION = 'credit-mock/0.1';
export const VERSION_ASSESSMENT = 'credit-mock/0.2';
export const PROVIDER_ID = 'credit-provider-mock';
export const MAX_BYTES = 8192;
export const WATERMARK = 'SIMULAÇÃO ILUSTRATIVA — SEM VALOR COMERCIAL — NÃO É OFERTA, APROVAÇÃO OU CONTRATAÇÃO';
export const ASSESSMENT_CAPABILITIES = [
  'GET_CUSTOMER_PROFILE',
  'CHECK_CUSTOMER_REGISTRATION',
  'GET_CREDIT_PROFILE',
  'FIND_ELIGIBLE_PRODUCTS',
];
const SIMULATE_SCENARIOS = ['SUCCESS', 'MISSING_CONTEXT', 'REJECTED', 'HUMAN_REVIEW', 'UNAVAILABLE'];
const ASSESSMENT_SCENARIOS = [...SIMULATE_SCENARIOS, 'PENDING_REGISTRATION', 'NO_PROFILE', 'INELIGIBLE'];
const SUBJECT = /^cust-demo-[a-z0-9-]{2,40}$/;
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const exact = (value, keys) => object(value) && Object.keys(value).every((key) => keys.includes(key));
const id = (value) => typeof value === 'string' && /^[A-Za-z0-9_-]{8,80}$/.test(value);
const error = (status, errorCode, retryable = false) => ({
  status,
  body: { errorCode, retryable, testDouble: true, boundary: 'MOCK_ONLY', watermark: WATERMARK },
});

function authenticated(actual, expected) {
  if (typeof actual !== 'string' || typeof expected !== 'string' || expected.length < 16) return false;
  return timingSafeEqual(createHash('sha256').update(actual).digest(), createHash('sha256').update(expected).digest());
}

function envelope(body, capabilityId, version, status, result, reasonCodes) {
  return {
    status: 200,
    body: {
      contractVersion: version,
      requestId: body.requestId,
      correlationId: body.correlationId,
      capabilityId,
      providerId: PROVIDER_ID,
      status,
      result,
      reasonCodes,
      executedAt: new Date().toISOString(),
      providerReference: 'mock-' + createHash('sha256').update(JSON.stringify(body)).digest('hex').slice(0, 32),
    },
  };
}

function baseResult(kind) {
  return {
    kind,
    origin: 'NON_BINDING_DEMO',
    testDouble: true,
    boundary: 'MOCK_ONLY',
    watermark: WATERMARK,
    offerable: false,
    ruleVersion: 'DEMO_FIXTURE_V1',
  };
}

function simulate(body) {
  const keys = [
    'contractVersion',
    'requestId',
    'correlationId',
    'decisionId',
    'capabilityId',
    'capabilityVersion',
    'purpose',
    'inputs',
    'dataClassification',
    'requestedAt',
    'callback',
  ];
  if (
    !exact(body, keys) ||
    body.contractVersion !== VERSION ||
    body.capabilityId !== CAPABILITY ||
    body.capabilityVersion !== '1.0' ||
    body.purpose !== 'WORKING_CAPITAL_SIMULATION' ||
    !['PUBLIC', 'INTERNAL'].includes(body.dataClassification) ||
    ![body.requestId, body.correlationId, body.decisionId].every(id) ||
    typeof body.requestedAt !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/.test(body.requestedAt) ||
    !Number.isFinite(Date.parse(body.requestedAt)) ||
    (body.callback !== undefined && body.callback !== null) ||
    !exact(body.inputs, ['scenarioKey', 'principalCents', 'termMonths']) ||
    !SIMULATE_SCENARIOS.includes(body.inputs.scenarioKey)
  ) {
    return error(400, 'INVALID_PAYLOAD');
  }
  const { scenarioKey, principalCents, termMonths } = body.inputs;
  if (
    (principalCents !== undefined &&
      (!Number.isSafeInteger(principalCents) || principalCents < 10000 || principalCents > 100000000)) ||
    (termMonths !== undefined && (!Number.isInteger(termMonths) || termMonths < 1 || termMonths > 36))
  ) {
    return error(400, 'INVALID_PAYLOAD');
  }
  if (scenarioKey === 'UNAVAILABLE') return error(503, 'PROVIDER_UNAVAILABLE', true);
  const result = baseResult('SYNTHETIC_WORKING_CAPITAL_SIMULATION');
  let status = 'COMPLETED';
  let reasonCodes = [];
  if (scenarioKey === 'MISSING_CONTEXT' || principalCents === undefined || termMonths === undefined) {
    status = 'PENDING';
    reasonCodes = ['MISSING_CONTEXT'];
    result.missingFields = [principalCents === undefined && 'principalCents', termMonths === undefined && 'termMonths'].filter(
      Boolean,
    );
    if (!result.missingFields.length) result.missingFields = ['syntheticSupportingContext'];
  } else if (scenarioKey === 'REJECTED') {
    status = 'REJECTED';
    reasonCodes = ['SYNTHETIC_SCENARIO_REJECTED'];
  } else if (scenarioKey === 'HUMAN_REVIEW') {
    status = 'PENDING';
    reasonCodes = ['SYNTHETIC_HUMAN_REVIEW'];
    result.reviewQueued = false;
  } else {
    const monthlyRateBps = 100;
    const interestCents = Math.round((principalCents * monthlyRateBps * termMonths) / 10000);
    const totalCents = principalCents + interestCents;
    const base = Math.floor(totalCents / termMonths);
    Object.assign(result, {
      currency: 'BRL',
      principalCents,
      termMonths,
      monthlyRateBps,
      interestCents,
      totalCents,
      calculationRule: 'SIMPLE_INTEREST_SYNTHETIC_V1',
      installmentsCents: Array.from({ length: termMonths }, (_, i) => base + (i < totalCents % termMonths ? 1 : 0)),
      premises: [
        'Taxa fictícia de teste; sem calibração de mercado.',
        'Juros simples sobre o principal durante todo o prazo; não representa tabela Price ou SAC.',
        'Tributos, tarifas, garantias e CET não são calculados. Não constitui avaliação de risco.',
      ],
    });
  }
  return envelope(body, CAPABILITY, VERSION, status, result, reasonCodes);
}

function assess(capabilityId, body) {
  const keys = [
    'contractVersion',
    'requestId',
    'correlationId',
    'decisionId',
    'capabilityId',
    'capabilityVersion',
    'purpose',
    'inputs',
    'dataClassification',
    'requestedAt',
    'callback',
  ];
  if (
    !exact(body, keys) ||
    body.contractVersion !== VERSION_ASSESSMENT ||
    body.capabilityId !== capabilityId ||
    body.capabilityVersion !== '1.0' ||
    body.purpose !== 'WORKING_CAPITAL_ASSESSMENT' ||
    !['PUBLIC', 'INTERNAL'].includes(body.dataClassification) ||
    ![body.requestId, body.correlationId, body.decisionId].every(id) ||
    typeof body.requestedAt !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/.test(body.requestedAt) ||
    !Number.isFinite(Date.parse(body.requestedAt)) ||
    (body.callback !== undefined && body.callback !== null) ||
    !exact(body.inputs, ['scenarioKey', 'subjectRef']) ||
    !ASSESSMENT_SCENARIOS.includes(body.inputs.scenarioKey) ||
    !SUBJECT.test(body.inputs.subjectRef)
  ) {
    return error(400, 'INVALID_PAYLOAD');
  }
  const { scenarioKey, subjectRef } = body.inputs;
  if (scenarioKey === 'UNAVAILABLE') return error(503, 'PROVIDER_UNAVAILABLE', true);
  const result = baseResult('SYNTHETIC_' + capabilityId);
  result.subjectRef = subjectRef;
  let status = 'COMPLETED';
  let reasonCodes = [];
  if (scenarioKey === 'MISSING_CONTEXT' || (capabilityId === 'GET_CUSTOMER_PROFILE' && scenarioKey === 'NO_PROFILE')) {
    status = 'PENDING';
    reasonCodes = ['MISSING_CONTEXT'];
    result.missingFields = capabilityId === 'GET_CUSTOMER_PROFILE' ? ['syntheticCustomerProfile'] : ['syntheticSupportingContext'];
  } else if (capabilityId === 'CHECK_CUSTOMER_REGISTRATION' && scenarioKey === 'PENDING_REGISTRATION') {
    status = 'PENDING';
    reasonCodes = ['MISSING_CONTEXT'];
    result.registrationStatus = 'PENDING_SYNTHETIC';
    result.missingFields = ['syntheticRegistrationComplete'];
  } else if (capabilityId === 'FIND_ELIGIBLE_PRODUCTS' && scenarioKey === 'INELIGIBLE') {
    status = 'REJECTED';
    reasonCodes = ['SYNTHETIC_INELIGIBLE'];
    result.products = [];
    result.eligibilityRule = 'DEMO_FIXTURE_V1';
  } else if (scenarioKey === 'REJECTED') {
    status = 'REJECTED';
    reasonCodes = ['SYNTHETIC_SCENARIO_REJECTED'];
  } else if (scenarioKey === 'HUMAN_REVIEW') {
    status = 'PENDING';
    reasonCodes = ['SYNTHETIC_HUMAN_REVIEW'];
    result.reviewQueued = false;
  } else if (capabilityId === 'GET_CUSTOMER_PROFILE') {
    result.profile = {
      legalName: 'Empresa Sintética Demo Ltda',
      segment: 'comercio',
      subjectRef,
      personalDocument: false,
    };
  } else if (capabilityId === 'CHECK_CUSTOMER_REGISTRATION') {
    result.registrationStatus = 'COMPLETE_SYNTHETIC';
  } else if (capabilityId === 'GET_CREDIT_PROFILE') {
    result.creditProfile = { band: 'SYNTHETIC_BAND_A', bureau: false, subjectRef };
  } else if (capabilityId === 'FIND_ELIGIBLE_PRODUCTS') {
    result.eligibilityRule = 'DEMO_FIXTURE_V1';
    result.products = [
      {
        productCode: 'WC_SYNTHETIC_TEST_1',
        title: 'Capital de giro sintético de teste',
        offerable: false,
        commercialValidity: false,
        testDouble: true,
      },
    ];
  }
  return envelope(body, capabilityId, VERSION_ASSESSMENT, status, result, reasonCodes);
}

export function processRequest({ method, path, headers = {}, raw = '' }, { credential } = {}) {
  if (method === 'GET' && path === '/health') {
    return {
      status: 200,
      body: {
        status: 'ok',
        providerId: PROVIDER_ID,
        contractVersion: VERSION,
        supportedContractVersions: [VERSION, VERSION_ASSESSMENT],
        supportedCapabilities: [CAPABILITY, ...ASSESSMENT_CAPABILITIES],
        testDouble: true,
        boundary: 'MOCK_ONLY',
        processUp: true,
        integratedWithSpider: false,
        chainReadiness: 'determined_by_spider',
      },
    };
  }
  const match = path.match(/^\/v1\/provider\/capabilities\/([^/]+)\/executions$/);
  if (method !== 'POST' || !match) return error(404, 'NOT_FOUND');
  if (!authenticated(headers['x-credit-mock-credential'], credential)) return error(401, 'UNAUTHORIZED');
  const capabilityId = match[1];
  if (capabilityId !== CAPABILITY && !ASSESSMENT_CAPABILITIES.includes(capabilityId)) {
    return error(400, 'CAPABILITY_NOT_AVAILABLE');
  }
  if (!(headers['content-type'] || '').toLowerCase().startsWith('application/json')) return error(415, 'UNSUPPORTED_MEDIA_TYPE');
  if (Buffer.byteLength(raw, 'utf8') > MAX_BYTES) return error(413, 'PAYLOAD_TOO_LARGE');
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return error(400, 'INVALID_PAYLOAD');
  }
  return capabilityId === CAPABILITY ? simulate(body) : assess(capabilityId, body);
}

export async function handleRequest(req, res, options) {
  const send = (output) => {
    res.writeHead(output.status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify(output.body));
  };
  let size = 0;
  const chunks = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BYTES) {
      send(error(413, 'PAYLOAD_TOO_LARGE'));
      return;
    }
    chunks.push(chunk);
  }
  send(
    processRequest(
      {
        method: req.method,
        path: new URL(req.url, 'http://127.0.0.1').pathname,
        headers: req.headers,
        raw: Buffer.concat(chunks).toString('utf8'),
      },
      options,
    ),
  );
}

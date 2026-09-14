import { createHash, timingSafeEqual } from 'node:crypto';
import { calculateSyntheticHomePremium, RATING_RULE_VERSION } from './homePremium.js';

const WATERMARK =
  'DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO';
const QUOTE_WATERMARK =
  'SIMULAÇÃO DEMONSTRATIVA — SEM VALIDADE COMERCIAL — NÃO É OFERTA ICATU NEM CONTRATAÇÃO';
export const MAX_BYTES = 8192;
const PROVIDER_ID = 'insurance-provider-mock';
const LEGACY_PROVIDER_ID = 'SEGSENSE_PROVIDER_MOCK';
const ORIGIN = 'ILLUSTRATIVE_NOT_ICATU_CONTRACT';
const SUPPORTED = 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO';
const HOME_QUOTE = 'GENERATE_SYNTHETIC_HOME_QUOTE';
const recentExecutions = [];

function rememberExecution(scenarioKey, requestId) {
  recentExecutions.push({ scenarioKey, requestId });
  if (recentExecutions.length > 32) {
    recentExecutions.shift();
  }
}

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
      body: {
        status: 'ok',
        providerId: LEGACY_PROVIDER_ID,
        testDouble: true,
        satelliteRole: 'PROVIDER_TEST_DOUBLE',
        recentExecutions: recentExecutions.map((item) => ({
          scenarioKey: item.scenarioKey,
          requestId: item.requestId,
        })),
      },
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
  if (capabilityId === HOME_QUOTE) {
    return processHomeQuote(body);
  }
  if (capabilityId !== SUPPORTED) {
    return { status: 400, body: { errorCode: 'CAPABILITY_NOT_AVAILABLE', message: 'Capability não suportada.', retryable: false } };
  }
  if (
    body.contractVersion !== '1.0' ||
    body.capabilityId !== SUPPORTED ||
    body.purpose !== 'INSURANCE_PROTECTION_ASSESSMENT' ||
    !body.inputs ||
    body.inputs.scenarioKey === undefined ||
    typeof body.inputs.scenarioKey !== 'string' ||
    typeof body.requestId !== 'string' ||
    typeof body.correlationId !== 'string' ||
    typeof body.decisionId !== 'string'
  ) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Pedido de capability inválido.', retryable: false } };
  }
  if (body.originSnapshot || body.objective || body.intent || body.executionPlan) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Payload excede a minimização da capability.', retryable: false } };
  }
  const result = illustrativeResult(body.inputs.scenarioKey);
  if (!result) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Pedido de capability inválido.', retryable: false } };
  }
  rememberExecution(body.inputs.scenarioKey, body.requestId);
  return {
    status: 200,
    body: {
      requestId: body.requestId,
      correlationId: body.correlationId,
      capabilityId: SUPPORTED,
      providerId: PROVIDER_ID,
      status: 'COMPLETED',
      result,
      reasonCodes: [],
      executedAt: '2026-09-13T12:00:00Z',
      providerReference: `ill-${crypto.randomUUID()}`,
    },
  };
}

function processHomeQuote(body) {
  if (
    body.contractVersion !== '1.1' ||
    body.capabilityId !== HOME_QUOTE ||
    body.purpose !== 'INSURANCE_PROTECTION_ASSESSMENT' ||
    !body.inputs ||
    typeof body.inputs.scenarioKey !== 'string' ||
    typeof body.requestId !== 'string' ||
    typeof body.correlationId !== 'string' ||
    typeof body.decisionId !== 'string'
  ) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Pedido de cotação simulada inválido.', retryable: false } };
  }
  if (body.originSnapshot || body.objective || body.intent || body.executionPlan) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Payload excede a minimização da capability.', retryable: false } };
  }
  if (body.inputs.premiumAnnualCents !== undefined || body.inputs.premium !== undefined) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'O provedor calcula o prêmio; ele não é um input.', retryable: false } };
  }
  const calculated = calculateSyntheticHomePremium({
    dwellingType: body.inputs.dwellingType,
    insuredAmountCents: body.inputs.insuredAmountCents,
    coverPeriodMonths: body.inputs.coverPeriodMonths,
  });
  if (!calculated.ok) {
    return { status: 400, body: { errorCode: 'INVALID_PAYLOAD', message: 'Entrada de cotação simulada inválida.', retryable: false } };
  }
  rememberExecution(body.inputs.scenarioKey, body.requestId);
  return {
    status: 200,
    body: {
      contractVersion: '1.1',
      requestId: body.requestId,
      correlationId: body.correlationId,
      capabilityId: HOME_QUOTE,
      providerId: PROVIDER_ID,
      status: 'COMPLETED',
      result: {
        kind: 'SYNTHETIC_HOME_QUOTE',
        origin: 'NON_BINDING_DEMO',
        testDouble: true,
        currency: 'BRL',
        insuredAmountCents: calculated.insuredAmountCents,
        premiumAnnualCents: calculated.premiumAnnualCents,
        coverPeriodMonths: calculated.coverPeriodMonths,
        dwellingType: calculated.dwellingType,
        dwellingBps: calculated.dwellingBps,
        ratingRuleVersion: calculated.ratingRuleVersion,
        nearbyFiresDidNotAdjustPremium: true,
        calculatedAt: new Date().toISOString(),
        premises: [
          'Taxas inventadas para demonstrar o software, sem calibração de mercado.',
          'Incêndios próximos na fonte editorial não alteram o prêmio.',
          'Não é oferta Icatu, apólice, proposta nem contratação.',
        ],
        watermark: QUOTE_WATERMARK,
        status: 'NON_BINDING_DEMO',
      },
      reasonCodes: [],
      executedAt: new Date().toISOString(),
      providerReference: `qte-${crypto.randomUUID()}`,
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
  const result = illustrativeResult(body.scenarioKey);
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

function illustrativeResult(scenarioKey) {
  const familyUnderstand = {
    kind: 'ILLUSTRATIVE_PROTECTION_SCENARIO',
    origin: ORIGIN,
    testDouble: true,
    watermark: WATERMARK,
    items: [
      {
        code: 'ILLUSTRATIVE_FAMILY_CONTINUITY_CONVERSATION',
        title: 'Conversar sobre continuidade da renda familiar (ilustrativo)',
        kind: 'ILLUSTRATIVE_POSSIBILITY',
        notOfferable: true,
        needAddressed: 'dependentes precisam de continuidade',
        pertinence: 'O tema da fonte editorial governada é continuidade familiar e a intenção é entender opções ilustrativas.',
        limits: 'Não é produto, cobertura, preço nem oferta Icatu.',
      },
      {
        code: 'ILLUSTRATIVE_FAMILY_BROKER_REVIEW',
        title: 'Levar o cenário sintético a uma corretora autorizada (ilustrativo)',
        kind: 'ILLUSTRATIVE_POSSIBILITY',
        notOfferable: true,
        needAddressed: 'entender opções',
        pertinence: 'A pendência humana permanece: só uma seguradora autorizada pode dizer se existe produto.',
        limits: 'Não há cotação nem proposta nesta demonstração.',
      },
    ],
    pendingForHumanReview: [
      'Confirmar com a seguradora autorizada se existe produto adequado.',
      'Não há cotação, capital, prêmio ou emissão neste artefato.',
    ],
  };
  const familyCompare = {
    kind: 'ILLUSTRATIVE_PROTECTION_SCENARIO',
    origin: ORIGIN,
    testDouble: true,
    watermark: WATERMARK,
    items: [
      {
        code: 'ILLUSTRATIVE_FAMILY_GAP_MAP',
        title: 'Mapear lacunas ilustrativas da continuidade familiar',
        kind: 'ILLUSTRATIVE_POSSIBILITY',
        notOfferable: true,
        needAddressed: 'dependentes precisam de continuidade',
        pertinence: 'A intenção pediu comparar lacunas no mesmo tema de continuidade familiar.',
        limits: 'Não é diagnóstico atuarial nem catálogo de coberturas.',
      },
    ],
    pendingForHumanReview: [
      'Uma pessoa autorizada precisa avaliar se as lacunas ilustrativas correspondem a alguma proteção real.',
    ],
  };
  const incomeUnderstand = {
    kind: 'ILLUSTRATIVE_PROTECTION_SCENARIO',
    origin: ORIGIN,
    testDouble: true,
    watermark: WATERMARK,
    items: [
      {
        code: 'ILLUSTRATIVE_INCOME_PAUSE_CONVERSATION',
        title: 'Conversar sobre pausa da renda do trabalho (ilustrativo)',
        kind: 'ILLUSTRATIVE_POSSIBILITY',
        notOfferable: true,
        needAddressed: 'a renda pode parar se o trabalho parar',
        pertinence: 'O tema da fonte editorial governada é interrupção de renda e a intenção é entender opções ilustrativas.',
        limits: 'Não é produto, cobertura, preço nem oferta Icatu.',
      },
    ],
    pendingForHumanReview: [
      'Confirmar com a seguradora autorizada se existe proteção para interrupção de renda.',
    ],
  };
  const incomeCompare = {
    kind: 'ILLUSTRATIVE_PROTECTION_SCENARIO',
    origin: ORIGIN,
    testDouble: true,
    watermark: WATERMARK,
    items: [
      {
        code: 'ILLUSTRATIVE_INCOME_GAP_COMPARE',
        title: 'Comparar lacunas ilustrativas se o trabalho parar',
        kind: 'ILLUSTRATIVE_POSSIBILITY',
        notOfferable: true,
        needAddressed: 'a renda pode parar se o trabalho parar',
        pertinence: 'A intenção pediu comparar lacunas no tema de interrupção de renda.',
        limits: 'Não há valor, carência, capital ou disponibilidade de produto.',
      },
      {
        code: 'ILLUSTRATIVE_INCOME_HUMAN_HANDOFF',
        title: 'Encaminhar o cenário de renda a avaliação humana (ilustrativo)',
        kind: 'ILLUSTRATIVE_POSSIBILITY',
        notOfferable: true,
        needAddressed: 'comparar lacunas',
        pertinence: 'O Test Double não decide elegibilidade; a pendência é humana.',
        limits: 'Não é cotação nem proposta vinculante.',
      },
    ],
    pendingForHumanReview: [
      'Não há cotação, capital, prêmio ou emissão neste artefato.',
    ],
  };
  const legacySteps = {
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
  if (scenarioKey === 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1|UNDERSTAND_PROTECTION_OPTIONS') {
    return familyUnderstand;
  }
  if (scenarioKey === 'SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1|UNDERSTAND_PROTECTION_OPTIONS') {
    return declaredCopy(familyUnderstand);
  }
  if (scenarioKey === 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1|COMPARE_COVERAGE_GAPS') {
    return familyCompare;
  }
  if (scenarioKey === 'SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1|COMPARE_COVERAGE_GAPS') {
    return declaredCopy(familyCompare);
  }
  if (
    scenarioKey === 'SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1' ||
    scenarioKey === 'SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1|UNDERSTAND_PROTECTION_OPTIONS'
  ) {
    return incomeUnderstand;
  }
  if (scenarioKey === 'SEGSENSE_DECLARED_INCOME_INTERRUPTION_V1|UNDERSTAND_PROTECTION_OPTIONS') {
    return declaredCopy(incomeUnderstand);
  }
  if (scenarioKey === 'SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1|COMPARE_COVERAGE_GAPS') {
    return incomeCompare;
  }
  if (scenarioKey === 'SEGSENSE_DECLARED_INCOME_INTERRUPTION_V1|COMPARE_COVERAGE_GAPS') {
    return declaredCopy(incomeCompare);
  }
  if (scenarioKey === 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1') {
    return legacySteps;
  }
  return null;
}

function declaredCopy(result) {
  const copy = JSON.parse(JSON.stringify(result));
  for (const item of copy.items) {
    if (item.pertinence) {
      item.pertinence = String(item.pertinence).replace(
        'O tema da fonte editorial governada',
        'O tema declarado estruturado',
      );
    }
  }
  return copy;
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

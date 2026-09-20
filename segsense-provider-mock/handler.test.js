import { test } from 'node:test';
import assert from 'node:assert/strict';
import { processDemoRequest } from './handler.js';

/** Test-only fixture. The live process has no default credential. */
const CRED = 'local-demo-segsense-mock';
const allowedBody = JSON.stringify({
  contractVersion: 'segsense-mock-contract-v1',
  correlationId: '11111111-1111-1111-1111-111111111111',
  decisionId: 'spd-1',
  scenarioKey: 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1',
  declaredObjective: 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS',
});

test('health is public', () => {
  const got = processDemoRequest({ method: 'GET', path: '/health', headers: {}, raw: '' }, { credential: CRED });
  assert.equal(got.status, 200);
  assert.equal(got.body.providerId, 'SEGSENSE_PROVIDER_MOCK');
});

test('rejects missing credential', () => {
  const got = processDemoRequest(
    { method: 'POST', path: '/v1/illustrative-protection-items', headers: {}, raw: '{}' },
    { credential: CRED },
  );
  assert.equal(got.status, 401);
});

test('returns illustrative items without money or Icatu', () => {
  const got = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/illustrative-protection-items',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: allowedBody,
    },
    { credential: CRED },
  );
  assert.equal(got.status, 200);
  assert.equal(got.body.providerId, 'SEGSENSE_PROVIDER_MOCK');
  assert.equal(got.body.origin, 'ILLUSTRATIVE_NOT_ICATU_CONTRACT');
  assert.doesNotMatch(JSON.stringify(got.body), /R\$/);
  assert.doesNotMatch(JSON.stringify(got.body), /Icatu Seguros/i);
});

test('provider contract executes supported capability', () => {
  const got = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: JSON.stringify({
        contractVersion: '1.0',
        requestId: 'preq-1',
        correlationId: '11111111-1111-1111-1111-111111111111',
        decisionId: 'spd-1',
        capabilityId: 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO',
        capabilityVersion: '1.0',
        purpose: 'INSURANCE_PROTECTION_ASSESSMENT',
        inputs: { scenarioKey: 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1' },
        dataClassification: 'INTERNAL',
        requestedAt: '2026-09-13T12:00:00Z',
        callback: null,
      }),
    },
    { credential: CRED },
  );
  assert.equal(got.status, 200);
  assert.equal(got.body.providerId, 'insurance-provider-mock');
  assert.equal(got.body.status, 'COMPLETED');
  assert.equal(got.body.result.origin, 'ILLUSTRATIVE_NOT_ICATU_CONTRACT');
  assert.equal(got.body.result.testDouble, true);
  assert.equal(got.body.originSnapshot, undefined);
});

test('family understand and income compare return different possibilities', () => {
  const family = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: JSON.stringify({
        contractVersion: '1.0',
        requestId: 'preq-fam',
        correlationId: '11111111-1111-1111-1111-111111111111',
        decisionId: 'spd-fam',
        capabilityId: 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO',
        capabilityVersion: '1.0',
        purpose: 'INSURANCE_PROTECTION_ASSESSMENT',
        inputs: { scenarioKey: 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1|UNDERSTAND_PROTECTION_OPTIONS' },
        dataClassification: 'INTERNAL',
        requestedAt: '2026-09-13T12:00:00Z',
        callback: null,
      }),
    },
    { credential: CRED },
  );
  const income = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: JSON.stringify({
        contractVersion: '1.0',
        requestId: 'preq-inc',
        correlationId: '11111111-1111-1111-1111-111111111111',
        decisionId: 'spd-inc',
        capabilityId: 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO',
        capabilityVersion: '1.0',
        purpose: 'INSURANCE_PROTECTION_ASSESSMENT',
        inputs: { scenarioKey: 'SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1|COMPARE_COVERAGE_GAPS' },
        dataClassification: 'INTERNAL',
        requestedAt: '2026-09-13T12:00:00Z',
        callback: null,
      }),
    },
    { credential: CRED },
  );
  assert.equal(family.status, 200);
  assert.equal(income.status, 200);
  assert.equal(family.body.result.items[0].code, 'ILLUSTRATIVE_FAMILY_CONTINUITY_CONVERSATION');
  assert.equal(income.body.result.items[0].code, 'ILLUSTRATIVE_INCOME_GAP_COMPARE');
  assert.notEqual(family.body.result.items[0].title, income.body.result.items[0].title);
  assert.equal(family.body.result.items[0].kind, 'ILLUSTRATIVE_POSSIBILITY');
  assert.doesNotMatch(JSON.stringify(family.body), /Icatu Seguros/i);
  assert.doesNotMatch(JSON.stringify(income.body), /R\$/);
  const health = processDemoRequest({ method: 'GET', path: '/health', headers: {}, raw: '' }, { credential: CRED });
  const keys = health.body.recentExecutions.map((item) => item.scenarioKey);
  assert.ok(keys.includes('SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1|UNDERSTAND_PROTECTION_OPTIONS'));
  assert.ok(keys.includes('SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1|COMPARE_COVERAGE_GAPS'));
});

test('unsupported capability is rejected', () => {
  const got = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/GET_INSURANCE_OPTIONS/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: JSON.stringify({
        contractVersion: '1.0',
        requestId: 'preq-2',
        correlationId: '11111111-1111-1111-1111-111111111111',
        decisionId: 'spd-2',
        capabilityId: 'GET_INSURANCE_OPTIONS',
        capabilityVersion: '1.0',
        purpose: 'INSURANCE_PROTECTION_ASSESSMENT',
        inputs: { scenarioKey: 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1' },
        dataClassification: 'INTERNAL',
        requestedAt: '2026-09-13T12:00:00Z',
        callback: null,
      }),
    },
    { credential: CRED },
  );
  assert.equal(got.status, 400);
  assert.equal(got.body.errorCode, 'CAPABILITY_NOT_AVAILABLE');
});

test('unknown scenarioKey is invalid and does not invent possibilities', () => {
  const got = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: JSON.stringify({
        contractVersion: '1.0',
        requestId: 'preq-unk',
        correlationId: '11111111-1111-1111-1111-111111111111',
        decisionId: 'spd-unk',
        capabilityId: 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO',
        capabilityVersion: '1.0',
        purpose: 'INSURANCE_PROTECTION_ASSESSMENT',
        inputs: { scenarioKey: 'UNKNOWN_KEY' },
        dataClassification: 'INTERNAL',
        requestedAt: '2026-09-13T12:00:00Z',
        callback: null,
      }),
    },
    { credential: CRED },
  );
  assert.equal(got.status, 400);
  assert.equal(got.body.errorCode, 'INVALID_PAYLOAD');
});

test('declared scenarioKey is distinct from governed editorial pertinence', () => {
  const declared = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: JSON.stringify({
        contractVersion: '1.0',
        requestId: 'preq-decl',
        correlationId: '11111111-1111-1111-1111-111111111111',
        decisionId: 'spd-decl',
        capabilityId: 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO',
        capabilityVersion: '1.0',
        purpose: 'INSURANCE_PROTECTION_ASSESSMENT',
        inputs: { scenarioKey: 'SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1|UNDERSTAND_PROTECTION_OPTIONS' },
        dataClassification: 'INTERNAL',
        requestedAt: '2026-09-14T15:01:00Z',
        callback: null,
      }),
    },
    { credential: CRED },
  );
  assert.equal(declared.status, 200);
  assert.match(declared.body.result.items[0].pertinence, /tema declarado estruturado/);
  assert.doesNotMatch(declared.body.result.items[0].pertinence, /fonte editorial governada/);
});

function homeQuoteBody(overrides = {}) {
  return JSON.stringify({
    contractVersion: '1.1',
    requestId: 'preq-home-1',
    correlationId: '11111111-1111-1111-1111-111111111111',
    decisionId: 'spd-home-1',
    capabilityId: 'GENERATE_SYNTHETIC_HOME_QUOTE',
    capabilityVersion: '1.0',
    purpose: 'INSURANCE_PROTECTION_ASSESSMENT',
    inputs: {
      scenarioKey: 'SEGSENSE_NEARBY_FIRES_SYNTHETIC_V1|SIMULATE_HOME_QUOTE',
      dwellingType: 'APARTMENT',
      insuredAmountCents: 30_000_000,
      coverPeriodMonths: 12,
      ratingRuleVersion: 'HOME_QUOTE_SYNTHETIC_V1',
      ...overrides,
    },
    dataClassification: 'INTERNAL',
    requestedAt: '2026-09-14T18:00:00Z',
    callback: null,
  });
}

test('home quote capability calculates BRL premium', () => {
  const got = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/GENERATE_SYNTHETIC_HOME_QUOTE/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: homeQuoteBody(),
    },
    { credential: CRED },
  );
  assert.equal(got.status, 200);
  assert.equal(got.body.result.premiumAnnualCents, 54_000);
  assert.equal(got.body.result.origin, 'NON_BINDING_DEMO');
  assert.match(got.body.result.watermark, /SIMULAÇÃO DEMONSTRATIVA/);
  assert.equal(got.body.result.nearbyFiresDidNotAdjustPremium, true);
});

test('home quote house changes premium and does not reuse illustrative path', () => {
  const got = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/GENERATE_SYNTHETIC_HOME_QUOTE/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: homeQuoteBody({ dwellingType: 'HOUSE' }),
    },
    { credential: CRED },
  );
  assert.equal(got.body.result.premiumAnnualCents, 66_000);
  assert.equal(got.body.result.items, undefined);
});

test('home quote rejects input premium and keeps illustrative capability free of R$', () => {
  const forged = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/GENERATE_SYNTHETIC_HOME_QUOTE/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: homeQuoteBody({ premiumAnnualCents: 1 }),
    },
    { credential: CRED },
  );
  assert.equal(forged.status, 400);
});

test('crop paths return demonstrative items without money', () => {
  const got = processDemoRequest(
    {
      method: 'POST',
      path: '/v1/provider/capabilities/DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS/executions',
      headers: { 'x-segsense-mock-credential': CRED },
      raw: JSON.stringify({
        contractVersion: '1.0',
        requestId: 'preq-crop-1',
        correlationId: '11111111-1111-1111-1111-111111111111',
        decisionId: 'spd-crop-1',
        capabilityId: 'DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS',
        capabilityVersion: '1.0',
        purpose: 'INSURANCE_PROTECTION_ASSESSMENT',
        inputs: { scenarioKey: 'SEGSENSE_URL_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|UNDERSTAND_PROTECTION_OPTIONS' },
        dataClassification: 'INTERNAL',
        requestedAt: '2026-09-15T12:00:00Z',
        callback: null,
      }),
    },
    { credential: CRED },
  );
  assert.equal(got.status, 200);
  assert.equal(got.body.capabilityId, 'DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS');
  assert.equal(got.body.result.origin, 'ILLUSTRATIVE_NOT_ICATU_CONTRACT');
  assert.equal(got.body.result.items.length, 2);
  assert.doesNotMatch(JSON.stringify(got.body), /R\$/);
  assert.equal(got.body.result.premiumAnnualCents, undefined);
  assert.match(got.body.result.pendingForHumanReview[0], /cultura agrícola/);
  assert.match(got.body.result.pendingForHumanReview[1], /região/);
  assert.match(got.body.result.pendingForHumanReview[2], /período/);
  assert.match(got.body.result.pendingForHumanReview[3], /situação produtiva/);
});

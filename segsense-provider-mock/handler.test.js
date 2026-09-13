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

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const express = require('express');
const { registerSpiderBibliotecaRoutes, executeCapability } = require('./spider-biblioteca');

test('recusa appId de outro aplicativo', async () => {
  const result = await executeCapability({}, 'LIST_HUB_CATALOG', { appId: 'inove4us' }, {});
  assert.equal(result.status, 403);
});

test('provedor exige credencial e devolve catálogo pela capacidade', async () => {
  const app = express();
  app.use(express.json());
  const pool = {
    query: async (sql) => {
      if (String(sql).includes('app_registry')) {
        return { rows: [{ app_id: 'lojadepaes', name: 'Loja de Pães', active: true }] };
      }
      return {
        rows: [
          {
            id: '00bf4a0c-e598-414d-96cb-88cd47278e44',
            app_id: 'lojadepaes',
            name: 'Assinatura da Biblioteca',
            type: 'plan',
            sku: 'LOJADEPAES_BIBLIOTECA_MENSAL',
            price: 19,
            currency: 'BRL',
            features: ['20 consultas'],
            meta_json: { credits: 20, checkout_mode: 'subscription', recurring: true },
            active: true,
          },
        ],
      };
    },
  };
  registerSpiderBibliotecaRoutes(app, pool, {
    env: { ACTIONHUB_BIBLIOTECA_PROVIDER_SECRET: 'biblioteca-test-secret' },
  });
  const server = await new Promise((resolve) => {
    const s = app.listen(0, () => resolve(s));
  });
  const port = server.address().port;
  const denied = await fetch(`http://127.0.0.1:${port}/v1/provider/capabilities/LIST_HUB_CATALOG/executions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contractVersion: '1.5',
      requestId: 'preq-1',
      correlationId: 'corr-catalog-1',
      capabilityId: 'LIST_HUB_CATALOG',
      inputs: { appId: 'lojadepaes' },
    }),
  });
  assert.equal(denied.status, 401);
  const ok = await fetch(`http://127.0.0.1:${port}/v1/provider/capabilities/LIST_HUB_CATALOG/executions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-ActionHub-Biblioteca-Credential': 'biblioteca-test-secret',
    },
    body: JSON.stringify({
      contractVersion: '1.5',
      requestId: 'preq-1',
      correlationId: 'corr-catalog-1',
      capabilityId: 'LIST_HUB_CATALOG',
      inputs: { appId: 'lojadepaes' },
    }),
  });
  assert.equal(ok.status, 200);
  const body = await ok.json();
  assert.equal(body.providerId, 'actionhub-biblioteca');
  assert.equal(body.result.app_id, 'lojadepaes');
  assert.equal(body.result.plans[0].sku, 'LOJADEPAES_BIBLIOTECA_MENSAL');
  await new Promise((resolve) => server.close(resolve));
});

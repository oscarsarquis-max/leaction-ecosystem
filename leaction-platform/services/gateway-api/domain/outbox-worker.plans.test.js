'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { resolveWebhookUrl, isLojaPlansEvent } = require('./outbox-worker');

test('eventos de planos da Loja não usam o webhook de pedidos', () => {
  process.env.APP_WEBHOOK_URL_LOJADEPAES = 'https://lojadepaes.com.br/api/v1/webhooks/actionhub';
  delete process.env.APP_PLANS_WEBHOOK_URL_LOJADEPAES;
  delete process.env.LOJADEPAES_PLANS_WEBHOOK_URL;
  assert.equal(isLojaPlansEvent('lojadepaes', 'CREDITS_GRANTED'), true);
  assert.equal(isLojaPlansEvent('lojadepaes', 'PAYMENT_APPROVED'), false);
  assert.equal(isLojaPlansEvent('inove4us', 'CREDITS_GRANTED'), false);
  assert.equal(resolveWebhookUrl('lojadepaes', 'https://db.example/pay', 'CREDITS_GRANTED'), '');
  process.env.APP_PLANS_WEBHOOK_URL_LOJADEPAES = 'https://lojadepaes.com.br/api/v1/webhooks/actionhub/plans';
  assert.equal(
    resolveWebhookUrl('lojadepaes', 'https://db.example/pay', 'CREDITS_GRANTED'),
    'https://lojadepaes.com.br/api/v1/webhooks/actionhub/plans'
  );
  assert.equal(
    resolveWebhookUrl('lojadepaes', 'https://db.example/pay', 'PAYMENT_APPROVED'),
    'https://lojadepaes.com.br/api/v1/webhooks/actionhub'
  );
  delete process.env.APP_PLANS_WEBHOOK_URL_LOJADEPAES;
  delete process.env.APP_WEBHOOK_URL_LOJADEPAES;
});

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { formCpfIdentification, buildLegacyCardPaymentBody } = require('./payer-data');
const { createPixPayment, createCardPayment } = require('../mercadopago');

const FROZEN =
  '{"transaction_amount":70,"token":"tok_test","description":"Pedido","installments":1,"payment_method_id":"master","payer":{"email":"cliente@example.test"},"external_reference":"order-1"}';

function legacy(identification) {
  return buildLegacyCardPaymentBody({
    transactionAmount: 70,
    token: 'tok_test',
    description: 'Pedido',
    installments: 1,
    methodId: 'master',
    email: 'cliente@example.test',
    identification: identification || null,
    externalReference: 'order-1',
  });
}

const ALLOWED = {
  transaction_amount: true,
  token: true,
  description: true,
  installments: true,
  payment_method_id: true,
  external_reference: true,
  payer: {
    email: true,
    identification: { type: true, number: true },
  },
};

function assertClosed(value, schema, where) {
  if (value && typeof value === 'object') {
    for (const key of Object.keys(value)) {
      assert.equal(
        Boolean(schema) && Object.prototype.hasOwnProperty.call(schema, key),
        true,
        `campo fora da lista: ${where}.${key}`,
      );
      if (schema[key] !== true) assertClosed(value[key], schema[key], `${where}.${key}`);
    }
  }
}

test('sem CPF, o corpo do cartão continua o de hoje', () => {
  const body = legacy();
  assert.equal(JSON.stringify(body), FROZEN);
  assert.equal(formCpfIdentification(''), null);
  assert.equal(formCpfIdentification(null), null);
});

test('o CPF do formulário entra só em payer.identification', () => {
  const identification = formCpfIdentification('529.982.247-25');
  const sent = legacy(identification);
  assert.deepEqual(identification, { type: 'CPF', number: '52998224725' });
  assert.equal(sent.payer.email, 'cliente@example.test');
  assert.deepEqual(sent.payer.identification, identification);
  assert.equal(Object.keys(sent.payer).join(','), 'email,identification');
  assert.equal(Object.prototype.hasOwnProperty.call(sent, 'additional_info'), false);
  assert.equal(Object.prototype.hasOwnProperty.call(sent, 'statement_descriptor'), false);
  assert.equal(Object.prototype.hasOwnProperty.call(sent, 'three_d_secure_mode'), false);
  assertClosed(sent, ALLOWED, 'corpo');
});

test('CPF inválido é descartado sem ir para o log e a cobrança segue', () => {
  const logs = [];
  const original = console.warn;
  console.warn = (...args) => logs.push(args.join(' '));
  try {
    assert.equal(formCpfIdentification('111.111.111-11'), null);
    assert.equal(formCpfIdentification('000'), null);
  } finally {
    console.warn = original;
  }
  const text = logs.join('\n');
  assert.equal(text.includes('11111111111'), false);
  assert.equal(text.includes('000'), false);
  assert.match(text, /identification/);
  assert.equal(JSON.stringify(legacy()), FROZEN);
});

test('o Pix e o cartão não leem chave de pagador nem aparelho', () => {
  const pix = createPixPayment.toString();
  const card = createCardPayment.toString();
  const payer = fs.readFileSync(path.join(__dirname, 'payer-data.js'), 'utf8');
  const mercado = fs.readFileSync(path.join(__dirname, '..', 'mercadopago.js'), 'utf8');
  for (const source of [pix, card, payer, mercado]) {
    assert.equal(source.includes('PAY_SEND_'), false);
    assert.equal(source.includes('PAY_STATEMENT_DESCRIPTOR'), false);
    assert.equal(source.includes('X-meli-session-id'), false);
    assert.equal(source.includes('security.js'), false);
    assert.equal(source.includes('three_d_secure'), false);
  }
  assert.equal(pix.includes('additional_info'), false);
  assert.equal(card.includes('additional_info'), false);
});

test('a cobrança manda uma vez o e-mail e o CPF do formulário', async () => {
  const axios = require('axios');
  const previousToken = process.env.MP_ACCESS_TOKEN;
  const previousSandboxEmail = process.env.MP_SANDBOX_PAYER_EMAIL;
  process.env.MP_ACCESS_TOKEN = 'TEST-unit';
  delete process.env.MP_SANDBOX_PAYER_EMAIL;
  const bodies = [];
  const headers = [];
  const original = axios.post;
  axios.post = async (_url, body, config) => {
    bodies.push(JSON.parse(JSON.stringify(body)));
    headers.push(config && config.headers ? config.headers : {});
    return { data: { id: 1, status: 'approved', status_detail: 'accredited' } };
  };
  try {
    const result = await createCardPayment({
      payerEmail: 'cliente@example.test',
      cardTokenId: 'tok_test',
      paymentMethodId: 'master',
      amount: 70,
      externalReference: 'order-1',
      description: 'Pedido',
      payerIdentification: { type: 'CPF', number: '11111111111' },
      payerDocument: '529.982.247-25',
    });
    assert.equal(result.status, 'approved');
    assert.equal(bodies.length, 1);
    assert.equal(bodies[0].payer.email, 'cliente@example.test');
    assert.deepEqual(bodies[0].payer.identification, { type: 'CPF', number: '52998224725' });
    assert.equal(Object.keys(bodies[0].payer).join(','), 'email,identification');
    assert.equal(Object.prototype.hasOwnProperty.call(bodies[0], 'additional_info'), false);
    assert.equal(Object.prototype.hasOwnProperty.call(bodies[0], 'statement_descriptor'), false);
    assert.equal(Object.prototype.hasOwnProperty.call(headers[0], 'X-meli-session-id'), false);
    assertClosed(bodies[0], ALLOWED, 'corpo');
  } finally {
    axios.post = original;
    if (previousToken == null) delete process.env.MP_ACCESS_TOKEN;
    else process.env.MP_ACCESS_TOKEN = previousToken;
    if (previousSandboxEmail == null) delete process.env.MP_SANDBOX_PAYER_EMAIL;
    else process.env.MP_SANDBOX_PAYER_EMAIL = previousSandboxEmail;
  }
});

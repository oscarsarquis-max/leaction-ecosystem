const test = require('node:test');
const assert = require('node:assert/strict');
const {
  satelliteEnabled,
  normalizeSatellitePayer,
  buildLegacyCardPaymentBody,
  finalizeCardPaymentBody,
  cardDeviceHeader,
} = require('./payer-data');
const { createPixPayment } = require('../mercadopago');

const FROZEN =
  '{"transaction_amount":70,"token":"tok_test","description":"Pedido","installments":1,"payment_method_id":"master","payer":{"email":"cliente@example.test"},"external_reference":"order-1"}';

function legacy() {
  return buildLegacyCardPaymentBody({
    transactionAmount: 70,
    token: 'tok_test',
    description: 'Pedido',
    installments: 1,
    methodId: 'master',
    email: 'cliente@example.test',
    identification: null,
    externalReference: 'order-1',
  });
}

const payer = {
  first_name: 'Ana',
  last_name: 'Souza',
  email: 'ana@example.test',
  identification: { type: 'CPF', number: '529.982.247-25' },
  phone: { area_code: '11', number: '987654321' },
  address: {
    zip_code: '01310-100',
    street_name: 'Paulista',
    street_number: '1000',
    neighborhood: 'Bela Vista',
    city: 'São Paulo',
    federal_unit: 'sp',
  },
};

test('sem a chave, o corpo do cartão é o de hoje, mesmo com pagador', () => {
  const body = legacy();
  assert.equal(JSON.stringify(body), FROZEN);
  const sent = finalizeCardPaymentBody(body, {
    sendPayer: false,
    appId: 'lojadepaes',
    payerProfile: payer,
    description: 'Pedido',
  });
  assert.equal(sent, body);
  assert.equal(JSON.stringify(sent), FROZEN);
  assert.equal(satelliteEnabled('PAY_SEND_PAYER_DATA', 'lojadepaes'), false);
  assert.equal(satelliteEnabled('PAY_SEND_DEVICE_ID', 'lojadepaes'), false);
});

test('com a chave, cada campo do pagador vai ao lugar certo e o 3DS não entra', () => {
  const previous = process.env.PAY_STATEMENT_DESCRIPTOR;
  process.env.PAY_STATEMENT_DESCRIPTOR = 'lojadepaes:LOJADEPAES';
  try {
    const sent = finalizeCardPaymentBody(legacy(), {
      sendPayer: true,
      appId: 'lojadepaes',
      payerProfile: payer,
      description: 'Pedido',
    });
    assert.equal(sent.payer.email, 'cliente@example.test');
    assert.equal(sent.payer.first_name, 'Ana');
    assert.equal(sent.payer.last_name, 'Souza');
    assert.deepEqual(sent.payer.identification, { type: 'CPF', number: '52998224725' });
    assert.deepEqual(sent.additional_info.payer.phone, { area_code: '11', number: '987654321' });
    assert.equal(sent.additional_info.payer.address.zip_code, '01310100');
    assert.equal(sent.additional_info.payer.address.street_name, 'Paulista');
    assert.equal(sent.additional_info.payer.address.federal_unit, 'SP');
    assert.equal(sent.additional_info.payer.first_name, 'Ana');
    assert.deepEqual(sent.additional_info.items[0], {
      title: 'Pedido',
      quantity: 1,
      unit_price: 70,
      category_id: 'food',
    });
    assert.equal(sent.statement_descriptor, 'LOJADEPAES');
    assert.equal(sent.external_reference, 'order-1');
    assert.equal(Object.prototype.hasOwnProperty.call(sent, 'three_d_secure_mode'), false);
  } finally {
    if (previous == null) delete process.env.PAY_STATEMENT_DESCRIPTOR;
    else process.env.PAY_STATEMENT_DESCRIPTOR = previous;
  }
});

test('campo inválido é descartado e a cobrança segue', () => {
  const sent = finalizeCardPaymentBody(legacy(), {
    sendPayer: true,
    appId: 'lojadepaes',
    payerProfile: {
      first_name: 'Ana',
      phone: 'abc',
      identification: { type: 'CPF', number: '11111111111' },
    },
    payerDocument: '000',
    description: 'Pedido',
  });
  assert.equal(sent.payer.first_name, 'Ana');
  assert.equal(sent.payer.identification, undefined);
  assert.equal(sent.additional_info.payer.phone, undefined);
  assert.equal(sent.additional_info.items[0].category_id, 'food');
});

test('o cabeçalho do aparelho só segue com a chave daquele satélite', () => {
  assert.equal(cardDeviceHeader('abc-123', false), null);
  assert.equal(cardDeviceHeader('', true), null);
  assert.equal(cardDeviceHeader('abc-123', true), 'abc-123');
  const previous = process.env.PAY_SEND_DEVICE_ID;
  process.env.PAY_SEND_DEVICE_ID = 'lojadepaes';
  try {
    assert.equal(satelliteEnabled('PAY_SEND_DEVICE_ID', 'lojadepaes'), true);
    assert.equal(satelliteEnabled('PAY_SEND_DEVICE_ID', 'paneldx'), false);
  } finally {
    if (previous == null) delete process.env.PAY_SEND_DEVICE_ID;
    else process.env.PAY_SEND_DEVICE_ID = previous;
  }
});

test('o Pix não ganha pagador extra nem aparelho', () => {
  const source = createPixPayment.toString();
  assert.equal(source.includes('additional_info'), false);
  assert.equal(source.includes('X-meli-session-id'), false);
  assert.equal(source.includes('three_d_secure'), false);
  assert.equal(source.includes('PAY_SEND_PAYER_DATA'), false);
});

test('o log não mostra documento, telefone nem endereço', () => {
  const logs = [];
  const original = console.warn;
  console.warn = (...args) => logs.push(args.join(' '));
  try {
    normalizeSatellitePayer({
      first_name: 'Ana',
      identification: { type: 'CPF', number: '11111111111' },
      phone: '999',
      address: { street_name: 'Rua Muito Secreta XYZ', zip_code: '12' },
    });
  } finally {
    console.warn = original;
  }
  const text = logs.join('\n');
  assert.equal(text.includes('11111111111'), false);
  assert.equal(text.includes('Rua Muito Secreta'), false);
  assert.equal(text.includes('999'), false);
  assert.match(text, /identification/);
  assert.match(text, /phone/);
});

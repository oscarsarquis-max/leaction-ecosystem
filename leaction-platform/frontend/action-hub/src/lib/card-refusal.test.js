const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const {
  EXACT,
  GENERIC,
  customerCardMessage,
  presentCardFailure,
  UNMAPPED,
  messageLeaksTechnical,
  checkoutSafetyLine,
  CardRefusalNotice,
} = require('./card-refusal');

test('cada recusa vira frase sem código e sem cartão de teste', () => {
  const codes = [
    ...Object.keys(EXACT),
    'cc_rejected_bad_filled_card_number',
    'cc_rejected_bad_filled_date',
    'cc_rejected_bad_filled_security_code',
    'cc_rejected_bad_filled_other',
    'cc_rejected_bad_filled_zip',
    'cc_rejected_other_reason',
    '',
  ];
  for (const code of codes) {
    const phrase = customerCardMessage(code);
    assert.equal(messageLeaksTechnical(phrase), false, code);
    if (code) assert.equal(phrase.includes(code), false);
  }
  assert.equal(
    customerCardMessage('cc_rejected_high_risk'),
    'O pagamento com este cartão não foi aprovado pela análise de segurança do Mercado Pago. Tente outro cartão ou pague com Pix.',
  );
  assert.equal(customerCardMessage('desconhecido'), GENERIC);
});

test('a recusa aparece uma vez e oferece Pix, sem texto de teste', () => {
  const message = customerCardMessage('cc_rejected_high_risk');
  const html = renderToStaticMarkup(
    React.createElement(CardRefusalNotice, {
      message,
      pixHref: 'https://lojadepaes.com.br/pedido/LP77B815537C',
    }),
  );
  assert.equal((html.match(/role="alert"/g) || []).length, 1);
  assert.equal((html.match(/Pagar com Pix/g) || []).length, 1);
  assert.equal(html.includes('cc_rejected'), false);
  assert.equal(messageLeaksTechnical(html), false);
  assert.equal(html.includes('/pedido/LP77B815537C'), true);
});

test('credencial de produção não fala em cartão de teste e a frase do titular aparece uma vez', () => {
  const line = checkoutSafetyLine(false);
  assert.equal((line.match(/Use o cartão do titular da compra/g) || []).length, 1);
  assert.equal(/teste|APRO|5031/i.test(line), false);
  assert.equal(/teste/i.test(checkoutSafetyLine(true)), true);
});

test('erro 400 mostra a frase genérica e nenhum texto em inglês', () => {
  const presented = presentCardFailure({
    status: 400,
    mp_status_detail: '',
  });
  assert.equal(presented.message, UNMAPPED);
  assert.equal(presented.refused, true);
  const html = renderToStaticMarkup(
    React.createElement(CardRefusalNotice, {
      message: presented.message,
      pixHref: 'https://lojadepaes.com.br/pedido/LP77B815537C',
    }),
  );
  const english =
    'The name of the following parameters is wrong: [additional_info.payer.address.city]';
  assert.equal(html.includes(english), false);
  assert.equal(html.includes('parameters'), false);
  assert.equal(html.includes('additional_info'), false);
  assert.equal(html.includes(UNMAPPED), true);
  assert.equal((html.match(/Pagar com Pix/g) || []).length, 1);
});

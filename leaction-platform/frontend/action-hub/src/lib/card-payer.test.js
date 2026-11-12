const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { CPF_FORM_MESSAGE, cpfDigits, cardDocumentForSubmit, PayerCpf } = require('./card-payer');

test('o CPF do formulário só segue com dígitos válidos', () => {
  assert.equal(cpfDigits(''), null);
  assert.equal(cpfDigits('111.111.111-11'), null);
  assert.equal(cpfDigits('529.982.247-25'), '52998224725');
});

test('sem CPF válido o pagamento do formulário não é enviado', () => {
  assert.deepEqual(cardDocumentForSubmit('', true), {
    ok: false,
    digits: null,
    message: CPF_FORM_MESSAGE,
  });
  assert.equal(cardDocumentForSubmit('111.111.111-11', true).ok, false);
  const ready = cardDocumentForSubmit('529.982.247-25', true);
  assert.equal(ready.ok, true);
  assert.equal(ready.digits, '52998224725');
  assert.equal(cardDocumentForSubmit('', false).ok, true);
});

test('o campo de CPF é obrigatório e o script de segurança não existe', () => {
  const html = renderToStaticMarkup(
    React.createElement(PayerCpf, { value: '', onChange: () => {} }),
  );
  assert.equal((html.match(/CPF do titular/g) || []).length, 2);
  assert.equal(html.includes('recomendado'), false);
  assert.equal(html.includes('required'), true);
  const payer = fs.readFileSync(path.join(__dirname, 'card-payer.js'), 'utf8');
  const brick = fs.readFileSync(
    path.join(__dirname, '..', 'components', 'MercadoPagoSubscriptionBrick.tsx'),
    'utf8',
  );
  for (const source of [payer, brick, html]) {
    assert.equal(source.includes('security.js'), false);
    assert.equal(source.includes('MP_DEVICE_SESSION_ID'), false);
    assert.equal(source.includes('device_session_id'), false);
  }
});

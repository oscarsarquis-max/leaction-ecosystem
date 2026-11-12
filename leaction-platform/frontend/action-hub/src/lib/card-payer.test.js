const test = require('node:test');
const assert = require('node:assert/strict');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const {
  MP_SECURITY_SCRIPT,
  optionalCpfDigits,
  readDeviceSessionId,
  OptionalPayerCpf,
} = require('./card-payer');

test('o CPF é opcional: vazio segue, inválido é descartado, válido só tem dígitos', () => {
  assert.equal(optionalCpfDigits(''), null);
  assert.equal(optionalCpfDigits('111.111.111-11'), null);
  assert.equal(optionalCpfDigits('529.982.247-25'), '52998224725');
});

test('o campo de CPF não é obrigatório e o script de segurança não trava o pagamento', () => {
  const html = renderToStaticMarkup(
    React.createElement(OptionalPayerCpf, { value: '', onChange: () => {} }),
  );
  assert.equal((html.match(/CPF do titular \(recomendado\)/g) || []).length, 2);
  assert.equal(html.includes('required'), false);
  assert.equal(MP_SECURITY_SCRIPT.async, true);
  assert.equal(MP_SECURITY_SCRIPT.view, 'checkout');
  assert.equal(MP_SECURITY_SCRIPT.src, 'https://www.mercadopago.com/v2/security.js');
  assert.equal(readDeviceSessionId({}), '');
  assert.equal(readDeviceSessionId({ MP_DEVICE_SESSION_ID: 'sess-1' }), 'sess-1');
  assert.equal(readDeviceSessionId(null), '');
});

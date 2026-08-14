'use strict';

/**
 * Smoke local (sem HTTP) das regras aditivas do checkout School.
 * Não chama Mercado Pago nem altera pedidos.
 *
 *   node services/gateway-api/scripts/smoke-catalog-school-checkout.js
 */

const assert = require('assert');
const { isValidCpf, isValidCnpj, validatePayerDocument } = require('../domain/br-documents');
const {
  isSchoolCatalogApp,
  parseSchoolCatalogCheckout,
} = require('../domain/catalog-school-checkout');

assert.strictEqual(isSchoolCatalogApp('inove4us'), false);
assert.strictEqual(isSchoolCatalogApp('inove4us-school'), true);

assert.strictEqual(isValidCpf('529.982.247-25'), true);
assert.strictEqual(isValidCpf('111.111.111-11'), false);
assert.strictEqual(isValidCnpj('11.222.333/0001-81'), true);
assert.strictEqual(isValidCnpj('00.000.000/0000-00'), false);

const inoveLike = parseSchoolCatalogCheckout({
  app_id: 'inove4us-school',
  sku: 'school-starter-50',
  subject_id: 'diretor@escola.org',
  subject_type: 'email',
});
assert.strictEqual(inoveLike.ok, false, 'e-mail no subject_id do School deve falhar');

const ok = parseSchoolCatalogCheckout({
  app_id: 'inove4us-school',
  sku: 'school-starter-50',
  subject_id: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
  subject_type: 'instituicao',
  payer_email: 'diretor@escola.org',
  razao_social: 'Colégio Horizonte',
  payer_document: '52998224725',
  payer_document_type: 'cpf',
});
assert.strictEqual(ok.ok, true, ok.error);
assert.strictEqual(ok.fields.payer_document_type, 'cpf');
assert.strictEqual(ok.fields.instituicao_id, 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee');

const doc = validatePayerDocument('cnpj', '11222333000181');
assert.strictEqual(doc.ok, true);

console.log('smoke-catalog-school-checkout: OK');

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const {
  centsToMercadoPagoAmount,
  mercadoPagoAmountToCents,
  assertCents,
} = require('./money-cents');

describe('money-cents', () => {
  it('converte 2490 centavos para o decimal do MP via string, não divisão flutuante', () => {
    assert.equal(centsToMercadoPagoAmount(2490), Number('24.90'));
    assert.equal(centsToMercadoPagoAmount(1), Number('0.01'));
    assert.equal(centsToMercadoPagoAmount(100), Number('1.00'));
    assert.equal(centsToMercadoPagoAmount(10_000_000), Number('100000.00'));
  });

  it('volta do decimal do MP para o mesmo inteiro de centavos', () => {
    assert.equal(mercadoPagoAmountToCents('24.90'), 2490);
    assert.equal(mercadoPagoAmountToCents('24.9'), 2490);
    assert.equal(mercadoPagoAmountToCents(1), 100);
    assert.equal(mercadoPagoAmountToCents('0.01'), 1);
  });

  it('rejeita centavos fora da faixa e valores com mais de duas casas', () => {
    assert.throws(() => assertCents(0), /inteiro/);
    assert.throws(() => assertCents(10_000_001), /inteiro/);
    assert.throws(() => assertCents(24.9), /inteiro/);
    assert.throws(() => mercadoPagoAmountToCents('24.901'), /inválido/);
  });
});

'use strict';

/**
 * Unidades: contrato satélite↔Hub em centavos inteiros.
 * O Mercado Pago espera número decimal em reais; a conversão só acontece aqui,
 * com aritmética de inteiros (sem Number(cents) / 100).
 */

const MIN_CENTS = 1;
const MAX_CENTS = 10_000_000;

function assertCents(cents) {
  if (!Number.isInteger(cents) || cents < MIN_CENTS || cents > MAX_CENTS) {
    const err = new Error(
      `amount_cents deve ser inteiro entre ${MIN_CENTS} e ${MAX_CENTS}`
    );
    err.statusCode = 400;
    throw err;
  }
  return cents;
}

/** 2490 → 24.9 (número JSON para a API MP), via string "24.90". */
function centsToMercadoPagoAmount(cents) {
  const safe = assertCents(cents);
  const whole = Math.trunc(safe / 100);
  const frac = safe % 100;
  return Number(`${whole}.${String(frac).padStart(2, '0')}`);
}

/**
 * Converte o decimal do MP de volta para centavos.
 * Aceita number ou string "24.90". Recusa valores que não tenham no máximo 2 casas.
 */
function mercadoPagoAmountToCents(value) {
  if (value == null) {
    const err = new Error('valor Mercado Pago ausente');
    err.statusCode = 422;
    throw err;
  }
  const text = typeof value === 'number' && Number.isInteger(value)
    ? `${value}.00`
    : String(value).trim();
  const match = /^(-?)(\d+)\.(\d{1,2})$/.exec(text) || /^(-?)(\d+)$/.exec(text);
  if (!match) {
    const err = new Error('valor Mercado Pago inválido para conversão em centavos');
    err.statusCode = 422;
    throw err;
  }
  const sign = match[1] === '-' ? -1 : 1;
  const whole = Number(match[2]);
  const fracRaw = match[3] || '00';
  const frac = Number(fracRaw.padEnd(2, '0'));
  const cents = sign * (whole * 100 + frac);
  if (!Number.isInteger(cents)) {
    const err = new Error('valor Mercado Pago inválido para conversão em centavos');
    err.statusCode = 422;
    throw err;
  }
  return cents;
}

module.exports = {
  MIN_CENTS,
  MAX_CENTS,
  assertCents,
  centsToMercadoPagoAmount,
  mercadoPagoAmountToCents,
};

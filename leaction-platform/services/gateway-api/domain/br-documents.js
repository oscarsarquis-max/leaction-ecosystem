'use strict';

/** Validação de CPF/CNPJ (dígitos verificadores) para checkout B2B School. */

function onlyDigits(value) {
  return String(value || '').replace(/\D/g, '');
}

function allSameDigits(digits) {
  return /^(\d)\1+$/.test(digits);
}

function mod11(digits, weights) {
  const sum = digits
    .slice(0, weights.length)
    .split('')
    .reduce((acc, ch, i) => acc + Number(ch) * weights[i], 0);
  const rest = sum % 11;
  return rest < 2 ? 0 : 11 - rest;
}

function isValidCpf(raw) {
  const d = onlyDigits(raw);
  if (d.length !== 11 || allSameDigits(d)) return false;
  const dv1 = mod11(d, [10, 9, 8, 7, 6, 5, 4, 3, 2]);
  if (dv1 !== Number(d[9])) return false;
  const dv2 = mod11(d, [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]);
  return dv2 === Number(d[10]);
}

function isValidCnpj(raw) {
  const d = onlyDigits(raw);
  if (d.length !== 14 || allSameDigits(d)) return false;
  const dv1 = mod11(d, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  if (dv1 !== Number(d[12])) return false;
  const dv2 = mod11(d, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return dv2 === Number(d[13]);
}

/**
 * @param {string} type cnpj|cpf
 * @param {string} raw
 * @returns {{ ok: true, type: 'cnpj'|'cpf', digits: string } | { ok: false, error: string }}
 */
function validatePayerDocument(type, raw) {
  const kind = String(type || '').trim().toLowerCase();
  if (kind !== 'cnpj' && kind !== 'cpf') {
    return { ok: false, error: 'Informe o tipo de documento: cnpj ou cpf.' };
  }
  const digits = onlyDigits(raw);
  if (kind === 'cpf') {
    if (!isValidCpf(digits)) {
      return { ok: false, error: 'CPF inválido. Confira os dígitos.' };
    }
    return { ok: true, type: 'cpf', digits };
  }
  if (!isValidCnpj(digits)) {
    return { ok: false, error: 'CNPJ inválido. Confira os dígitos.' };
  }
  return { ok: true, type: 'cnpj', digits };
}

module.exports = {
  onlyDigits,
  isValidCpf,
  isValidCnpj,
  validatePayerDocument,
};

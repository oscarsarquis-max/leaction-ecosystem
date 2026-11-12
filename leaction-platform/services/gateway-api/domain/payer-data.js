'use strict';

/** CPF do formulário. Dígito inválido é descartado; a cobrança segue com o e-mail. */

function digitsOf(value) {
  return String(value || '').replace(/\D/g, '');
}

function isValidCpf(digits) {
  if (!/^\d{11}$/.test(digits) || /^(\d)\1{10}$/.test(digits)) return false;
  const check = (length) => {
    let sum = 0;
    for (let i = 0; i < length; i += 1) sum += Number(digits[i]) * (length + 1 - i);
    const mod = (sum * 10) % 11;
    return mod === 10 ? 0 : mod;
  };
  return check(9) === Number(digits[9]) && check(10) === Number(digits[10]);
}

function formCpfIdentification(raw) {
  const digits = digitsOf(raw);
  if (!digits) return null;
  if (!isValidCpf(digits)) {
    console.warn('[pagamento] campo do pagador descartado: identification');
    return null;
  }
  return { type: 'CPF', number: digits };
}

function buildLegacyCardPaymentBody({
  transactionAmount,
  token,
  description,
  installments,
  methodId,
  email,
  identification,
  externalReference,
}) {
  const payload = {
    transaction_amount: transactionAmount,
    token,
    description: description || 'Action Hub — pagamento',
    installments,
    payment_method_id: methodId,
    payer: {
      email,
      ...(identification ? { identification } : {}),
    },
  };
  if (externalReference) {
    payload.external_reference = String(externalReference);
  }
  return payload;
}

module.exports = {
  isValidCpf,
  formCpfIdentification,
  buildLegacyCardPaymentBody,
};

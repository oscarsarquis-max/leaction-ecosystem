const React = require('react');

const CPF_FORM_MESSAGE = 'Informe um CPF válido do titular para pagar com cartão.';

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

function cpfDigits(raw) {
  const digits = digitsOf(raw);
  if (!isValidCpf(digits)) return null;
  return digits;
}

function cardDocumentForSubmit(raw, required) {
  const digits = cpfDigits(raw);
  if (required && !digits) return { ok: false, digits: null, message: CPF_FORM_MESSAGE };
  return { ok: true, digits, message: '' };
}

function PayerCpf({ value, onChange }) {
  return React.createElement(
    'label',
    { className: 'mb-4 block text-sm text-slate-700' },
    React.createElement('span', { className: 'mb-1 block font-medium' }, 'CPF do titular'),
    React.createElement('input', {
      value: value || '',
      onChange: (event) => onChange(event.target.value),
      inputMode: 'numeric',
      autoComplete: 'off',
      required: true,
      'aria-required': true,
      'aria-label': 'CPF do titular',
      className: 'w-full rounded-xl border border-slate-300 px-3 py-3 text-sm',
    }),
  );
}

module.exports = {
  CPF_FORM_MESSAGE,
  cpfDigits,
  cardDocumentForSubmit,
  PayerCpf,
};

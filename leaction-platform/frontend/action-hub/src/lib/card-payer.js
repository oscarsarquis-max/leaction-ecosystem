const React = require('react');

const MP_SECURITY_SCRIPT = {
  src: 'https://www.mercadopago.com/v2/security.js',
  async: true,
  view: 'checkout',
};

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

function optionalCpfDigits(raw) {
  const digits = digitsOf(raw);
  if (!digits) return null;
  if (!isValidCpf(digits)) return null;
  return digits;
}

function readDeviceSessionId(source) {
  try {
    const host = source || (typeof window !== 'undefined' ? window : null);
    const value = host ? host.MP_DEVICE_SESSION_ID : '';
    return typeof value === 'string' ? value.trim() : '';
  } catch {
    return '';
  }
}

function OptionalPayerCpf({ value, onChange }) {
  return React.createElement(
    'label',
    { className: 'mb-4 block text-sm text-slate-700' },
    React.createElement('span', { className: 'mb-1 block font-medium' }, 'CPF do titular (recomendado)'),
    React.createElement('input', {
      value: value || '',
      onChange: (event) => onChange(event.target.value),
      inputMode: 'numeric',
      autoComplete: 'off',
      'aria-label': 'CPF do titular (recomendado)',
      className: 'w-full rounded-xl border border-slate-300 px-3 py-3 text-sm',
    }),
  );
}

module.exports = {
  MP_SECURITY_SCRIPT,
  optionalCpfDigits,
  readDeviceSessionId,
  OptionalPayerCpf,
};

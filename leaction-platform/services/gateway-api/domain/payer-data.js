'use strict';

/** Dados opcionais do pagador. Campo inválido é descartado; a cobrança segue. */

function satelliteEnabled(envName, appId) {
  const raw = String(process.env[envName] || '').trim().toLowerCase();
  if (!raw || raw === '0' || raw === 'false' || raw === 'off') return false;
  const id = String(appId || '').trim().toLowerCase();
  if (!id) return false;
  return raw
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .includes(id);
}

function statementDescriptorFor(appId) {
  const raw = String(process.env.PAY_STATEMENT_DESCRIPTOR || '').trim();
  const id = String(appId || '').trim().toLowerCase();
  if (!raw || !id) return null;
  for (const part of raw.split(',')) {
    const idx = part.indexOf(':');
    if (idx <= 0) continue;
    const app = part.slice(0, idx).trim().toLowerCase();
    const value = part
      .slice(idx + 1)
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 13);
    if (app === id && value) return value;
  }
  return null;
}

function discard(field) {
  console.warn(`[pagamento] campo do pagador descartado: ${field}`);
}

function omitted() {
  console.warn('[pagamento] pagador omitido na cobrança');
}

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

function isValidCnpj(digits) {
  if (!/^\d{14}$/.test(digits) || /^(\d)\1{13}$/.test(digits)) return false;
  const check = (length) => {
    let sum = 0;
    let pos = length - 7;
    for (let i = 0; i < length; i += 1) {
      sum += Number(digits[i]) * pos;
      pos = pos === 2 ? 9 : pos - 1;
    }
    const mod = sum % 11;
    return mod < 2 ? 0 : 11 - mod;
  };
  return check(12) === Number(digits[12]) && check(13) === Number(digits[13]);
}

function cleanName(value, max) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (!text || text.length > max) return null;
  if (!/^[\p{L}][\p{L} '\u2019.-]{0,}$/u.test(text)) return null;
  return text;
}

function normalizeIdentification(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const type = String(raw.type || '').trim().toUpperCase();
  const number = digitsOf(raw.number);
  if (type === 'CPF' && isValidCpf(number)) return { type, number };
  if (type === 'CNPJ' && isValidCnpj(number)) return { type, number };
  discard('identification');
  return null;
}

function normalizePhone(raw) {
  if (raw == null || raw === '') return null;
  const source = typeof raw === 'object' ? raw : { number: raw };
  let digits = digitsOf(`${source.area_code || ''}${source.number || ''}`);
  if (!digits && source.number == null && source.area_code == null) {
    digits = digitsOf(raw);
  }
  if (digits.startsWith('55') && (digits.length === 12 || digits.length === 13)) {
    digits = digits.slice(2);
  }
  if (digits.length !== 10 && digits.length !== 11) {
    discard('phone');
    return null;
  }
  return { area_code: digits.slice(0, 2), number: digits.slice(2) };
}

function normalizeAddress(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const address = {};
  const zip = digitsOf(raw.zip_code);
  if (raw.zip_code != null && raw.zip_code !== '') {
    if (zip.length === 8) address.zip_code = zip;
    else discard('zip_code');
  }
  if (raw.street_name != null && raw.street_name !== '') {
    const value = String(raw.street_name).replace(/\s+/g, ' ').trim().slice(0, 80);
    if (value) address.street_name = value;
    else discard('street_name');
  }
  if (raw.street_number != null && raw.street_number !== '') {
    const value = String(raw.street_number).replace(/\s+/g, ' ').trim().slice(0, 20);
    if (value) address.street_number = value;
    else discard('street_number');
  }
  if (raw.neighborhood != null && raw.neighborhood !== '') {
    const value = String(raw.neighborhood).replace(/\s+/g, ' ').trim().slice(0, 80);
    if (value) address.neighborhood = value;
    else discard('neighborhood');
  }
  if (raw.city != null && raw.city !== '') {
    const value = String(raw.city).replace(/\s+/g, ' ').trim().slice(0, 80);
    if (value) address.city = value;
    else discard('city');
  }
  if (raw.federal_unit != null && raw.federal_unit !== '') {
    const value = String(raw.federal_unit).trim().toUpperCase();
    if (/^[A-Z]{2}$/.test(value)) address.federal_unit = value;
    else discard('federal_unit');
  }
  if (!Object.keys(address).length) return null;
  return address;
}

function normalizeSatellitePayer(raw) {
  try {
    if (!raw || typeof raw !== 'object') return null;
    const payer = {};
    if (raw.first_name != null && raw.first_name !== '') {
      const first = cleanName(raw.first_name, 40);
      if (first) payer.first_name = first;
      else discard('first_name');
    }
    if (raw.last_name != null && raw.last_name !== '') {
      const last = cleanName(raw.last_name, 80);
      if (last) payer.last_name = last;
      else discard('last_name');
    }
    if (raw.email != null && raw.email !== '') {
      const email = String(raw.email).trim().toLowerCase();
      if (email.includes('@') && email.length <= 254 && !email.includes(' ')) payer.email = email;
      else discard('email');
    }
    if (raw.identification) {
      const identification = normalizeIdentification(raw.identification);
      if (identification) payer.identification = identification;
    }
    if (raw.phone) {
      const phone = normalizePhone(raw.phone);
      if (phone) payer.phone = phone;
    }
    if (raw.address) {
      const address = normalizeAddress(raw.address);
      if (address) payer.address = address;
    }
    return Object.keys(payer).length ? payer : null;
  } catch {
    omitted();
    return null;
  }
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

function enrichCardPaymentBody(legacy, { appId, payerProfile, payerDocument, description }) {
  const next = JSON.parse(JSON.stringify(legacy));
  const profile = normalizeSatellitePayer(payerProfile) || {};
  if (!profile.identification && payerDocument) {
    const identification = normalizeIdentification({ type: 'CPF', number: payerDocument });
    if (identification) profile.identification = identification;
  }
  if (profile.first_name) next.payer.first_name = profile.first_name;
  if (profile.last_name) next.payer.last_name = profile.last_name;
  if (profile.identification && !next.payer.identification) {
    next.payer.identification = profile.identification;
  }
  const infoPayer = {};
  if (profile.first_name) infoPayer.first_name = profile.first_name;
  if (profile.last_name) infoPayer.last_name = profile.last_name;
  if (profile.phone) infoPayer.phone = profile.phone;
  if (profile.address) infoPayer.address = profile.address;
  const amount = next.transaction_amount;
  const title = String(description || next.description || 'Pedido').slice(0, 120);
  next.additional_info = {
    ...(Object.keys(infoPayer).length ? { payer: infoPayer } : {}),
    items: [
      {
        title,
        quantity: 1,
        unit_price: amount,
        category_id: 'food',
      },
    ],
  };
  const descriptor = statementDescriptorFor(appId);
  if (descriptor) next.statement_descriptor = descriptor;
  return next;
}

function finalizeCardPaymentBody(legacy, options) {
  if (!options || !options.sendPayer) return legacy;
  try {
    return enrichCardPaymentBody(legacy, options);
  } catch {
    omitted();
    return legacy;
  }
}

function cardDeviceHeader(deviceSessionId, sendDevice) {
  if (!sendDevice) return null;
  const device = String(deviceSessionId || '').trim();
  if (!device || device.length > 120 || !/^[A-Za-z0-9._:-]+$/.test(device)) return null;
  return device;
}

module.exports = {
  satelliteEnabled,
  statementDescriptorFor,
  normalizeSatellitePayer,
  buildLegacyCardPaymentBody,
  finalizeCardPaymentBody,
  cardDeviceHeader,
  isValidCpf,
};

'use strict';

/**
 * S2S de rotação — mesmo padrão do Hub (Bearer + X-App-Secret).
 * Timeout curto: a versão anterior permanece ativa se isto falhar.
 */

const TIMEOUT_MS = 5000;

async function notifySatelliteRotation({ url, rotationSecret, tipo, novo_valor }) {
  const secret = String(rotationSecret || '').trim();
  if (!secret) {
    throw new Error('rotation_secret ausente para o canal S2S');
  }
  const target = String(url || '').trim();
  if (!target) {
    throw new Error('rotation_webhook_url ausente');
  }

  const res = await fetch(target, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${secret}`,
      'X-App-Secret': secret,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ tipo, novo_valor }),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`satélite HTTP ${res.status}: ${text.slice(0, 240)}`);
  }
  return { status: res.status, body: text.slice(0, 240) };
}

function generateSecretValue() {
  const { randomBytes } = require('crypto');
  return randomBytes(32).toString('base64url');
}

module.exports = {
  notifySatelliteRotation,
  generateSecretValue,
  TIMEOUT_MS,
};

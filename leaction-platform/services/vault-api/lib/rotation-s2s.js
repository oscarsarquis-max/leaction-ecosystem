'use strict';

/**
 * S2S de rotação — mesmo padrão do Hub (Bearer + X-App-Secret).
 * Timeout curto: a versão anterior permanece ativa se isto falhar.
 *
 * Dois canais isolados em sistemas_rotacao:
 *   - infraestrutura: rotation_webhook_url / rotation_secret
 *   - contas privilegiadas: conta_webhook_url / conta_secret
 */

const TIMEOUT_MS = 5000;

async function notifySatelliteChannel({
  url,
  channelSecret,
  payload,
  missingUrlMessage,
  missingSecretMessage,
}) {
  const secret = String(channelSecret || '').trim();
  if (!secret) {
    throw new Error(missingSecretMessage || 'secret ausente para o canal S2S');
  }
  const target = String(url || '').trim();
  if (!target) {
    throw new Error(missingUrlMessage || 'webhook_url ausente');
  }

  const res = await fetch(target, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${secret}`,
      'X-App-Secret': secret,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`satélite HTTP ${res.status}: ${text.slice(0, 240)}`);
  }
  return { status: res.status, body: text.slice(0, 240) };
}

async function notifySatelliteRotation({ url, rotationSecret, tipo, novo_valor }) {
  return notifySatelliteChannel({
    url,
    channelSecret: rotationSecret,
    payload: { tipo, novo_valor },
    missingSecretMessage: 'rotation_secret ausente para o canal S2S',
    missingUrlMessage: 'rotation_webhook_url ausente',
  });
}

async function notifySatelliteConta({ url, contaSecret, payload }) {
  return notifySatelliteChannel({
    url,
    channelSecret: contaSecret,
    payload,
    missingSecretMessage: 'conta_secret ausente para o canal S2S de contas',
    missingUrlMessage: 'conta_webhook_url ausente',
  });
}

function generateSecretValue() {
  const { randomBytes } = require('crypto');
  return randomBytes(32).toString('base64url');
}

module.exports = {
  notifySatelliteChannel,
  notifySatelliteRotation,
  notifySatelliteConta,
  generateSecretValue,
  TIMEOUT_MS,
};

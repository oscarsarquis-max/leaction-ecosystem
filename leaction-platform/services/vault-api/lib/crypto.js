'use strict';

/**
 * AES-256-GCM — chave mestra só em VAULT_MASTER_KEY (nunca no banco / repo).
 * Formato persistido: iv(12) || tag(16) || ciphertext
 */

const crypto = require('crypto');

const ALGO = 'aes-256-gcm';
const IV_LEN = 12;
const TAG_LEN = 16;
const KEY_LEN = 32;

function resolveMasterKey() {
  const raw = String(process.env.VAULT_MASTER_KEY || '').trim();
  if (!raw) {
    const err = new Error('VAULT_MASTER_KEY não configurada');
    err.status = 503;
    throw err;
  }

  if (/^[0-9a-fA-F]{64}$/.test(raw)) {
    return Buffer.from(raw, 'hex');
  }

  try {
    const fromB64 = Buffer.from(raw, 'base64');
    if (fromB64.length === KEY_LEN) return fromB64;
  } catch {
    /* ignore */
  }

  const err = new Error(
    'VAULT_MASTER_KEY inválida (use 32 bytes em hex de 64 chars ou base64)'
  );
  err.status = 503;
  throw err;
}

function encryptPlaintext(plain) {
  const key = resolveMasterKey();
  const iv = crypto.randomBytes(IV_LEN);
  const cipher = crypto.createCipheriv(ALGO, key, iv);
  const enc = Buffer.concat([cipher.update(String(plain), 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, enc]);
}

function decryptBuffer(buf) {
  if (!Buffer.isBuffer(buf) || buf.length < IV_LEN + TAG_LEN + 1) {
    const err = new Error('valor_cifrado inválido');
    err.status = 500;
    throw err;
  }
  const key = resolveMasterKey();
  const iv = buf.subarray(0, IV_LEN);
  const tag = buf.subarray(IV_LEN, IV_LEN + TAG_LEN);
  const data = buf.subarray(IV_LEN + TAG_LEN);
  const decipher = crypto.createDecipheriv(ALGO, key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(data), decipher.final()]).toString('utf8');
}

module.exports = {
  encryptPlaintext,
  decryptBuffer,
  resolveMasterKey,
};

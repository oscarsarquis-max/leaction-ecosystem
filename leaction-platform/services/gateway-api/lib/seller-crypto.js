'use strict';

/**
 * Cifra de tokens OAuth do recebedor (AES-256-GCM).
 * Formato armazenado: base64(iv 12 | tag 16 | ciphertext).
 * Chave: SELLER_TOKEN_KEY = 32 bytes em base64.
 */

const crypto = require('crypto');

const IV_LEN = 12;
const TAG_LEN = 16;
const KEY_LEN = 32;

function loadSellerTokenKey(raw = process.env.SELLER_TOKEN_KEY) {
  const value = String(raw || '').trim();
  if (!value) {
    const err = new Error('SELLER_TOKEN_KEY ausente');
    err.statusCode = 503;
    throw err;
  }
  let key;
  try {
    key = Buffer.from(value, 'base64');
  } catch {
    const err = new Error('SELLER_TOKEN_KEY inválida');
    err.statusCode = 503;
    throw err;
  }
  if (key.length !== KEY_LEN) {
    const err = new Error('SELLER_TOKEN_KEY deve ter 32 bytes em base64');
    err.statusCode = 503;
    throw err;
  }
  return key;
}

function encryptSellerSecret(plainText, keyRaw) {
  const key = loadSellerTokenKey(keyRaw);
  const iv = crypto.randomBytes(IV_LEN);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const enc = Buffer.concat([
    cipher.update(String(plainText), 'utf8'),
    cipher.final(),
  ]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, enc]).toString('base64');
}

function decryptSellerSecret(blob, keyRaw) {
  const key = loadSellerTokenKey(keyRaw);
  const buf = Buffer.from(String(blob || ''), 'base64');
  if (buf.length < IV_LEN + TAG_LEN + 1) {
    const err = new Error('blob cifrado inválido');
    err.statusCode = 500;
    throw err;
  }
  const iv = buf.subarray(0, IV_LEN);
  const tag = buf.subarray(IV_LEN, IV_LEN + TAG_LEN);
  const data = buf.subarray(IV_LEN + TAG_LEN);
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(data), decipher.final()]).toString('utf8');
}

module.exports = {
  encryptSellerSecret,
  decryptSellerSecret,
  loadSellerTokenKey,
};

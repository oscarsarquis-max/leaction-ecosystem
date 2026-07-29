/**
 * Criptografia em nível de aplicação (AES-256-GCM) para PII — LGPD art. 46 / ASVS 5.0.
 * Formato persistido: base64( iv[12] || ciphertext || tag[16] )
 * Lookup de e-mail: HMAC-SHA256 (emailHash), nunca decrypt em massa.
 */
import { createCipheriv, createDecipheriv, createHmac, randomBytes, timingSafeEqual } from 'node:crypto'

const ALGO = 'aes-256-gcm'
const IV_LEN = 12
const TAG_LEN = 16

function getKey(): Buffer {
  const raw = process.env.PII_ENCRYPTION_KEY
  if (!raw || !raw.trim()) {
    throw new Error('PII_ENCRYPTION_KEY ausente — defina 32 bytes em base64 no .env')
  }
  const key = Buffer.from(raw.trim(), 'base64')
  if (key.length !== 32) {
    throw new Error(`PII_ENCRYPTION_KEY deve ter 32 bytes (base64); recebido ${key.length}`)
  }
  return key
}

export function encryptPii(plaintext: string): string {
  const key = getKey()
  const iv = randomBytes(IV_LEN)
  const cipher = createCipheriv(ALGO, key, iv)
  const enc = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()])
  const tag = cipher.getAuthTag()
  return Buffer.concat([iv, enc, tag]).toString('base64')
}

export function decryptPii(payloadB64: string): string {
  const key = getKey()
  const buf = Buffer.from(payloadB64, 'base64')
  if (buf.length < IV_LEN + TAG_LEN + 1) {
    throw new Error('Ciphertext PII inválido')
  }
  const iv = buf.subarray(0, IV_LEN)
  const tag = buf.subarray(buf.length - TAG_LEN)
  const data = buf.subarray(IV_LEN, buf.length - TAG_LEN)
  const decipher = createDecipheriv(ALGO, key, iv)
  decipher.setAuthTag(tag)
  return Buffer.concat([decipher.update(data), decipher.final()]).toString('utf8')
}

/** Normaliza e-mail e gera hash HMAC para índice único / login. */
export function hashEmail(email: string): string {
  const key = getKey()
  const normalized = email.trim().toLowerCase()
  return createHmac('sha256', key).update(normalized).digest('hex')
}

export function emailsMatchHash(email: string, emailHash: string): boolean {
  const a = Buffer.from(hashEmail(email), 'hex')
  const b = Buffer.from(emailHash, 'hex')
  if (a.length !== b.length) return false
  return timingSafeEqual(a, b)
}

/** Redação segura para logs — nunca emitir PII/credenciais. */
export function redactForLog(value: unknown): string {
  if (value == null) return String(value)
  if (typeof value === 'string') {
    if (value.length <= 4) return '***'
    return `${value.slice(0, 2)}…[${value.length} chars]`
  }
  return '[redacted]'
}

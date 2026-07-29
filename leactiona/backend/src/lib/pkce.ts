import { createHash, timingSafeEqual } from 'node:crypto'

export function assertS256Challenge(codeChallenge: string): void {
  // Base64url sem padding, 43 chars típicos para SHA-256
  if (!/^[A-Za-z0-9_-]{43}$/.test(codeChallenge)) {
    throw Object.assign(new Error('code_challenge inválido (S256)'), { statusCode: 400 })
  }
}

export function verifyPkceS256(codeVerifier: string, codeChallenge: string): boolean {
  if (!codeVerifier || codeVerifier.length < 43 || codeVerifier.length > 128) return false
  const digest = createHash('sha256').update(codeVerifier).digest()
  const computed = digest
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
  const a = Buffer.from(computed)
  const b = Buffer.from(codeChallenge)
  if (a.length !== b.length) return false
  return timingSafeEqual(a, b)
}

export function challengeFromVerifier(codeVerifier: string): string {
  return createHash('sha256')
    .update(codeVerifier)
    .digest('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

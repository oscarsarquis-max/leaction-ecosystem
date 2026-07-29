import {
  calculateJwkThumbprint,
  compactVerify,
  decodeProtectedHeader,
  importJWK,
  type JWK,
  type JWTPayload,
} from 'jose'
import { createHash, timingSafeEqual } from 'node:crypto'

export type DpopContext = {
  jkt: string
  htm: string
  htu: string
}

/**
 * Valida proof DPoP (FAPI 2.0 / RFC 9449 simplificado).
 * Exige header DPoP, typ=dpop+jwt, jwk pública no header, claims htm/htu/iat/jti.
 */
export async function verifyDpopProof(opts: {
  dpopHeader: string
  method: string
  url: string
  accessToken?: string
  expectedJkt?: string
}): Promise<DpopContext> {
  const { dpopHeader, method, url, accessToken, expectedJkt } = opts
  if (!dpopHeader) {
    throw Object.assign(new Error('Cabeçalho DPoP obrigatório'), { statusCode: 401 })
  }

  const header = decodeProtectedHeader(dpopHeader)
  if (header.typ !== 'dpop+jwt') {
    throw Object.assign(new Error('DPoP typ inválido'), { statusCode: 401 })
  }
  if (!header.jwk || typeof header.jwk !== 'object') {
    throw Object.assign(new Error('DPoP sem jwk no header'), { statusCode: 401 })
  }

  const jwk = header.jwk as JWK
  const key = await importJWK(jwk, header.alg)
  const { payload } = await compactVerify(dpopHeader, key)
  const claims = JSON.parse(new TextDecoder().decode(payload)) as JWTPayload & {
    htm?: string
    htu?: string
    ath?: string
    jti?: string
  }

  if (!claims.jti || !claims.iat) {
    throw Object.assign(new Error('DPoP sem jti/iat'), { statusCode: 401 })
  }
  const age = Math.abs(Date.now() / 1000 - Number(claims.iat))
  if (age > 60) {
    throw Object.assign(new Error('DPoP expirado'), { statusCode: 401 })
  }

  if ((claims.htm ?? '').toUpperCase() !== method.toUpperCase()) {
    throw Object.assign(new Error('DPoP htm não confere'), { statusCode: 401 })
  }

  // Compara htu sem query string
  const expectedHtu = url.split('?')[0]
  if (claims.htu !== expectedHtu) {
    throw Object.assign(new Error('DPoP htu não confere'), { statusCode: 401 })
  }

  const jkt = await calculateJwkThumbprint(jwk, 'sha256')
  if (expectedJkt && expectedJkt !== jkt) {
    throw Object.assign(new Error('DPoP jkt não corresponde ao token'), { statusCode: 401 })
  }

  if (accessToken) {
    const ath = createHash('sha256').update(accessToken).digest('base64url')
    if (!claims.ath || !safeEq(claims.ath, ath)) {
      throw Object.assign(new Error('DPoP ath inválido'), { statusCode: 401 })
    }
  }

  return { jkt, htm: method.toUpperCase(), htu: expectedHtu }
}

function safeEq(a: string, b: string): boolean {
  const ba = Buffer.from(a)
  const bb = Buffer.from(b)
  if (ba.length !== bb.length) return false
  return timingSafeEqual(ba, bb)
}

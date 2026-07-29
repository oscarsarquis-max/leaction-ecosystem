import { createHash, randomBytes } from 'node:crypto'
import { exportJWK, generateKeyPair, SignJWT, type JWK, type KeyLike } from 'jose'
import type { FastifyInstance } from 'fastify'
import { challengeFromVerifier } from '../../backend/src/lib/pkce.js'

export const TEST_HOST = '127.0.0.1:5020'
export const TEST_BASE = `http://${TEST_HOST}`

export async function makeDpopKey() {
  const { privateKey, publicKey } = await generateKeyPair('ES256', { extractable: true })
  const jwk = await exportJWK(publicKey)
  const publicJwk: JWK = { kty: jwk.kty, crv: jwk.crv, x: jwk.x, y: jwk.y }
  return { privateKey, publicJwk }
}

export async function signDpop(opts: {
  privateKey: KeyLike
  publicJwk: JWK
  method: string
  path: string
  accessToken?: string
}): Promise<string> {
  const htu = `${TEST_BASE}${opts.path}`
  const payload: Record<string, string> = {
    htm: opts.method.toUpperCase(),
    htu,
    jti: randomBytes(16).toString('hex'),
  }
  if (opts.accessToken) {
    payload.ath = createHash('sha256').update(opts.accessToken).digest('base64url')
  }
  return new SignJWT(payload)
    .setProtectedHeader({ alg: 'ES256', typ: 'dpop+jwt', jwk: opts.publicJwk })
    .setIssuedAt()
    .sign(opts.privateKey)
}

export async function loginAs(
  app: FastifyInstance,
  email: string,
  password: string,
): Promise<{ accessToken: string; privateKey: KeyLike; publicJwk: JWK }> {
  const { privateKey, publicJwk } = await makeDpopKey()
  const codeVerifier = randomBytes(32).toString('base64url')
  const codeChallenge = challengeFromVerifier(codeVerifier)
  const path = '/api/v1/auth/login'
  const dpop = await signDpop({ privateKey, publicJwk, method: 'POST', path })
  const res = await app.inject({
    method: 'POST',
    url: path,
    headers: {
      host: TEST_HOST,
      'content-type': 'application/json',
      dpop,
    },
    payload: {
      email,
      password,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
    },
  })
  if (res.statusCode !== 200) {
    throw new Error(`login failed ${res.statusCode}: ${res.body}`)
  }
  const body = res.json() as { access_token: string }
  return { accessToken: body.access_token, privateKey, publicJwk }
}

export async function authedGet(
  app: FastifyInstance,
  path: string,
  session: { accessToken: string; privateKey: KeyLike; publicJwk: JWK },
) {
  const dpop = await signDpop({
    privateKey: session.privateKey,
    publicJwk: session.publicJwk,
    method: 'GET',
    path,
    accessToken: session.accessToken,
  })
  return app.inject({
    method: 'GET',
    url: path,
    headers: {
      host: TEST_HOST,
      authorization: `Bearer ${session.accessToken}`,
      dpop,
    },
  })
}

import 'dotenv/config'
import assert from 'node:assert/strict'
import { createHash, randomBytes } from 'node:crypto'
import { after, before, describe, it } from 'node:test'
import { exportJWK, generateKeyPair, SignJWT, type JWK, type KeyLike } from 'jose'
import { prisma } from '../backend/src/lib/prisma.js'
import { createUserEncrypted } from '../backend/src/lib/users.js'
import { decryptPii, encryptPii } from '../backend/src/lib/crypto.js'
import { challengeFromVerifier } from '../backend/src/lib/pkce.js'
import { buildApp } from '../backend/src/app.js'
import type { FastifyInstance } from 'fastify'

const HOST = '127.0.0.1:5020'
const BASE = `http://${HOST}`

async function makeDpopKey() {
  const { privateKey, publicKey } = await generateKeyPair('ES256', { extractable: true })
  const jwk = await exportJWK(publicKey)
  // Apenas componentes públicos no header DPoP
  const publicJwk: JWK = { kty: jwk.kty, crv: jwk.crv, x: jwk.x, y: jwk.y }
  return { privateKey, publicJwk }
}

async function signDpop(opts: {
  privateKey: KeyLike
  publicJwk: JWK
  method: string
  path: string
  accessToken?: string
}): Promise<string> {
  const htu = `${BASE}${opts.path}`
  const payload: Record<string, string> = {
    htm: opts.method.toUpperCase(),
    htu,
    jti: randomBytes(16).toString('hex'),
  }
  if (opts.accessToken) {
    payload.ath = createHash('sha256').update(opts.accessToken).digest('base64url')
  }
  return new SignJWT(payload)
    .setProtectedHeader({
      alg: 'ES256',
      typ: 'dpop+jwt',
      jwk: opts.publicJwk,
    })
    .setIssuedAt()
    .sign(opts.privateKey)
}

describe('auth-rbac (prompt 2)', () => {
  let app: FastifyInstance

  before(async () => {
    assert.ok(process.env.DATABASE_URL)
    assert.ok(process.env.PII_ENCRYPTION_KEY)

    await prisma.organization.upsert({
      where: { id: 'global' },
      create: { id: 'global', name: 'LEACTIONA' },
      update: {},
    })

    await prisma.refreshToken.deleteMany()
    await prisma.user.deleteMany()

    app = await buildApp()
    await app.ready()
  })

  after(async () => {
    await app.close()
    await prisma.$disconnect()
  })

  it('AES-256-GCM: CPF cifrado no banco e recuperado em claro', async () => {
    const cpf = '98765432100'
    const created = await createUserEncrypted({
      name: 'Aluno Crypto',
      email: `crypto.${Date.now()}@leactiona.local`,
      cpf,
      password: 'SenhaSegura!9xK2',
      role: 'STUDENT',
    })

    const row = await prisma.user.findUniqueOrThrow({ where: { id: created.id } })
    assert.notEqual(row.cpfEnc, cpf)
    assert.notEqual(row.cpfEnc, encryptPii(cpf)) // IV aleatório ⇒ ciphertext diferente
    assert.equal(decryptPii(row.cpfEnc), cpf)
    assert.equal(created.cpf, cpf)
  })

  it('RBAC: STUDENT recebe 403 em rota exclusiva ADMIN', async () => {
    const email = `student.${Date.now()}@leactiona.local`
    const password = 'SenhaSegura!9xK2'
    await createUserEncrypted({
      name: 'Aluno RBAC',
      email,
      cpf: '11122233344',
      password,
      role: 'STUDENT',
    })

    const { privateKey, publicJwk } = await makeDpopKey()
    const codeVerifier = randomBytes(32).toString('base64url')
    const codeChallenge = challengeFromVerifier(codeVerifier)

    const loginPath = '/api/v1/auth/login'
    const dpopLogin = await signDpop({
      privateKey,
      publicJwk,
      method: 'POST',
      path: loginPath,
    })

    const loginRes = await app.inject({
      method: 'POST',
      url: loginPath,
      headers: {
        host: HOST,
        'content-type': 'application/json',
        dpop: dpopLogin,
      },
      payload: {
        email,
        password,
        code_challenge: codeChallenge,
        code_challenge_method: 'S256',
      },
    })

    assert.equal(loginRes.statusCode, 200, loginRes.body)
    const body = loginRes.json() as {
      access_token: string
      role: string
    }
    assert.equal(body.role, 'STUDENT')
    assert.ok(body.access_token)

    const adminPath = '/api/v1/admin/ping'
    const dpopAdmin = await signDpop({
      privateKey,
      publicJwk,
      method: 'GET',
      path: adminPath,
      accessToken: body.access_token,
    })

    const adminRes = await app.inject({
      method: 'GET',
      url: adminPath,
      headers: {
        host: HOST,
        authorization: `Bearer ${body.access_token}`,
        dpop: dpopAdmin,
      },
    })

    assert.equal(adminRes.statusCode, 403, adminRes.body)
  })

  it('ADMIN autentica e acessa /api/v1/admin/ping com 200', async () => {
    const email = `admin.${Date.now()}@leactiona.local`
    const password = 'SenhaSegura!9xK2'
    await createUserEncrypted({
      name: 'Admin RBAC',
      email,
      cpf: '55566677788',
      password,
      role: 'ADMIN',
    })

    const { privateKey, publicJwk } = await makeDpopKey()
    const codeVerifier = randomBytes(32).toString('base64url')
    const codeChallenge = challengeFromVerifier(codeVerifier)
    const loginPath = '/api/v1/auth/login'
    const dpopLogin = await signDpop({
      privateKey,
      publicJwk,
      method: 'POST',
      path: loginPath,
    })

    const loginRes = await app.inject({
      method: 'POST',
      url: loginPath,
      headers: {
        host: HOST,
        'content-type': 'application/json',
        dpop: dpopLogin,
      },
      payload: {
        email,
        password,
        code_challenge: codeChallenge,
        code_challenge_method: 'S256',
      },
    })
    assert.equal(loginRes.statusCode, 200, loginRes.body)
    const { access_token } = loginRes.json() as { access_token: string }

    const adminPath = '/api/v1/admin/ping'
    const dpopAdmin = await signDpop({
      privateKey,
      publicJwk,
      method: 'GET',
      path: adminPath,
      accessToken: access_token,
    })
    const adminRes = await app.inject({
      method: 'GET',
      url: adminPath,
      headers: {
        host: HOST,
        authorization: `Bearer ${access_token}`,
        dpop: dpopAdmin,
      },
    })
    assert.equal(adminRes.statusCode, 200, adminRes.body)
  })
})

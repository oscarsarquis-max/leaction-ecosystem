import { randomBytes } from 'node:crypto'
import { SignJWT, jwtVerify, type JWTPayload } from 'jose'
import type { UserRole } from '@prisma/client'
import { prisma } from './prisma.js'
import { getJwtKeys } from './jwt-keys.js'
import { hashOpaqueToken } from './password.js'

export const ACCESS_TTL_SEC = 15 * 60 // 15 min — ASVS
export const REFRESH_TTL_SEC = 7 * 24 * 60 * 60

export type AccessClaims = JWTPayload & {
  sub: string
  role: UserRole
  org: 'global'
  cnf: { jkt: string }
}

export async function signAccessToken(input: {
  userId: string
  role: UserRole
  jkt: string
}): Promise<{ accessToken: string; expiresIn: number }> {
  const { privateKey } = await getJwtKeys()
  const expiresIn = ACCESS_TTL_SEC
  const accessToken = await new SignJWT({
    role: input.role,
    org: 'global',
    cnf: { jkt: input.jkt },
  })
    .setProtectedHeader({ alg: 'RS256', typ: 'at+jwt' })
    .setSubject(input.userId)
    .setIssuer(process.env.JWT_ISSUER ?? 'https://leactiona.com.br')
    .setAudience(process.env.JWT_AUDIENCE ?? 'leactiona-api')
    .setIssuedAt()
    .setExpirationTime(`${expiresIn}s`)
    .sign(privateKey)

  return { accessToken, expiresIn }
}

export async function verifyAccessToken(token: string): Promise<AccessClaims> {
  const { publicKey } = await getJwtKeys()
  const { payload } = await jwtVerify(token, publicKey, {
    issuer: process.env.JWT_ISSUER ?? 'https://leactiona.com.br',
    audience: process.env.JWT_AUDIENCE ?? 'leactiona-api',
  })
  const role = payload.role as UserRole | undefined
  const cnf = payload.cnf as { jkt?: string } | undefined
  if (!payload.sub || !role || !cnf?.jkt) {
    throw Object.assign(new Error('Access token inválido'), { statusCode: 401 })
  }
  return payload as AccessClaims
}

export async function issueRefreshToken(input: {
  userId: string
  codeChallenge: string
  dpopJkt: string
}): Promise<string> {
  const raw = randomBytes(32).toString('base64url')
  const tokenHash = hashOpaqueToken(raw)
  const expiresAt = new Date(Date.now() + REFRESH_TTL_SEC * 1000)
  await prisma.refreshToken.create({
    data: {
      userId: input.userId,
      tokenHash,
      codeChallenge: input.codeChallenge,
      dpopJkt: input.dpopJkt,
      expiresAt,
    },
  })
  return raw
}

export async function rotateRefreshToken(input: {
  refreshToken: string
  codeVerifierOk: boolean
  dpopJkt: string
}): Promise<{ userId: string; role: UserRole; newRefresh: string } | null> {
  if (!input.codeVerifierOk) return null
  const tokenHash = hashOpaqueToken(input.refreshToken)
  const row = await prisma.refreshToken.findUnique({
    where: { tokenHash },
    include: { user: true },
  })
  if (!row || row.revokedAt || row.expiresAt < new Date()) return null
  if (row.dpopJkt !== input.dpopJkt) return null

  await prisma.refreshToken.update({
    where: { id: row.id },
    data: { revokedAt: new Date() },
  })

  const newRefresh = await issueRefreshToken({
    userId: row.userId,
    codeChallenge: row.codeChallenge,
    dpopJkt: row.dpopJkt,
  })

  return { userId: row.userId, role: row.user.role, newRefresh }
}

export async function getRefreshChallenge(refreshToken: string): Promise<string | null> {
  const row = await prisma.refreshToken.findUnique({
    where: { tokenHash: hashOpaqueToken(refreshToken) },
  })
  if (!row || row.revokedAt || row.expiresAt < new Date()) return null
  return row.codeChallenge
}

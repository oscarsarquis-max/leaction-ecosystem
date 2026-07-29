import type { FastifyPluginAsync } from 'fastify'
import { z } from 'zod'
import { compare as bcryptCompare } from 'bcryptjs'
import { prisma } from '../lib/prisma.js'
import { hashEmail } from '../lib/crypto.js'
import { assertS256Challenge, verifyPkceS256 } from '../lib/pkce.js'
import { verifyDpopProof } from '../lib/dpop.js'
import {
  getRefreshChallenge,
  issueRefreshToken,
  rotateRefreshToken,
  signAccessToken,
} from '../lib/tokens.js'
import { toUserPlain } from '../lib/users.js'

const loginBody = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  code_challenge: z.string().min(43).max(128),
  code_challenge_method: z.literal('S256'),
})

const refreshBody = z.object({
  grant_type: z.literal('refresh_token'),
  refresh_token: z.string().min(20),
  code_verifier: z.string().min(43).max(128),
})

function absoluteUrl(req: { headers: Record<string, unknown>; url: string; protocol?: string }): string {
  const proto = (req.headers['x-forwarded-proto'] as string) || 'http'
  const host = (req.headers.host as string) || '127.0.0.1'
  return `${proto}://${host}${req.url.split('?')[0]}`
}

export const authRoutes: FastifyPluginAsync = async (app) => {
  /**
   * POST /api/v1/auth/login
   * Retorna JWT RS256 (≤15min) + refresh. Exige PKCE S256 + DPoP (FAPI 2.0).
   */
  app.post('/api/v1/auth/login', async (req, reply) => {
    const parsed = loginBody.safeParse(req.body)
    if (!parsed.success) {
      return reply.code(400).send({ error: 'invalid_request', details: parsed.error.flatten() })
    }
    const { email, password, code_challenge, code_challenge_method } = parsed.data
    if (code_challenge_method !== 'S256') {
      return reply.code(400).send({ error: 'unsupported_challenge_method' })
    }
    try {
      assertS256Challenge(code_challenge)
    } catch {
      return reply.code(400).send({ error: 'invalid_code_challenge' })
    }

    const dpopHeader = req.headers.dpop
    if (typeof dpopHeader !== 'string') {
      return reply.code(401).send({ error: 'dpop_required' })
    }

    let jkt: string
    try {
      const dpop = await verifyDpopProof({
        dpopHeader,
        method: 'POST',
        url: absoluteUrl(req),
      })
      jkt = dpop.jkt
    } catch (e) {
      const err = e as Error & { statusCode?: number }
      return reply.code(err.statusCode ?? 401).send({ error: 'invalid_dpop', message: err.message })
    }

    const row = await prisma.user.findUnique({
      where: { emailHash: hashEmail(email) },
    })
    // Resposta uniforme — não revelar se e-mail existe
    if (!row) {
      return reply.code(401).send({ error: 'invalid_credentials' })
    }
    const ok = await bcryptCompare(password, row.passwordHash)
    if (!ok) {
      return reply.code(401).send({ error: 'invalid_credentials' })
    }

    const { accessToken, expiresIn } = await signAccessToken({
      userId: row.id,
      role: row.role,
      jkt,
    })
    const refreshToken = await issueRefreshToken({
      userId: row.id,
      codeChallenge: code_challenge,
      dpopJkt: jkt,
    })

    const user = toUserPlain(row)
    return {
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: 'DPoP',
      expires_in: expiresIn,
      role: user.role,
      // e-mail descriptografado só para o próprio titular autenticado
      user: { id: user.id, role: user.role, organization_id: 'global' },
    }
  })

  /** Refresh com PKCE code_verifier + DPoP (mesmo jkt da sessão). */
  app.post('/api/v1/auth/token', async (req, reply) => {
    const parsed = refreshBody.safeParse(req.body)
    if (!parsed.success) {
      return reply.code(400).send({ error: 'invalid_request' })
    }

    const dpopHeader = req.headers.dpop
    if (typeof dpopHeader !== 'string') {
      return reply.code(401).send({ error: 'dpop_required' })
    }

    let jkt: string
    try {
      const dpop = await verifyDpopProof({
        dpopHeader,
        method: 'POST',
        url: absoluteUrl(req),
      })
      jkt = dpop.jkt
    } catch (e) {
      const err = e as Error & { statusCode?: number }
      return reply.code(err.statusCode ?? 401).send({ error: 'invalid_dpop', message: err.message })
    }

    const challenge = await getRefreshChallenge(parsed.data.refresh_token)
    if (!challenge) {
      return reply.code(401).send({ error: 'invalid_grant' })
    }
    const verifierOk = verifyPkceS256(parsed.data.code_verifier, challenge)
    const rotated = await rotateRefreshToken({
      refreshToken: parsed.data.refresh_token,
      codeVerifierOk: verifierOk,
      dpopJkt: jkt,
    })
    if (!rotated) {
      return reply.code(401).send({ error: 'invalid_grant' })
    }

    const { accessToken, expiresIn } = await signAccessToken({
      userId: rotated.userId,
      role: rotated.role,
      jkt,
    })

    return {
      access_token: accessToken,
      refresh_token: rotated.newRefresh,
      token_type: 'DPoP',
      expires_in: expiresIn,
    }
  })
}

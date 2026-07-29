import type { FastifyPluginAsync, FastifyReply, FastifyRequest } from 'fastify'
import type { UserRole } from '@prisma/client'
import { verifyAccessToken, type AccessClaims } from '../lib/tokens.js'
import { verifyDpopProof } from '../lib/dpop.js'

export type AuthUser = {
  id: string
  role: UserRole
  organizationId: 'global'
  jkt: string
  accessToken: string
}

declare module 'fastify' {
  interface FastifyRequest {
    authUser?: AuthUser
  }
}

function absoluteUrl(req: FastifyRequest): string {
  const proto = (req.headers['x-forwarded-proto'] as string) || 'http'
  const host = req.headers.host || '127.0.0.1'
  return `${proto}://${host}${req.url.split('?')[0]}`
}

export async function authenticate(req: FastifyRequest, _reply: FastifyReply): Promise<void> {
  const header = req.headers.authorization
  if (!header?.startsWith('Bearer ')) {
    throw Object.assign(new Error('Bearer token obrigatório'), { statusCode: 401 })
  }
  const accessToken = header.slice('Bearer '.length).trim()
  const claims: AccessClaims = await verifyAccessToken(accessToken)
  const jkt = claims.cnf.jkt

  const dpop = req.headers.dpop
  if (typeof dpop !== 'string') {
    throw Object.assign(new Error('DPoP obrigatório nas rotas protegidas'), { statusCode: 401 })
  }

  await verifyDpopProof({
    dpopHeader: dpop,
    method: req.method,
    url: absoluteUrl(req),
    accessToken,
    expectedJkt: jkt,
  })

  req.authUser = {
    id: claims.sub!,
    role: claims.role,
    organizationId: 'global',
    jkt,
    accessToken,
  }
}

export function requireRoles(...allowed: UserRole[]) {
  return async (req: FastifyRequest, _reply: FastifyReply): Promise<void> => {
    await authenticate(req, _reply)
    const role = req.authUser?.role
    if (!role || !allowed.includes(role)) {
      throw Object.assign(new Error('Forbidden — papel insuficiente (RBAC)'), {
        statusCode: 403,
      })
    }
  }
}

export const authPlugin: FastifyPluginAsync = async (app) => {
  app.decorate('authenticate', authenticate)
  app.decorate('requireRoles', requireRoles)
}

declare module 'fastify' {
  interface FastifyInstance {
    authenticate: typeof authenticate
    requireRoles: typeof requireRoles
  }
}

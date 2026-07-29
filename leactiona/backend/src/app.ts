import Fastify from 'fastify'
import helmet from '@fastify/helmet'
import rateLimit from '@fastify/rate-limit'
import cors from '@fastify/cors'
import { prisma } from './lib/prisma.js'
import { authPlugin } from './plugins/auth.js'
import { authRoutes } from './routes/auth.js'
import { adminRoutes } from './routes/admin.js'
import { lmsRoutes } from './routes/lms.js'
import { xapiRoutes } from './routes/xapi.js'
import { gamificationRoutes } from './routes/gamification.js'
import { certificateRoutes } from './routes/certificates.js'

function corsOrigins(): string[] | boolean {
  const raw = process.env.CORS_ALLOWED_ORIGINS?.trim()
  if (process.env.NODE_ENV === 'production') {
    if (!raw) {
      throw new Error('CORS_ALLOWED_ORIGINS obrigatório em production')
    }
    return raw.split(',').map((s) => s.trim()).filter(Boolean)
  }
  if (!raw) {
    // Dev: FE estático Next (:3020) + API (:5020)
    return ['http://127.0.0.1:3020', 'http://localhost:3020']
  }
  return raw.split(',').map((s) => s.trim()).filter(Boolean)
}

/**
 * App Fastify — core + auth + lms + xapi + gamification + certificates.
 * Helmet (HSTS/CSP) · CORS allowlist · rate-limit app-level (borda CloudFront/API GW na infra).
 */
export async function buildApp() {
  const app = Fastify({
    logger: {
      level: process.env.LOG_LEVEL ?? 'info',
      redact: {
        paths: [
          'req.headers.authorization',
          'req.headers.dpop',
          'req.body.password',
          'req.body.cpf',
          'req.body.email',
          'req.body.name',
          'req.body.refresh_token',
          'req.body.code_verifier',
          'req.body.PII_ENCRYPTION_KEY',
        ],
        censor: '[REDACTED]',
      },
    },
  })

  await app.register(cors, {
    origin: corsOrigins(),
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'DPoP'],
  })

  await app.register(helmet, {
    global: true,
    hsts: { maxAge: 31536000, includeSubDomains: true, preload: true },
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", 'data:', 'https:'],
        connectSrc: ["'self'"],
        // API JSON — player SPA aplica CSP própria com youtube/vimeo
        frameSrc: ["'none'"],
        objectSrc: ["'none'"],
      },
    },
    referrerPolicy: { policy: 'no-referrer' },
    xContentTypeOptions: true,
  })

  await app.register(rateLimit, {
    global: true,
    max: Number(process.env.RATE_LIMIT_MAX ?? 120),
    timeWindow: '1 minute',
  })

  // Rate limit mais restrito em auth (API4)
  await app.register(async (scoped) => {
    await scoped.register(rateLimit, {
      max: Number(process.env.AUTH_RATE_LIMIT_MAX ?? 20),
      timeWindow: '1 minute',
      keyGenerator: (req) => req.ip,
    })
    await scoped.register(authRoutes)
  })

  app.decorate('prisma', prisma)
  await app.register(authPlugin)
  await app.register(adminRoutes)
  await app.register(lmsRoutes)
  await app.register(xapiRoutes)
  await app.register(gamificationRoutes)
  await app.register(certificateRoutes)

  app.get('/health', async () => {
    await prisma.$queryRaw`SELECT 1`
    return { status: 'ok', service: 'leactiona-backend', tenant: 'single' }
  })

  app.setErrorHandler((err, _req, reply) => {
    const status = (err as Error & { statusCode?: number }).statusCode ?? 500
    const message = status >= 500 ? 'internal_error' : err.message
    if (status >= 500) {
      _req.log.error({ err: { name: err.name, message: err.message } }, 'request_failed')
    }
    reply.code(status).send({ error: message })
  })

  app.addHook('onClose', async () => {
    await prisma.$disconnect()
  })

  return app
}

declare module 'fastify' {
  interface FastifyInstance {
    prisma: typeof prisma
  }
}

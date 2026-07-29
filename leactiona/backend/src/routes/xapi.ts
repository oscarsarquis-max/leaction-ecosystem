import type { FastifyPluginAsync } from 'fastify'
import { z } from 'zod'
import { authenticate } from '../plugins/auth.js'
import { sanitizeStatement, buildVideoCompletedStatement, VERB_COMPLETED } from '../lib/xapi.js'
import { sendStatementsToLrs } from '../lib/lrs.js'
import { verifyLrsWebhookSignature } from '../lib/webhook-hmac.js'
import { prisma } from '../lib/prisma.js'
import { writeAuditLog } from '../lib/audit.js'
import { completeLessonForUser } from '../lib/gamification.js'

const completeBody = z.object({
  lesson_id: z.string().min(1),
  duration_sec: z.number().min(0).max(86400).optional(),
})

export const xapiRoutes: FastifyPluginAsync = async (app) => {
  /**
   * Proxy autenticado → Learning Locker (evita expor LRS_KEY no browser).
   * Frontend otimizado: envia statements aqui; backend encaminha async.
   */
  app.post(
    '/api/v1/xapi/statements',
    { preHandler: authenticate },
    async (req, reply) => {
      const body = req.body
      const list = Array.isArray(body) ? body : [body]
      let sanitized
      try {
        sanitized = list.map((s) => sanitizeStatement(s))
      } catch (e) {
        const err = e as Error
        return reply.code(400).send({ error: 'invalid_xapi_statement', message: err.message })
      }

      // Garante actor = usuário autenticado (BOLA / anti-spoof)
      for (const s of sanitized) {
        s.actor = {
          objectType: 'Agent',
          account: {
            homePage: 'https://leactiona.com.br',
            name: req.authUser!.id,
          },
        }
      }

      try {
        const result = await sendStatementsToLrs(sanitized)
        if (!result.ok) {
          return reply.code(502).send({ error: 'lrs_upstream_error', status: result.status })
        }
        return reply.code(200).send({
          ok: true,
          statement_ids: result.statementIds,
          mocked: result.mocked ?? false,
        })
      } catch (e) {
        const err = e as Error & { statusCode?: number }
        return reply.code(err.statusCode ?? 500).send({ error: err.message })
      }
    },
  )

  /** Atalho: conclusão de vídeo/lição → statement completed + envio LRS. */
  app.post(
    '/api/v1/xapi/video-completed',
    { preHandler: authenticate },
    async (req, reply) => {
      const parsed = completeBody.safeParse(req.body)
      if (!parsed.success) {
        return reply.code(400).send({ error: 'invalid_request' })
      }
      const lesson = await prisma.lesson.findUnique({
        where: { id: parsed.data.lesson_id },
        include: { module: { include: { course: true } } },
      })
      if (!lesson || lesson.module.course.organizationId !== 'global') {
        return reply.code(404).send({ error: 'lesson_not_found' })
      }

      const statement = buildVideoCompletedStatement({
        userId: req.authUser!.id,
        lessonId: lesson.id,
        lessonTitle: lesson.title,
        durationSec: parsed.data.duration_sec,
      })

      const result = await sendStatementsToLrs([statement])
      if (!result.ok) {
        return reply.code(502).send({ error: 'lrs_upstream_error', status: result.status })
      }

      // Progresso/pontos só via motor server-side (idempotente)
      let gamification = null
      try {
        gamification = await completeLessonForUser(
          req.authUser!.id,
          req.authUser!.role,
          lesson.id,
        )
      } catch {
        gamification = null
      }

      return {
        ok: true,
        verb: VERB_COMPLETED,
        statement,
        statement_ids: result.statementIds,
        mocked: result.mocked ?? false,
        gamification,
      }
    },
  )

  /**
   * Webhook LRS → sincroniza progresso local (HMAC-SHA256).
   * Body: { statements: XapiStatement[] } ou statement único.
   */
  app.post('/api/v1/xapi/webhook', async (req, reply) => {
    // Assina o mesmo JSON que o cliente enviou (serialização estável nos testes/prod).
    const raw = JSON.stringify(req.body)
    const sig = req.headers['x-lrs-signature']
    if (!verifyLrsWebhookSignature(raw, typeof sig === 'string' ? sig : undefined)) {
      return reply.code(401).send({ error: 'invalid_signature' })
    }

    const payload = req.body as unknown

    const statementsRaw = Array.isArray((payload as { statements?: unknown }).statements)
      ? (payload as { statements: unknown[] }).statements
      : [payload]

    let updated = 0
    for (const item of statementsRaw) {
      let st
      try {
        st = sanitizeStatement(item)
      } catch {
        continue
      }
      if (st.verb.id !== VERB_COMPLETED) continue
      const userId = st.actor.account?.name
      const lessonMatch = st.object.id.match(/\/lessons\/([^/?#]+)/)
      if (!userId || !lessonMatch) continue
      const lessonId = lessonMatch[1]!
      const lesson = await prisma.lesson.findUnique({
        where: { id: lessonId },
        include: { module: true },
      })
      if (!lesson) continue

      const enrollment = await prisma.enrollment.findUnique({
        where: {
          userId_courseId: { userId, courseId: lesson.module.courseId },
        },
      })
      if (!enrollment) continue

      const progress = Math.min(100, Math.max(enrollment.progressPct, 100))
      await prisma.enrollment.update({
        where: { id: enrollment.id },
        data: {
          progressPct: progress,
          status: progress >= 100 ? 'COMPLETED' : enrollment.status,
        },
      })
      updated += 1
    }

    await writeAuditLog({
      actorUserId: null,
      action: 'xapi.webhook_sync',
      entityType: 'Enrollment',
      entityId: 'batch',
      metadata: { updated },
    })

    return { ok: true, updated }
  })
}

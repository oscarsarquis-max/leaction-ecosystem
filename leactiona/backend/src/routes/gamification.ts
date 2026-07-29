import type { FastifyPluginAsync } from 'fastify'
import { z } from 'zod'
import { authenticate } from '../plugins/auth.js'
import {
  completeLessonForUser,
  getRanking,
  recordAssessmentScore,
} from '../lib/gamification.js'
import { prisma } from '../lib/prisma.js'

export const gamificationRoutes: FastifyPluginAsync = async (app) => {
  /**
   * Conclusão de lição — servidor calcula pontos/progresso/badges.
   * Body não aceita `points` do cliente.
   */
  app.post<{ Params: { id: string } }>(
    '/api/v1/lessons/:id/complete',
    { preHandler: authenticate },
    async (req, reply) => {
      // Ignora qualquer tentativa de enviar pontos pelo cliente
      try {
        const result = await completeLessonForUser(
          req.authUser!.id,
          req.authUser!.role,
          req.params.id,
        )
        return result
      } catch (e) {
        const err = e as Error & { statusCode?: number; reason?: string }
        return reply.code(err.statusCode ?? 500).send({
          error: err.message,
          reason: err.reason,
        })
      }
    },
  )

  app.post<{ Params: { courseId: string } }>(
    '/api/v1/courses/:courseId/assessment-result',
    { preHandler: authenticate },
    async (req, reply) => {
      const parsed = z
        .object({ score: z.number() })
        .safeParse(req.body)
      if (!parsed.success) {
        return reply.code(400).send({ error: 'invalid_request' })
      }
      try {
        const result = await recordAssessmentScore({
          userId: req.authUser!.id,
          courseId: req.params.courseId,
          score: parsed.data.score,
        })
        return result
      } catch (e) {
        const err = e as Error & { statusCode?: number }
        return reply.code(err.statusCode ?? 500).send({ error: err.message })
      }
    },
  )

  app.get('/api/v1/gamification/ranking', { preHandler: authenticate }, async (req) => {
    const limit = Number((req.query as { limit?: string }).limit ?? 50)
    const ranking = await getRanking(limit)
    return { ranking, organization_id: 'global' }
  })

  app.get('/api/v1/gamification/me', { preHandler: authenticate }, async (req) => {
    const userId = req.authUser!.id
    const profile = await prisma.gamificationProfile.findUnique({ where: { userId } })
    const badges = await prisma.userBadge.findMany({
      where: { userId },
      include: { badge: true },
      orderBy: { earnedAt: 'desc' },
    })
    return {
      profile: profile
        ? { points: profile.points, rank: profile.rank }
        : { points: 0, rank: 0 },
      badges: badges.map((b) => ({
        code: b.badge.code,
        title: b.badge.title,
        earned_at: b.earnedAt,
      })),
    }
  })
}

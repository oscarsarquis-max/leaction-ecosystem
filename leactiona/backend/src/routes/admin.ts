import type { FastifyPluginAsync } from 'fastify'
import { z } from 'zod'
import { requireRoles } from '../plugins/auth.js'
import { prisma } from '../lib/prisma.js'
import { writeAuditLog } from '../lib/audit.js'
import { encryptPii } from '../lib/crypto.js'

/** Rotas exclusivas ADMIN — RBAC + auditoria de matrícula/exclusão. */
export const adminRoutes: FastifyPluginAsync = async (app) => {
  app.get(
    '/api/v1/admin/ping',
    { preHandler: requireRoles('ADMIN') },
    async (req) => ({
      ok: true,
      role: req.authUser!.role,
      organization_id: 'global',
    }),
  )

  const enrollBody = z.object({
    user_id: z.string().min(1),
    course_id: z.string().min(1),
    is_paid_access: z.boolean(),
  })

  /** POST /api/v1/admin/enrollments — matrícula manual (sem billing). */
  app.post(
    '/api/v1/admin/enrollments',
    { preHandler: requireRoles('ADMIN') },
    async (req, reply) => {
      const parsed = enrollBody.safeParse(req.body)
      if (!parsed.success) {
        return reply.code(400).send({ error: 'invalid_request' })
      }
      const { user_id, course_id, is_paid_access } = parsed.data

      const [user, course] = await Promise.all([
        prisma.user.findUnique({ where: { id: user_id } }),
        prisma.course.findFirst({ where: { id: course_id, organizationId: 'global' } }),
      ])
      if (!user || !course) {
        return reply.code(404).send({ error: 'user_or_course_not_found' })
      }

      const previous = await prisma.enrollment.findUnique({
        where: { userId_courseId: { userId: user_id, courseId: course_id } },
      })

      const enrollment = await prisma.enrollment.upsert({
        where: { userId_courseId: { userId: user_id, courseId: course_id } },
        create: {
          userId: user_id,
          courseId: course_id,
          isPaidAccess: is_paid_access,
          status: 'ACTIVE',
        },
        update: {
          isPaidAccess: is_paid_access,
          status: 'ACTIVE',
        },
      })

      await writeAuditLog({
        actorUserId: req.authUser!.id,
        action: previous ? 'enrollment.is_paid_access_updated' : 'enrollment.created',
        entityType: 'Enrollment',
        entityId: enrollment.id,
        metadata: {
          user_id,
          course_id,
          is_paid_access,
          previous_is_paid_access: previous?.isPaidAccess ?? null,
        },
      })

      return reply.code(previous ? 200 : 201).send({
        enrollment: {
          id: enrollment.id,
          user_id: enrollment.userId,
          course_id: enrollment.courseId,
          is_paid_access: enrollment.isPaidAccess,
          status: enrollment.status,
        },
      })
    },
  )

  /**
   * DELETE /api/v1/admin/users/:id — exclusão física de PII (LGPD).
   * Progresso/enrollments são removidos em cascade; estatísticas futuras podem
   * usar tabelas anonimizadas separadas.
   */
  app.delete<{ Params: { id: string } }>(
    '/api/v1/admin/users/:id',
    { preHandler: requireRoles('ADMIN') },
    async (req, reply) => {
      const targetId = req.params.id
      if (targetId === req.authUser!.id) {
        return reply.code(400).send({ error: 'cannot_delete_self' })
      }
      const user = await prisma.user.findUnique({ where: { id: targetId } })
      if (!user) return reply.code(404).send({ error: 'user_not_found' })

      // Sobrescreve PII com ciphertext de placeholders antes do delete (defense in depth)
      await prisma.user.update({
        where: { id: targetId },
        data: {
          nameEnc: encryptPii('REDACTED'),
          emailEnc: encryptPii(`deleted-${targetId}@invalid.local`),
          cpfEnc: encryptPii('00000000000'),
          emailHash: `deleted:${targetId}`,
          passwordHash: '!',
        },
      })

      await writeAuditLog({
        actorUserId: req.authUser!.id,
        action: 'user.deleted_lgpd',
        entityType: 'User',
        entityId: targetId,
        metadata: { role: user.role },
      })

      await prisma.user.delete({ where: { id: targetId } })
      return reply.code(204).send()
    },
  )
}

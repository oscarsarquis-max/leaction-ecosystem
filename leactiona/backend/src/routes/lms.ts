import type { FastifyPluginAsync } from 'fastify'
import { z } from 'zod'
import { prisma } from '../lib/prisma.js'
import { authenticate, requireRoles } from '../plugins/auth.js'
import { canAccessCourseContent, canAccessLessonContent } from '../lib/access.js'
import { signMediaUrl } from '../lib/signed-url.js'

const mediaType = z.enum(['VIDEO', 'AUDIO', 'PDF', 'SCORM', 'H5P'])

const courseBody = z.object({
  title: z.string().min(1).max(200),
  description: z.string().max(5000).optional(),
  is_free: z.boolean().optional(),
  is_active: z.boolean().optional(),
  min_grade: z.number().min(0).max(100).optional(),
})

const moduleBody = z.object({
  title: z.string().min(1).max(200),
  position: z.number().int().min(0).optional(),
})

const lessonBody = z.object({
  title: z.string().min(1).max(200),
  position: z.number().int().min(0).optional(),
  media_type: mediaType,
  media_url: z.string().min(1).max(2000),
  points_on_complete: z.number().int().min(0).max(10000).optional(),
})

function mapCourse(c: {
  id: string
  title: string
  description: string
  isFree: boolean
  isActive: boolean
  minGrade: number
}) {
  return {
    id: c.id,
    title: c.title,
    description: c.description,
    is_free: c.isFree,
    is_active: c.isActive,
    min_grade: c.minGrade,
  }
}

export const lmsRoutes: FastifyPluginAsync = async (app) => {
  // —— Listagem (BOLA / filtro por acesso) ——
  app.get('/api/v1/courses', { preHandler: authenticate }, async (req) => {
    const user = req.authUser!
    const courses = await prisma.course.findMany({
      where: { organizationId: 'global', isActive: true },
      orderBy: { title: 'asc' },
    })

    if (user.role === 'ADMIN' || user.role === 'TEACHER') {
      return { courses: courses.map(mapCourse) }
    }

    const enrollments = await prisma.enrollment.findMany({
      where: {
        userId: user.id,
        status: { in: ['ACTIVE', 'COMPLETED'] },
      },
    })
    const paidIds = new Set(
      enrollments.filter((e) => e.isPaidAccess).map((e) => e.courseId),
    )

    const visible = courses.filter((c) => c.isFree || paidIds.has(c.id))
    return {
      courses: visible.map((c) => ({
        ...mapCourse(c),
        access: c.isFree ? 'free' : 'paid',
      })),
    }
  })

  app.get<{ Params: { id: string } }>(
    '/api/v1/courses/:id',
    { preHandler: authenticate },
    async (req, reply) => {
      const user = req.authUser!
      const course = await prisma.course.findFirst({
        where: { id: req.params.id, organizationId: 'global' },
        include: {
          modules: {
            orderBy: { position: 'asc' },
            include: { lessons: { orderBy: { position: 'asc' } } },
          },
        },
      })
      if (!course) return reply.code(404).send({ error: 'course_not_found' })

      const access = await canAccessCourseContent({
        userId: user.id,
        role: user.role,
        courseId: course.id,
      })

      // Metadados do curso: alunos veem se free ou matriculados; staff sempre
      const canSeeStructure =
        access.allowed || user.role === 'ADMIN' || user.role === 'TEACHER'
      if (!canSeeStructure && !course.isFree) {
        // Curso pago sem acesso: só metadados mínimos (sem media_url)
        return {
          course: mapCourse(course),
          access: { allowed: false, reason: access.reason },
          modules: [],
        }
      }

      return {
        course: mapCourse(course),
        access: { allowed: access.allowed, reason: access.reason },
        modules: course.modules.map((m) => ({
          id: m.id,
          title: m.title,
          position: m.position,
          lessons: m.lessons.map((l) => ({
            id: l.id,
            title: l.title,
            position: l.position,
            media_type: l.mediaType,
            // URL só no GET lesson (com assinatura) — evita vazamento em listagem
          })),
        })),
      }
    },
  )

  // —— Lição com BOLA + URL assinada ——
  app.get<{ Params: { id: string } }>(
    '/api/v1/lessons/:id',
    { preHandler: authenticate },
    async (req, reply) => {
      const user = req.authUser!
      const lesson = await prisma.lesson.findUnique({
        where: { id: req.params.id },
        include: { module: { include: { course: true } } },
      })
      if (!lesson || lesson.module.course.organizationId !== 'global') {
        return reply.code(404).send({ error: 'lesson_not_found' })
      }

      const access = await canAccessLessonContent({
        userId: user.id,
        role: user.role,
        lessonId: lesson.id,
      })

      if (!access.allowed) {
        return reply.code(403).send({
          error: 'forbidden_content',
          reason: access.reason,
          message:
            'Conteúdo restrito: curso pago exige matrícula ativa com is_paid_access=true',
        })
      }

      const signed = signMediaUrl(lesson.mediaUrl)
      return {
        lesson: {
          id: lesson.id,
          title: lesson.title,
          position: lesson.position,
          media_type: lesson.mediaType,
          media_url: signed.url,
          media_url_expires_at: signed.expires_at,
          media_url_signed: signed.signed,
          points_on_complete: lesson.pointsOnComplete,
          module_id: lesson.moduleId,
          course_id: lesson.module.courseId,
          course_is_free: lesson.module.course.isFree,
        },
        access: { allowed: true, reason: access.reason },
      }
    },
  )

  // —— CRUD Course (ADMIN/TEACHER) ——
  app.post(
    '/api/v1/courses',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const parsed = courseBody.safeParse(req.body)
      if (!parsed.success) {
        return reply.code(400).send({ error: 'invalid_request', details: parsed.error.flatten() })
      }
      const c = await prisma.course.create({
        data: {
          organizationId: 'global',
          title: parsed.data.title,
          description: parsed.data.description ?? '',
          isFree: parsed.data.is_free ?? false,
          isActive: parsed.data.is_active ?? true,
          minGrade: parsed.data.min_grade ?? 70,
        },
      })
      return reply.code(201).send({ course: mapCourse(c) })
    },
  )

  app.patch<{ Params: { id: string } }>(
    '/api/v1/courses/:id',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const parsed = courseBody.partial().safeParse(req.body)
      if (!parsed.success) {
        return reply.code(400).send({ error: 'invalid_request' })
      }
      const existing = await prisma.course.findFirst({
        where: { id: req.params.id, organizationId: 'global' },
      })
      if (!existing) return reply.code(404).send({ error: 'course_not_found' })
      const c = await prisma.course.update({
        where: { id: existing.id },
        data: {
          title: parsed.data.title,
          description: parsed.data.description,
          isFree: parsed.data.is_free,
          isActive: parsed.data.is_active,
          minGrade: parsed.data.min_grade,
        },
      })
      return { course: mapCourse(c) }
    },
  )

  app.delete<{ Params: { id: string } }>(
    '/api/v1/courses/:id',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const existing = await prisma.course.findFirst({
        where: { id: req.params.id, organizationId: 'global' },
      })
      if (!existing) return reply.code(404).send({ error: 'course_not_found' })
      await prisma.course.delete({ where: { id: existing.id } })
      return reply.code(204).send()
    },
  )

  // —— Modules ——
  app.post<{ Params: { courseId: string } }>(
    '/api/v1/courses/:courseId/modules',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const parsed = moduleBody.safeParse(req.body)
      if (!parsed.success) return reply.code(400).send({ error: 'invalid_request' })
      const course = await prisma.course.findFirst({
        where: { id: req.params.courseId, organizationId: 'global' },
      })
      if (!course) return reply.code(404).send({ error: 'course_not_found' })
      const m = await prisma.module.create({
        data: {
          courseId: course.id,
          title: parsed.data.title,
          position: parsed.data.position ?? 0,
        },
      })
      return reply.code(201).send({
        module: { id: m.id, course_id: m.courseId, title: m.title, position: m.position },
      })
    },
  )

  app.patch<{ Params: { id: string } }>(
    '/api/v1/modules/:id',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const parsed = moduleBody.partial().safeParse(req.body)
      if (!parsed.success) return reply.code(400).send({ error: 'invalid_request' })
      const existing = await prisma.module.findUnique({
        where: { id: req.params.id },
        include: { course: true },
      })
      if (!existing || existing.course.organizationId !== 'global') {
        return reply.code(404).send({ error: 'module_not_found' })
      }
      const m = await prisma.module.update({
        where: { id: existing.id },
        data: { title: parsed.data.title, position: parsed.data.position },
      })
      return {
        module: { id: m.id, course_id: m.courseId, title: m.title, position: m.position },
      }
    },
  )

  app.delete<{ Params: { id: string } }>(
    '/api/v1/modules/:id',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const existing = await prisma.module.findUnique({
        where: { id: req.params.id },
        include: { course: true },
      })
      if (!existing || existing.course.organizationId !== 'global') {
        return reply.code(404).send({ error: 'module_not_found' })
      }
      await prisma.module.delete({ where: { id: existing.id } })
      return reply.code(204).send()
    },
  )

  // —— Lessons ——
  app.post<{ Params: { moduleId: string } }>(
    '/api/v1/modules/:moduleId/lessons',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const parsed = lessonBody.safeParse(req.body)
      if (!parsed.success) {
        return reply.code(400).send({ error: 'invalid_request', details: parsed.error.flatten() })
      }
      const mod = await prisma.module.findUnique({
        where: { id: req.params.moduleId },
        include: { course: true },
      })
      if (!mod || mod.course.organizationId !== 'global') {
        return reply.code(404).send({ error: 'module_not_found' })
      }
      const l = await prisma.lesson.create({
        data: {
          moduleId: mod.id,
          title: parsed.data.title,
          position: parsed.data.position ?? 0,
          mediaType: parsed.data.media_type,
          mediaUrl: parsed.data.media_url,
          pointsOnComplete: parsed.data.points_on_complete ?? 10,
        },
      })
      return reply.code(201).send({
        lesson: {
          id: l.id,
          module_id: l.moduleId,
          title: l.title,
          position: l.position,
          media_type: l.mediaType,
        },
      })
    },
  )

  app.patch<{ Params: { id: string } }>(
    '/api/v1/lessons/:id',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const parsed = lessonBody.partial().safeParse(req.body)
      if (!parsed.success) return reply.code(400).send({ error: 'invalid_request' })
      const existing = await prisma.lesson.findUnique({
        where: { id: req.params.id },
        include: { module: { include: { course: true } } },
      })
      if (!existing || existing.module.course.organizationId !== 'global') {
        return reply.code(404).send({ error: 'lesson_not_found' })
      }
      const l = await prisma.lesson.update({
        where: { id: existing.id },
        data: {
          title: parsed.data.title,
          position: parsed.data.position,
          mediaType: parsed.data.media_type,
          mediaUrl: parsed.data.media_url,
          pointsOnComplete: parsed.data.points_on_complete,
        },
      })
      return {
        lesson: {
          id: l.id,
          module_id: l.moduleId,
          title: l.title,
          position: l.position,
          media_type: l.mediaType,
        },
      }
    },
  )

  app.delete<{ Params: { id: string } }>(
    '/api/v1/lessons/:id',
    { preHandler: requireRoles('ADMIN', 'TEACHER') },
    async (req, reply) => {
      const existing = await prisma.lesson.findUnique({
        where: { id: req.params.id },
        include: { module: { include: { course: true } } },
      })
      if (!existing || existing.module.course.organizationId !== 'global') {
        return reply.code(404).send({ error: 'lesson_not_found' })
      }
      await prisma.lesson.delete({ where: { id: existing.id } })
      return reply.code(204).send()
    },
  )
}

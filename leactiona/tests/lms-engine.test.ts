import 'dotenv/config'
import assert from 'node:assert/strict'
import { after, before, describe, it } from 'node:test'
import type { FastifyInstance } from 'fastify'
import { prisma } from '../backend/src/lib/prisma.js'
import { createUserEncrypted } from '../backend/src/lib/users.js'
import { buildApp } from '../backend/src/app.js'
import { authedGet, loginAs } from './helpers/http-auth.js'

describe('lms-engine (prompt 3)', () => {
  let app: FastifyInstance
  let freeLessonId: string
  let paidLessonId: string
  let paidCourseId: string
  let studentId: string
  let studentEmail: string
  const password = 'SenhaSegura!9xK2'

  before(async () => {
    assert.ok(process.env.DATABASE_URL)
    assert.ok(process.env.PII_ENCRYPTION_KEY)
    process.env.SIGNED_URL_MODE = 'local'

    await prisma.organization.upsert({
      where: { id: 'global' },
      create: { id: 'global', name: 'LEACTIONA' },
      update: {},
    })

    await prisma.auditLog.deleteMany()
    await prisma.refreshToken.deleteMany()
    await prisma.enrollment.deleteMany()
    await prisma.lesson.deleteMany()
    await prisma.module.deleteMany()
    await prisma.course.deleteMany()
    await prisma.user.deleteMany()

    studentEmail = `aluno.lms.${Date.now()}@leactiona.local`
    const student = await createUserEncrypted({
      name: 'Aluno LMS',
      email: studentEmail,
      cpf: '12312312312',
      password,
      role: 'STUDENT',
    })
    studentId = student.id

    const freeCourse = await prisma.course.create({
      data: {
        organizationId: 'global',
        title: 'Curso Gratuito',
        isFree: true,
        isActive: true,
        modules: {
          create: {
            title: 'Módulo Free',
            position: 1,
            lessons: {
              create: {
                title: 'Lição Free',
                position: 1,
                mediaType: 'VIDEO',
                mediaUrl: 's3://leactiona-media/free/intro.mp4',
              },
            },
          },
        },
      },
      include: { modules: { include: { lessons: true } } },
    })
    freeLessonId = freeCourse.modules[0].lessons[0].id

    const paidCourse = await prisma.course.create({
      data: {
        organizationId: 'global',
        title: 'Curso Pago',
        isFree: false,
        isActive: true,
        modules: {
          create: {
            title: 'Módulo Pago',
            position: 1,
            lessons: {
              create: {
                title: 'Lição Paga',
                position: 1,
                mediaType: 'PDF',
                mediaUrl: 's3://leactiona-media/paid/apostila.pdf',
              },
            },
          },
        },
      },
      include: { modules: { include: { lessons: true } } },
    })
    paidCourseId = paidCourse.id
    paidLessonId = paidCourse.modules[0].lessons[0].id

    app = await buildApp()
    await app.ready()
  })

  after(async () => {
    await app.close()
    await prisma.$disconnect()
  })

  it('bloqueia lição paga sem matrícula ou com is_paid_access=false', async () => {
    const session = await loginAs(app, studentEmail, password)

    const noEnroll = await authedGet(app, `/api/v1/lessons/${paidLessonId}`, session)
    assert.equal(noEnroll.statusCode, 403, noEnroll.body)
    assert.equal(noEnroll.json().reason, 'no_enrollment')

    await prisma.enrollment.create({
      data: {
        userId: studentId,
        courseId: paidCourseId,
        isPaidAccess: false,
        status: 'ACTIVE',
      },
    })

    const unpaid = await authedGet(app, `/api/v1/lessons/${paidLessonId}`, session)
    assert.equal(unpaid.statusCode, 403, unpaid.body)
    assert.equal(unpaid.json().reason, 'unpaid')

    await prisma.enrollment.deleteMany({ where: { userId: studentId, courseId: paidCourseId } })
  })

  it('libera lição gratuita para qualquer aluno autenticado', async () => {
    const session = await loginAs(app, studentEmail, password)
    const res = await authedGet(app, `/api/v1/lessons/${freeLessonId}`, session)
    assert.equal(res.statusCode, 200, res.body)
    const body = res.json() as {
      access: { allowed: boolean; reason: string }
      lesson: { media_url: string; media_url_signed: boolean; course_is_free: boolean }
    }
    assert.equal(body.access.allowed, true)
    assert.equal(body.access.reason, 'free')
    assert.equal(body.lesson.course_is_free, true)
    assert.equal(body.lesson.media_url_signed, true)
    assert.match(body.lesson.media_url, /Signature=/)
  })

  it('GET /api/v1/courses lista free e omite pago sem matrícula', async () => {
    const session = await loginAs(app, studentEmail, password)
    const res = await authedGet(app, '/api/v1/courses', session)
    assert.equal(res.statusCode, 200, res.body)
    const courses = (res.json() as { courses: { title: string }[] }).courses
    const titles = courses.map((c) => c.title)
    assert.ok(titles.includes('Curso Gratuito'))
    assert.ok(!titles.includes('Curso Pago'))
  })
})

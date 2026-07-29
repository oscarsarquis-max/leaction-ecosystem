import 'dotenv/config'
import assert from 'node:assert/strict'
import { after, before, describe, it } from 'node:test'
import type { FastifyInstance } from 'fastify'
import { prisma } from '../backend/src/lib/prisma.js'
import { createUserEncrypted } from '../backend/src/lib/users.js'
import { buildApp } from '../backend/src/app.js'
import { completeLessonForUser, recordAssessmentScore } from '../backend/src/lib/gamification.js'
import { sanitizePdfText } from '../backend/src/lib/certificates.js'
import { loginAs, signDpop, TEST_HOST } from './helpers/http-auth.js'

async function downloadCert(
  app: FastifyInstance,
  session: Awaited<ReturnType<typeof loginAs>>,
  courseId: string,
) {
  const path = `/api/v1/certificates/${courseId}/download`
  const dpop = await signDpop({
    privateKey: session.privateKey,
    publicJwk: session.publicJwk,
    method: 'GET',
    path,
    accessToken: session.accessToken,
  })
  return app.inject({
    method: 'GET',
    url: path,
    headers: {
      host: TEST_HOST,
      authorization: `Bearer ${session.accessToken}`,
      dpop,
    },
  })
}

describe('certificate-generator (prompt 6)', () => {
  let app: FastifyInstance
  let courseId: string
  let lessonA: string
  let lessonB: string
  let studentEmail: string
  let studentId: string
  const password = 'SenhaSegura!9xK2'

  before(async () => {
    assert.ok(process.env.DATABASE_URL)
    assert.ok(process.env.PII_ENCRYPTION_KEY)

    await prisma.organization.upsert({
      where: { id: 'global' },
      create: { id: 'global', name: 'LEACTIONA' },
      update: {},
    })

    await prisma.userBadge.deleteMany()
    await prisma.badge.deleteMany()
    await prisma.lessonCompletion.deleteMany()
    await prisma.gamificationProfile.deleteMany()
    await prisma.refreshToken.deleteMany()
    await prisma.enrollment.deleteMany()
    await prisma.lesson.deleteMany()
    await prisma.module.deleteMany()
    await prisma.course.deleteMany()
    await prisma.user.deleteMany()

    studentEmail = `cert.${Date.now()}@leactiona.local`
    const student = await createUserEncrypted({
      name: 'Aluno Certificado',
      email: studentEmail,
      cpf: '33333333333',
      password,
      role: 'STUDENT',
    })
    studentId = student.id

    const course = await prisma.course.create({
      data: {
        organizationId: 'global',
        title: 'Curso Certificado',
        isFree: true,
        isActive: true,
        minGrade: 70,
        modules: {
          create: {
            title: 'M1',
            position: 1,
            lessons: {
              create: [
                {
                  title: 'L1',
                  position: 1,
                  mediaType: 'VIDEO',
                  mediaUrl: 'https://example.com/1',
                  pointsOnComplete: 10,
                },
                {
                  title: 'L2',
                  position: 2,
                  mediaType: 'VIDEO',
                  mediaUrl: 'https://example.com/2',
                  pointsOnComplete: 10,
                },
              ],
            },
          },
        },
      },
      include: { modules: { include: { lessons: true } } },
    })
    courseId = course.id
    const lessons = course.modules[0]!.lessons.sort((a, b) => a.position - b.position)
    lessonA = lessons[0]!.id
    lessonB = lessons[1]!.id

    app = await buildApp()
    await app.ready()
  })

  after(async () => {
    await app.close()
  })

  it('sanitiza texto para PDF (anti-injection + bidi)', () => {
    const dirty = 'Nome\u0000Evil)\\(\\\\script\u202Ecurso'
    const clean = sanitizePdfText(dirty)
    assert.ok(!clean.includes('\u0000'))
    assert.ok(!clean.includes('('))
    assert.ok(!clean.includes(')'))
    assert.ok(!clean.includes('\\'))
    assert.ok(!clean.includes('\u202E'))
  })

  it('gera PDF valido (buffer %PDF) quando 100% + nota >= 70', async () => {
    await completeLessonForUser(studentId, 'STUDENT', lessonA)
    await completeLessonForUser(studentId, 'STUDENT', lessonB)
    await recordAssessmentScore({ userId: studentId, courseId, score: 85 })

    const session = await loginAs(app, studentEmail, password)
    const res = await downloadCert(app, session, courseId)

    assert.equal(res.statusCode, 200, res.body)
    assert.equal(res.headers['content-type'], 'application/pdf')
    const cd = String(res.headers['content-disposition'] ?? '')
    assert.match(cd, /attachment/)
    assert.ok(!cd.includes('\r') && !cd.includes('\n'))
    assert.match(cd, /filename\*=UTF-8''/)
    const buf = Buffer.from(res.rawPayload)
    assert.ok(buf.length > 200)
    assert.equal(buf.subarray(0, 4).toString('ascii'), '%PDF')
  })

  it('100% sem nota registrada ainda emite (regra provisória Assessment)', async () => {
    const email = `cert.nograde.${Date.now()}@leactiona.local`
    const u = await createUserEncrypted({
      name: 'Sem Nota',
      email,
      cpf: '66666666666',
      password,
      role: 'STUDENT',
    })
    await completeLessonForUser(u.id, 'STUDENT', lessonA)
    await completeLessonForUser(u.id, 'STUDENT', lessonB)

    const session = await loginAs(app, email, password)
    const res = await downloadCert(app, session, courseId)
    assert.equal(res.statusCode, 200, res.body)
    assert.equal(Buffer.from(res.rawPayload).subarray(0, 4).toString('ascii'), '%PDF')
  })

  it('rejeita download com progresso incompleto', async () => {
    // Novo aluno: só 1/2 lições
    const email = `cert.inc.${Date.now()}@leactiona.local`
    const u = await createUserEncrypted({
      name: 'Incompleto',
      email,
      cpf: '44444444444',
      password,
      role: 'STUDENT',
    })
    await completeLessonForUser(u.id, 'STUDENT', lessonA)
    await recordAssessmentScore({ userId: u.id, courseId, score: 90 })

    const session = await loginAs(app, email, password)
    const res = await downloadCert(app, session, courseId)
    assert.equal(res.statusCode, 403)
    const body = res.json() as { error: string }
    assert.equal(body.error, 'incomplete_progress')
  })

  it('rejeita download com nota abaixo de 70%', async () => {
    const email = `cert.low.${Date.now()}@leactiona.local`
    const u = await createUserEncrypted({
      name: 'Nota Baixa',
      email,
      cpf: '55555555555',
      password,
      role: 'STUDENT',
    })
    await completeLessonForUser(u.id, 'STUDENT', lessonA)
    await completeLessonForUser(u.id, 'STUDENT', lessonB)
    await recordAssessmentScore({ userId: u.id, courseId, score: 55 })

    const session = await loginAs(app, email, password)
    const res = await downloadCert(app, session, courseId)
    assert.equal(res.statusCode, 403)
    const body = res.json() as { error: string; details?: { average_grade: number } }
    assert.equal(body.error, 'grade_below_minimum')
    assert.ok((body.details?.average_grade ?? 100) < 70)
  })
})

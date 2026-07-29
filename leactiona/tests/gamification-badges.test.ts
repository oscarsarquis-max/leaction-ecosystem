import 'dotenv/config'
import assert from 'node:assert/strict'
import { after, before, describe, it } from 'node:test'
import type { FastifyInstance } from 'fastify'
import { prisma } from '../backend/src/lib/prisma.js'
import { createUserEncrypted } from '../backend/src/lib/users.js'
import { buildApp } from '../backend/src/app.js'
import { loginAs, signDpop, TEST_HOST } from './helpers/http-auth.js'
import { courseCompleteBadgeCode } from '../backend/src/lib/gamification.js'

async function completeLesson(
  app: FastifyInstance,
  session: Awaited<ReturnType<typeof loginAs>>,
  lessonId: string,
) {
  const path = `/api/v1/lessons/${lessonId}/complete`
  const dpop = await signDpop({
    privateKey: session.privateKey,
    publicJwk: session.publicJwk,
    method: 'POST',
    path,
    accessToken: session.accessToken,
  })
  return app.inject({
    method: 'POST',
    url: path,
    headers: {
      host: TEST_HOST,
      authorization: `Bearer ${session.accessToken}`,
      dpop,
      'content-type': 'application/json',
    },
    payload: { points: 999999 }, // deve ser ignorado
  })
}

describe('gamification-badges (prompt 5)', () => {
  let app: FastifyInstance
  let courseId: string
  let lessonA: string
  let lessonB: string
  let studentEmail: string
  let studentId: string
  let otherEmail: string
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

    studentEmail = `gami.${Date.now()}@leactiona.local`
    otherEmail = `gami2.${Date.now()}@leactiona.local`
    const student = await createUserEncrypted({
      name: 'Aluno Gami',
      email: studentEmail,
      cpf: '11111111111',
      password,
      role: 'STUDENT',
    })
    studentId = student.id
    await createUserEncrypted({
      name: 'Aluno Dois',
      email: otherEmail,
      cpf: '22222222222',
      password,
      role: 'STUDENT',
    })

    const course = await prisma.course.create({
      data: {
        organizationId: 'global',
        title: 'Curso Gami',
        isFree: true,
        isActive: true,
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
                  mediaUrl: 'https://youtu.be/aaaaaaaaaaa',
                  pointsOnComplete: 10,
                },
                {
                  title: 'L2',
                  position: 2,
                  mediaType: 'PDF',
                  mediaUrl: 's3://bucket/l2.pdf',
                  pointsOnComplete: 15,
                },
              ],
            },
          },
        },
      },
      include: { modules: { include: { lessons: true } } },
    })
    courseId = course.id
    const lessons = course.modules[0].lessons.sort((a, b) => a.position - b.position)
    lessonA = lessons[0].id
    lessonB = lessons[1].id

    app = await buildApp()
    await app.ready()
  })

  after(async () => {
    await app.close()
    await prisma.$disconnect()
  })

  it('concede UserBadge ao atingir 100% e é idempotente (sem duplicar)', async () => {
    const session = await loginAs(app, studentEmail, password)

    const r1 = await completeLesson(app, session, lessonA)
    assert.equal(r1.statusCode, 200, r1.body)
    assert.equal(r1.json().idempotent, false)
    assert.equal(r1.json().points_awarded, 10)

    const r2 = await completeLesson(app, session, lessonB)
    assert.equal(r2.statusCode, 200, r2.body)
    assert.equal(r2.json().progress_pct, 100)
    assert.ok(r2.json().badges_awarded.includes(courseCompleteBadgeCode(courseId)))
    // 10 + 15 + 500 badge
    assert.equal(r2.json().total_points, 10 + 15 + 500)

    const again = await completeLesson(app, session, lessonB)
    assert.equal(again.statusCode, 200, again.body)
    assert.equal(again.json().idempotent, true)
    assert.equal(again.json().points_awarded, 0)
    assert.deepEqual(again.json().badges_awarded, [])
    assert.equal(again.json().total_points, 525)

    const badgeCount = await prisma.userBadge.count({
      where: {
        userId: studentId,
        badge: { code: courseCompleteBadgeCode(courseId) },
      },
    })
    assert.equal(badgeCount, 1)
  })

  it('atualiza GamificationProfile e ranking após conclusão de lição', async () => {
    // other student completa só L1 (10 pts) — ranking atrás do primeiro (525)
    const session = await loginAs(app, otherEmail, password)
    const res = await completeLesson(app, session, lessonA)
    assert.equal(res.statusCode, 200, res.body)
    assert.equal(res.json().points_awarded, 10)
    assert.ok(res.json().rank >= 1)

    const path = '/api/v1/gamification/ranking'
    const dpop = await signDpop({
      privateKey: session.privateKey,
      publicJwk: session.publicJwk,
      method: 'GET',
      path,
      accessToken: session.accessToken,
    })
    const rankRes = await app.inject({
      method: 'GET',
      url: path,
      headers: {
        host: TEST_HOST,
        authorization: `Bearer ${session.accessToken}`,
        dpop,
      },
    })
    assert.equal(rankRes.statusCode, 200, rankRes.body)
    const ranking = (rankRes.json() as { ranking: { user_id: string; points: number; rank: number }[] })
      .ranking
    assert.ok(ranking.length >= 2)
    assert.equal(ranking[0].user_id, studentId)
    assert.equal(ranking[0].points, 525)
    assert.equal(ranking[0].rank, 1)
    assert.equal(ranking[1].points, 10)
    assert.equal(ranking[1].rank, 2)
  })

  it('concorrência: N completes simultâneos não duplicam pontos', async () => {
    // limpa completions do other para L2 e usa só L2
    const other = await prisma.user.findFirstOrThrow({
      where: { role: 'STUDENT', id: { not: studentId } },
    })
    await prisma.lessonCompletion.deleteMany({
      where: { userId: other.id, lessonId: lessonB },
    })
    // reset points for other to known base (10 from L1)
    await prisma.gamificationProfile.update({
      where: { userId: other.id },
      data: { points: 10 },
    })

    const session = await loginAs(app, otherEmail, password)
    const results = await Promise.all(
      Array.from({ length: 8 }, () => completeLesson(app, session, lessonB)),
    )
    for (const r of results) {
      assert.equal(r.statusCode, 200, r.body)
    }
    const awarded = results.filter((r) => r.json().idempotent === false)
    assert.equal(awarded.length, 1)
    const idempotent = results.filter((r) => r.json().idempotent === true)
    assert.equal(idempotent.length, 7)

    const profile = await prisma.gamificationProfile.findUniqueOrThrow({
      where: { userId: other.id },
    })
    // 10 (L1) + 15 (L2) + 500 (course complete badge) = 525
    assert.equal(profile.points, 525)

    const completions = await prisma.lessonCompletion.count({
      where: { userId: other.id, lessonId: lessonB },
    })
    assert.equal(completions, 1)
  })
})

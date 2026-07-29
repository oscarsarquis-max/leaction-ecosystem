import 'dotenv/config'
import assert from 'node:assert/strict'
import { after, before, describe, it } from 'node:test'
import type { FastifyInstance } from 'fastify'
import { prisma } from '../backend/src/lib/prisma.js'
import { createUserEncrypted } from '../backend/src/lib/users.js'
import { buildApp } from '../backend/src/app.js'
import { loginAs, signDpop, TEST_HOST } from './helpers/http-auth.js'
import { renderMediaPlayerMarkup } from '../frontend/src/player/render-player.ts'
import { signLrsWebhookBody } from '../backend/src/lib/webhook-hmac.js'
import { VERB_COMPLETED } from '../backend/src/lib/xapi.js'

describe('player-xapi (prompt 4)', () => {
  let app: FastifyInstance
  let lessonId: string
  let studentEmail: string
  const password = 'SenhaSegura!9xK2'

  before(async () => {
    assert.ok(process.env.DATABASE_URL)
    assert.ok(process.env.PII_ENCRYPTION_KEY)
    process.env.LRS_MOCK = '1'
    process.env.LRS_WEBHOOK_SECRET = 'test-webhook-secret'

    await prisma.organization.upsert({
      where: { id: 'global' },
      create: { id: 'global', name: 'LEACTIONA' },
      update: {},
    })

    await prisma.refreshToken.deleteMany()
    await prisma.enrollment.deleteMany()
    await prisma.lesson.deleteMany()
    await prisma.module.deleteMany()
    await prisma.course.deleteMany()
    await prisma.user.deleteMany()

    studentEmail = `player.${Date.now()}@leactiona.local`
    const student = await createUserEncrypted({
      name: 'Aluno Player',
      email: studentEmail,
      cpf: '99988877766',
      password,
      role: 'STUDENT',
    })

    const course = await prisma.course.create({
      data: {
        organizationId: 'global',
        title: 'Curso Player',
        isFree: true,
        isActive: true,
        modules: {
          create: {
            title: 'M1',
            position: 1,
            lessons: {
              create: {
                title: 'Vídeo introdutório',
                position: 1,
                mediaType: 'VIDEO',
                mediaUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
              },
            },
          },
        },
      },
      include: { modules: { include: { lessons: true } } },
    })
    lessonId = course.modules[0].lessons[0].id

    await prisma.enrollment.create({
      data: {
        userId: student.id,
        courseId: course.id,
        isPaidAccess: true,
        status: 'ACTIVE',
        progressPct: 0,
      },
    })

    app = await buildApp()
    await app.ready()
  })

  after(async () => {
    await app.close()
    await prisma.$disconnect()
  })

  it('envia statement xAPI ao LRS (mock) ao concluir vídeo', async () => {
    const session = await loginAs(app, studentEmail, password)
    const path = '/api/v1/xapi/video-completed'
    const dpop = await signDpop({
      privateKey: session.privateKey,
      publicJwk: session.publicJwk,
      method: 'POST',
      path,
      accessToken: session.accessToken,
    })

    const res = await app.inject({
      method: 'POST',
      url: path,
      headers: {
        host: TEST_HOST,
        'content-type': 'application/json',
        authorization: `Bearer ${session.accessToken}`,
        dpop,
      },
      payload: { lesson_id: lessonId, duration_sec: 120 },
    })

    assert.equal(res.statusCode, 200, res.body)
    const body = res.json() as {
      ok: boolean
      mocked: boolean
      verb: string
      statement: { verb: { id: string }; object: { id: string }; result: { completion: boolean } }
    }
    assert.equal(body.ok, true)
    assert.equal(body.mocked, true)
    assert.equal(body.verb, VERB_COMPLETED)
    assert.equal(body.statement.result.completion, true)
    assert.match(body.statement.object.id, new RegExp(lessonId))
  })

  it('renderiza player com iframe YouTube e camada interativa sobreposta', () => {
    const html = renderMediaPlayerMarkup({
      mediaUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      title: 'Demo overlay',
      overlays: [
        {
          id: 'q1',
          atSec: 15,
          type: 'mcq',
          text: 'Pergunta interativa',
          choices: ['A', 'B'],
        },
      ],
      activeOverlayId: 'q1',
    })

    assert.match(html, /data-testid="player-root"/)
    assert.match(html, /data-testid="player-iframe"/)
    assert.match(html, /youtube-nocookie\.com\/embed\//)
    assert.match(html, /data-testid="player-overlay"/)
    assert.match(html, /Pergunta interativa/)
    assert.match(html, /data-overlay-id="q1"/)
    // overlay vem depois do iframe no markup (camada por cima no CSS absolute)
    const iframeIdx = html.indexOf('data-testid="player-iframe"')
    const overlayIdx = html.indexOf('data-testid="player-overlay"')
    assert.ok(iframeIdx >= 0 && overlayIdx > iframeIdx)
  })

  it('rejeita webhook LRS sem HMAC válido e aceita com assinatura', async () => {
    const payload = {
      statements: [
        {
          actor: {
            account: { homePage: 'https://leactiona.com.br', name: 'x' },
          },
          verb: { id: VERB_COMPLETED },
          object: { id: `https://leactiona.com.br/lessons/${lessonId}` },
          result: { completion: true },
        },
      ],
    }
    const bad = await app.inject({
      method: 'POST',
      url: '/api/v1/xapi/webhook',
      headers: { 'content-type': 'application/json', 'x-lrs-signature': 'sha256=deadbeef' },
      payload,
    })
    assert.equal(bad.statusCode, 401)

    // Assina o corpo exatamente como o handler (JSON.stringify do objeto parseado).
    const sig = signLrsWebhookBody(JSON.stringify(payload), 'test-webhook-secret')
    const good = await app.inject({
      method: 'POST',
      url: '/api/v1/xapi/webhook',
      headers: {
        'content-type': 'application/json',
        'x-lrs-signature': sig,
      },
      payload,
    })
    assert.equal(good.statusCode, 200, good.body)
    assert.equal(good.json().ok, true)
  })
})


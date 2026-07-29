import 'dotenv/config'
import assert from 'node:assert/strict'
import { after, before, describe, it } from 'node:test'
import { prisma } from '../backend/src/lib/prisma.js'
import { createUserEncrypted, findUserByEmail, toUserPlain } from '../backend/src/lib/users.js'
import { decryptPii } from '../backend/src/lib/crypto.js'

describe('database-core (prompt 1)', () => {
  before(async () => {
    assert.ok(process.env.DATABASE_URL, 'DATABASE_URL obrigatório')
    assert.ok(process.env.PII_ENCRYPTION_KEY, 'PII_ENCRYPTION_KEY obrigatório')

    await prisma.organization.upsert({
      where: { id: 'global' },
      create: { id: 'global', name: 'LEACTIONA' },
      update: {},
    })

    // limpeza isolada do teste
    await prisma.userBadge.deleteMany()
    await prisma.badge.deleteMany()
    await prisma.enrollment.deleteMany()
    await prisma.gamificationProfile.deleteMany()
    await prisma.lesson.deleteMany()
    await prisma.module.deleteMany()
    await prisma.course.deleteMany()
    await prisma.user.deleteMany()
  })

  after(async () => {
    await prisma.$disconnect()
  })

  it('conecta, migra (schema) e persiste User com PII criptografada/decodificada', async () => {
    const plain = {
      name: 'Maria Silva',
      email: 'maria.teste@leactiona.local',
      cpf: '12345678901',
      password: 'SenhaForte!12345',
    }

    const created = await createUserEncrypted({ ...plain, role: 'STUDENT' })
    assert.equal(created.name, plain.name)
    assert.equal(created.email, plain.email.toLowerCase())
    assert.equal(created.cpf, plain.cpf)
    assert.equal(created.organizationId, 'global')

    const row = await prisma.user.findUniqueOrThrow({ where: { id: created.id } })
    // ciphertext ≠ plaintext no banco
    assert.notEqual(row.nameEnc, plain.name)
    assert.notEqual(row.emailEnc, plain.email.toLowerCase())
    assert.notEqual(row.cpfEnc, plain.cpf)
    assert.equal(decryptPii(row.nameEnc), plain.name)
    assert.equal(decryptPii(row.emailEnc), plain.email.toLowerCase())
    assert.equal(decryptPii(row.cpfEnc), plain.cpf)

    const found = await findUserByEmail(plain.email)
    assert.ok(found)
    assert.equal(found!.id, created.id)
    assert.deepEqual(toUserPlain(row).email, found!.email)
  })

  it('deleção de Course remove Modules em cascata', async () => {
    const course = await prisma.course.create({
      data: {
        organizationId: 'global',
        title: 'Curso Cascade',
        isFree: true,
        isActive: true,
        modules: {
          create: [
            { title: 'Módulo A', position: 1 },
            { title: 'Módulo B', position: 2 },
          ],
        },
      },
      include: { modules: true },
    })

    assert.equal(course.modules.length, 2)
    const moduleIds = course.modules.map((m) => m.id)

    await prisma.course.delete({ where: { id: course.id } })

    const leftover = await prisma.module.findMany({
      where: { id: { in: moduleIds } },
    })
    assert.equal(leftover.length, 0)
  })
})

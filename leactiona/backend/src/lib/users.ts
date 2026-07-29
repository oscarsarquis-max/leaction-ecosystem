import { hash as bcryptHash } from 'bcryptjs'
import type { User, UserRole } from '@prisma/client'
import { encryptPii, decryptPii, hashEmail } from './crypto.js'
import { validatePasswordPolicy } from './password.js'
import { prisma } from './prisma.js'

export type UserPlain = {
  id: string
  name: string
  email: string
  cpf: string
  role: UserRole
  organizationId: string
  createdAt: Date
  updatedAt: Date
}

export function toUserPlain(row: User): UserPlain {
  return {
    id: row.id,
    name: decryptPii(row.nameEnc),
    email: decryptPii(row.emailEnc),
    cpf: decryptPii(row.cpfEnc),
    role: row.role,
    organizationId: row.organizationId,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  }
}

export async function createUserEncrypted(input: {
  name: string
  email: string
  cpf: string
  password: string
  role?: UserRole
}): Promise<UserPlain> {
  const policyErr = validatePasswordPolicy(input.password)
  if (policyErr) {
    throw Object.assign(new Error(policyErr.message), {
      statusCode: 400,
      code: policyErr.code,
    })
  }
  const passwordHash = await bcryptHash(input.password, 12)
  const row = await prisma.user.create({
    data: {
      organizationId: 'global',
      nameEnc: encryptPii(input.name.trim()),
      emailEnc: encryptPii(input.email.trim().toLowerCase()),
      cpfEnc: encryptPii(input.cpf.replace(/\D/g, '')),
      emailHash: hashEmail(input.email),
      passwordHash,
      role: input.role ?? 'STUDENT',
    },
  })
  return toUserPlain(row)
}

export async function findUserByEmail(email: string): Promise<UserPlain | null> {
  const row = await prisma.user.findUnique({
    where: { emailHash: hashEmail(email) },
  })
  return row ? toUserPlain(row) : null
}

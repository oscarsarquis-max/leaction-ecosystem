import type { Prisma } from '@prisma/client'
import { prisma } from './prisma.js'

/**
 * Log de auditoria append-only (sem update/delete na API).
 * Metadata nunca deve conter PII/credenciais — só IDs e flags.
 */
export async function writeAuditLog(input: {
  actorUserId: string | null
  action: string
  entityType: string
  entityId: string
  metadata?: Prisma.InputJsonValue
}): Promise<void> {
  await prisma.auditLog.create({
    data: {
      actorUserId: input.actorUserId,
      action: input.action,
      entityType: input.entityType,
      entityId: input.entityId,
      metadata: input.metadata ?? {},
    },
  })
}

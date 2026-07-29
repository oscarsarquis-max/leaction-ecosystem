import { PrismaClient } from '@prisma/client'

/**
 * Cliente Prisma singleton para o backend Fastify.
 * Todas as queries são parametrizadas pelo ORM (mitiga SQL injection — ASVS / API8).
 *
 * Nunca habilitar log `query`: parâmetros de escrita/busca de usuário carregam
 * e-mail/CPF em claro *antes* da cifra — viola LGPD mesmo em dev.
 */
const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient }

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: ['warn', 'error'],
  })

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma
}

export type { PrismaClient }

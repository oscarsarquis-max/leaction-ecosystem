import 'dotenv/config'
import { buildApp } from './app.js'
import { prisma } from './lib/prisma.js'

async function ensureGlobalOrg() {
  await prisma.organization.upsert({
    where: { id: 'global' },
    create: { id: 'global', name: 'LEACTIONA' },
    update: {},
  })
}

const port = Number(process.env.PORT ?? 5020)
const host = process.env.HOST ?? '127.0.0.1'

const app = await buildApp()
await ensureGlobalOrg()
await app.listen({ port, host })
app.log.info(`LEACTIONA API em http://${host}:${port}`)

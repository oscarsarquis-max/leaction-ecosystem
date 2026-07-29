/**
 * Cliente Learning Locker (LRS externo) — Basic Auth ou chave API sobre HTTPS.
 * Credenciais só via env; nunca logar Authorization/body com PII.
 */
import type { XapiStatement } from './xapi.js'

export type LrsSendResult = {
  ok: boolean
  status: number
  statementIds?: string[]
  mocked?: boolean
}

function requireHttps(url: string): void {
  if (process.env.NODE_ENV === 'production' && !url.startsWith('https://')) {
    throw new Error('LRS_ENDPOINT deve usar HTTPS em produção')
  }
}

export function getLrsConfig() {
  const endpoint = process.env.LRS_ENDPOINT?.replace(/\/$/, '')
  const key = process.env.LRS_KEY
  const secret = process.env.LRS_SECRET
  const authHeader = process.env.LRS_AUTH_HEADER // opcional: "Basic xxx"
  return { endpoint, key, secret, authHeader }
}

function buildAuthHeader(cfg: ReturnType<typeof getLrsConfig>): string {
  if (cfg.authHeader) return cfg.authHeader
  if (cfg.key && cfg.secret) {
    const token = Buffer.from(`${cfg.key}:${cfg.secret}`, 'utf8').toString('base64')
    return `Basic ${token}`
  }
  throw new Error('LRS_KEY/LRS_SECRET ou LRS_AUTH_HEADER não configurados')
}

/**
 * Envia 1..N statements ao Learning Locker.
 * Se LRS_MOCK=1, não chama rede (testes).
 */
export async function sendStatementsToLrs(
  statements: XapiStatement[],
  fetchImpl: typeof fetch = fetch,
): Promise<LrsSendResult> {
  if (!statements.length) {
    return { ok: false, status: 400 }
  }

  if (process.env.LRS_MOCK === '1') {
    return {
      ok: true,
      status: 200,
      mocked: true,
      statementIds: statements.map((s) => s.id ?? cryptoRandomId()),
    }
  }

  const cfg = getLrsConfig()
  if (!cfg.endpoint) {
    throw Object.assign(new Error('LRS_ENDPOINT ausente'), { statusCode: 503 })
  }
  requireHttps(cfg.endpoint)

  const url = `${cfg.endpoint}/data/xAPI/statements`
  const res = await fetchImpl(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Experience-API-Version': '1.0.3',
      Authorization: buildAuthHeader(cfg),
    },
    body: JSON.stringify(statements.length === 1 ? statements[0] : statements),
  })

  const text = await res.text()
  let statementIds: string[] | undefined
  try {
    const parsed = JSON.parse(text) as unknown
    if (Array.isArray(parsed)) statementIds = parsed.map(String)
  } catch {
    /* corpo vazio ou não-JSON */
  }

  return { ok: res.ok, status: res.status, statementIds }
}

function cryptoRandomId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Fila offline de statements (PRD CA05) — localStorage + flush para backend.
 * Sem PII nos logs; actor é preenchido no servidor.
 */

export type QueuedStatement = {
  queuedAt: string
  statement: Record<string, unknown>
}

const STORAGE_KEY = 'leactiona.xapi.queue'

export function loadQueue(storage: Storage = localStorage): QueuedStatement[] {
  try {
    const raw = storage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    return Array.isArray(parsed) ? (parsed as QueuedStatement[]) : []
  } catch {
    return []
  }
}

export function saveQueue(items: QueuedStatement[], storage: Storage = localStorage): void {
  storage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export function enqueueStatement(
  statement: Record<string, unknown>,
  storage: Storage = localStorage,
): void {
  const q = loadQueue(storage)
  q.push({ queuedAt: new Date().toISOString(), statement })
  saveQueue(q, storage)
}

export async function flushQueue(opts: {
  post: (statements: Record<string, unknown>[]) => Promise<boolean>
  storage?: Storage
}): Promise<{ sent: number; remaining: number }> {
  const storage = opts.storage ?? localStorage
  const q = loadQueue(storage)
  if (!q.length) return { sent: 0, remaining: 0 }
  const statements = q.map((i) => i.statement)
  const ok = await opts.post(statements)
  if (!ok) return { sent: 0, remaining: q.length }
  saveQueue([], storage)
  return { sent: statements.length, remaining: 0 }
}

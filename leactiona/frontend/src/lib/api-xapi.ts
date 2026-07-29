import { enqueueStatement, flushQueue } from './xapi-queue'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:5020'

/**
 * Envia conclusão de vídeo ao backend (que encaminha ao Learning Locker).
 * Em falha de rede, enfileira no localStorage.
 */
export async function reportVideoCompleted(opts: {
  lessonId: string
  accessToken: string
  dpop: string
  durationSec?: number
}): Promise<{ ok: boolean; queued?: boolean }> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/xapi/video-completed`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${opts.accessToken}`,
        DPoP: opts.dpop,
      },
      body: JSON.stringify({
        lesson_id: opts.lessonId,
        duration_sec: opts.durationSec,
      }),
    })
    if (!res.ok) throw new Error(`status ${res.status}`)
    return { ok: true }
  } catch {
    enqueueStatement({
      verb: { id: 'http://adlnet.gov/expapi/verbs/completed' },
      object: { id: `https://leactiona.com.br/lessons/${opts.lessonId}` },
      result: { completion: true },
    })
    return { ok: false, queued: true }
  }
}

export async function flushXapiQueue(opts: {
  accessToken: string
  dpop: string
}): Promise<{ sent: number; remaining: number }> {
  return flushQueue({
    post: async (statements) => {
      const res = await fetch(`${API_BASE}/api/v1/xapi/statements`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${opts.accessToken}`,
          DPoP: opts.dpop,
        },
        body: JSON.stringify(statements),
      })
      return res.ok
    },
  })
}

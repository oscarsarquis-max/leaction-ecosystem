import { createHmac, timingSafeEqual } from 'node:crypto'

/**
 * Verifica assinatura HMAC-SHA256 de webhooks do LRS.
 * Header esperado: X-LRS-Signature: sha256=<hex>
 */
export function verifyLrsWebhookSignature(
  rawBody: string | Buffer,
  signatureHeader: string | undefined,
  secret = process.env.LRS_WEBHOOK_SECRET,
): boolean {
  if (!secret || !signatureHeader) return false
  const match = signatureHeader.match(/^sha256=([a-f0-9]+)$/i)
  if (!match) return false
  const expected = createHmac('sha256', secret).update(rawBody).digest('hex')
  const a = Buffer.from(expected, 'utf8')
  const b = Buffer.from(match[1]!.toLowerCase(), 'utf8')
  if (a.length !== b.length) return false
  return timingSafeEqual(a, b)
}

export function signLrsWebhookBody(
  rawBody: string,
  secret = process.env.LRS_WEBHOOK_SECRET ?? 'test-secret',
): string {
  const hex = createHmac('sha256', secret).update(rawBody).digest('hex')
  return `sha256=${hex}`
}

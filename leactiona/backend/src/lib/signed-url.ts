/**
 * URLs assinadas de curta duração para mídia S3/CloudFront (ASVS).
 * YouTube/Vimeo externos: retornados sem assinatura.
 * Dev/teste sem chave CloudFront: HMAC local.
 */
import { createHmac, createSign, randomBytes } from 'node:crypto'
import { readFileSync } from 'node:fs'

const DEFAULT_TTL = Number(process.env.MEDIA_URL_TTL_SEC ?? 300)

function isExternalPlayerUrl(url: string): boolean {
  try {
    const u = new URL(url)
    return (
      u.hostname.includes('youtube.com') ||
      u.hostname.includes('youtu.be') ||
      u.hostname.includes('vimeo.com') ||
      u.hostname.includes('player.vimeo.com')
    )
  } catch {
    return false
  }
}

function localSign(objectKey: string, expiresAt: number): string {
  const secret = process.env.MEDIA_SIGNING_SECRET || process.env.PII_ENCRYPTION_KEY
  if (!secret) throw new Error('MEDIA_SIGNING_SECRET ou PII_ENCRYPTION_KEY necessário')
  const base = process.env.MEDIA_CDN_BASE_URL ?? 'https://cdn.leactiona.local'
  const sig = createHmac('sha256', secret)
    .update(`${objectKey}:${expiresAt}`)
    .digest('base64url')
  const url = new URL(`/media/${objectKey.replace(/^\/+/, '')}`, base)
  url.searchParams.set('Expires', String(expiresAt))
  url.searchParams.set('Signature', sig)
  return url.toString()
}

function cloudFrontSign(objectKey: string, expiresAt: number): string {
  const keyPairId = process.env.CLOUDFRONT_KEY_PAIR_ID
  const pemPath = process.env.CLOUDFRONT_PRIVATE_KEY_PATH
  const pemEnv = process.env.CLOUDFRONT_PRIVATE_KEY_PEM?.replace(/\\n/g, '\n')
  const dist = process.env.CLOUDFRONT_DISTRIBUTION_DOMAIN
  if (!keyPairId || !dist || (!pemPath && !pemEnv)) {
    return localSign(objectKey, expiresAt)
  }
  const privateKey = pemEnv ?? readFileSync(pemPath!, 'utf8')
  const resource = `https://${dist}/${objectKey.replace(/^\/+/, '')}`
  const policy = JSON.stringify({
    Statement: [
      {
        Resource: resource,
        Condition: { DateLessThan: { 'AWS:EpochTime': expiresAt } },
      },
    ],
  })
  const signer = createSign('RSA-SHA1')
  signer.update(policy)
  const signature = signer
    .sign(privateKey, 'base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '~')
    .replace(/=+$/, '')
  const url = new URL(resource)
  url.searchParams.set('Expires', String(expiresAt))
  url.searchParams.set('Signature', signature)
  url.searchParams.set('Key-Pair-Id', keyPairId)
  return url.toString()
}

function toObjectKey(mediaUrl: string): string {
  if (mediaUrl.startsWith('s3://')) {
    return mediaUrl.replace(/^s3:\/\/[^/]+\//, '')
  }
  if (mediaUrl.startsWith('https://') || mediaUrl.startsWith('http://')) {
    try {
      return new URL(mediaUrl).pathname.replace(/^\//, '')
    } catch {
      return mediaUrl
    }
  }
  return mediaUrl
}

export function signMediaUrl(mediaUrl: string, ttlSec = DEFAULT_TTL): {
  url: string
  expires_at: number
  signed: boolean
} {
  const expiresAt = Math.floor(Date.now() / 1000) + ttlSec

  if (isExternalPlayerUrl(mediaUrl)) {
    return { url: mediaUrl, expires_at: expiresAt, signed: false }
  }

  const objectKey = toObjectKey(mediaUrl)
  const mode = process.env.SIGNED_URL_MODE ?? 'auto'
  const url =
    mode === 'local' || !process.env.CLOUDFRONT_KEY_PAIR_ID
      ? localSign(objectKey, expiresAt)
      : cloudFrontSign(objectKey, expiresAt)

  return { url, expires_at: expiresAt, signed: true }
}

export function freshNonce(): string {
  return randomBytes(8).toString('hex')
}

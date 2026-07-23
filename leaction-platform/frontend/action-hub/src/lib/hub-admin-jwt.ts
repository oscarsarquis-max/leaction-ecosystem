import { createHmac, timingSafeEqual } from 'crypto';

const DEFAULT_ADMIN_EMAILS = 'admin@actionhub.com.br,sysadmin@inove4us.com.br';

function jwtSecret(): string {
  return (process.env.JWT_SECRET || '').trim();
}

function gatewayBase(): string {
  return (process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001').replace(/\/$/, '');
}

/** Allowlist alinhada ao gateway (`HUB_ADMIN_EMAILS`) e ao client (`NEXT_PUBLIC_HUB_ADMIN_EMAILS`). */
export function getHubAdminEmails(): string[] {
  const raw =
    process.env.HUB_ADMIN_EMAILS ||
    process.env.HUB_SYSADMIN_EMAIL ||
    process.env.NEXT_PUBLIC_HUB_ADMIN_EMAILS ||
    process.env.NEXT_PUBLIC_HUB_SYSADMIN_EMAIL ||
    DEFAULT_ADMIN_EMAILS;
  return String(raw)
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

function b64urlToBuffer(value: string): Buffer {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/');
  const pad = padded.length % 4 === 0 ? '' : '='.repeat(4 - (padded.length % 4));
  return Buffer.from(padded + pad, 'base64');
}

function decodeJwtEmailUnsafe(token: string): string | null {
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    const payload = JSON.parse(b64urlToBuffer(parts[1]).toString('utf-8')) as {
      email?: string;
      exp?: number;
    };
    if (typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()) return null;
    const email = String(payload.email || '')
      .trim()
      .toLowerCase();
    return email || null;
  } catch {
    return null;
  }
}

/** Verifica JWT HS256 emitido pelo gateway (`jwt.sign({ sub, email }, JWT_SECRET)`). */
export function verifyHubJwt(token: string): { email: string; sub?: string } | null {
  const secret = jwtSecret();
  if (!secret || !token) return null;

  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const [headerB64, payloadB64, sigB64] = parts;

  const expected = createHmac('sha256', secret)
    .update(`${headerB64}.${payloadB64}`)
    .digest('base64url');

  try {
    const a = Buffer.from(sigB64);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  } catch {
    return null;
  }

  try {
    const header = JSON.parse(b64urlToBuffer(headerB64).toString('utf-8')) as { alg?: string };
    if (header.alg && header.alg !== 'HS256') return null;

    const payload = JSON.parse(b64urlToBuffer(payloadB64).toString('utf-8')) as {
      email?: string;
      sub?: string;
      exp?: number;
    };
    if (typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()) return null;

    const email = String(payload.email || '')
      .trim()
      .toLowerCase();
    if (!email) return null;
    return { email, sub: payload.sub ? String(payload.sub) : undefined };
  } catch {
    return null;
  }
}

export function extractBearerToken(request: Request): string {
  const auth = String(request.headers.get('authorization') || '').trim();
  const m = /^Bearer\s+(.+)$/i.exec(auth);
  return m ? String(m[1] || '').trim() : '';
}

/**
 * Admin Hub válido.
 * 1) JWT local (se JWT_SECRET no FE)
 * 2) Validação no gateway `/admin/apps` (produção atual sem JWT_SECRET no Next)
 */
export async function resolveHubAdminFromRequest(
  request: Request
): Promise<{ email: string; via: 'hub_admin' } | null> {
  const token = extractBearerToken(request);
  if (!token) return null;

  const local = verifyHubJwt(token);
  if (local && getHubAdminEmails().includes(local.email)) {
    return { email: local.email, via: 'hub_admin' };
  }

  try {
    const res = await fetch(`${gatewayBase()}/admin/apps`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
      },
      cache: 'no-store',
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) return null;
    const email = decodeJwtEmailUnsafe(token);
    if (!email || !getHubAdminEmails().includes(email)) return null;
    return { email, via: 'hub_admin' };
  } catch {
    return null;
  }
}

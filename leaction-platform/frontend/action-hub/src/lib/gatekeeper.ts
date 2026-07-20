import { createHash, timingSafeEqual } from 'crypto';

export const GK_BYPASS_COOKIE = 'ah_gk_bypass';

export function getProductionMasterKey(): string {
  return String(process.env.PRODUCTION_MASTER_KEY || '').trim();
}

export function isGatekeeperAdminEnabled(): boolean {
  if ((process.env.NODE_ENV || 'development') === 'production') return true;
  return String(process.env.GATEKEEPER_ALLOW_DEV || '').toLowerCase() === 'true';
}

export function isValidMasterSecret(provided: string | null | undefined): boolean {
  const expected = getProductionMasterKey();
  const got = String(provided || '').trim();
  if (!expected || !got) return false;
  const a = Buffer.from(expected, 'utf8');
  const b = Buffer.from(got, 'utf8');
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

/** Hash estável do secret — cookie não guarda o master key em claro. */
export function bypassCookieValue(): string {
  const key = getProductionMasterKey();
  if (!key) return '';
  return createHash('sha256').update(`ah-gk|${key}`).digest('hex').slice(0, 32);
}

export function gatewayBase(): string {
  return (process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001').replace(
    /\/$/,
    ''
  );
}

import { createHmac, randomBytes, timingSafeEqual } from 'crypto';
import type { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import { resolveHubAdminFromRequest } from '@/lib/hub-admin-jwt';

export const CURATION_AUTH_COOKIE = 'mp_curation_auth';
const SESSION_TTL_MS = 12 * 60 * 60 * 1000;

function authSecret(): string {
  return (
    process.env.MARKETPLACE_CURATION_AUTH_SECRET ||
    process.env.JWT_SECRET ||
    'dev-only-curation-auth-secret-change-me'
  ).trim();
}

export function curationCredentialsConfigured(): boolean {
  const user = (process.env.MARKETPLACE_CURATION_USER || '').trim();
  const password = (process.env.MARKETPLACE_CURATION_PASSWORD || '').trim();
  return Boolean(user && password);
}

export function validateCurationCredentials(user: string, password: string): boolean {
  const expectedUser = (process.env.MARKETPLACE_CURATION_USER || '').trim();
  const expectedPassword = (process.env.MARKETPLACE_CURATION_PASSWORD || '').trim();
  if (!expectedUser || !expectedPassword) return false;
  return user.trim() === expectedUser && password === expectedPassword;
}

function signPayload(payload: string): string {
  return createHmac('sha256', authSecret()).update(payload).digest('base64url');
}

export function createSessionToken(user: string): string {
  const payload = Buffer.from(
    JSON.stringify({ exp: Date.now() + SESSION_TTL_MS, u: user.trim() })
  ).toString('base64url');
  return `${payload}.${signPayload(payload)}`;
}

export function parseSessionToken(token: string | undefined | null): { user: string } | null {
  if (!token) return null;
  const dot = token.lastIndexOf('.');
  if (dot <= 0) return null;

  const payload = token.slice(0, dot);
  const signature = token.slice(dot + 1);
  const expected = signPayload(payload);

  try {
    const a = Buffer.from(signature);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  } catch {
    return null;
  }

  try {
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8')) as {
      exp?: number;
      u?: string;
    };
    if (!data.u || !data.exp || data.exp < Date.now()) return null;
    return { user: data.u };
  } catch {
    return null;
  }
}

export function curationAuthCookieOptions() {
  const secure = process.env.NODE_ENV === 'production';
  return {
    httpOnly: true,
    secure,
    sameSite: 'lax' as const,
    path: '/',
    maxAge: SESSION_TTL_MS / 1000,
  };
}

export async function isCurationAuthenticated(): Promise<boolean> {
  const jar = await cookies();
  const token = jar.get(CURATION_AUTH_COOKIE)?.value;
  return parseSessionToken(token) !== null;
}

export type CurationAuthOk = {
  via: 'hub_admin' | 'curation_cookie';
  user: string;
};

/** Cookie legado da curadoria OU JWT de admin do Action Hub. */
export async function resolveCurationAuth(
  request?: Request
): Promise<CurationAuthOk | null> {
  if (request) {
    const hub = await resolveHubAdminFromRequest(request);
    if (hub) return { via: 'hub_admin', user: hub.email };
  }

  const jar = await cookies();
  const token = jar.get(CURATION_AUTH_COOKIE)?.value;
  const session = parseSessionToken(token);
  if (session) return { via: 'curation_cookie', user: session.user };
  return null;
}

export async function requireCurationAuth(request?: Request): Promise<NextResponse | null> {
  const ok = await resolveCurationAuth(request);
  if (ok) return null;

  const { NextResponse: NR } = await import('next/server');
  return NR.json({ status: 'error', error: 'Não autorizado.' }, { status: 401 });
}

export function generateAuthSecret(): string {
  return randomBytes(32).toString('base64url');
}

import { NextRequest, NextResponse } from 'next/server';
import {
  GK_BYPASS_COOKIE,
  bypassCookieValue,
  getProductionMasterKey,
  isGatekeeperAdminEnabled,
  isValidMasterSecret,
} from '@/lib/gatekeeper';

export async function GET(req: NextRequest) {
  if (!isGatekeeperAdminEnabled()) {
    return new NextResponse(
      'Rotas de homologação disponíveis apenas em produção. Em dev, GATEKEEPER_ALLOW_DEV=true.',
      { status: 403 }
    );
  }
  if (!getProductionMasterKey() || !isValidMasterSecret(req.nextUrl.searchParams.get('secret'))) {
    return new NextResponse('Acesso negado.', { status: 403 });
  }

  const token = bypassCookieValue();
  if (!token) {
    return new NextResponse('Acesso negado.', { status: 403 });
  }

  // Atrás do nginx o req.url pode vir como localhost:PORT — forçar origem pública.
  const publicBase = (
    process.env.ACTION_HUB_PUBLIC_URL ||
    process.env.NEXT_PUBLIC_ACTION_HUB_URL ||
    ''
  ).replace(/\/$/, '');
  const xfHost = (req.headers.get('x-forwarded-host') || '').split(',')[0].trim();
  const xfProto = (req.headers.get('x-forwarded-proto') || 'https').split(',')[0].trim();
  const host = xfHost || (req.headers.get('host') || '').trim();
  const origin =
    publicBase ||
    (host && !/^localhost(:\d+)?$/i.test(host) && !/^127\.0\.0\.1(:\d+)?$/i.test(host)
      ? `${xfProto}://${host}`
      : 'https://actionhub.com.br');

  const res = NextResponse.redirect(new URL('/', origin));
  res.cookies.set(GK_BYPASS_COOKIE, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: true,
    path: '/',
    maxAge: 60 * 60 * 24 * 14,
  });
  return res;
}

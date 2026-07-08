import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import {
  CURATION_AUTH_COOKIE,
  createSessionToken,
  curationAuthCookieOptions,
  curationCredentialsConfigured,
  validateCurationCredentials,
} from '@/lib/marketplace-curation-auth';

export async function POST(request: NextRequest) {
  if (!curationCredentialsConfigured()) {
    return NextResponse.json(
      { authenticated: false, error: 'Credenciais da curadoria não configuradas no servidor.' },
      { status: 503 }
    );
  }

  let body: { user?: string; password?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ authenticated: false, error: 'JSON inválido.' }, { status: 400 });
  }

  const user = (body.user || '').trim();
  const password = body.password || '';

  if (!user || !password) {
    return NextResponse.json(
      { authenticated: false, error: 'Informe usuário e senha.' },
      { status: 400 }
    );
  }

  if (!validateCurationCredentials(user, password)) {
    return NextResponse.json(
      { authenticated: false, error: 'Usuário ou senha inválidos.' },
      { status: 401 }
    );
  }

  const token = createSessionToken(user);
  const jar = await cookies();
  jar.set(CURATION_AUTH_COOKIE, token, curationAuthCookieOptions());

  return NextResponse.json({ authenticated: true, user });
}

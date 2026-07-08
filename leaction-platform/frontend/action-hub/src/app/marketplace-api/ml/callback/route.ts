import { NextRequest, NextResponse } from 'next/server';

const MARKETPLACE_INTERNAL = (
  process.env.MARKETPLACE_INTERNAL_URL || 'http://127.0.0.1:4012'
).replace(/\/$/, '');

/** Proxy callback OAuth ML (code → tokens no Flask :4012). */
export async function GET(request: NextRequest) {
  const upstream = `${MARKETPLACE_INTERNAL}/api/marketplace/ml/callback${request.nextUrl.search}`;

  try {
    const response = await fetch(upstream, {
      redirect: 'manual',
      headers: { Accept: 'text/html,application/json' },
      signal: AbortSignal.timeout(20000),
    });

    const location = response.headers.get('location');
    if (location && response.status >= 300 && response.status < 400) {
      return NextResponse.redirect(location);
    }

    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'text/plain' },
    });
  } catch {
    return new NextResponse('Falha ao concluir OAuth Mercado Livre.', { status: 502 });
  }
}

import { NextRequest, NextResponse } from 'next/server';

import { requireCurationAuth } from '@/lib/marketplace-curation-auth';

const MARKETPLACE_INTERNAL = (
  process.env.MARKETPLACE_INTERNAL_URL || 'http://127.0.0.1:4012'
).replace(/\/$/, '');

/** Proxy PUT → Flask /api/marketplace/curation/:category */
export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ category: string }> }
) {
  const denied = await requireCurationAuth(request);
  if (denied) return denied;

  const { category } = await context.params;
  const safeCategory = encodeURIComponent((category || '').trim().toLowerCase());
  const upstream = `${MARKETPLACE_INTERNAL}/api/marketplace/curation/${safeCategory}`;

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ status: 'error', error: 'JSON inválido' }, { status: 400 });
  }

  try {
    const response = await fetch(upstream, {
      method: 'PUT',
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
    const data = await response.json().catch(() => ({}));

    return NextResponse.json(data, {
      status: response.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return NextResponse.json(
      { status: 'error', error: 'Marketplace indisponível.' },
      { status: 503 }
    );
  }
}

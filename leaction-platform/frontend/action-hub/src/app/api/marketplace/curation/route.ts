import { NextResponse } from 'next/server';

import { requireCurationAuth } from '@/lib/marketplace-curation-auth';

const MARKETPLACE_INTERNAL = (
  process.env.MARKETPLACE_INTERNAL_URL || 'http://127.0.0.1:4012'
).replace(/\/$/, '');

/** Proxy GET → Flask /api/marketplace/curation */
export async function GET(request: Request) {
  const denied = await requireCurationAuth(request);
  if (denied) return denied;

  const upstream = `${MARKETPLACE_INTERNAL}/api/marketplace/curation`;

  try {
    const response = await fetch(upstream, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(15000),
    });
    const data = await response.json().catch(() => ({}));

    return NextResponse.json(data, {
      status: response.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return NextResponse.json(
      { status: 'error', error: 'Marketplace indisponível.', rules: [], count: 0 },
      { status: 503 }
    );
  }
}

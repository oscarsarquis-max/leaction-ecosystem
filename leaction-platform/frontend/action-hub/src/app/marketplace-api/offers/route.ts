import { NextRequest, NextResponse } from 'next/server';

import { normalizeOfferImages } from '@/utils/marketplaceImages';

const MARKETPLACE_INTERNAL = (
  process.env.MARKETPLACE_INTERNAL_URL || 'http://127.0.0.1:4012'
).replace(/\/$/, '');

/** Proxy server-side para o plugin Marketplace (evita CORS e rewrites instáveis). */
export async function GET(request: NextRequest) {
  const search = request.nextUrl.search;
  const upstream = `${MARKETPLACE_INTERNAL}/api/marketplace/offers${search}`;

  try {
    const response = await fetch(upstream, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(15000),
    });
    const data = await response.json().catch(() => ({}));

    if (Array.isArray(data.offers)) {
      data.offers = normalizeOfferImages(data.offers);
    }

    return NextResponse.json(data, {
      status: response.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return NextResponse.json(
      {
        status: 'error',
        error: 'Plugin Marketplace indisponível. Inicie: cd backend && python run.py',
        offers: [],
      },
      { status: 503 }
    );
  }
}

import { NextRequest, NextResponse } from 'next/server';

import { normalizeOfferImages } from '@/utils/marketplaceImages';
import { requireCurationAuth } from '@/lib/marketplace-curation-auth';

const MARKETPLACE_INTERNAL = (
  process.env.MARKETPLACE_INTERNAL_URL || 'http://127.0.0.1:4012'
).replace(/\/$/, '');

/** Proxy GET → Flask /api/marketplace/offers (preview da vitrine). */
export async function GET(request: NextRequest) {
  const denied = await requireCurationAuth();
  if (denied) return denied;

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
        error: 'Marketplace indisponível.',
        offers: [],
        count: 0,
      },
      { status: 503 }
    );
  }
}

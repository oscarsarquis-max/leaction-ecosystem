import { NextRequest, NextResponse } from 'next/server';

import { normalizeOfferImages } from '@/utils/marketplaceImages';

const MARKETPLACE_INTERNAL = (
  process.env.MARKETPLACE_INTERNAL_URL || 'http://127.0.0.1:4012'
).replace(/\/$/, '');

/** Proxy: vitrine genérica ou contextual (sprints PanelDX). */
export async function GET(request: NextRequest) {
  const search = request.nextUrl.search;
  const upstream = `${MARKETPLACE_INTERNAL}/api/marketplace/vitrine${search}`;

  try {
    const response = await fetch(upstream, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(20000),
    });
    const data = await response.json().catch(() => ({}));

    if (Array.isArray(data.recommended)) {
      data.recommended = normalizeOfferImages(
        data.recommended as Record<string, unknown>[]
      );
    }
    if (Array.isArray(data.shelves)) {
      data.shelves = data.shelves.map((shelf: { offers?: unknown[] }) => ({
        ...shelf,
        offers: Array.isArray(shelf.offers)
          ? normalizeOfferImages(shelf.offers as Record<string, unknown>[])
          : [],
      }));
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
        mode: 'generic',
        recommended: [],
        shelves: [],
      },
      { status: 503 }
    );
  }
}

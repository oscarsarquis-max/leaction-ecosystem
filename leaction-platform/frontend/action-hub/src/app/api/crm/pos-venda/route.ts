import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function gatewayBase(): string {
  return (process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001').replace(/\/$/, '');
}

function crmHeaders(): Record<string, string> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  const secret = (process.env.CRM_TRACKING_SECRET || '').trim();
  if (secret) headers['x-crm-secret'] = secret;
  return headers;
}

/** Proxy GET /api/crm/pos-venda */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const qs = new URLSearchParams();
  for (const key of ['alerta', 'sistema', 'desde']) {
    const v = (searchParams.get(key) || '').trim();
    if (v) qs.set(key, v);
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  try {
    const upstream = await fetch(`${gatewayBase()}/api/crm/pos-venda${suffix}`, {
      headers: crmHeaders(),
      cache: 'no-store',
    });
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'gateway_unavailable';
    return NextResponse.json({ ok: false, error: message }, { status: 502 });
  }
}

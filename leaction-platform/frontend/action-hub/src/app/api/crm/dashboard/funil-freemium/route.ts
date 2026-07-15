import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function gatewayBase(): string {
  return (process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001').replace(/\/$/, '');
}

function crmSecret(): string {
  return (process.env.CRM_TRACKING_SECRET || '').trim();
}

/** Proxy server-side do funil freemium — injeta x-crm-secret sem expor no browser. */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const sistema = (searchParams.get('sistema') || 'paneldx').trim();
  const secret = crmSecret();
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (secret) headers['x-crm-secret'] = secret;

  try {
    const upstream = await fetch(
      `${gatewayBase()}/api/crm/dashboard/funil-freemium?sistema=${encodeURIComponent(sistema)}`,
      { headers, cache: 'no-store' }
    );
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('Content-Type') || 'application/json' },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'gateway_unavailable';
    return NextResponse.json({ ok: false, error: message }, { status: 502 });
  }
}

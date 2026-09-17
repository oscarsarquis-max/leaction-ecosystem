import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function gatewayBase(): string {
  return (process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001').replace(/\/$/, '');
}

function crmHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
  const secret = (process.env.CRM_TRACKING_SECRET || '').trim();
  if (secret) headers['x-crm-secret'] = secret;
  return headers;
}

/** Proxy PATCH /api/crm/feedbacks/:id */
export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  const fid = String(id || '').trim();
  let payload: unknown = {};
  try {
    payload = await request.json();
  } catch {
    payload = {};
  }
  try {
    const upstream = await fetch(
      `${gatewayBase()}/api/crm/feedbacks/${encodeURIComponent(fid)}`,
      {
        method: 'PATCH',
        headers: crmHeaders(),
        body: JSON.stringify(payload),
        cache: 'no-store',
      }
    );
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

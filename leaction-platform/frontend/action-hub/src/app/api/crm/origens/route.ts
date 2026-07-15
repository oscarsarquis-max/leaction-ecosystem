import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function gatewayBase(): string {
  return (process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001').replace(/\/$/, '');
}

function crmSecret(): string {
  return (process.env.CRM_TRACKING_SECRET || '').trim();
}

function crmHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
  const secret = crmSecret();
  if (secret) headers['x-crm-secret'] = secret;
  return headers;
}

/** Lista origens cadastradas (+ detectadas em sessões). */
export async function GET() {
  try {
    const upstream = await fetch(`${gatewayBase()}/api/crm/origens`, {
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

/** Cadastra / atualiza origem analisável. */
export async function POST(request: Request) {
  try {
    const payload = await request.json().catch(() => ({}));
    const upstream = await fetch(`${gatewayBase()}/api/crm/origens`, {
      method: 'POST',
      headers: crmHeaders(),
      body: JSON.stringify(payload),
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

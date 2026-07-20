import { NextRequest, NextResponse } from 'next/server';

const GK_BYPASS_COOKIE = 'ah_gk_bypass';

const EXEMPT_EXACT = new Set(['/manutencao', '/api/health', '/favicon.ico']);

const EXEMPT_PREFIXES = [
  '/_next/',
  '/gatekeeper/',
  '/hub-api/webhooks/',
  '/hub-api/gatekeeper/',
  '/webhooks/',
  // Checkout satélite (inove4us → vitrine/Brick) mesmo com site em manutenção
  '/checkout/',
  '/hub-api/v1/catalog/',
  '/hub-api/v1/checkout/',
  '/hub-api/config/payments',
  '/hub-api/payments/',
  '/hub-api/orders/',
  // Action-Sponge: sensores S2S (inove4us/PanelDX) mesmo com site em manutenção
  '/hub-api/api/crm/tracking/',
];

function isExempt(pathname: string, searchParams: URLSearchParams): boolean {
  if (EXEMPT_EXACT.has(pathname)) return true;
  if (pathname === '/checkout' || pathname.startsWith('/checkout/')) return true;
  // Brick white-label: /dashboard?checkout=<orderId>
  if (pathname === '/dashboard' && searchParams.has('checkout')) return true;
  return EXEMPT_PREFIXES.some((p) => pathname === p.slice(0, -1) || pathname.startsWith(p));
}

async function isLocked(req: NextRequest): Promise<boolean> {
  const internal = (
    process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001'
  ).replace(/\/$/, '');
  try {
    const res = await fetch(`${internal}/gatekeeper/status`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });
    if (!res.ok) {
      return process.env.NODE_ENV === 'production';
    }
    const data = (await res.json()) as { locked?: boolean };
    return !!data.locked;
  } catch {
    // Em produção, falha de status = fail-closed (manutenção)
    return process.env.NODE_ENV === 'production';
  }
}

export async function middleware(req: NextRequest) {
  const { pathname, searchParams } = req.nextUrl;
  if (isExempt(pathname, searchParams)) return NextResponse.next();

  // Assets estáticos comuns
  if (/\.(png|jpg|jpeg|gif|svg|ico|webp|css|js|woff2?)$/i.test(pathname)) {
    return NextResponse.next();
  }

  const locked = await isLocked(req);
  if (!locked) return NextResponse.next();

  const bypass = req.cookies.get(GK_BYPASS_COOKIE)?.value;
  // Cookie válido é qualquer valor não-vazio setado pela rota /gatekeeper/bypass
  // (hash do master key). Sem comparação aqui no edge para não exigir crypto.
  if (bypass && bypass.length >= 16) {
    return NextResponse.next();
  }

  if (pathname.startsWith('/hub-api/') || pathname.startsWith('/api/')) {
    return NextResponse.json(
      { error: 'Sistema em preparação para lançamento.', maintenance: true },
      { status: 503 }
    );
  }

  const url = req.nextUrl.clone();
  url.pathname = '/manutencao';
  url.search = '';
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image).*)'],
};

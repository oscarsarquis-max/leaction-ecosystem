import { NextRequest, NextResponse } from 'next/server';

function isAllowedImageUrl(raw: string): boolean {
  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== 'https:') return false;
    const host = parsed.hostname.toLowerCase();
    return host === 'mlstatic.com' || host.endsWith('.mlstatic.com');
  } catch {
    return false;
  }
}

/** Proxy server-side de imagens ML (evita bloqueio de hotlink/referrer no browser). */
export async function GET(request: NextRequest) {
  const rawUrl = request.nextUrl.searchParams.get('url');
  if (!rawUrl || !isAllowedImageUrl(rawUrl)) {
    return NextResponse.json({ error: 'URL de imagem inválida' }, { status: 400 });
  }

  try {
    const upstream = await fetch(rawUrl, {
      headers: {
        Accept: 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
        Referer: 'https://www.mercadolivre.com.br/',
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
      signal: AbortSignal.timeout(12000),
      cache: 'force-cache',
      next: { revalidate: 86400 },
    });

    if (!upstream.ok) {
      return NextResponse.json(
        { error: `Imagem indisponível (${upstream.status})` },
        { status: upstream.status }
      );
    }

    const contentType = upstream.headers.get('content-type') || 'image/webp';
    const body = await upstream.arrayBuffer();

    return new NextResponse(body, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400, stale-while-revalidate=604800',
      },
    });
  } catch {
    return NextResponse.json({ error: 'Falha ao carregar imagem' }, { status: 502 });
  }
}

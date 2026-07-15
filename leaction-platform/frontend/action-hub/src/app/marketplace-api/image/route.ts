import { NextRequest, NextResponse } from 'next/server';

function isAllowedImageUrl(raw: string): boolean {
  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return false;
    const host = parsed.hostname.toLowerCase();
    const allowed = [
      'mlstatic.com',
      'media-amazon.com',
      'ssl-images-amazon.com',
      'images-amazon.com',
    ];
    return allowed.some((suffix) => host === suffix || host.endsWith(`.${suffix}`));
  } catch {
    return false;
  }
}

/** Proxy server-side de imagens ML/Amazon (evita bloqueio de hotlink/referrer no browser). */
export async function GET(request: NextRequest) {
  const rawUrl = request.nextUrl.searchParams.get('url');
  if (!rawUrl) {
    return NextResponse.json({ error: 'URL de imagem ausente' }, { status: 400 });
  }

  const secureUrl = rawUrl.replace(/^http:\/\//i, 'https://');
  if (!isAllowedImageUrl(secureUrl)) {
    return NextResponse.json({ error: 'URL de imagem inválida' }, { status: 400 });
  }

  try {
    const upstream = await fetch(secureUrl, {
      headers: {
        Accept: 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
        Referer: 'https://www.mercadolivre.com.br/',
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
      redirect: 'follow',
      signal: AbortSignal.timeout(15000),
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
    // Alguns CDNs devolvem HTML/JSON de erro com status 200
    if (!contentType.toLowerCase().startsWith('image/')) {
      return NextResponse.json(
        { error: `Content-Type inválido: ${contentType}` },
        { status: 502 }
      );
    }

    const body = await upstream.arrayBuffer();
    if (!body.byteLength) {
      return NextResponse.json({ error: 'Imagem vazia' }, { status: 502 });
    }

    return new NextResponse(body, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400, stale-while-revalidate=604800',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch {
    return NextResponse.json({ error: 'Falha ao carregar imagem' }, { status: 502 });
  }
}

/**
 * Normalização de URLs de imagem do marketplace (Mercado Livre CDN + placeholders).
 */

const ML_IMAGE_HOSTS = ['mlstatic.com'];

/** Garante HTTPS — evita Mixed Content no browser. */
export function forceHttpsMarketplaceImageUrl(url: string): string {
  return url.replace(/^http:\/\//i, 'https://');
}

export function isMercadoLivreCdnUrl(url: string): boolean {
  try {
    const host = new URL(url).hostname;
    return ML_IMAGE_HOSTS.some((allowed) => host === allowed || host.endsWith(`.${allowed}`));
  } catch {
    return false;
  }
}

export function isExternalMarketplaceImage(src: string): boolean {
  return src.startsWith('http://') || src.startsWith('https://');
}

export function isMarketplacePlaceholderPath(src: string): boolean {
  return src.startsWith('/marketplace/') || src.endsWith('.svg');
}

/** Proxy same-origin (fallback quando CDN bloqueia carregamento direto). */
export function toMarketplaceImageProxyPath(raw: string): string {
  const secure = forceHttpsMarketplaceImageUrl(raw);
  return `/marketplace-api/image?url=${encodeURIComponent(secure)}`;
}

export function toRelativeAssetPath(raw: string): string | null {
  try {
    const parsed = new URL(raw);
    if (
      parsed.pathname.startsWith('/marketplace-api/image') ||
      parsed.pathname.startsWith('/marketplace/placeholders')
    ) {
      return `${parsed.pathname}${parsed.search}`;
    }
  } catch {
    // not a full URL
  }
  return null;
}

export function resolveMarketplaceImageUrl(
  raw?: string | null,
  options?: { proxyMl?: boolean }
): string | null {
  if (!raw || typeof raw !== 'string') return null;
  let trimmed = forceHttpsMarketplaceImageUrl(raw.trim());
  if (!trimmed || trimmed.startsWith('data:')) return null;

  const relativeFromAbsolute = toRelativeAssetPath(trimmed);
  if (relativeFromAbsolute) {
    return relativeFromAbsolute;
  }

  if (trimmed.startsWith('/marketplace-api/image') || trimmed.startsWith('/')) {
    return trimmed;
  }

  if (trimmed.startsWith('//')) {
    trimmed = `https:${trimmed}`;
  }

  if (!trimmed.startsWith('https://')) {
    return null;
  }

  if (options?.proxyMl && isMercadoLivreCdnUrl(trimmed)) {
    return toMarketplaceImageProxyPath(trimmed);
  }

  return trimmed;
}

/** Normaliza imagens no payload — HTTPS + proxy same-origin para CDN ML. */
export function normalizeOfferImages(
  offers: Record<string, unknown>[]
): Record<string, unknown>[] {
  return offers.map((offer) => {
    const image = offer.image;
    if (typeof image !== 'string' || !image.trim()) {
      return offer;
    }

    const normalized = forceHttpsMarketplaceImageUrl(image.trim());

    const relative = toRelativeAssetPath(normalized);
    if (relative) {
      return { ...offer, image: relative };
    }

    if (normalized.startsWith('/')) {
      return { ...offer, image: normalized };
    }

    if (isMercadoLivreCdnUrl(normalized)) {
      return { ...offer, image: toMarketplaceImageProxyPath(normalized) };
    }

    return { ...offer, image: normalized };
  });
}

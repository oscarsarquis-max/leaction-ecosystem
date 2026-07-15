/**
 * Normalização de URLs de imagem do marketplace (Mercado Livre CDN + placeholders).
 */

const ML_IMAGE_HOSTS = ['mlstatic.com'];
const AMAZON_IMAGE_HOSTS = [
  'media-amazon.com',
  'ssl-images-amazon.com',
  'images-amazon.com',
  'images-na.ssl-images-amazon.com',
];

/** Garante HTTPS — evita Mixed Content no browser. */
export function forceHttpsMarketplaceImageUrl(url: string): string {
  return url.replace(/^http:\/\//i, 'https://');
}

function hostnameMatches(host: string, allowed: string[]): boolean {
  return allowed.some((suffix) => host === suffix || host.endsWith(`.${suffix}`));
}

export function isMercadoLivreCdnUrl(url: string): boolean {
  try {
    return hostnameMatches(new URL(url).hostname.toLowerCase(), ML_IMAGE_HOSTS);
  } catch {
    return false;
  }
}

export function isAmazonCdnUrl(url: string): boolean {
  try {
    return hostnameMatches(new URL(url).hostname.toLowerCase(), AMAZON_IMAGE_HOSTS);
  } catch {
    return false;
  }
}

/** CDNs que o browser costuma bloquear por hotlink/referrer em localhost. */
export function isProxiedMarketplaceCdnUrl(url: string): boolean {
  return isMercadoLivreCdnUrl(url) || isAmazonCdnUrl(url);
}

export function isExternalMarketplaceImage(src: string): boolean {
  return src.startsWith('http://') || src.startsWith('https://');
}

export function isMarketplacePlaceholderPath(src: string): boolean {
  const value = src.trim();
  return (
    value.startsWith('/marketplace/') ||
    value.startsWith('marketplace/') ||
    value.endsWith('.svg')
  );
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
      parsed.pathname.startsWith('/marketplace/placeholders') ||
      parsed.pathname.startsWith('/marketplace/')
    ) {
      return `${parsed.pathname}${parsed.search}`;
    }
  } catch {
    // not a full URL
  }
  return null;
}

function normalizeLocalPath(trimmed: string): string {
  if (trimmed.startsWith('marketplace/')) {
    return `/${trimmed}`;
  }
  return trimmed;
}

export function resolveMarketplaceImageUrl(
  raw?: string | null,
  options?: { proxyMl?: boolean }
): string | null {
  if (!raw || typeof raw !== 'string') return null;
  let trimmed = forceHttpsMarketplaceImageUrl(raw.trim());
  if (!trimmed || trimmed.startsWith('data:')) return null;

  trimmed = normalizeLocalPath(trimmed);

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

  if (options?.proxyMl !== false && isProxiedMarketplaceCdnUrl(trimmed)) {
    return toMarketplaceImageProxyPath(trimmed);
  }

  return trimmed;
}

/** Normaliza imagens no payload — HTTPS + proxy same-origin para CDN ML/Amazon. */
export function normalizeOfferImages(
  offers: Record<string, unknown>[]
): Record<string, unknown>[] {
  return offers.map((offer) => {
    const image = offer.image;
    if (typeof image !== 'string' || !image.trim()) {
      return offer;
    }

    const normalized = normalizeLocalPath(forceHttpsMarketplaceImageUrl(image.trim()));

    const relative = toRelativeAssetPath(normalized);
    if (relative) {
      return { ...offer, image: relative };
    }

    if (normalized.startsWith('/')) {
      return { ...offer, image: normalized };
    }

    if (isProxiedMarketplaceCdnUrl(normalized)) {
      return { ...offer, image: toMarketplaceImageProxyPath(normalized) };
    }

    return { ...offer, image: normalized };
  });
}

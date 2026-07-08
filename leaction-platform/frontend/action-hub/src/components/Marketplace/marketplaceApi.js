const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_MARKETPLACE_API_BASE || '/marketplace-api';

/** Opções do select de busca — ids alinhados ao orquestrador Flask. */
export const SEARCH_CATEGORIES = [
  { value: '', label: 'Todos' },
  { value: 'formacao', label: 'Formação e Liderança' },
  { value: 'equipamentos', label: 'Infraestrutura de TI' },
  { value: 'software', label: 'Software Educacional/Corporativo' },
];

export function buildOffersUrl({ q = '', category = '', limit = 8 } = {}) {
  const base = DEFAULT_API_BASE.replace(/\/$/, '');
  const params = new URLSearchParams();
  if (q.trim()) params.set('q', q.trim());
  if (category.trim()) params.set('category', category.trim());
  if (limit) params.set('limit', String(limit));

  const qs = params.toString();
  if (base.startsWith('/')) {
    return `${base}/offers${qs ? `?${qs}` : ''}`;
  }
  return `${base}/api/marketplace/offers${qs ? `?${qs}` : ''}`;
}

export async function fetchMarketplaceOffers({ q, category, limit, signal } = {}) {
  const url = buildOffersUrl({ q, category, limit });
  const response = await fetch(url, {
    cache: 'no-store',
    headers: { Accept: 'application/json' },
    signal,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Erro HTTP ${response.status}`);
  }
  return {
    offers: Array.isArray(data.offers) ? data.offers : [],
    source: data.source || '',
    notice: typeof data.notice === 'string' ? data.notice : '',
    category: data.category || category || '',
    query: data.query || q || '',
  };
}

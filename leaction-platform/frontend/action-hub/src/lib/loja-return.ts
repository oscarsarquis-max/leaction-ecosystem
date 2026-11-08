import { parseReturnOrigin, parseReturnTo } from '@/lib/hub-api';

export const LOJA_DEFAULT_ORIGIN = 'https://lojadepaes.com.br';
export const LOJA_DEFAULT_RETURN_TO = '/#biblioteca';

const ALLOWED = new Set([
  'https://lojadepaes.com.br',
  'http://127.0.0.1:5175',
  'http://localhost:5175',
]);

export function safeLojaReturnOrigin(raw: string | null | undefined): string {
  const origin = parseReturnOrigin(raw);
  if (origin && ALLOWED.has(origin)) return origin;
  return LOJA_DEFAULT_ORIGIN;
}

export function safeLojaReturnTo(raw: string | null | undefined): string {
  const path = parseReturnTo(raw);
  if (path === '/') return LOJA_DEFAULT_RETURN_TO;
  return path;
}

export function lojaReturnHref(originRaw: string | null | undefined, pathRaw: string | null | undefined): string {
  const origin = safeLojaReturnOrigin(originRaw);
  const path = safeLojaReturnTo(pathRaw);
  return `${origin}${path}`;
}

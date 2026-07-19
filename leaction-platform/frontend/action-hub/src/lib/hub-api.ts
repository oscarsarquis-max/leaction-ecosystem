const DEFAULT_GATEWAY_INTERNAL = 'http://127.0.0.1:4001';
const PANELDX_PORT = (process.env.NEXT_PUBLIC_PANELDX_PORT || '3000').trim();

/**
 * Base do gateway-api no browser: mesmo host do Action Hub, path /hub-api (proxy Next.js).
 * Em SSR usa env interno ou localhost.
 */
export function getHubApiBase(): string {
  if (typeof window !== 'undefined') {
    return `${window.location.origin.replace(/\/$/, '')}/hub-api`;
  }
  const env = (process.env.NEXT_PUBLIC_HUB_API_URL || '').trim();
  if (env) return env.replace(/\/$/, '');
  return DEFAULT_GATEWAY_INTERNAL;
}

/** @deprecated use getHubApiBase() — mantido para imports legados */
export const HUB_API_BASE = DEFAULT_GATEWAY_INTERNAL;

/** Chave pública Mercado Pago (Sandbox/Produção) — exposta ao browser para o Brick. */
export const MP_PUBLIC_KEY = (process.env.NEXT_PUBLIC_MP_PUBLIC_KEY || '').trim();

/** Valor mensal da assinatura exibido no Brick (deve coincidir com MP_SUBSCRIPTION_AMOUNT no gateway). */
export const MP_SUBSCRIPTION_AMOUNT = Number(
  process.env.NEXT_PUBLIC_MP_SUBSCRIPTION_AMOUNT || '99'
);

export type PaymentConfigResponse = {
  mercadopago_enabled: boolean;
  checkout_mode?: 'card' | 'subscription';
  public_key: string;
  paneldx_payment_amount?: number;
  sandbox_mode?: boolean;
  sandbox_payer_email?: string;
  brick_pair_valid?: boolean;
  brick_pair_hint?: string | null;
  server_tokenize_fallback?: boolean;
  subscription: {
    reason: string;
    amount: number;
    currency_id: string;
    frequency: number;
    frequency_type: string;
  };
};

const CHECKOUT_UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/** Extrai order_id UUID de ?checkout= (rejeita placeholders como simulado_hub). */
export function parseCheckoutOrderId(raw: string | null | undefined): string {
  const value = (raw || '').trim();
  return CHECKOUT_UUID_RE.test(value) ? value : '';
}

/** Origem do app cliente (white-label) — ex.: https://paneldx.com.br */
export function parseReturnOrigin(raw: string | null | undefined): string {
  const value = (raw || '').trim();
  if (!value) return '';
  try {
    const parsed = new URL(value.includes('://') ? value : `https://${value}`);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
    return parsed.origin;
  } catch {
    return '';
  }
}

/** Caminho seguro no app de origem para retorno pós-pagamento. */
export function parseReturnTo(raw: string | null | undefined): string {
  const value = (raw || '').trim();
  if (!value || !value.startsWith('/') || value.startsWith('//')) {
    // Fallback neutro — NÃO forçar /projeto (PanelDX); cada app envia return_to.
    return '/';
  }
  return value;
}

/**
 * Monta URL de retorno pós-pagamento: origem do cliente (dinâmica) + caminho.
 * O domínio NÃO é inferido do Action Hub — vem de ?return_origin= enviado pelo app parceiro.
 */
export function buildClientReturnUrl(
  returnOrigin?: string | null,
  returnTo?: string | null
): string {
  const origin = parseReturnOrigin(returnOrigin);
  const path = parseReturnTo(returnTo);
  if (origin) return `${origin}${path}`;

  // Fallbacks de dev — preferir inove4us / PanelDX por env; nunca misturar apps
  const inoveBase = (process.env.NEXT_PUBLIC_INOVE4US_URL || '').trim().replace(/\/$/, '');
  if (inoveBase && (path.startsWith('/mesa') || path.startsWith('/pagamento') || path.startsWith('/desafio') || path.startsWith('/acesso'))) {
    return `${inoveBase}${path}`;
  }
  const paneldxBase = (process.env.NEXT_PUBLIC_PANELDX_URL || '').trim().replace(/\/$/, '');
  if (paneldxBase) return `${paneldxBase}${path}`;
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      // Último recurso: Porta do app sugerida pelo path
      const port =
        path.startsWith('/mesa') ||
        path.startsWith('/pagamento') ||
        path.startsWith('/desafio') ||
        path.startsWith('/acesso')
          ? '5174'
          : PANELDX_PORT;
      return `${protocol}//${hostname}:${port}${path}`;
    }
  }
  return `http://localhost:5174${path === '/' ? '/mesa-do-inovador' : path}`;
}

/** @deprecated use buildClientReturnUrl(returnOrigin, returnTo) */
export function buildPanelDxReturnUrl(returnTo?: string | null): string {
  return buildClientReturnUrl(null, returnTo);
}

/** @deprecated white-label: use parseReturnOrigin + buildClientReturnUrl */
export function getPanelDxAppUrl(): string {
  const devBase = (process.env.NEXT_PUBLIC_PANELDX_URL || '').trim().replace(/\/$/, '');
  if (devBase) return devBase;
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `${protocol}//${hostname}:${PANELDX_PORT}`;
    }
  }
  return `http://localhost:${PANELDX_PORT}`;
}

/** Indica se a URL de checkout parece incompleta (sem order_id util). */
export function isCheckoutParamMissing(raw: string | null | undefined): boolean {
  return parseCheckoutOrderId(raw).length === 0;
}

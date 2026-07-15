import type { StaticImageData } from 'next/image';
import paneldxLogo from '@/imagens/paneldx/logo.jpg';

export type ClientBrandId = 'paneldx' | (string & {});

export type ClientBrandTheme = {
  id: ClientBrandId;
  displayName: string;
  productLabel: string;
  checkoutTitle: string;
  logo: StaticImageData;
  logoAlt: string;
  /** Mesmas medidas do `.header-logo` do PanelDX (layout.ejs / style.css). */
  logoLayout?: {
    heightPx: number;
    marginTopPx: number;
    borderPx: number;
  };
  colors: {
    headerBg: string;
    pageBg: string;
    accent: string;
    accentHover: string;
    accentMuted: string;
    textOnHeader: string;
    textMutedOnHeader: string;
    cardBorder: string;
    infoBg: string;
    infoBorder: string;
    infoText: string;
    success: string;
    successHover: string;
  };
};

const PANELDX_BRAND: ClientBrandTheme = {
  id: 'paneldx',
  displayName: 'Panel DX',
  productLabel: 'Diagnóstico de Maturidade Digital',
  checkoutTitle: 'Contratar PanelDX',
  logo: paneldxLogo,
  logoAlt: 'Panel DX — diagnóstico de maturidade digital educacional LeAction',
  colors: {
    headerBg: '#ffffff',
    pageBg: '#fafaf9',
    accent: '#f97316',
    accentHover: '#ea580c',
    accentMuted: '#fff7ed',
    textOnHeader: '#1c1917',
    textMutedOnHeader: '#78716c',
    cardBorder: '#e7e5e4',
    infoBg: '#fff7ed',
    infoBorder: '#fdba74',
    infoText: '#7c2d12',
    success: '#059669',
    successHover: '#047857',
  },
};

const BRAND_REGISTRY: Record<string, ClientBrandTheme> = {
  paneldx: PANELDX_BRAND,
};

export function parseClientId(raw: string | null | undefined): string {
  const value = (raw || '').trim().toLowerCase();
  if (!value || !/^[a-z0-9_-]+$/.test(value)) return '';
  return value;
}

export function inferClientFromGatewayRef(gatewayRef: string | null | undefined): string {
  const match = /^hub:([^:]+):/i.exec(String(gatewayRef || '').trim());
  return match ? parseClientId(match[1]) : '';
}

export function resolveClientBrand(
  clientId?: string | null,
  productType?: string | null
): ClientBrandTheme | null {
  const normalized = parseClientId(clientId);
  if (normalized && BRAND_REGISTRY[normalized]) {
    return BRAND_REGISTRY[normalized];
  }
  if (productType === 'PANELDX_ASSESSMENT' || productType === 'PANELDX_SUBSCRIPTION') {
    return PANELDX_BRAND;
  }
  return null;
}

export function listRegisteredClientBrands(): ClientBrandId[] {
  return Object.keys(BRAND_REGISTRY);
}

const CHECKOUT_HEADER_HEIGHT_PX = 60;
const CHECKOUT_CONTENT_GAP_PX = 16;

/** Espaço reservado abaixo do header fixo (logo inline — sem sobreposição). */
export function getCheckoutContentOffset(_brand: ClientBrandTheme): number {
  return CHECKOUT_HEADER_HEIGHT_PX + CHECKOUT_CONTENT_GAP_PX;
}

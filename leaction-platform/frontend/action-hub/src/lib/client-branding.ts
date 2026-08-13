import type { StaticImageData } from 'next/image';
import paneldxLogo from '@/imagens/paneldx/logo.jpg';

export type ClientBrandId = 'paneldx' | 'inove4us' | (string & {});

export type ClientBrandTheme = {
  id: ClientBrandId;
  displayName: string;
  productLabel: string;
  checkoutTitle: string;
  logo: StaticImageData | string;
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

/** Branding inove4us (Mesa do Inovador) — cores bordo/brand do produto. */
const INOVE4US_BRAND: ClientBrandTheme = {
  id: 'inove4us',
  displayName: 'inove4us',
  productLabel: 'Mesa do Inovador',
  checkoutTitle: 'Escolher seu plano',
  logo: '/brands/inove4us.png',
  logoAlt: 'inove4us — Mesa do Inovador',
  colors: {
    headerBg: '#ffffff',
    pageBg: '#faf7f5',
    accent: '#7f1d1d',
    accentHover: '#991b1b',
    accentMuted: '#fef2f2',
    textOnHeader: '#450a0a',
    textMutedOnHeader: '#78716c',
    cardBorder: '#e7e5e4',
    infoBg: '#fef2f2',
    infoBorder: '#fecaca',
    infoText: '#7f1d1d',
    // CTA pós-pagamento — mesma família bordo (sem verde no brand inove4us)
    success: '#7f1d1d',
    successHover: '#991b1b',
  },
};

/** Branding inove4us School (Torre de Controle B2B). */
const INOVE4US_SCHOOL_BRAND: ClientBrandTheme = {
  id: 'inove4us-school',
  displayName: 'inove4us School',
  productLabel: 'Torre de Controle da escola',
  checkoutTitle: 'Contratar o inove4us School',
  logo: '/brands/inove4us.png',
  logoAlt: 'inove4us School — Torre de Controle',
  colors: {
    headerBg: '#ffffff',
    pageBg: '#f4f2ec',
    accent: '#1f6f4a',
    accentHover: '#165536',
    accentMuted: '#e3f1e9',
    textOnHeader: '#1e2a4a',
    textMutedOnHeader: '#5b5551',
    cardBorder: '#d8d4c8',
    infoBg: '#e3f1e9',
    infoBorder: '#1f6f4a',
    infoText: '#123f2a',
    success: '#1f6f4a',
    successHover: '#165536',
  },
};

const BRAND_REGISTRY: Record<string, ClientBrandTheme> = {
  paneldx: PANELDX_BRAND,
  inove4us: INOVE4US_BRAND,
  'inove4us-school': INOVE4US_SCHOOL_BRAND,
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
  if (productType === 'HUB_CATALOG') {
    return INOVE4US_BRAND;
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

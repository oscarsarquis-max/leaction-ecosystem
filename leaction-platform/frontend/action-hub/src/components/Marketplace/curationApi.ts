/** Cliente HTTP do painel de curadoria — proxy Next.js /api/marketplace. */

import axios from 'axios';

const API_BASE = '/api/marketplace';

export type CurationRule = {
  id: string;
  search_terms: string[];
  positive_keywords: string[];
  negative_keywords: string[];
  updated_at?: string | null;
};

export type CurationRuleUpdate = {
  search_terms?: string[];
  positive_keywords?: string[];
  negative_keywords?: string[];
};

export type PreviewOffer = {
  id: string;
  title: string;
  price_label?: string;
  image?: string | null;
  link?: string;
  fallback?: boolean;
};

export const CATEGORY_IDS = ['formacao', 'equipamentos', 'software'] as const;

export const CATEGORY_LABELS: Record<string, string> = {
  global: 'Regras globais',
  formacao: 'Formação e Conteúdo Executivo',
  equipamentos: 'Infraestrutura e Conectividade',
  software: 'Software e Ferramentas Digitais',
};

/** Converte texto com vírgulas ou quebras de linha em lista. */
export function textToList(text: string): string[] {
  return text
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function listToCommaText(items: string[] | null | undefined): string {
  return (items || []).join(', ');
}

export function listToMultilineText(items: string[] | null | undefined): string {
  return (items || []).join('\n');
}

export function labelForCategory(id: string): string {
  return CATEGORY_LABELS[id] || id;
}

export function rulesToMap(rules: CurationRule[]): Record<string, CurationRule> {
  return Object.fromEntries(rules.map((rule) => [rule.id, rule]));
}

export async function fetchCurationRules(): Promise<CurationRule[]> {
  try {
    const { data } = await axios.get(`${API_BASE}/curation`, {
      headers: { Accept: 'application/json' },
      timeout: 15000,
    });
    if (!Array.isArray(data?.rules)) {
      throw new Error(data?.error || 'Resposta inválida ao carregar curadoria.');
    }
    return data.rules;
  } catch (err) {
    throw new Error(extractAxiosError(err, 'Erro ao carregar curadoria.'));
  }
}

export async function updateCurationRule(
  category: string,
  payload: CurationRuleUpdate
): Promise<CurationRule> {
  try {
    const { data } = await axios.put(
      `${API_BASE}/curation/${encodeURIComponent(category)}`,
      payload,
      {
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        timeout: 15000,
      }
    );
    if (!data?.rule) {
      throw new Error(data?.error || 'Resposta sem regra atualizada.');
    }
    return data.rule;
  } catch (err) {
    throw new Error(extractAxiosError(err, 'Erro ao salvar regras.'));
  }
}

export async function fetchPreviewOffers(category: string, limit = 4) {
  try {
    const { data } = await axios.get(`${API_BASE}/preview`, {
      params: { category, limit },
      headers: { Accept: 'application/json' },
      timeout: 20000,
    });
    return {
      offers: (Array.isArray(data?.offers) ? data.offers : []) as PreviewOffer[],
      live: Boolean(data?.live),
      count: Number(data?.count) || 0,
      fallback: Boolean(data?.vendors?.mercadolivre?.fallback),
      notice: typeof data?.notice === 'string' ? data.notice : '',
      query: typeof data?.query === 'string' ? data.query : '',
    };
  } catch (err) {
    throw new Error(extractAxiosError(err, 'Erro ao testar busca.'));
  }
}

function extractAxiosError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const apiError = err.response?.data?.error;
    if (typeof apiError === 'string' && apiError.trim()) return apiError;
    if (err.message) return err.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

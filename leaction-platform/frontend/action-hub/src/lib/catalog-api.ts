import axios from 'axios';
import { getHubApiBase } from '@/lib/hub-api';

export type CatalogPlanPublic = {
  id: string;
  app_id: string;
  sku: string;
  name: string;
  type: string;
  price: number;
  currency: string;
  features: string[];
  credits: number | null;
};

export function formatCatalogCurrency(value: number, currency = 'BRL'): string {
  try {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: currency || 'BRL',
    }).format(Number(value) || 0);
  } catch {
    return `R$ ${(Number(value) || 0).toFixed(2)}`;
  }
}

export async function fetchCatalogPlans(appId: string): Promise<CatalogPlanPublic[]> {
  const id = String(appId || '').trim().toLowerCase();
  if (!id) return [];
  const res = await axios.get(`${getHubApiBase()}/v1/catalog/${encodeURIComponent(id)}`);
  const plans = Array.isArray(res.data?.plans) ? res.data.plans : [];
  return plans.map((p: CatalogPlanPublic) => ({
    id: String(p.id),
    app_id: String(p.app_id || id),
    sku: String(p.sku || ''),
    name: String(p.name || ''),
    type: String(p.type || 'plan'),
    price: Number(p.price) || 0,
    currency: String(p.currency || 'BRL'),
    features: Array.isArray(p.features) ? p.features.map(String) : [],
    credits: p.credits != null && Number.isFinite(Number(p.credits)) ? Number(p.credits) : null,
  }));
}

export async function startCatalogCheckout(payload: {
  app_id: string;
  sku: string;
  subject_id: string;
  return_origin?: string;
  return_to?: string;
  hub_public_url?: string;
}): Promise<string> {
  const res = await axios.post(`${getHubApiBase()}/v1/checkout/catalog`, {
    ...payload,
    hub_public_url:
      payload.hub_public_url ||
      (typeof window !== 'undefined' ? window.location.origin : undefined),
  });
  const url = String(res.data?.checkout_url || '').trim();
  if (!url) throw new Error('Gateway não retornou checkout_url.');
  return url;
}

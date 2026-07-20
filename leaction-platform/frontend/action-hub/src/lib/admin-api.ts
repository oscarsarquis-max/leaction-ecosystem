'use client';

import axios, { type AxiosInstance } from 'axios';
import { getHubApiBase } from '@/lib/hub-api';

export type AdminApp = {
  app_id: string;
  name: string;
  webhook_url: string | null;
  return_origins: string[];
  active: boolean;
  created_at?: string;
  has_secret: boolean;
  secret_hint: string | null;
};

export type CatalogPlanType = 'plan' | 'credit_pack' | 'addon' | 'seat';

export type CatalogPlan = {
  id: string;
  app_id: string;
  name: string;
  type: CatalogPlanType;
  sku: string;
  price: number;
  currency: string;
  features: unknown;
  meta_json: Record<string, unknown>;
  active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type PlanUpsertBody = {
  app_id?: string;
  name: string;
  type: CatalogPlanType;
  sku: string;
  price: number;
  currency?: string;
  features?: unknown[];
  meta_json?: Record<string, unknown>;
  active?: boolean;
};

function createAdminClient(token: string): AxiosInstance {
  return axios.create({
    baseURL: getHubApiBase(),
    timeout: 20000,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
}

export async function fetchAdminApps(token: string): Promise<AdminApp[]> {
  const client = createAdminClient(token);
  const { data } = await client.get<{ apps: AdminApp[] }>('/admin/apps');
  return Array.isArray(data?.apps) ? data.apps : [];
}

export async function updateAdminApp(
  token: string,
  appId: string,
  body: Partial<{ name: string; active: boolean; webhook_url: string | null }>
): Promise<AdminApp> {
  const client = createAdminClient(token);
  const { data } = await client.put<{ app: AdminApp }>(
    `/admin/apps/${encodeURIComponent(appId)}`,
    body
  );
  return data.app;
}

export async function fetchAdminPlans(
  token: string,
  appId: string
): Promise<CatalogPlan[]> {
  const client = createAdminClient(token);
  const { data } = await client.get<{ plans: CatalogPlan[] }>('/admin/plans', {
    params: { app_id: appId },
  });
  return Array.isArray(data?.plans) ? data.plans : [];
}

export async function createAdminPlan(
  token: string,
  body: PlanUpsertBody & { app_id: string }
): Promise<CatalogPlan> {
  const client = createAdminClient(token);
  const { data } = await client.post<{ plan: CatalogPlan }>('/admin/plans', body);
  return data.plan;
}

export async function updateAdminPlan(
  token: string,
  planId: string,
  body: PlanUpsertBody
): Promise<CatalogPlan> {
  const client = createAdminClient(token);
  const { data } = await client.put<{ plan: CatalogPlan }>(
    `/admin/plans/${encodeURIComponent(planId)}`,
    body
  );
  return data.plan;
}

export type InjectCreditsBody = {
  app_id: string;
  subject_id: string;
  amount: number;
  reason: string;
};

export type InjectCreditsResult = {
  success?: boolean;
  message?: string;
  app_id: string;
  subject_id: string;
  credits_added: number;
  credits_balance?: number;
  reason: string;
  idempotency_key?: string;
  event_type?: string;
};

export async function injectAdminCredits(
  token: string,
  body: InjectCreditsBody
): Promise<InjectCreditsResult> {
  const client = createAdminClient(token);
  const { data } = await client.post<InjectCreditsResult>(
    '/admin/credits/inject',
    body
  );
  return data;
}

export type AdminPayment = {
  id: string;
  status: string;
  payment_status?: string | null;
  created_at: string;
  paid_at?: string | null;
  gateway_reference?: string | null;
  payer_email?: string | null;
  product_name?: string | null;
  product_sku?: string | null;
  product_type?: string | null;
  app_id?: string | null;
  subject_id?: string | null;
  plan_name?: string | null;
  plan_sku?: string | null;
  amount?: number | null;
  currency?: string;
  contract_id?: string | null;
  contract_status?: string | null;
  latest_notice?: string | null;
};

export type AdminPaymentCounts = {
  total: number;
  pending: number;
  paid: number;
  other: number;
};

export type AdminPaymentStatPoint = {
  day: string;
  plan_name: string;
  app_id: string;
  orders_total: number;
  orders_paid: number;
  orders_pending: number;
  revenue: number;
};

export async function fetchAdminPayments(
  token: string,
  params?: {
    status?: string;
    app_id?: string;
    limit?: number;
    include_test?: boolean;
  }
): Promise<{ payments: AdminPayment[]; counts: AdminPaymentCounts }> {
  const client = createAdminClient(token);
  const { data } = await client.get<{
    payments: AdminPayment[];
    counts: AdminPaymentCounts;
  }>('/admin/payments', {
    params: {
      status: params?.status,
      app_id: params?.app_id,
      limit: params?.limit,
      ...(params?.include_test ? { include_test: '1' } : {}),
    },
  });
  return {
    payments: Array.isArray(data?.payments) ? data.payments : [],
    counts: data?.counts || { total: 0, pending: 0, paid: 0, other: 0 },
  };
}

export async function fetchAdminPaymentStats(
  token: string,
  params?: { days?: number; app_id?: string; include_test?: boolean }
): Promise<AdminPaymentStatPoint[]> {
  const client = createAdminClient(token);
  const { data } = await client.get<{ series: AdminPaymentStatPoint[] }>(
    '/admin/payments/stats',
    {
      params: {
        days: params?.days,
        app_id: params?.app_id,
        ...(params?.include_test ? { include_test: '1' } : {}),
      },
    }
  );
  return Array.isArray(data?.series) ? data.series : [];
}

export async function postAdminPaymentNotice(
  token: string,
  orderId: string,
  body: { message: string; status_label?: string }
): Promise<{ success?: boolean; notice?: { id: string } }> {
  const client = createAdminClient(token);
  const { data } = await client.post(
    `/admin/payments/${encodeURIComponent(orderId)}/notice`,
    body
  );
  return data;
}

export function planTypeLabel(type: string): string {
  switch (type) {
    case 'plan':
      return 'Assinatura Mensal';
    case 'credit_pack':
      return 'Pacote de Créditos';
    case 'addon':
      return 'Add-on';
    case 'seat':
      return 'Seat';
    default:
      return type;
  }
}

export function formatBrl(price: number, currency = 'BRL'): string {
  try {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: currency || 'BRL',
    }).format(Number(price) || 0);
  } catch {
    return `R$ ${Number(price || 0).toFixed(2)}`;
  }
}

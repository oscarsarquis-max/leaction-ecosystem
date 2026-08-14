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
      return 'Assinatura mensal';
    case 'credit_pack':
      return 'Pacote de créditos';
    case 'addon':
      return 'Complemento';
    case 'seat':
      return 'Licença (vaga)';
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

export type CmsSistemaDestino =
  | 'hub-publico'
  | 'actionhub'
  | 'inove4us'
  | 'paneldx'
  | 'todos'
  | 'comercial_publico';
export type CmsPostStatus = 'rascunho' | 'publicado';

export type CmsPost = {
  id: number;
  slug: string;
  titulo: string;
  resumo: string | null;
  conteudo_html: string | null;
  imagem_capa: string | null;
  sistema_destino: CmsSistemaDestino | string;
  status: CmsPostStatus | string;
  publicado_em: string | null;
  criado_em: string;
};

export type CmsPostUpsertBody = {
  titulo: string;
  slug?: string;
  resumo?: string;
  conteudo_html?: string;
  imagem_capa?: string | null;
  sistema_destino: CmsSistemaDestino | string;
  status: CmsPostStatus | string;
};

export async function fetchCmsPostsAdmin(token: string): Promise<CmsPost[]> {
  const client = createAdminClient(token);
  const { data } = await client.get<{ posts: CmsPost[] }>('/api/cms/posts/admin');
  return Array.isArray(data?.posts) ? data.posts : [];
}

export async function createCmsPost(
  token: string,
  body: CmsPostUpsertBody
): Promise<CmsPost> {
  const client = createAdminClient(token);
  const { data } = await client.post<{ post: CmsPost }>('/api/cms/posts', body);
  return data.post;
}

export async function updateCmsPost(
  token: string,
  id: number,
  body: CmsPostUpsertBody
): Promise<CmsPost> {
  const client = createAdminClient(token);
  const { data } = await client.put<{ post: CmsPost }>(
    `/api/cms/posts/${encodeURIComponent(String(id))}`,
    body
  );
  return data.post;
}

export type CmsUploadResult = {
  success: boolean;
  url: string;
  public_url?: string;
  storage?: 's3' | 'local' | string;
  error?: string;
};

/** Upload Multer → S3 (mesmo contrato do PanelDX: field `imagem`). */
export async function uploadCmsImage(
  token: string,
  file: File
): Promise<CmsUploadResult> {
  const form = new FormData();
  form.append('imagem', file);
  const res = await fetch(`${getHubApiBase()}/api/admin/cms/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const data = (await res.json().catch(() => ({}))) as CmsUploadResult;
  if (!res.ok || !data.success) {
    throw new Error(data.error || `Falha no upload (HTTP ${res.status})`);
  }
  return data;
}

export type CmsSiteConfig = {
  success?: boolean;
  config_key?: string;
  landing_page_data: Record<string, unknown>;
  instructions_data: string;
  updated_at?: string | null;
};

export type CmsSiteConfigKey = 'default' | 'inove4us' | 'inove4us-school';

export async function fetchCmsSiteAdmin(
  token: string,
  configKey: CmsSiteConfigKey = 'default'
): Promise<CmsSiteConfig> {
  const client = createAdminClient(token);
  const { data } = await client.get<CmsSiteConfig>('/api/admin/cms', {
    params: { config_key: configKey },
  });
  return data;
}

export async function saveCmsSiteAdmin(
  token: string,
  body: {
    config_key?: CmsSiteConfigKey;
    landing_page_data?: Record<string, unknown>;
    instructions_data?: string;
  }
): Promise<CmsSiteConfig> {
  const client = createAdminClient(token);
  const { data } = await client.put<CmsSiteConfig>('/api/admin/cms', body);
  return data;
}

export type CmsAssistenteChatRecord = {
  id: number;
  sistema_destino: CmsSistemaDestino | string;
  status: CmsPostStatus | string;
  tree: Record<string, unknown>;
  publicado_em: string | null;
  atualizado_em: string | null;
  atualizado_por: string | null;
  created_at: string | null;
};

export type CmsAssistenteChatAdminResponse = {
  rascunho: CmsAssistenteChatRecord | null;
  publicado: CmsAssistenteChatRecord | null;
};

export type CmsAssistenteChatUpsertBody = {
  sistema_destino: CmsSistemaDestino | string;
  tree: Record<string, unknown>;
  status: CmsPostStatus | string;
};

export async function fetchCmsAssistenteChatAdmin(
  token: string,
  sistemaDestino: string
): Promise<CmsAssistenteChatAdminResponse> {
  const client = createAdminClient(token);
  const { data } = await client.get<CmsAssistenteChatAdminResponse>(
    '/api/cms/assistente-chat/admin',
    { params: { sistema_destino: sistemaDestino } }
  );
  return {
    rascunho: data?.rascunho ?? null,
    publicado: data?.publicado ?? null,
  };
}

export async function saveCmsAssistenteChat(
  token: string,
  body: CmsAssistenteChatUpsertBody
): Promise<CmsAssistenteChatRecord> {
  const client = createAdminClient(token);
  const { data } = await client.put<{ assistente_chat: CmsAssistenteChatRecord }>(
    '/api/cms/assistente-chat',
    body
  );
  return data.assistente_chat;
}

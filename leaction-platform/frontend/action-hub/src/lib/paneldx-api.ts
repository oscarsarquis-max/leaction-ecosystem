/**
 * Catálogo PanelDX no ActionHub — via gateway (CRM ao vivo + fallback cache Hub).
 */

export type PanelDxPlanoVitrine = {
  id: number;
  nome: string;
  valor_mensal: number;
  periodicidade: string;
  descricao_beneficios: string[];
  max_usuarios?: number;
  ativo?: boolean;
  tipo_plano?: string;
};

export type PanelDxVitrineSource = 'paneldx_live' | 'hub_cache';

export type PanelDxVitrineResponse = {
  status: string;
  source?: PanelDxVitrineSource;
  planos: PanelDxPlanoVitrine[];
  addons?: PanelDxAddonVitrine[];
  error?: string;
  sync_id?: string;
  received_at?: string;
  published_at?: string;
};

export type PanelDxVitrineFetchResult = {
  planos: PanelDxPlanoVitrine[];
  source?: PanelDxVitrineSource;
  received_at?: string;
};

export type PanelDxAddonVitrine = {
  id: number;
  nome: string;
  valor_mensal: number;
  periodicidade: string;
  max_usuarios: number;
  tipo_plano: 'addon';
};

export type PanelDxAddonResponse = {
  status: string;
  addon: PanelDxAddonVitrine;
  error?: string;
};

/** Reexport hub API base. */
export { getHubApiBase } from '@/lib/hub-api';

function filterPlanosAtivos(planos: PanelDxPlanoVitrine[]): PanelDxPlanoVitrine[] {
  return planos.filter((p) => p && p.ativo !== false);
}

export function formatPanelDxSeatLabel(maxUsuarios?: number): string {
  const n = Number(maxUsuarios);
  if (!Number.isFinite(n) || n >= 999) return 'Usuários Ilimitados';
  if (n <= 0) return 'Até 1 usuário ativo';
  return `Até ${n} usuários ativos`;
}

export function formatPanelDxCurrency(value: number): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n);
}

export function formatVitrineUpdatedAt(iso?: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

/** Planos + metadados (origem CRM ou cache). */
export async function fetchPanelDxPlanosVitrineWithMeta(): Promise<PanelDxVitrineFetchResult> {
  const { getHubApiBase } = await import('@/lib/hub-api');
  const hubBase = getHubApiBase();
  const res = await fetch(`${hubBase}/v1/vitrine/paneldx?_=${Date.now()}`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    return { planos: [] };
  }
  const data = (await res.json()) as PanelDxVitrineResponse;
  const planos = Array.isArray(data.planos) ? data.planos : [];
  return {
    planos: filterPlanosAtivos(planos),
    source: data.source,
    received_at: data.received_at,
  };
}

/** Planos base publicados (CRM ao vivo via gateway). */
export async function fetchPanelDxPlanosVitrine(): Promise<PanelDxPlanoVitrine[]> {
  const { planos } = await fetchPanelDxPlanosVitrineWithMeta();
  return planos;
}

export function parseClientIdParam(raw: string | null | undefined): string {
  const value = String(raw || '').trim();
  if (!value || !/^\d+$/.test(value)) return '';
  return value;
}

export function parsePlanIdParam(raw: string | null | undefined): string {
  const value = String(raw || '').trim();
  if (!value || !/^\d+$/.test(value)) return '';
  return value;
}

export function parseAddonIdParam(raw: string | null | undefined): string {
  return parsePlanIdParam(raw);
}

export function parseAddonFromHandoffParams(
  params: Pick<URLSearchParams, 'get'>
): PanelDxAddonVitrine | null {
  const id = parseAddonIdParam(params.get('addon_id'));
  if (!id) return null;

  const nome = (params.get('addon_nome') || '').trim();
  const valorRaw = params.get('addon_valor');
  const valor = valorRaw != null ? Number(valorRaw) : NaN;
  if (!nome || !Number.isFinite(valor) || valor <= 0) return null;

  return {
    id: Number(id),
    nome,
    valor_mensal: valor,
    periodicidade: (params.get('addon_periodicidade') || 'Mensal').trim() || 'Mensal',
    max_usuarios: Number(params.get('addon_max_usuarios') || 0) || 0,
    tipo_plano: 'addon',
  };
}

export async function fetchPanelDxAddon(
  addonId: string | number,
  handoff?: Pick<URLSearchParams, 'get'> | null
): Promise<PanelDxAddonVitrine> {
  const fromUrl = handoff ? parseAddonFromHandoffParams(handoff) : null;
  if (fromUrl && String(fromUrl.id) === String(addonId)) {
    return fromUrl;
  }

  const id = parseAddonIdParam(String(addonId));
  if (!id) throw new Error('ID do pacote add-on inválido.');

  const { getHubApiBase } = await import('@/lib/hub-api');
  const res = await fetch(`${getHubApiBase()}/v1/vitrine/paneldx/addons/${id}?_=${Date.now()}`, {
    cache: 'no-store',
  });
  const data = (await res.json().catch(() => ({}))) as PanelDxAddonResponse;
  if (!res.ok || !data.addon) {
    throw new Error(
      data.error ||
        'Pacote add-on não encontrado. Publique a vitrine no CRM PanelDX (inclui add-ons).'
    );
  }
  return data.addon;
}

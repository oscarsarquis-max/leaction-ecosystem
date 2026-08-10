import { NextResponse } from 'next/server';

import { extractBearerToken, resolveHubAdminFromRequest } from '@/lib/hub-admin-jwt';

export type ServiceStatus = 'UP' | 'DOWN' | 'TIMEOUT';

export type ServiceStatusItem = {
  name: string;
  status: ServiceStatus;
  latency: number | null;
  lastChecked: string;
  detail?: string;
};

const PROBE_TIMEOUT_MS = 5000;
/** offers/vitrine batem ML ao vivo — 5s gerava TIMEOUT falso no monitor com o processo UP. */
const MARKETPLACE_FUNCTIONAL_PROBE_TIMEOUT_MS = 30_000;

function stripSlash(url: string): string {
  return url.replace(/\/$/, '');
}

function gatewayBaseCandidates(): string[] {
  const out: string[] = [];
  const push = (raw?: string | null) => {
    const v = String(raw || '').trim();
    if (!v) return;
    const base = stripSlash(v);
    if (!out.includes(base)) out.push(base);
  };
  push(process.env.HUB_GATEWAY_INTERNAL_URL);
  push('http://127.0.0.1:4001');
  // Fallback público: evita falso DOWN quando o Next não alcança o loopback do gateway.
  push(process.env.HUB_GATEWAY_PUBLIC_URL);
  push(process.env.NEXT_PUBLIC_GATEWAY_URL);
  push(process.env.ACTION_HUB_API_URL);
  push('https://api.actionhub.com.br');
  return out;
}

function marketplaceBaseCandidates(): string[] {
  const out: string[] = [];
  const push = (raw?: string | null) => {
    const v = String(raw || '').trim();
    if (!v) return;
    const base = stripSlash(v);
    if (!out.includes(base)) out.push(base);
  };
  push(process.env.MARKETPLACE_INTERNAL_URL);
  push('http://127.0.0.1:4012');
  return out;
}

/** FE health via loopback — hairpin HTTPS (origin público) falha em vários EC2/NAT. */
function frontendHealthUrl(request: Request): string {
  const explicit = String(process.env.HUB_FRONTEND_INTERNAL_URL || '').trim();
  if (explicit) return `${stripSlash(explicit)}/api/health`;
  const port = String(process.env.PORT || '4000').trim() || '4000';
  // Em produção o Action Hub FE escuta PORT (setup-env-remote = 4000).
  if (process.env.NODE_ENV === 'production') {
    return `http://127.0.0.1:${port}/api/health`;
  }
  return `${new URL(request.url).origin}/api/health`;
}

async function firstReachableBase(
  candidates: string[],
  healthPath: string,
  isOk: (res: Response, body: unknown) => boolean = (res) => res.ok
): Promise<{ base: string; latency: number } | null> {
  for (const base of candidates) {
    const started = Date.now();
    try {
      const res = await fetch(`${base}${healthPath}`, {
        cache: 'no-store',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
      });
      let body: unknown = null;
      try {
        body = await res.json();
      } catch {
        body = null;
      }
      if (isOk(res, body)) {
        return { base, latency: Date.now() - started };
      }
    } catch {
      // tenta próximo candidato
    }
  }
  return null;
}

/** Apps do catálogo de planos (Gestão de Planos atende Inove4us e PanelDX). */
function planProbeAppIds(): string[] {
  const fromEnv = (
    process.env.STATUS_PROBE_APP_IDS ||
    process.env.HUB_STATUS_PLAN_APP_IDS ||
    ''
  ).trim();
  if (fromEnv) {
    return fromEnv
      .split(',')
      .map((id) => id.trim().toLowerCase())
      .filter(Boolean);
  }
  return ['inove4us', 'paneldx'];
}

function mergePlanProbes(
  probes: Array<ServiceStatusItem & { appId: string }>
): ServiceStatusItem {
  const lastChecked = new Date().toISOString();
  const labels = probes.map((p) => p.appId).join(' + ');
  const latencies = probes
    .map((p) => p.latency)
    .filter((n): n is number => typeof n === 'number');
  const latency = latencies.length ? Math.max(...latencies) : null;

  const down = probes.filter((p) => p.status === 'DOWN');
  const timedOut = probes.filter((p) => p.status === 'TIMEOUT');

  if (timedOut.length) {
    return {
      name: 'Gestão de Planos',
      status: 'TIMEOUT',
      latency,
      lastChecked,
      detail: `Sem resposta no catálogo (${timedOut.map((p) => p.appId).join(', ')})`,
    };
  }
  if (down.length) {
    return {
      name: 'Gestão de Planos',
      status: 'DOWN',
      latency,
      lastChecked,
      detail: `Falha no catálogo (${down.map((p) => `${p.appId}: ${p.detail || 'erro'}`).join('; ')})`,
    };
  }

  return {
    name: 'Gestão de Planos',
    status: 'UP',
    latency,
    lastChecked,
    detail: `Gateway · catálogo de planos (${labels})`,
  };
}

async function probeService(
  name: string,
  url: string,
  isOk: (res: Response, body: unknown) => boolean,
  headers: Record<string, string> = {},
  timeoutMs: number = PROBE_TIMEOUT_MS
): Promise<ServiceStatusItem> {
  const lastChecked = new Date().toISOString();
  const started = Date.now();

  try {
    const res = await fetch(url, {
      cache: 'no-store',
      headers: { Accept: 'application/json', ...headers },
      signal: AbortSignal.timeout(timeoutMs),
    });
    const latency = Date.now() - started;
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }

    if (isOk(res, body)) {
      return { name, status: 'UP', latency, lastChecked };
    }

    return {
      name,
      status: 'DOWN',
      latency,
      lastChecked,
      detail: `HTTP ${res.status}`,
    };
  } catch (err) {
    const latency = Date.now() - started;
    const message = err instanceof Error ? err.message : String(err);
    const timedOut =
      (err instanceof Error && err.name === 'TimeoutError') ||
      /aborted|timeout/i.test(message);

    return {
      name,
      status: timedOut ? 'TIMEOUT' : 'DOWN',
      latency,
      lastChecked,
      detail: timedOut ? `Timeout após ${timeoutMs}ms` : message.slice(0, 160),
    };
  }
}

function paymentsOk(res: Response): boolean {
  return res.ok;
}

function plansOk(res: Response, body: unknown): boolean {
  if (!res.ok) return false;
  if (body && typeof body === 'object' && 'plans' in body) {
    return Array.isArray((body as { plans?: unknown }).plans);
  }
  return true;
}

function marketplaceOk(res: Response, body: unknown): boolean {
  if (!res.ok) return false;
  if (body && typeof body === 'object' && 'status' in body) {
    return String((body as { status?: string }).status).toLowerCase() === 'ok';
  }
  return true;
}

function marketplaceOffersOk(res: Response, body: unknown): boolean {
  if (!res.ok) return false;
  if (body && typeof body === 'object' && 'offers' in body) {
    return Array.isArray((body as { offers?: unknown }).offers);
  }
  return false;
}

function marketplaceVitrineOk(res: Response): boolean {
  return res.ok;
}

/**
 * Health sozinho mente — a UI usa /offers e /vitrine.
 * Se health sobe mas a rota funcional quebra (ex.: dependência ausente), o monitor deve DOWN.
 */
async function probeMarketplace(): Promise<ServiceStatusItem> {
  const reached = await firstReachableBase(
    marketplaceBaseCandidates(),
    '/api/marketplace/health',
    marketplaceOk
  );

  if (!reached) {
    return {
      name: 'API do Marketplace',
      status: 'DOWN',
      latency: null,
      lastChecked: new Date().toISOString(),
      detail:
        'Plugin Marketplace inacessível em MARKETPLACE_INTERNAL_URL / :4012 (processo parado ou porta fechada)',
    };
  }

  const base = reached.base;
  const healthBody = await (async () => {
    try {
      const res = await fetch(`${base}/api/marketplace/health`, {
        cache: 'no-store',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
      });
      return (await res.json()) as Record<string, unknown>;
    } catch {
      return null;
    }
  })();

  const [offers, vitrine] = await Promise.all([
    probeService(
      'Ofertas do Marketplace',
      `${base}/api/marketplace/offers`,
      marketplaceOffersOk,
      {},
      MARKETPLACE_FUNCTIONAL_PROBE_TIMEOUT_MS
    ),
    probeService(
      'Vitrine do Marketplace',
      `${base}/api/marketplace/vitrine`,
      marketplaceVitrineOk,
      {},
      MARKETPLACE_FUNCTIONAL_PROBE_TIMEOUT_MS
    ),
  ]);

  const latency = Math.max(
    reached.latency,
    offers.latency ?? 0,
    vitrine.latency ?? 0
  );

  if (offers.status !== 'UP' || vitrine.status !== 'UP') {
    const parts: string[] = [];
    if (offers.status !== 'UP') {
      parts.push(`/offers ${offers.status}${offers.detail ? ` (${offers.detail})` : ''}`);
    }
    if (vitrine.status !== 'UP') {
      parts.push(`/vitrine ${vitrine.status}${vitrine.detail ? ` (${vitrine.detail})` : ''}`);
    }
    return {
      name: 'API do Marketplace',
      status: offers.status === 'TIMEOUT' || vitrine.status === 'TIMEOUT' ? 'TIMEOUT' : 'DOWN',
      latency,
      lastChecked: new Date().toISOString(),
      detail: `Health OK em ${base}, mas rota funcional falhou: ${parts.join('; ')}`,
    };
  }

  const mlReady = healthBody?.ml_tokens_ready === true;
  const detailParts = [
    `Plugin · ${base} · health + ofertas + vitrine`,
    mlReady
      ? 'Tokens Mercado Livre OK'
      : 'Tokens ML ausentes (busca ao vivo limitada; vitrine curada pode valer)',
  ];

  return {
    name: 'API do Marketplace',
    status: 'UP',
    latency,
    lastChecked: new Date().toISOString(),
    detail: detailParts.join(' · '),
  };
}

function frontendOk(res: Response, body: unknown): boolean {
  if (!res.ok) return false;
  if (body && typeof body === 'object' && 'ok' in body) {
    return Boolean((body as { ok?: boolean }).ok);
  }
  return true;
}

/** GET /api/sys/status — agrega healthchecks do ecossistema ActionHub (admin). */
export async function GET(request: Request) {
  const admin = await resolveHubAdminFromRequest(request);
  if (!admin) {
    return NextResponse.json(
      { status: 'error', error: 'Não autorizado.' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  const bearer = extractBearerToken(request);
  const authHeaders: Record<string, string> | undefined = bearer
    ? { Authorization: `Bearer ${bearer}` }
    : undefined;
  const planAppIds = planProbeAppIds();

  // Resolve gateway uma vez (loopback → público) para não marcar Action Pay/Planos DOWN à toa.
  const gwReached = await firstReachableBase(
    gatewayBaseCandidates(),
    '/health',
    (res, body) => {
      if (!res.ok) return false;
      if (body && typeof body === 'object' && 'ok' in body) {
        return Boolean((body as { ok?: boolean }).ok);
      }
      return true;
    }
  );
  const gw = gwReached?.base || gatewayBaseCandidates()[0];

  const [actionPay, planProbes, marketplace, frontend] = await Promise.all([
    gwReached
      ? probeService('Action Pay', `${gw}/config/payments`, paymentsOk).then((item) => ({
          ...item,
          detail:
            item.detail ||
            `Gateway · pagamentos / Mercado Pago · via ${gw}`,
        }))
      : Promise.resolve({
          name: 'Action Pay',
          status: 'DOWN' as const,
          latency: null,
          lastChecked: new Date().toISOString(),
          detail:
            'Gateway inacessível (HUB_GATEWAY_INTERNAL_URL / :4001 / api.actionhub.com.br)',
        }),
    gwReached
      ? Promise.all(
          planAppIds.map(async (appId) => {
            const item = await probeService(
              `Gestão de Planos (${appId})`,
              `${gw}/admin/plans?app_id=${encodeURIComponent(appId)}`,
              plansOk,
              authHeaders
            );
            return { ...item, appId };
          })
        )
      : Promise.resolve(
          planAppIds.map((appId) => ({
            name: `Gestão de Planos (${appId})`,
            status: 'DOWN' as const,
            latency: null,
            lastChecked: new Date().toISOString(),
            detail: 'Gateway inacessível',
            appId,
          }))
        ),
    probeMarketplace(),
    probeService('Frontend do Action Hub', frontendHealthUrl(request), frontendOk),
  ]);

  const planManagement = mergePlanProbes(planProbes);

  // Postgres é exercitado de verdade pela Gestão de Planos (catalog_plans).
  const lastChecked = new Date().toISOString();
  const dbProbe = planManagement.status === 'UP' ? planManagement : actionPay;
  const postgres: ServiceStatusItem =
    planManagement.status === 'UP'
      ? {
          name: 'PostgreSQL',
          status: 'UP',
          latency: planManagement.latency,
          lastChecked,
          detail: 'Inferido via Gestão de Planos (catalog_plans)',
        }
      : {
          name: 'PostgreSQL',
          status: planManagement.status === 'TIMEOUT' ? 'TIMEOUT' : 'DOWN',
          latency: dbProbe.latency,
          lastChecked,
          detail: 'Indisponível — Gestão de Planos sem resposta no banco',
        };

  const services: ServiceStatusItem[] = [
    actionPay,
    planManagement,
    marketplace,
    postgres,
    frontend,
  ];

  return NextResponse.json(services, {
    headers: { 'Cache-Control': 'no-store' },
  });
}

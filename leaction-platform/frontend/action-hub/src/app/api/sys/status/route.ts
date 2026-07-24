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

function gatewayBase(): string {
  return (process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001').replace(
    /\/$/,
    ''
  );
}

function marketplaceBase(): string {
  return (process.env.MARKETPLACE_INTERNAL_URL || 'http://127.0.0.1:4012').replace(
    /\/$/,
    ''
  );
}

/** Apps do catálogo de planos (Plan Management atende Inove4us e PanelDX). */
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
      name: 'Plan Management',
      status: 'TIMEOUT',
      latency,
      lastChecked,
      detail: `Timeout no catálogo (${timedOut.map((p) => p.appId).join(', ')})`,
    };
  }
  if (down.length) {
    return {
      name: 'Plan Management',
      status: 'DOWN',
      latency,
      lastChecked,
      detail: `Falha no catálogo (${down.map((p) => `${p.appId}: ${p.detail || 'erro'}`).join('; ')})`,
    };
  }

  return {
    name: 'Plan Management',
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
  headers: Record<string, string> = {}
): Promise<ServiceStatusItem> {
  const lastChecked = new Date().toISOString();
  const started = Date.now();

  try {
    const res = await fetch(url, {
      cache: 'no-store',
      headers: { Accept: 'application/json', ...headers },
      signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
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
      detail: timedOut ? `Timeout após ${PROBE_TIMEOUT_MS}ms` : message.slice(0, 160),
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

  const origin = new URL(request.url).origin;
  const bearer = extractBearerToken(request);
  const authHeaders = bearer ? { Authorization: `Bearer ${bearer}` } : {};
  const planAppIds = planProbeAppIds();
  const gw = gatewayBase();

  const [actionPay, planProbes, marketplace, frontend] = await Promise.all([
    probeService('Action Pay', `${gw}/config/payments`, paymentsOk).then((item) => ({
      ...item,
      detail: item.detail || 'Gateway · pagamentos / Mercado Pago',
    })),
    Promise.all(
      planAppIds.map(async (appId) => {
        const item = await probeService(
          `Plan Management (${appId})`,
          `${gw}/admin/plans?app_id=${encodeURIComponent(appId)}`,
          plansOk,
          authHeaders
        );
        return { ...item, appId };
      })
    ),
    probeService(
      'Marketplace API',
      `${marketplaceBase()}/api/marketplace/health`,
      marketplaceOk
    ),
    probeService('ActionHub Frontend', `${origin}/api/health`, frontendOk),
  ]);

  const planManagement = mergePlanProbes(planProbes);

  // Postgres é exercitado de verdade pelo Plan Management (catalog_plans).
  const lastChecked = new Date().toISOString();
  const dbProbe = planManagement.status === 'UP' ? planManagement : actionPay;
  const postgres: ServiceStatusItem =
    planManagement.status === 'UP'
      ? {
          name: 'PostgreSQL',
          status: 'UP',
          latency: planManagement.latency,
          lastChecked,
          detail: 'Inferido via Plan Management (catalog_plans)',
        }
      : {
          name: 'PostgreSQL',
          status: planManagement.status === 'TIMEOUT' ? 'TIMEOUT' : 'DOWN',
          latency: dbProbe.latency,
          lastChecked,
          detail: 'Indisponível — Plan Management sem resposta no banco',
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

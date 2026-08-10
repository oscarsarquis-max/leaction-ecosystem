'use strict';

/**
 * Probes de saúde dos 5 serviços do monitor Action Hub (sem sessão de browser).
 * Usado pelo status-watcher (alertas SES).
 */

const PROBE_TIMEOUT_MS = 5000;
const MARKETPLACE_FUNCTIONAL_PROBE_TIMEOUT_MS = 30_000;

function stripSlash(url) {
  return String(url || '').replace(/\/$/, '');
}

function gatewayBase() {
  return stripSlash(
    process.env.HUB_GATEWAY_INTERNAL_URL ||
      process.env.STATUS_ALERT_GATEWAY_URL ||
      `http://127.0.0.1:${process.env.GATEWAY_PORT || 4001}`
  );
}

function marketplaceBase() {
  return stripSlash(
    process.env.MARKETPLACE_INTERNAL_URL ||
      process.env.STATUS_ALERT_MARKETPLACE_URL ||
      'http://127.0.0.1:4012'
  );
}

function frontendHealthUrl() {
  const explicit = String(process.env.HUB_FRONTEND_INTERNAL_URL || '').trim();
  if (explicit) return `${stripSlash(explicit)}/api/health`;
  const port = String(process.env.HUB_FRONTEND_PORT || process.env.PORT || '4000').trim() || '4000';
  return `http://127.0.0.1:${port}/api/health`;
}

function planProbeAppIds() {
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

function probeJwt() {
  return String(process.env.STATUS_ALERT_PROBE_JWT || '').trim();
}

/**
 * @returns {Promise<{ name: string, status: 'UP'|'DOWN'|'TIMEOUT', latency: number|null, lastChecked: string, detail?: string, probeUrl?: string }>}
 */
async function probeHttp(name, url, isOk, headers = {}, timeoutMs = PROBE_TIMEOUT_MS) {
  const lastChecked = new Date().toISOString();
  const started = Date.now();
  try {
    const res = await fetch(url, {
      cache: 'no-store',
      headers: { Accept: 'application/json', ...headers },
      signal: AbortSignal.timeout(timeoutMs),
    });
    const latency = Date.now() - started;
    let body = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    if (isOk(res, body)) {
      return { name, status: 'UP', latency, lastChecked, probeUrl: url };
    }
    return {
      name,
      status: 'DOWN',
      latency,
      lastChecked,
      detail: `HTTP ${res.status}`,
      probeUrl: url,
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
      probeUrl: url,
    };
  }
}

function paymentsOk(res) {
  return res.ok;
}

function plansOk(res, body) {
  if (!res.ok) return false;
  if (body && typeof body === 'object' && 'plans' in body) {
    return Array.isArray(body.plans);
  }
  return true;
}

function marketplaceOk(res, body) {
  if (!res.ok) return false;
  if (body && typeof body === 'object' && 'status' in body) {
    return String(body.status).toLowerCase() === 'ok';
  }
  return true;
}

function marketplaceOffersOk(res, body) {
  if (!res.ok) return false;
  if (body && typeof body === 'object' && 'offers' in body) {
    return Array.isArray(body.offers);
  }
  return false;
}

function marketplaceVitrineOk(res) {
  return res.ok;
}

function frontendOk(res, body) {
  if (!res.ok) return false;
  if (body && typeof body === 'object' && 'ok' in body) {
    return Boolean(body.ok);
  }
  return true;
}

async function probeActionPay() {
  const url = `${gatewayBase()}/config/payments`;
  const item = await probeHttp('Action Pay', url, paymentsOk);
  if (item.status === 'UP' && !item.detail) {
    item.detail = `Gateway · pagamentos / Mercado Pago · via ${gatewayBase()}`;
  }
  return item;
}

async function probePlanManagement() {
  const jwt = probeJwt();
  const headers = jwt ? { Authorization: `Bearer ${jwt}` } : {};
  const appIds = planProbeAppIds();
  const gw = gatewayBase();

  if (!jwt) {
    return {
      name: 'Gestão de Planos',
      status: 'DOWN',
      latency: null,
      lastChecked: new Date().toISOString(),
      detail: 'STATUS_ALERT_PROBE_JWT ausente — não é possível autenticar /admin/plans',
      probeUrl: `${gw}/admin/plans`,
    };
  }

  const probes = await Promise.all(
    appIds.map((appId) =>
      probeHttp(
        `Gestão de Planos (${appId})`,
        `${gw}/admin/plans?app_id=${encodeURIComponent(appId)}`,
        plansOk,
        headers
      ).then((item) => ({ ...item, appId }))
    )
  );

  const lastChecked = new Date().toISOString();
  const labels = probes.map((p) => p.appId).join(' + ');
  const latencies = probes.map((p) => p.latency).filter((n) => typeof n === 'number');
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
      probeUrl: `${gw}/admin/plans`,
    };
  }
  if (down.length) {
    return {
      name: 'Gestão de Planos',
      status: 'DOWN',
      latency,
      lastChecked,
      detail: `Falha no catálogo (${down.map((p) => `${p.appId}: ${p.detail || 'erro'}`).join('; ')})`,
      probeUrl: `${gw}/admin/plans`,
    };
  }
  return {
    name: 'Gestão de Planos',
    status: 'UP',
    latency,
    lastChecked,
    detail: `Gateway · catálogo de planos (${labels})`,
    probeUrl: `${gw}/admin/plans`,
  };
}

async function probeMarketplace() {
  const base = marketplaceBase();
  const healthUrl = `${base}/api/marketplace/health`;
  const health = await probeHttp('API do Marketplace', healthUrl, marketplaceOk);
  if (health.status !== 'UP') {
    return {
      ...health,
      detail:
        health.detail ||
        `Plugin Marketplace inacessível em ${base} (processo parado ou porta fechada)`,
    };
  }

  const [offers, vitrine] = await Promise.all([
    probeHttp(
      'Ofertas',
      `${base}/api/marketplace/offers`,
      marketplaceOffersOk,
      {},
      MARKETPLACE_FUNCTIONAL_PROBE_TIMEOUT_MS
    ),
    probeHttp(
      'Vitrine',
      `${base}/api/marketplace/vitrine`,
      marketplaceVitrineOk,
      {},
      MARKETPLACE_FUNCTIONAL_PROBE_TIMEOUT_MS
    ),
  ]);

  const latency = Math.max(health.latency ?? 0, offers.latency ?? 0, vitrine.latency ?? 0);
  if (offers.status !== 'UP' || vitrine.status !== 'UP') {
    const parts = [];
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
      probeUrl: healthUrl,
    };
  }

  return {
    name: 'API do Marketplace',
    status: 'UP',
    latency,
    lastChecked: new Date().toISOString(),
    detail: `Plugin · ${base} · health + ofertas + vitrine`,
    probeUrl: healthUrl,
  };
}

/**
 * @param {import('pg').Pool} pool
 */
async function probePostgres(pool) {
  const lastChecked = new Date().toISOString();
  const started = Date.now();
  const probeUrl = 'postgresql://…/leaction_hub (SELECT 1)';
  if (!pool) {
    return {
      name: 'PostgreSQL',
      status: 'DOWN',
      latency: null,
      lastChecked,
      detail: 'Pool pg ausente no gateway',
      probeUrl,
    };
  }
  try {
    await pool.query('SELECT 1 AS ok');
    return {
      name: 'PostgreSQL',
      status: 'UP',
      latency: Date.now() - started,
      lastChecked,
      detail: 'SELECT 1 via pool do gateway',
      probeUrl,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      name: 'PostgreSQL',
      status: 'DOWN',
      latency: Date.now() - started,
      lastChecked,
      detail: message.slice(0, 160),
      probeUrl,
    };
  }
}

async function probeFrontend() {
  const url = frontendHealthUrl();
  const item = await probeHttp('Frontend do Action Hub', url, frontendOk);
  if (item.status === 'UP' && !item.detail) {
    item.detail = `Next.js · ${url}`;
  }
  return item;
}

/**
 * @param {import('pg').Pool} pool
 * @returns {Promise<Array>}
 */
async function runAllStatusProbes(pool) {
  const [actionPay, planManagement, marketplace, postgres, frontend] = await Promise.all([
    probeActionPay(),
    probePlanManagement(),
    probeMarketplace(),
    probePostgres(pool),
    probeFrontend(),
  ]);
  return [actionPay, planManagement, marketplace, postgres, frontend];
}

module.exports = {
  runAllStatusProbes,
  gatewayBase,
  marketplaceBase,
  frontendHealthUrl,
  planProbeAppIds,
};

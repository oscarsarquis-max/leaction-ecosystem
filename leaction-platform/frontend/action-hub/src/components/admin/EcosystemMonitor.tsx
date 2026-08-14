'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Radio,
  RefreshCw,
  RotateCcw,
  Server,
  ServerCrash,
  Timer,
} from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';

type ServiceStatus = 'UP' | 'DOWN' | 'TIMEOUT';

type ServiceStatusItem = {
  name: string;
  status: ServiceStatus;
  latency: number | null;
  lastChecked: string;
  detail?: string;
};

type MitigateService = 'marketplace' | 'gateway';

const POLL_MS = 30_000;

function mitigationFor(
  name: string
): { service: MitigateService; label: string } | null {
  if (name === 'API do Marketplace') {
    return { service: 'marketplace', label: 'Reiniciar Marketplace' };
  }
  if (name === 'Action Pay' || name === 'Gestão de Planos') {
    return { service: 'gateway', label: 'Reiniciar gateway' };
  }
  return null;
}

function formatCheckedAt(iso: string | null | undefined) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function StatusBadge({ status }: { status: ServiceStatus }) {
  if (status === 'UP') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-green-400 opacity-60" />
          <span className="relative inline-flex size-2 animate-pulse rounded-full bg-green-500" />
        </span>
        No ar
      </span>
    );
  }
  if (status === 'TIMEOUT') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900">
        <Timer className="size-3.5" aria-hidden />
        Sem resposta
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500 px-2.5 py-1 text-xs font-semibold text-white">
      <span className="size-2 rounded-full bg-white/90" aria-hidden />
      Fora
    </span>
  );
}

function ServiceCard({
  service,
  mitigating,
  onMitigate,
}: {
  service: ServiceStatusItem;
  mitigating: boolean;
  onMitigate?: (svc: MitigateService) => void;
}) {
  const down = service.status === 'DOWN' || service.status === 'TIMEOUT';
  const Icon =
    service.status === 'UP' ? CheckCircle2 : service.status === 'TIMEOUT' ? Timer : ServerCrash;
  const action = mitigationFor(service.name);

  return (
    <article
      className={`rounded-xl border bg-white p-5 shadow-sm transition ${
        down ? 'border-red-300 ring-1 ring-red-100' : 'border-stone-200'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${
              down ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-700'
            }`}
          >
            <Icon className="size-5" aria-hidden />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-stone-900">{service.name}</h2>
            {service.detail ? (
              <p className="mt-0.5 line-clamp-2 text-xs text-stone-500">{service.detail}</p>
            ) : (
              <p className="mt-0.5 flex items-center gap-1 text-xs text-stone-500">
                <Server className="size-3" aria-hidden />
                Verificação de saúde
              </p>
            )}
          </div>
        </div>
        <StatusBadge status={service.status} />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-stone-100 pt-4">
        <div>
          <dt className="text-[10px] font-bold uppercase tracking-wider text-stone-400">
            Latência
          </dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-stone-800">
            {typeof service.latency === 'number' ? `${service.latency} ms` : '—'}
          </dd>
        </div>
        <div>
          <dt className="text-[10px] font-bold uppercase tracking-wider text-stone-400">
            Última verificação
          </dt>
          <dd className="mt-0.5 text-sm font-medium text-stone-800">
            {formatCheckedAt(service.lastChecked)}
          </dd>
        </div>
      </dl>

      {action && onMitigate ? (
        <div className="mt-4 border-t border-stone-100 pt-3">
          <button
            type="button"
            disabled={mitigating}
            onClick={() => onMitigate(action.service)}
            className={`inline-flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition disabled:opacity-60 ${
              down
                ? 'bg-emerald-500 text-white hover:bg-emerald-400'
                : 'border border-stone-200 bg-stone-50 text-stone-800 hover:bg-stone-100'
            }`}
          >
            {mitigating ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <RotateCcw className="size-4" aria-hidden />
            )}
            {action.label}
          </button>
        </div>
      ) : null}
    </article>
  );
}

const AUTH_BANNER =
  'Sessão admin expirada — faça login de novo para ver o status.';

function isAuthFailureMessage(message: string): boolean {
  return /n[aã]o autorizado|unauthorized|sess[aã]o admin/i.test(message);
}

export function EcosystemMonitor() {
  const { token } = useHubSession();
  const [services, setServices] = useState<ServiceStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authBlocked, setAuthBlocked] = useState(false);
  const [mitigateMsg, setMitigateMsg] = useState<string | null>(null);
  const [mitigatingService, setMitigatingService] = useState<MitigateService | null>(
    null
  );
  const [secondsLeft, setSecondsLeft] = useState(POLL_MS / 1000);
  const inFlight = useRef(false);

  const loadStatus = useCallback(
    async (manual = false) => {
      if (inFlight.current) return;
      inFlight.current = true;
      if (manual) setRefreshing(true);
      setError(null);

      try {
        const auth = String(token || '').trim();
        if (!auth) {
          // Não pintar os 5 serviços como DOWN — é falha de sessão, não de infra.
          setAuthBlocked(true);
          setServices([]);
          setError(AUTH_BANNER);
          return;
        }

        const res = await fetch('/api/sys/status', {
          cache: 'no-store',
          headers: {
            Accept: 'application/json',
            Authorization: `Bearer ${auth}`,
          },
          signal: AbortSignal.timeout(60_000),
        });

        if (res.status === 401) {
          setAuthBlocked(true);
          setServices([]);
          setError(AUTH_BANNER);
          return;
        }

        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as { error?: string };
          throw new Error(body.error || `HTTP ${res.status}`);
        }

        const data = (await res.json()) as unknown;
        if (!Array.isArray(data)) {
          throw new Error('Resposta inválida da API de status.');
        }

        setAuthBlocked(false);
        setServices(
          data.map((row) => {
            const item = row as Partial<ServiceStatusItem>;
            const status =
              item.status === 'UP' || item.status === 'TIMEOUT' || item.status === 'DOWN'
                ? item.status
                : 'DOWN';
            return {
              name: String(item.name || 'Serviço'),
              status,
              latency: typeof item.latency === 'number' ? item.latency : null,
              lastChecked: String(item.lastChecked || new Date().toISOString()),
              detail: item.detail ? String(item.detail) : undefined,
            };
          })
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Falha ao carregar status';
        if (isAuthFailureMessage(message)) {
          setAuthBlocked(true);
          setServices([]);
          setError(AUTH_BANNER);
          return;
        }

        const timedOut =
          (err instanceof Error && err.name === 'TimeoutError') ||
          /aborted|timeout/i.test(message);

        setAuthBlocked(false);
        setError(timedOut ? 'Timeout ao agregar status dos serviços.' : message);
        // Mantém a lista anterior; só marca DOWN/TIMEOUT se já havia dados reais.
        setServices((prev) =>
          prev.length
            ? prev.map((s) => ({
                ...s,
                status: timedOut ? 'TIMEOUT' : 'DOWN',
                lastChecked: new Date().toISOString(),
                detail: timedOut ? 'Timeout na agregação' : message,
              }))
            : prev
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
        setSecondsLeft(POLL_MS / 1000);
        inFlight.current = false;
      }
    },
    [token]
  );

  const runMitigation = useCallback(
    async (service: MitigateService) => {
      const auth = String(token || '').trim();
      if (!auth || mitigatingService) return;

      const label = service === 'marketplace' ? 'Marketplace' : 'Gateway';
      if (
        !window.confirm(
          `Reiniciar ${label} agora?\n\nIsso encerra o processo local e sobe de novo (pode levar ~30–60s).`
        )
      ) {
        return;
      }

      setMitigatingService(service);
      setMitigateMsg(`Reiniciando ${label}…`);
      try {
        const res = await fetch('/api/sys/mitigate', {
          method: 'POST',
          cache: 'no-store',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${auth}`,
          },
          body: JSON.stringify({ action: 'restart', service }),
          signal: AbortSignal.timeout(120_000),
        });
        const body = (await res.json().catch(() => ({}))) as {
          ok?: boolean;
          message?: string;
          error?: string;
        };
        if (!res.ok || !body.ok) {
          throw new Error(body.message || body.error || `HTTP ${res.status}`);
        }
        setMitigateMsg(body.message || `${label} reiniciado.`);
        await loadStatus(true);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Falha na mitigação';
        setMitigateMsg(`Falha: ${message}`);
      } finally {
        setMitigatingService(null);
      }
    },
    [token, mitigatingService, loadStatus]
  );

  useEffect(() => {
    void loadStatus(false);
  }, [loadStatus]);

  useEffect(() => {
    const poll = window.setInterval(() => {
      void loadStatus(false);
    }, POLL_MS);
    return () => window.clearInterval(poll);
  }, [loadStatus]);

  useEffect(() => {
    const tick = window.setInterval(() => {
      setSecondsLeft((s) => (s <= 1 ? POLL_MS / 1000 : s - 1));
    }, 1000);
    return () => window.clearInterval(tick);
  }, []);

  useEffect(() => {
    if (!mitigateMsg) return undefined;
    const t = window.setTimeout(() => setMitigateMsg(null), 8000);
    return () => window.clearTimeout(t);
  }, [mitigateMsg]);

  const upCount = services.filter((s) => s.status === 'UP').length;
  const total = services.length;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[0.14em] text-emerald-600">
            <Radio className="size-3.5" aria-hidden />
            Operações
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-stone-900">
            Status do Ecossistema
          </h1>
          <p className="mt-1 max-w-xl text-sm text-stone-500">
            Monitoramento dos serviços internos do ActionHub. Quando algo falha,
            use a mitigação rápida (reinício) no card do serviço.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm text-stone-500">
            Próxima atualização em{' '}
            <span className="font-semibold tabular-nums text-stone-800">{secondsLeft}s</span>
          </p>
          <button
            type="button"
            onClick={() => void loadStatus(true)}
            disabled={refreshing || loading || mitigatingService !== null}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3.5 py-2 text-sm font-semibold text-stone-800 shadow-sm transition hover:bg-stone-50 disabled:opacity-60"
          >
            {refreshing || loading ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="size-4" aria-hidden />
            )}
            Atualizar Agora
          </button>
        </div>
      </header>

      {mitigateMsg ? (
        <div
          className={`rounded-xl border px-4 py-3 text-sm ${
            mitigateMsg.startsWith('Falha')
              ? 'border-red-200 bg-red-50 text-red-800'
              : 'border-emerald-200 bg-emerald-50 text-emerald-900'
          }`}
        >
          {mitigateMsg}
        </div>
      ) : null}

      {authBlocked ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p className="inline-flex items-start gap-2 font-medium">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
            {error || AUTH_BANNER}
          </p>
          <p className="mt-1 text-amber-800/90">
            Os serviços não foram marcados como fora do ar — é preciso autenticar de novo
            para consultar o status real.
          </p>
        </div>
      ) : null}

      {!loading && !authBlocked && total > 0 ? (
        <div className="rounded-xl border border-stone-200 bg-white px-4 py-3 shadow-sm">
          <p className="text-sm text-stone-600">
            <span className="font-semibold text-stone-900">
              {upCount}/{total}
            </span>{' '}
            serviços operacionais
            {error ? (
              <span className="ml-2 inline-flex items-center gap-1 text-amber-700">
                <AlertTriangle className="size-3.5" aria-hidden />
                {error}
              </span>
            ) : null}
          </p>
        </div>
      ) : null}

      {loading && !authBlocked && services.length === 0 ? (
        <div className="flex items-center justify-center gap-2 rounded-xl border border-stone-200 bg-white py-16 text-sm text-stone-500 shadow-sm">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Verificando serviços…
        </div>
      ) : authBlocked ? (
        <div className="rounded-xl border border-dashed border-stone-200 bg-white py-12 text-center text-sm text-stone-500 shadow-sm">
          Status dos serviços oculto até o login admin.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {services.map((service) => {
            const action = mitigationFor(service.name);
            return (
              <ServiceCard
                key={service.name}
                service={service}
                mitigating={
                  mitigatingService !== null &&
                  action?.service === mitigatingService
                }
                onMitigate={action ? runMitigation : undefined}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

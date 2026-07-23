'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  Clock3,
  Download,
  Loader2,
  Lock,
  Percent,
  Plus,
  RotateCcw,
  Users,
  type LucideIcon,
} from 'lucide-react';
import { useAuthGate } from '@/lib/require-hub-login';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const COLOR_PRIMARY = '#7f1d1d';
const COLOR_SECONDARY = '#dc2626';
const COLOR_ACCENT = '#f97316';
const COLOR_NEUTRAL = '#cbd5e1';

type OrigemItem = {
  slug: string;
  nome: string;
  descricao?: string | null;
  ativo?: boolean;
  sessoes?: number;
  fonte?: string;
};

type LiveFeedItem = {
  id: string;
  ipHash: string;
  ferramenta: string;
  ferramentaKey: 'mesa' | 'solucionador' | 'home' | 'outro';
  tempoSessao: string;
};

type DashboardViewModel = {
  kpis: {
    totalVisitas: number;
    taxaConversaoFreemium: number;
    tempoMedioUsoLabel: string;
    taxaRetencao: number;
    tendencias: { visitas: number; conversao: number; tempo: number; retencao: number };
  };
  evolucao: Array<{ dia: string; pageviews: number; eventos: number }>;
  dispositivos: Array<{ name: string; value: number; color: string }>;
  funil: Array<{ etapa: string; valor: number; fill: string }>;
  liveFeed: LiveFeedItem[];
};

const EMPTY_DASHBOARD: DashboardViewModel = {
  kpis: {
    totalVisitas: 0,
    taxaConversaoFreemium: 0,
    tempoMedioUsoLabel: '0s',
    taxaRetencao: 0,
    tendencias: { visitas: 0, conversao: 0, tempo: 0, retencao: 0 },
  },
  evolucao: [],
  dispositivos: [
    { name: 'Desktop', value: 0, color: COLOR_PRIMARY },
    { name: 'Mobile', value: 0, color: COLOR_ACCENT },
  ],
  funil: [
    { etapa: 'Home', valor: 0, fill: COLOR_PRIMARY },
    { etapa: 'Interesse (Clique)', valor: 0, fill: COLOR_SECONDARY },
    { etapa: 'Uso Real', valor: 0, fill: COLOR_ACCENT },
  ],
  liveFeed: [],
};

function formatNumber(n: number): string {
  return new Intl.NumberFormat('pt-BR').format(n);
}

function funilDropoffs(funil: DashboardViewModel['funil']) {
  return funil.map((step, i) => {
    if (i === 0) return { ...step, convPct: 100, dropoffPct: 0 };
    const prev = funil[i - 1].valor;
    const conv = prev > 0 ? Math.round((step.valor / prev) * 1000) / 10 : 0;
    return {
      ...step,
      convPct: Math.min(100, conv),
      dropoffPct: Math.max(0, Math.round((100 - Math.min(100, conv)) * 10) / 10),
    };
  });
}

function inferFerramenta(url: string | null | undefined, evento: string | null | undefined) {
  const path = String(url || '').toLowerCase();
  const ev = String(evento || '').toLowerCase();
  if (ev.includes('pagamento_aprovado') || ev.includes('checkout_iniciar')) {
    return { ferramenta: 'Pagamento / assinatura', ferramentaKey: 'solucionador' as const };
  }
  if (ev.includes('plano_gerar') || path.includes('etapa=plano')) {
    return { ferramenta: 'Elaborou plano', ferramentaKey: 'solucionador' as const };
  }
  if (ev.includes('desafio_estruturar') || ev.includes('caminho_selecionar')) {
    return { ferramenta: 'Criou desafio', ferramentaKey: 'mesa' as const };
  }
  if (path.includes('/desafio')) {
    return { ferramenta: 'Desafio', ferramentaKey: 'mesa' as const };
  }
  if (path.includes('mesa') || ev.includes('mesa') || path.includes('/inovador')) {
    return { ferramenta: 'Mesa do Inovador', ferramentaKey: 'mesa' as const };
  }
  if (path.includes('solucionador') || path.includes('consultor') || ev.includes('solucionador')) {
    return { ferramenta: 'Solucionador', ferramentaKey: 'solucionador' as const };
  }
  if (!path || path.endsWith('/') || path.includes('/acesso') || path.includes('/home')) {
    return { ferramenta: 'Home', ferramentaKey: 'home' as const };
  }
  return { ferramenta: evento || 'Sessão', ferramentaKey: 'outro' as const };
}

function mapApiToDashboard(api: any): DashboardViewModel {
  const funil = api?.funil || {};
  const eng = api?.engajamento || {};
  const ret = api?.retencao || {};
  const dev = api?.dispositivos || {};
  const isInove =
    String(api?.funil_modelo || '').startsWith('inove4us_') ||
    api?.sistema_origem === 'inove4us';

  const visitas = Number(funil.visitas_home || funil.total_sessoes || 0);
  const cliques = Number(
    isInove
      ? funil.desafios_estruturados || funil.cliques_ferramentas || 0
      : funil.cliques_ferramentas || 0
  );
  const uso = Number(
    isInove
      ? funil.planos_gerados || funil.acesso_ferramentas || 0
      : funil.acesso_ferramentas || 0
  );
  const pagamentos = Number(funil.pagamentos_aprovados || 0);
  const conv = Number(
    (isInove
      ? funil.taxas_conversao?.plano_para_pagamento_pct ??
        funil.taxas_conversao?.home_para_uso_pct
      : funil.taxas_conversao?.home_para_uso_pct) || 0
  );
  const retencao = Number(ret.taxa_retencao_pct || 0);

  const avgMesa = Number(eng.mesa_do_inovador?.segundos || 0);
  const avgSol = Number(eng.solucionador?.segundos || 0);
  const amostrasMesa = Number(eng.mesa_do_inovador?.amostras || 0);
  const amostrasSol = Number(eng.solucionador?.amostras || 0);
  const amostraTotal = amostrasMesa + amostrasSol;
  const tempoMedioSeg =
    amostraTotal > 0
      ? (avgMesa * amostrasMesa + avgSol * amostrasSol) / amostraTotal
      : avgMesa || avgSol || 0;
  const mins = Math.floor(tempoMedioSeg / 60);
  const secs = Math.round(tempoMedioSeg % 60);
  const tempoLabel = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

  const liveFeed: LiveFeedItem[] = (api?.sessoes_recentes || []).slice(0, 8).map((r: any) => {
    const tool = inferFerramenta(r.ultima_url, r.ultimo_evento);
    return {
      id: String(r.id_sessao),
      ipHash: String(r.id_sessao).slice(0, 12) + '…',
      ferramenta: tool.ferramenta,
      ferramentaKey: tool.ferramentaKey,
      tempoSessao: `${Number(r.qtd_eventos || 0)} evt`,
    };
  });

  const evolucao = Array.isArray(api?.evolucao_acessos)
    ? api.evolucao_acessos.map((d: any) => ({
        dia: String(d.dia),
        pageviews: Number(d.pageviews || 0),
        eventos: Number(d.eventos || 0),
      }))
    : [];

  return {
    kpis: {
      totalVisitas: visitas,
      taxaConversaoFreemium: conv,
      tempoMedioUsoLabel: tempoLabel,
      taxaRetencao: retencao,
      tendencias: { visitas: 0, conversao: 0, tempo: 0, retencao: 0 },
    },
    evolucao,
    dispositivos: [
      { name: 'Desktop', value: Number(dev.desktop || 0), color: COLOR_PRIMARY },
      { name: 'Mobile', value: Number(dev.mobile || 0), color: COLOR_ACCENT },
      ...(Number(dev.desconhecido || 0) > 0
        ? [{ name: 'Desconhecido', value: Number(dev.desconhecido || 0), color: COLOR_NEUTRAL }]
        : []),
    ],
    funil: isInove
      ? [
          { etapa: 'Acesso / Mesa', valor: visitas, fill: COLOR_PRIMARY },
          { etapa: 'Criou desafio', valor: cliques, fill: COLOR_SECONDARY },
          { etapa: 'Elaborou plano', valor: uso, fill: COLOR_ACCENT },
          {
            etapa: 'Pagou / assinou',
            valor: pagamentos,
            fill: COLOR_NEUTRAL,
          },
        ]
      : [
          { etapa: 'Home', valor: visitas, fill: COLOR_PRIMARY },
          { etapa: 'Interesse (Clique)', valor: cliques, fill: COLOR_SECONDARY },
          { etapa: 'Uso Real', valor: uso, fill: COLOR_ACCENT },
        ],
    liveFeed,
  };
}

export default function CrmTrackingConversionPage() {
  const router = useRouter();
  const { hydrated, isAuthenticated, requireLogin } = useAuthGate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardViewModel | null>(null);
  const [origens, setOrigens] = useState<OrigemItem[]>([]);
  const [sistema, setSistema] = useState('inove4us');
  const [loadError, setLoadError] = useState('');
  const [showNovaOrigem, setShowNovaOrigem] = useState(false);
  const [novaSlug, setNovaSlug] = useState('');
  const [novaNome, setNovaNome] = useState('');
  const [novaDesc, setNovaDesc] = useState('');
  const [savingOrigem, setSavingOrigem] = useState(false);
  const [origemMsg, setOrigemMsg] = useState('');

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      requireLogin(
        '/dashboard/crm/tracking',
        'Faça login para acessar o Action-Sponge Analytics.'
      );
    }
  }, [hydrated, isAuthenticated, requireLogin]);

  const loadOrigens = useCallback(async () => {
    const res = await fetch('/api/crm/origens', { cache: 'no-store' });
    const json = await res.json().catch(() => ({}));
    if (!res.ok || !json?.ok) {
      throw new Error(json?.error || 'Falha ao listar origens');
    }
    const list: OrigemItem[] = Array.isArray(json.origens) ? json.origens : [];
    setOrigens(list);
    return list;
  }, []);

  const loadDashboard = useCallback(async (sistemaAtual: string) => {
    const res = await fetch(
      `/api/crm/dashboard/funil-freemium?sistema=${encodeURIComponent(sistemaAtual)}`,
      { cache: 'no-store' }
    );
    const json = await res.json().catch(() => ({}));
    if (!res.ok || json?.ok === false) {
      throw new Error(json?.error || 'Falha ao carregar analytics');
    }
    setData(mapApiToDashboard(json));
  }, []);

  useEffect(() => {
    if (!hydrated || !isAuthenticated) return;
    let cancelled = false;

    async function boot() {
      try {
        const list = await loadOrigens();
        if (cancelled || !list.length) return;
        if (!list.some((o) => o.slug === sistema)) {
          setSistema(list.find((o) => o.slug === 'inove4us')?.slug || list[0].slug);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : 'Erro ao listar origens');
        }
      }
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, [hydrated, isAuthenticated, loadOrigens, sistema]);

  useEffect(() => {
    if (!hydrated || !isAuthenticated || !sistema) return;
    let cancelled = false;
    async function reload() {
      setLoading(true);
      setLoadError('');
      try {
        await loadDashboard(sistema);
      } catch (err) {
        if (!cancelled) {
          setData(EMPTY_DASHBOARD);
          setLoadError(err instanceof Error ? err.message : 'Erro ao carregar');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void reload();
    return () => {
      cancelled = true;
    };
  }, [sistema, hydrated, isAuthenticated, loadDashboard]);

  async function handleCreateOrigem(e: FormEvent) {
    e.preventDefault();
    setSavingOrigem(true);
    setOrigemMsg('');
    try {
      const res = await fetch('/api/crm/origens', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slug: novaSlug,
          nome: novaNome || novaSlug,
          descricao: novaDesc,
        }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok || !json?.ok) {
        throw new Error(json?.error || 'Não foi possível cadastrar a origem');
      }
      const slug = String(json.origem?.slug || novaSlug).toLowerCase();
      await loadOrigens();
      setSistema(slug);
      setShowNovaOrigem(false);
      setNovaSlug('');
      setNovaNome('');
      setNovaDesc('');
      setOrigemMsg(`Origem “${json.origem?.nome || slug}” disponível para análise.`);
    } catch (err) {
      setOrigemMsg(err instanceof Error ? err.message : 'Erro ao cadastrar');
    } finally {
      setSavingOrigem(false);
    }
  }

  const funilComDropoff = useMemo(
    () => funilDropoffs(data?.funil ?? EMPTY_DASHBOARD.funil),
    [data]
  );

  const deviceTotal = useMemo(() => {
    const list = data?.dispositivos ?? EMPTY_DASHBOARD.dispositivos;
    return list.reduce((acc, d) => acc + d.value, 0) || 1;
  }, [data]);

  const origemAtual = origens.find((o) => o.slug === sistema);

  if (!hydrated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center bg-stone-50 text-stone-500">
        <Loader2 className="size-5 animate-spin" aria-hidden />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 bg-stone-50 px-4 text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-orange-50 text-orange-600 ring-1 ring-orange-200">
          <Lock className="size-7" aria-hidden />
        </span>
        <div>
          <h1 className="text-xl font-bold text-stone-900">Analytics protegido</h1>
          <p className="mt-1 max-w-md text-sm text-stone-500">
            O Action-Sponge Analytics só pode ser acessado com login no ActionHub.
          </p>
        </div>
        <button
          type="button"
          onClick={() =>
            requireLogin(
              '/dashboard/crm/tracking',
              'Faça login para acessar o Action-Sponge Analytics.'
            )
          }
          className="rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-600"
        >
          Ir para login
        </button>
        <button
          type="button"
          onClick={() => router.push('/')}
          className="text-sm font-medium text-stone-500 hover:text-stone-800"
        >
          Voltar à home
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-10">
        <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <Link
              href="/"
              className="mb-3 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition hover:text-orange-800"
            >
              <ArrowLeft className="size-4" aria-hidden />
              Voltar ao Action Hub
            </Link>
            <div className="min-w-0">
              <h1 className="text-2xl font-bold tracking-tight text-stone-900 md:text-3xl">
                Action-Sponge Analytics
              </h1>
              <p className="mt-1 text-sm text-stone-500">
                CRM · Funil PLG · Análise por origem
                {origemAtual ? ` · ${origemAtual.nome}` : ''}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Origem
              </span>
              <select
                value={sistema}
                onChange={(e) => setSistema(e.target.value)}
                className="min-w-[10rem] border-0 bg-transparent text-sm font-semibold text-slate-800 outline-none"
              >
                {origens.length === 0 ? (
                  <option value={sistema}>{sistema}</option>
                ) : (
                  origens.map((o) => (
                    <option key={o.slug} value={o.slug}>
                      {o.nome}
                      {typeof o.sessoes === 'number' ? ` (${o.sessoes})` : ''}
                    </option>
                  ))
                )}
              </select>
            </label>
            <button
              type="button"
              onClick={() => {
                setShowNovaOrigem((v) => !v);
                setOrigemMsg('');
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-3.5 py-2 text-sm font-semibold text-orange-800 transition hover:bg-orange-100"
            >
              <Plus className="size-4" aria-hidden />
              Nova origem
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm"
            >
              <CalendarDays className="size-4 text-slate-500" aria-hidden />
              Últimos 30 Dias
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm"
              title="Exportar (em breve)"
            >
              <Download className="size-4 text-slate-500" aria-hidden />
              Exportar
            </button>
          </div>
        </header>

        {showNovaOrigem ? (
          <form
            onSubmit={handleCreateOrigem}
            className="mb-6 rounded-xl border border-orange-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-base font-semibold text-slate-900">Cadastrar origem</h2>
            <p className="mt-1 text-xs text-slate-500">
              O slug vira o <code>sistema_origem</code> enviado pelos sensores S2S.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <label className="text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase text-slate-500">
                  Slug
                </span>
                <input
                  required
                  value={novaSlug}
                  onChange={(e) => setNovaSlug(e.target.value)}
                  placeholder="ex: inove4us"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase text-slate-500">
                  Nome
                </span>
                <input
                  required
                  value={novaNome}
                  onChange={(e) => setNovaNome(e.target.value)}
                  placeholder="ex: inove4us"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase text-slate-500">
                  Descrição
                </span>
                <input
                  value={novaDesc}
                  onChange={(e) => setNovaDesc(e.target.value)}
                  placeholder="opcional"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </label>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={savingOrigem}
                className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-60"
              >
                {savingOrigem ? 'Salvando…' : 'Salvar origem'}
              </button>
              <button
                type="button"
                onClick={() => setShowNovaOrigem(false)}
                className="text-sm font-medium text-slate-500 hover:text-slate-800"
              >
                Cancelar
              </button>
            </div>
          </form>
        ) : null}

        {origemMsg ? (
          <p className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {origemMsg}
          </p>
        ) : null}
        {loadError ? (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {loadError}
          </p>
        ) : null}

        <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {loading ? (
            <>
              <SkeletonKpi />
              <SkeletonKpi />
              <SkeletonKpi />
              <SkeletonKpi />
            </>
          ) : (
            <>
              <KpiCard
                icon={Users}
                label="Total de Visitas"
                value={formatNumber(data!.kpis.totalVisitas)}
                trend={data!.kpis.tendencias.visitas}
              />
              <KpiCard
                icon={Percent}
                label="Taxa de Conversão"
                value={`${data!.kpis.taxaConversaoFreemium}%`}
                trend={data!.kpis.tendencias.conversao}
                accent
              />
              <KpiCard
                icon={Clock3}
                label="Tempo Médio de Uso"
                value={data!.kpis.tempoMedioUsoLabel}
                trend={data!.kpis.tendencias.tempo}
              />
              <KpiCard
                icon={RotateCcw}
                label="Taxa de Retenção"
                value={`${data!.kpis.taxaRetencao}%`}
                trend={data!.kpis.tendencias.retencao}
              />
            </>
          )}
        </section>

        <section className="mb-6 grid gap-4 lg:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-slate-900">Evolução de Acessos</h2>
              <p className="text-xs text-slate-500">Pageviews e eventos · origem selecionada</p>
            </div>
            {loading ? (
              <SkeletonChart height={280} />
            ) : (
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={data!.evolucao}
                    margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis
                      dataKey="dia"
                      tick={{ fill: '#94a3b8', fontSize: 11 }}
                      axisLine={{ stroke: '#e2e8f0' }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: '#94a3b8', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      width={40}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 10,
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 4px 12px rgba(15,23,42,0.06)',
                        fontSize: 12,
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="pageviews"
                      name="Pageviews"
                      stroke={COLOR_PRIMARY}
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 5, fill: COLOR_SECONDARY }}
                    />
                    <Line
                      type="monotone"
                      dataKey="eventos"
                      name="Eventos"
                      stroke={COLOR_SECONDARY}
                      strokeWidth={1.75}
                      strokeOpacity={0.55}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-slate-900">Origem de Dispositivos</h2>
              <p className="text-xs text-slate-500">Desktop vs Mobile</p>
            </div>
            {loading ? (
              <SkeletonChart height={280} />
            ) : (
              <>
                <div className="mx-auto h-[200px] w-full max-w-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data!.dispositivos}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={58}
                        outerRadius={82}
                        paddingAngle={3}
                        strokeWidth={0}
                      >
                        {data!.dispositivos.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value) => {
                          const n = typeof value === 'number' ? value : Number(value) || 0;
                          return [
                            `${formatNumber(n)} (${Math.round((n / deviceTotal) * 100)}%)`,
                            'Sessões',
                          ];
                        }}
                        contentStyle={{
                          borderRadius: 10,
                          border: '1px solid #e2e8f0',
                          fontSize: 12,
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="mt-3 space-y-2">
                  {data!.dispositivos.map((d) => (
                    <li
                      key={d.name}
                      className="flex items-center justify-between text-sm text-slate-600"
                    >
                      <span className="inline-flex items-center gap-2">
                        <span
                          className="size-2.5 rounded-full"
                          style={{ backgroundColor: d.color }}
                          aria-hidden
                        />
                        {d.name}
                      </span>
                      <span className="font-semibold tabular-nums text-slate-900">
                        {Math.round((d.value / deviceTotal) * 100)}%
                        <span className="ml-1.5 font-normal text-slate-400">
                          ({formatNumber(d.value)})
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  Funil de Conversão (PLG)
                </h2>
                <p className="text-xs text-slate-500">Home → Interesse → Uso Real</p>
              </div>
              {!loading ? (
                <div className="flex flex-wrap gap-1.5">
                  {funilComDropoff.slice(1).map((step) => (
                    <span
                      key={step.etapa}
                      className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-semibold text-slate-600"
                    >
                      {step.etapa.split(' ')[0]}: {step.convPct}%
                      <span className="ml-1 font-medium text-slate-400">
                        (−{step.dropoffPct}%)
                      </span>
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
            {loading ? (
              <SkeletonChart height={240} />
            ) : (
              <div className="h-[240px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    layout="vertical"
                    data={funilComDropoff}
                    margin={{ top: 4, right: 48, left: 8, bottom: 4 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                    <XAxis type="number" hide />
                    <YAxis
                      type="category"
                      dataKey="etapa"
                      width={120}
                      tick={{ fill: '#475569', fontSize: 12, fontWeight: 500 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      formatter={(value, _name, item) => {
                        const n = typeof value === 'number' ? value : Number(value) || 0;
                        const payload = item?.payload as {
                          convPct?: number;
                          dropoffPct?: number;
                        };
                        const extra =
                          payload?.convPct != null && payload.convPct < 100
                            ? ` · conv ${payload.convPct}% (−${payload.dropoffPct}%)`
                            : '';
                        return [`${formatNumber(n)}${extra}`, 'Sessões'];
                      }}
                      contentStyle={{
                        borderRadius: 10,
                        border: '1px solid #e2e8f0',
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="valor" radius={[0, 8, 8, 0]} barSize={28}>
                      {funilComDropoff.map((entry) => (
                        <Cell key={entry.etapa} fill={entry.fill} />
                      ))}
                      <LabelList
                        dataKey="valor"
                        position="right"
                        formatter={(label) => {
                          const n =
                            typeof label === 'number' ? label : Number(label) || 0;
                          return formatNumber(n);
                        }}
                        style={{ fill: '#334155', fontSize: 12, fontWeight: 600 }}
                      />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Live Feed de Sessões</h2>
                <p className="text-xs text-slate-500">Sessões recentes da origem selecionada</p>
              </div>
            </div>

            {loading ? (
              <div className="space-y-3">
                <SkeletonFeedRow />
                <SkeletonFeedRow />
                <SkeletonFeedRow />
              </div>
            ) : data!.liveFeed.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                Nenhuma sessão registrada para esta origem ainda.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-[10px] uppercase tracking-wide text-slate-400">
                      <th className="px-1 py-2 font-semibold">Status</th>
                      <th className="px-1 py-2 font-semibold">Sessão</th>
                      <th className="px-1 py-2 font-semibold">Ferramenta</th>
                      <th className="px-1 py-2 font-semibold text-right">Eventos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data!.liveFeed.map((row) => (
                      <tr key={row.id} className="border-b border-slate-50 last:border-0">
                        <td className="px-1 py-3">
                          <span className="relative flex size-2.5">
                            <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-50" />
                            <span className="relative inline-flex size-2.5 rounded-full bg-emerald-500" />
                          </span>
                        </td>
                        <td className="px-1 py-3 font-mono text-xs text-slate-500">
                          {row.ipHash}
                        </td>
                        <td className="px-1 py-3">
                          <ToolBadge kind={row.ferramentaKey} label={row.ferramenta} />
                        </td>
                        <td className="px-1 py-3 text-right tabular-nums text-slate-700">
                          {row.tempoSessao}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function KpiCard({
  icon: Icon,
  label,
  value,
  trend,
  accent = false,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  trend: number;
  accent?: boolean;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {label}
        </span>
        <span
          className="flex size-8 items-center justify-center rounded-lg"
          style={{
            backgroundColor: accent ? 'rgba(249,115,22,0.12)' : 'rgba(127,29,29,0.08)',
            color: accent ? COLOR_ACCENT : COLOR_PRIMARY,
          }}
        >
          <Icon className="size-4" aria-hidden />
        </span>
      </div>
      <p className="text-3xl font-bold tracking-tight tabular-nums text-slate-900">{value}</p>
      {trend !== 0 ? (
        <p className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-600">
          <ArrowUpRight className="size-3.5" aria-hidden />
          +{trend}% vs mês anterior
        </p>
      ) : (
        <p className="mt-2 text-xs text-slate-400">Dados da origem selecionada</p>
      )}
    </div>
  );
}

function ToolBadge({
  kind,
  label,
}: {
  kind: LiveFeedItem['ferramentaKey'];
  label: string;
}) {
  const styles =
    kind === 'mesa'
      ? { bg: 'bg-red-50', text: 'text-red-800', border: 'border-red-100' }
      : kind === 'solucionador'
        ? { bg: 'bg-orange-50', text: 'text-orange-800', border: 'border-orange-100' }
        : { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200' };

  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${styles.bg} ${styles.text} ${styles.border}`}
    >
      {label}
    </span>
  );
}

function SkeletonKpi() {
  return (
    <div className="animate-pulse rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex justify-between">
        <div className="h-3 w-24 rounded bg-slate-100" />
        <div className="size-8 rounded-lg bg-slate-100" />
      </div>
      <div className="mb-3 h-8 w-28 rounded bg-slate-100" />
      <div className="h-3 w-32 rounded bg-slate-100" />
    </div>
  );
}

function SkeletonChart({ height }: { height: number }) {
  return (
    <div
      className="animate-pulse rounded-lg bg-gradient-to-br from-slate-100 to-slate-50"
      style={{ height }}
    />
  );
}

function SkeletonFeedRow() {
  return (
    <div className="flex animate-pulse items-center gap-3 border-b border-slate-50 py-3">
      <div className="size-2.5 rounded-full bg-slate-200" />
      <div className="h-3 w-24 rounded bg-slate-100" />
      <div className="h-5 w-28 rounded-full bg-slate-100" />
      <div className="ml-auto h-3 w-14 rounded bg-slate-100" />
    </div>
  );
}

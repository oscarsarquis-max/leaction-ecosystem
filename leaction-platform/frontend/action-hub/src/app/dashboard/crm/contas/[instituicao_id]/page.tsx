'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Lock } from 'lucide-react';
import { useAuthGate } from '@/lib/require-hub-login';
function formatSp(iso: string | null | undefined) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  } catch {
    return '—';
  }
}

type ContaListItem = {
  instituicao_id: string;
  instituicao_nome?: string | null;
  nome: string;
  sistemas: string[];
  primeiro_acesso: string | null;
  ultimo_acesso: string | null;
  ultimo_login: string | null;
  sessoes_7d: number;
  sessoes_30d: number;
  usuarios_30d: number;
  tem_contrato: boolean;
  contrato_status: string | null;
  plano: string | null;
};

type SnapshotEstado = {
  data_ref: string | null;
  criado_em: string | null;
  dados: Record<string, unknown>;
};

type SnapshotProfessor = SnapshotEstado & {
  id_clie: string | null;
};

type TipoCount = { tipo_evento: string; count: number };

type UsuarioFicha = {
  usuario_origem_ref: string;
  usuario_nome?: string | null;
  sistema_origem: string | null;
  primeiro_acesso: string | null;
  ultimo_acesso: string | null;
  sessoes_30d: number;
  eventos_por_tipo_30d: TipoCount[];
};

type ContaFicha = ContaListItem & {
  eventos_30d: number;
  eventos_por_tipo_30d: TipoCount[];
  assentos: string | null;
  snapshot_school: SnapshotEstado | null;
  snapshot_inove: SnapshotEstado | null;
  snapshots_professores: SnapshotProfessor[];
  contratos: Array<{
    id: string;
    app_id: string;
    status: string;
    created_at: string | null;
    itens: Array<{ sku: string; tipo: string; quantidade: number }>;
  }>;
  entitlement: {
    app_id: string | null;
    seats: number | null;
    creditos: number | null;
    plano: string | null;
    valid_until: string | null;
    updated_at: string | null;
  } | null;
  usuarios: UsuarioFicha[];
  creditos_consumidos_30d: number;
  ultimas_sessoes: Array<{
    id_sessao: string;
    sistema_origem: string;
    usuario_origem_ref: string | null;
    usuario_nome?: string | null;
    inicio: string | null;
    ultimo_evento: string | null;
    n_eventos: number;
  }>;
  uso_30d?: {
    totais: {
      eventos: number;
      pessoas: number;
      sessoes: number;
      tempo_s: number;
    };
    funcionalidades: Array<{
      chave: string;
      rotulo: string;
      sistema: string | null;
      eventos: number;
      pct_eventos: number;
      pessoas: number;
      pct_pessoas: number;
      sessoes: number;
      pct_sessoes: number;
      tempo_s: number;
      pct_tempo: number;
      tempo_medio_por_sessao_s: number;
    }>;
  } | null;
};

const INOVE_COLS = [
  'aula_criar',
  'aula_fechar',
  'desafio_criar',
  'pei_aplicar',
  'wizard_gerar',
  'credito_consumir',
] as const;

const SCHOOL_COLS = [
  'turma_criar',
  'aluno_matricular',
  'professor_convidar',
  'alocacao_criar',
  'pei_criar',
  'comunicado_publicar',
] as const;

function countOf(u: UsuarioFicha, tipo: string) {
  const hit = (u.eventos_por_tipo_30d || []).find((e) => e.tipo_evento === tipo);
  return hit ? hit.count : 0;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function num(value: unknown): string {
  if (value == null || value === '') return '—';
  return String(value);
}

function formatTempoCurto(seconds: number): string {
  const n = Number(seconds) || 0;
  if (n <= 0) return '0s';
  if (n < 60) return `${n < 10 ? n.toFixed(1) : Math.round(n)}s`;
  const m = Math.floor(n / 60);
  const sec = Math.round(n % 60);
  if (m < 60) return sec ? `${m} min ${sec}s` : `${m} min`;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return mm ? `${h} h ${mm} min` : `${h} h`;
}

function MiniBars({
  items,
  valueOf,
  formatValue,
}: {
  items: NonNullable<ContaFicha['uso_30d']>['funcionalidades'];
  valueOf: (f: NonNullable<ContaFicha['uso_30d']>['funcionalidades'][number]) => number;
  formatValue: (f: NonNullable<ContaFicha['uso_30d']>['funcionalidades'][number]) => string;
}) {
  const max = Math.max(1, ...items.map((i) => valueOf(i)));
  return (
    <ul className="space-y-1.5">
      {items.length === 0 ? (
        <li className="text-sm text-slate-400">sem uso mapeado</li>
      ) : (
        items.map((item) => (
          <li key={`${item.chave}|${item.sistema || ''}`}>
            <div className="mb-0.5 flex items-baseline justify-between gap-2 text-sm">
              <span className="truncate text-stone-800">{item.rotulo}</span>
              <span className="shrink-0 tabular-nums text-stone-600">{formatValue(item)}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-stone-100">
              <div
                className="h-full rounded-full bg-emerald-500"
                style={{ width: `${Math.max(0, Math.min(100, (valueOf(item) / max) * 100))}%` }}
              />
            </div>
          </li>
        ))
      )}
    </ul>
  );
}

function SnapshotBlock({
  titulo,
  snap,
}: {
  titulo: string;
  snap: SnapshotEstado | null;
}) {
  if (!snap) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-stone-800">{titulo}</h3>
        <p className="mt-1 text-sm text-slate-500">sem snapshot ainda</p>
      </div>
    );
  }
  const d = asRecord(snap.dados);
  const gestores = asRecord(d.gestores);
  const vinculo = asRecord(d.professores_vinculo);
  const lic = asRecord(d.licencas);
  const aee = asRecord(d.aee);
  const pei = asRecord(d.pei);
  const ponte = asRecord(d.ponte_b2c);
  const creditos = asRecord(d.creditos);
  const isSchool = String(d.sistema || '') === 'inove4us-school';
  return (
    <div>
      <h3 className="text-sm font-semibold text-stone-800">{titulo}</h3>
      <p className="mt-1 text-xs text-slate-400">
        Referência {snap.data_ref || '—'} · recebido {formatSp(snap.criado_em)}
      </p>
      {isSchool ? (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-slate-400">Gestores cadastrados / ativos</dt>
            <dd>
              {num(gestores.cadastrados)} / {num(gestores.ativos)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Turmas / alunos</dt>
            <dd>
              {num(d.turmas)} / {num(d.alunos)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Vínculos professor pendente / ativo</dt>
            <dd>
              {num(vinculo.pendente)} / {num(vinculo.ativo)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Alocações ativas</dt>
            <dd>{num(d.alocacoes_ativas)}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Assentos em uso / total</dt>
            <dd>
              {num(lic.em_uso)} / {num(lic.total_assentos)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">SKU / contrato Hub</dt>
            <dd className="font-mono text-xs">
              {num(lic.sku_ultimo)} · {num(lic.contrato_hub_id)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">AEE condições ativas</dt>
            <dd>
              {num(aee.condicoes_ativas)}
              {aee.ultima_atualizacao ? ` · ${formatSp(String(aee.ultima_atualizacao))}` : ''}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">PEI ativos / assinatura dupla</dt>
            <dd>
              {num(pei.ativos)} / {num(pei.assinatura_dupla_completa)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Comunicados</dt>
            <dd>{num(d.comunicados_total)}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Ponte B2C pendente / backfill</dt>
            <dd>
              {num(ponte.notificacoes_pendentes)} / {num(d.backfill_pendente)}
            </dd>
          </div>
        </dl>
      ) : (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-slate-400">Professores vinculados</dt>
            <dd>{num(d.professores_vinculados)}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Créditos saldo / concedidos institucional</dt>
            <dd>
              {num(creditos.saldo_total)} / {num(creditos.concedidos_institucional_total)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">Aulas / desafios</dt>
            <dd>
              {num(d.aulas_total)} / {num(d.desafios_total)}
            </dd>
          </div>
        </dl>
      )}
    </div>
  );
}

export default function CrmContaFichaPage() {
  const params = useParams<{ instituicao_id: string }>();
  const router = useRouter();
  const id = String(params?.instituicao_id || '').trim();
  const { hydrated, isAuthenticated, requireLogin } = useAuthGate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [conta, setConta] = useState<ContaFicha | null>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      requireLogin(
        `/dashboard/crm/contas/${id}`,
        'Faça login para acessar as contas do Sponge.'
      );
    }
  }, [hydrated, isAuthenticated, requireLogin, id]);

  useEffect(() => {
    if (!hydrated || !isAuthenticated || !id) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    fetch(`/api/crm/contas/${encodeURIComponent(id)}`, { cache: 'no-store' })
      .then(async (res) => {
        const json = await res.json().catch(() => ({}));
        if (!res.ok || !json?.ok) {
          throw new Error(json?.error || `HTTP ${res.status}`);
        }
        if (!cancelled) setConta(json.conta as ContaFicha);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Falha ao carregar ficha');
          setConta(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hydrated, isAuthenticated, id]);

  const showInove = useMemo(
    () =>
      (conta?.sistemas || []).includes('inove4us') ||
      (conta?.usuarios || []).some((u) => u.sistema_origem === 'inove4us'),
    [conta]
  );
  const showSchool = useMemo(
    () =>
      (conta?.sistemas || []).includes('inove4us-school') ||
      (conta?.usuarios || []).some((u) => u.sistema_origem === 'inove4us-school'),
    [conta]
  );

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
        <Lock className="size-8 text-emerald-600" aria-hidden />
        <p className="text-sm text-stone-500">Login necessário.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-10">
        <Link
          href="/dashboard/crm/contas"
          className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-emerald-800"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Todas as contas
        </Link>

        {loading ? (
          <div className="flex justify-center py-16 text-slate-400">
            <Loader2 className="size-6 animate-spin" aria-hidden />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {error}
            <button
              type="button"
              className="ml-3 underline"
              onClick={() => router.push('/dashboard/crm/contas')}
            >
              Voltar
            </button>
          </div>
        ) : conta ? (
          <>
            <header className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h1 className="text-2xl font-bold text-stone-900" title={conta.instituicao_id}>
                    {conta.nome || conta.instituicao_nome || conta.instituicao_id}
                  </h1>
                  <p className="mt-1 font-mono text-xs text-slate-400">{conta.instituicao_id}</p>
                  <p className="mt-2 text-sm text-slate-600">
                    {(conta.sistemas || []).join(' · ') || 'sem sessões'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`/dashboard/crm/contas/${encodeURIComponent(conta.instituicao_id)}/atividade`}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Atividade
                  </Link>
                  <Link
                    href={`/dashboard/crm/tracking?instituicao_id=${encodeURIComponent(conta.instituicao_id)}`}
                    className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm font-semibold text-emerald-800 hover:bg-emerald-100"
                  >
                    Ver no funil
                  </Link>
                </div>
              </div>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Contrato</dt>
                  <dd className="font-semibold">
                    {conta.tem_contrato ? conta.contrato_status || 'sim' : 'sem contrato'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Plano</dt>
                  <dd className="font-mono text-xs">{conta.plano || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Entitlement</dt>
                  <dd>
                    {conta.entitlement
                      ? `seats ${conta.entitlement.seats ?? '—'} · créditos ${conta.entitlement.creditos ?? '—'} · ${conta.entitlement.plano || '—'}`
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Válido até</dt>
                  <dd>{formatSp(conta.entitlement?.valid_until)}</dd>
                </div>
              </dl>
            </header>

            <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Acesso
              </h2>
              <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <dt className="text-xs text-slate-400">Primeiro acesso</dt>
                  <dd>{formatSp(conta.primeiro_acesso)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Último acesso</dt>
                  <dd>{formatSp(conta.ultimo_acesso)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Último login</dt>
                  <dd>{formatSp(conta.ultimo_login)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Sessões 7d / 30d</dt>
                  <dd>
                    {conta.sessoes_7d} / {conta.sessoes_30d}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Usuários 30d</dt>
                  <dd>{conta.usuarios_30d}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Créditos consumidos 30d</dt>
                  <dd>{conta.creditos_consumidos_30d}</dd>
                </div>
              </dl>
            </section>

            <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                  Uso (30 dias)
                </h2>
                <Link
                  href="/dashboard/crm/uso"
                  className="text-xs font-medium text-emerald-700 hover:underline"
                >
                  Ver uso completo
                </Link>
              </div>
              <p className="mb-4 text-xs text-slate-400">
                Tempo estimado por intervalo entre ações; ausência de ação &gt; 10 min não conta.
              </p>
              {conta.uso_30d ? (
                <div className="grid gap-6 md:grid-cols-2">
                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-stone-800">Por tempo</h3>
                    <MiniBars
                      items={conta.uso_30d.funcionalidades}
                      valueOf={(f) => f.tempo_s}
                      formatValue={(f) => `${formatTempoCurto(f.tempo_s)} (${f.pct_tempo}%)`}
                    />
                  </div>
                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-stone-800">Por pessoas</h3>
                    <MiniBars
                      items={[...conta.uso_30d.funcionalidades].sort(
                        (a, b) => b.pessoas - a.pessoas || b.eventos - a.eventos
                      )}
                      valueOf={(f) => f.pessoas}
                      formatValue={(f) => `${f.pessoas} (${f.pct_pessoas}%)`}
                    />
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-400">sem dados de uso</p>
              )}
            </section>

            <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-slate-500">
                Estado (snapshot)
              </h2>
              <div className="grid gap-6 lg:grid-cols-2">
                <SnapshotBlock titulo="School" snap={conta.snapshot_school} />
                <SnapshotBlock titulo="Inove" snap={conta.snapshot_inove} />
              </div>
              {(conta.snapshots_professores || []).length ? (
                <div className="mt-6 overflow-x-auto">
                  <h3 className="mb-2 text-sm font-semibold text-stone-800">Professores (Inove)</h3>
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                      <tr>
                        <th className="px-3 py-2">id</th>
                        <th className="px-3 py-2">Plano</th>
                        <th className="px-3 py-2">Créditos</th>
                        <th className="px-3 py-2">Aulas</th>
                        <th className="px-3 py-2">Desafios</th>
                        <th className="px-3 py-2">Vínculo</th>
                        <th className="px-3 py-2">Ref.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {conta.snapshots_professores.map((p) => {
                        const d = asRecord(p.dados);
                        return (
                          <tr
                            key={`${p.id_clie || 'p'}-${p.criado_em || p.data_ref || ''}`}
                            className="border-t border-slate-100"
                          >
                            <td className="px-3 py-2 font-mono text-xs">{p.id_clie || '—'}</td>
                            <td className="px-3 py-2">{num(d.plan_tier)}</td>
                            <td className="px-3 py-2">{num(d.creditos_saldo)}</td>
                            <td className="px-3 py-2">{num(d.aulas_total)}</td>
                            <td className="px-3 py-2">{num(d.desafios_total)}</td>
                            <td className="px-3 py-2">
                              {d.vinculo_ativo === true
                                ? 'ativo'
                                : d.vinculo_ativo === false
                                  ? 'inativo'
                                  : '—'}
                            </td>
                            <td className="px-3 py-2 whitespace-nowrap">{p.data_ref || '—'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </section>

            <section className="mb-6 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
              <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Usuários (30d)
              </h2>
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Usuário</th>
                    <th className="px-3 py-2">Sistema</th>
                    <th className="px-3 py-2">Último acesso</th>
                    {(showInove ? INOVE_COLS : []).map((c) => (
                      <th key={c} className="px-2 py-2 font-mono">
                        {c}
                      </th>
                    ))}
                    {(showSchool ? SCHOOL_COLS : []).map((c) => (
                      <th key={c} className="px-2 py-2 font-mono">
                        {c}
                      </th>
                    ))}
                    {!showInove && !showSchool
                      ? INOVE_COLS.concat(SCHOOL_COLS as unknown as typeof INOVE_COLS).map((c) => (
                          <th key={c} className="px-2 py-2 font-mono">
                            {c}
                          </th>
                        ))
                      : null}
                  </tr>
                </thead>
                <tbody>
                  {(conta.usuarios || []).length === 0 ? (
                    <tr>
                      <td colSpan={20} className="px-3 py-6 text-center text-slate-400">
                        Nenhum usuário identificado.
                      </td>
                    </tr>
                  ) : (
                    conta.usuarios.map((u) => {
                      const cols =
                        showInove || showSchool
                          ? [...(showInove ? INOVE_COLS : []), ...(showSchool ? SCHOOL_COLS : [])]
                          : [...INOVE_COLS, ...SCHOOL_COLS];
                      return (
                        <tr key={u.usuario_origem_ref} className="border-t border-slate-100">
                          <td className="px-3 py-2 text-sm" title={u.usuario_origem_ref}>
                            {u.usuario_nome || u.usuario_origem_ref}
                          </td>
                          <td className="px-3 py-2 text-xs">{u.sistema_origem || '—'}</td>
                          <td className="px-3 py-2 whitespace-nowrap">{formatSp(u.ultimo_acesso)}</td>
                          {cols.map((c) => (
                            <td key={c} className="px-2 py-2 text-center">
                              {countOf(u, c)}
                            </td>
                          ))}
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </section>

            <section className="mb-6 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
              <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Eventos por tipo (30d) · {conta.eventos_30d} no total
              </h2>
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Tipo</th>
                    <th className="px-3 py-2">Qtd</th>
                  </tr>
                </thead>
                <tbody>
                  {(conta.eventos_por_tipo_30d || []).length === 0 ? (
                    <tr>
                      <td colSpan={2} className="px-3 py-6 text-center text-slate-400">
                        Sem eventos na janela.
                      </td>
                    </tr>
                  ) : (
                    conta.eventos_por_tipo_30d.map((e) => (
                      <tr key={e.tipo_evento} className="border-t border-slate-100">
                        <td className="px-3 py-2 font-mono text-xs">{e.tipo_evento}</td>
                        <td className="px-3 py-2">{e.count}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </section>

            {(conta.contratos || []).length ? (
              <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                  Contratos
                </h2>
                <ul className="space-y-3 text-sm">
                  {conta.contratos.map((c) => (
                    <li key={c.id} className="rounded-lg border border-slate-100 p-3">
                      <div className="font-mono text-xs text-slate-400">{c.id}</div>
                      <div>
                        {c.app_id} · {c.status} · {formatSp(c.created_at)}
                      </div>
                      <ul className="mt-1 text-xs text-slate-600">
                        {(c.itens || []).map((it, i) => (
                          <li key={`${it.sku}-${i}`}>
                            {it.tipo} · {it.sku} × {it.quantidade}
                          </li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
              <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Últimas sessões
              </h2>
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Sessão</th>
                    <th className="px-3 py-2">Sistema</th>
                    <th className="px-3 py-2">Usuário</th>
                    <th className="px-3 py-2">Início</th>
                    <th className="px-3 py-2">Último evento</th>
                    <th className="px-3 py-2">Eventos</th>
                  </tr>
                </thead>
                <tbody>
                  {(conta.ultimas_sessoes || []).map((s) => (
                    <tr key={s.id_sessao} className="border-t border-slate-100">
                      <td className="px-3 py-2 font-mono text-[11px]">{s.id_sessao}</td>
                      <td className="px-3 py-2 text-xs">{s.sistema_origem}</td>
                      <td className="px-3 py-2 text-sm" title={s.usuario_origem_ref || undefined}>
                        {s.usuario_nome || s.usuario_origem_ref || '—'}
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">{formatSp(s.inicio)}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{formatSp(s.ultimo_evento)}</td>
                      <td className="px-3 py-2">{s.n_eventos}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        ) : null}
      </div>
    </div>
  );
}

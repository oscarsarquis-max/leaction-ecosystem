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

type TipoCount = { tipo_evento: string; count: number };

type UsuarioFicha = {
  usuario_origem_ref: string;
  sistema_origem: string | null;
  primeiro_acesso: string | null;
  ultimo_acesso: string | null;
  sessoes_30d: number;
  eventos_por_tipo_30d: TipoCount[];
};

type ContaFicha = ContaListItem & {
  eventos_30d: number;
  eventos_por_tipo_30d: TipoCount[];
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
    inicio: string | null;
    ultimo_evento: string | null;
    n_eventos: number;
  }>;
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
                  <h1 className="text-2xl font-bold text-stone-900">{conta.nome}</h1>
                  <p className="mt-1 font-mono text-xs text-slate-400">{conta.instituicao_id}</p>
                  <p className="mt-2 text-sm text-slate-600">
                    {(conta.sistemas || []).join(' · ') || 'sem sessões'}
                  </p>
                </div>
                <Link
                  href={`/dashboard/crm/tracking?instituicao_id=${encodeURIComponent(conta.instituicao_id)}`}
                  className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm font-semibold text-emerald-800 hover:bg-emerald-100"
                >
                  Ver no funil
                </Link>
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
                          <td className="px-3 py-2 font-mono text-xs">{u.usuario_origem_ref}</td>
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
                      <td className="px-3 py-2 font-mono text-xs">{s.usuario_origem_ref || '—'}</td>
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

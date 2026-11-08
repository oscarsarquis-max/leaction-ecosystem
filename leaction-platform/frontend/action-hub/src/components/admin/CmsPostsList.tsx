'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { Bot, FilePlus2, LayoutTemplate, Loader2, Newspaper, RefreshCw } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import { fetchCmsPostsAdmin, type CmsPost } from '@/lib/admin-api';

function StatusBadge({ status }: { status: string }) {
  const published = status === 'publicado';
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${
        published
          ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
          : 'bg-amber-50 text-amber-800 ring-1 ring-amber-200'
      }`}
    >
      {published ? 'Publicado' : 'Rascunho'}
    </span>
  );
}

function DestinoBadge({ destino }: { destino: string }) {
  return (
    <span className="inline-flex rounded-lg bg-stone-100 px-2 py-0.5 text-xs font-semibold text-stone-700 ring-1 ring-stone-200">
      {destino === 'lepain' ? 'LePain' : destino}
    </span>
  );
}

function lepainLigado(post: CmsPost, posts: CmsPost[]) {
  if (post.idioma === 'pt') {
    return posts.some((other) => other.idioma === 'en' && other.grupo_id === post.id);
  }
  if (post.idioma === 'en' && post.grupo_id) {
    return posts.some((other) => other.idioma === 'pt' && other.id === post.grupo_id);
  }
  return false;
}

export function CmsPostsList() {
  const { token } = useHubSession();
  const [posts, setPosts] = useState<CmsPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchCmsPostsAdmin(token);
      setPosts(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao carregar posts');
      setPosts([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <Newspaper className="size-5 text-emerald-500" aria-hidden />
            <h1 className="text-xl font-bold text-stone-900">
              Gestão de Conteúdo (CMS)
            </h1>
          </div>
          <p className="max-w-xl text-sm text-stone-500">
            Posts headless + Micro-CMS (estrutura PanelDX) no Hub. O CMS do
            PanelDX permanece ativo até cutover autorizado.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50"
          >
            <RefreshCw className="size-4" aria-hidden />
            Atualizar
          </button>
          <Link
            href="/dashboard/cms/assistente"
            className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50"
          >
            <Bot className="size-4" aria-hidden />
            Assistente Nina
          </Link>
          <Link
            href="/dashboard/cms/site"
            className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50"
          >
            <LayoutTemplate className="size-4" aria-hidden />
            Micro-CMS (site)
          </Link>
          <Link
            href="/dashboard/cms/novo"
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-400"
          >
            <FilePlus2 className="size-4" aria-hidden />
            Novo Post
          </Link>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-2xl border border-stone-200 bg-stone-50">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-white text-[11px] font-bold uppercase tracking-wider text-stone-500">
              <tr>
                <th className="px-4 py-3">Título</th>
                <th className="px-4 py-3">Slug</th>
                <th className="px-4 py-3">Destino</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Publicado em</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-stone-500">
                    <Loader2 className="mx-auto size-5 animate-spin" aria-hidden />
                  </td>
                </tr>
              ) : posts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-stone-500">
                    Nenhum post ainda. Clique em <strong>Novo Post</strong> para
                    começar.
                  </td>
                </tr>
              ) : (
                posts.map((p) => (
                  <tr key={p.id} className="hover:bg-stone-50/80">
                    <td className="px-4 py-3 font-semibold text-stone-900">
                      {p.titulo}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-stone-500">
                      {p.slug}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <DestinoBadge destino={p.sistema_destino} />
                        {p.sistema_destino === 'lepain' ? (
                          <>
                            <span className="inline-flex rounded-lg bg-stone-100 px-2 py-0.5 text-[11px] font-bold text-stone-700 ring-1 ring-stone-200">
                              {(p.idioma || '').toUpperCase() || '—'}
                            </span>
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-bold ring-1 ${
                                lepainLigado(p, posts)
                                  ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
                                  : 'bg-amber-50 text-amber-800 ring-amber-200'
                              }`}
                            >
                              {lepainLigado(p, posts) ? 'PT ↔ EN' : 'sem EN'}
                            </span>
                            {p.idioma === 'pt' && !lepainLigado(p, posts) ? (
                              <Link
                                href={`/dashboard/cms/novo?grupo_id=${p.id}&secao=${encodeURIComponent(p.secao || 'insights')}`}
                                className="text-xs font-semibold text-emerald-700 underline-offset-2 hover:underline"
                              >
                                Criar versão EN
                              </Link>
                            ) : null}
                          </>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={p.status} />
                    </td>
                    <td className="px-4 py-3 text-stone-500">
                      {p.publicado_em
                        ? new Date(p.publicado_em).toLocaleString('pt-BR')
                        : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

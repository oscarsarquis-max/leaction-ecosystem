'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Bot, FilePlus2, LayoutTemplate, Loader2, MoreHorizontal, Newspaper, RefreshCw } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  deleteCmsPost,
  fetchCmsPostsAdmin,
  updateCmsPost,
  type CmsPost,
  type CmsPostUpsertBody,
} from '@/lib/admin-api';

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

function blogPostUrl(post: CmsPost) {
  const lang = post.idioma === 'en' ? 'en' : 'pt';
  const section = post.secao === 'right_now' ? 'right-now' : 'insights';
  return `https://lepain.lojadepaes.com.br/${lang}/${section}/${post.slug}`;
}

function upsertBody(post: CmsPost, status: string): CmsPostUpsertBody {
  const body: CmsPostUpsertBody = {
    titulo: post.titulo,
    slug: post.slug,
    resumo: post.resumo || '',
    conteudo_html: post.conteudo_html || '',
    imagem_capa: post.imagem_capa,
    sistema_destino: post.sistema_destino,
    status,
  };
  if (post.sistema_destino !== 'lepain') return body;
  return {
    ...body,
    secao: post.secao,
    idioma: post.idioma,
    grupo_id: post.grupo_id ?? null,
    sentidos: post.sentidos || [],
    resumo_instagram: post.resumo_instagram,
    right_now_tipo: post.right_now_tipo,
    data_evento: post.data_evento,
    valido_ate: post.valido_ate,
  };
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
  const [pendingDelete, setPendingDelete] = useState<CmsPost | null>(null);
  const [deleting, setDeleting] = useState(false);

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

  async function changeStatus(post: CmsPost) {
    if (!token) return;
    const next = post.status === 'publicado' ? 'rascunho' : 'publicado';
    setError(null);
    try {
      await updateCmsPost(token, post.id, upsertBody(post, next));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao atualizar o status');
    }
  }

  async function confirmDelete() {
    if (!token || !pendingDelete) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteCmsPost(token, pendingDelete.id);
      setPendingDelete(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao excluir');
    } finally {
      setDeleting(false);
    }
  }

  const deletePair = Boolean(
    pendingDelete &&
      pendingDelete.sistema_destino === 'lepain' &&
      pendingDelete.idioma === 'pt' &&
      lepainLigado(pendingDelete, posts)
  );

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
                <th className="px-4 py-3"><span className="sr-only">Ações</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-stone-500">
                    <Loader2 className="mx-auto size-5 animate-spin" aria-hidden />
                  </td>
                </tr>
              ) : posts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-stone-500">
                    Nenhum post ainda. Clique em <strong>Novo Post</strong> para
                    começar.
                  </td>
                </tr>
              ) : (
                posts.map((p) => (
                  <tr key={p.id} className="hover:bg-stone-50/80">
                    <td className="relative px-4 py-3 font-semibold text-stone-900">
                      <Link
                        href={`/dashboard/cms/${p.id}`}
                        className="absolute inset-0"
                        aria-label={`Editar ${p.titulo}`}
                      />
                      {p.titulo}
                    </td>
                    <td className="relative px-4 py-3 font-mono text-xs text-stone-500">
                      <Link
                        href={`/dashboard/cms/${p.id}`}
                        className="absolute inset-0"
                        tabIndex={-1}
                        aria-hidden="true"
                      />
                      {p.slug}
                    </td>
                    <td className="relative px-4 py-3">
                      <Link
                        href={`/dashboard/cms/${p.id}`}
                        className="absolute inset-0"
                        tabIndex={-1}
                        aria-hidden="true"
                      />
                      <div className="relative z-10 flex flex-wrap items-center gap-1.5 pointer-events-none">
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
                                className="pointer-events-auto text-xs font-semibold text-emerald-700 underline-offset-2 hover:underline"
                              >
                                Criar versão EN
                              </Link>
                            ) : null}
                          </>
                        ) : null}
                      </div>
                    </td>
                    <td className="relative px-4 py-3">
                      <Link
                        href={`/dashboard/cms/${p.id}`}
                        className="absolute inset-0"
                        tabIndex={-1}
                        aria-hidden="true"
                      />
                      <StatusBadge status={p.status} />
                    </td>
                    <td className="relative px-4 py-3 text-stone-500">
                      <Link
                        href={`/dashboard/cms/${p.id}`}
                        className="absolute inset-0"
                        tabIndex={-1}
                        aria-hidden="true"
                      />
                      {p.publicado_em
                        ? new Date(p.publicado_em).toLocaleString('pt-BR')
                        : '—'}
                    </td>
                    <td className="relative z-10 px-4 py-3">
                      <RowMenu
                        post={p}
                        onStatus={() => void changeStatus(p)}
                        onDelete={() => setPendingDelete(p)}
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      {pendingDelete ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 px-4"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="delete-title"
        >
          <div className="w-full max-w-md space-y-4 rounded-2xl bg-white p-5 shadow-xl">
            <h2 id="delete-title" className="text-lg font-bold text-stone-900">
              Excluir “{pendingDelete.titulo}”?
            </h2>
            {deletePair ? (
              <p className="text-sm text-stone-600">
                Este texto tem versão em inglês. As duas versões serão apagadas.
              </p>
            ) : (
              <p className="text-sm text-stone-600">Esta exclusão não pode ser desfeita.</p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPendingDelete(null)}
                className="rounded-xl border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void confirmDelete()}
                disabled={deleting}
                className="rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
              >
                {deletePair ? 'Excluir as duas versões' : 'Excluir'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function RowMenu({
  post,
  onStatus,
  onDelete,
}: {
  post: CmsPost;
  onStatus: () => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number } | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const published = post.status === 'publicado';

  useEffect(() => {
    if (!open) return;
    function onDoc(event: MouseEvent) {
      if (!box.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={box}>
      <button
        type="button"
        className="inline-flex items-center justify-center rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 hover:text-emerald-800"
        aria-label={`Ações de ${post.titulo}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          setMenuPos({ top: rect.bottom + 4, left: rect.right });
          setOpen((value) => !value);
        }}
      >
        <MoreHorizontal className="size-5" aria-hidden />
      </button>
      {open ? (
        <div
          role="menu"
          className="fixed z-50 w-48 -translate-x-full rounded-xl border border-stone-200 bg-white py-1 shadow-lg"
          style={menuPos ? { top: menuPos.top, left: menuPos.left } : undefined}
        >
          <Link
            role="menuitem"
            href={`/dashboard/cms/${post.id}`}
            className="block px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50"
            onClick={() => setOpen(false)}
          >
            Editar
          </Link>
          <button
            type="button"
            role="menuitem"
            className="block w-full px-3 py-2 text-left text-sm font-semibold text-stone-700 hover:bg-stone-50"
            onClick={() => {
              setOpen(false);
              onStatus();
            }}
          >
            {published ? 'Despublicar' : 'Publicar'}
          </button>
          {post.sistema_destino === 'lepain' && published ? (
            <a
              role="menuitem"
              href={blogPostUrl(post)}
              target="_blank"
              rel="noopener noreferrer"
              className="block px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50"
              onClick={() => setOpen(false)}
            >
              Ver no blog
            </a>
          ) : null}
          <button
            type="button"
            role="menuitem"
            className="block w-full px-3 py-2 text-left text-sm font-semibold text-red-700 hover:bg-red-50"
            onClick={() => {
              setOpen(false);
              onDelete();
            }}
          >
            Excluir
          </button>
        </div>
      ) : null}
    </div>
  );
}

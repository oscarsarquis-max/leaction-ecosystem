'use client';

import { useEffect, useState } from 'react';
import { Bell, LogOut, X } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import { getHubApiBase } from '@/lib/hub-api';
import type { CmsPost } from '@/lib/admin-api';

type LoggedAreaRightPanelProps = {
  userName: string;
  userEmail?: string | null;
};

export function LoggedAreaRightPanel({ userName, userEmail }: LoggedAreaRightPanelProps) {
  const { logout } = useHubSession();
  const [posts, setPosts] = useState<CmsPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState<CmsPost | null>(null);

  const initials = userName
    .split(/\s+|@/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || '')
    .join('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const base = getHubApiBase();
        const res = await fetch(
          `${base}/api/cms/posts?sistema_destino=actionhub&limit=4`,
          { headers: { Accept: 'application/json' }, cache: 'no-store' }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { posts?: CmsPost[] };
        if (!cancelled) {
          setPosts(Array.isArray(data?.posts) ? data.posts.slice(0, 4) : []);
        }
      } catch {
        if (!cancelled) setPosts([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!active) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setActive(null);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active]);

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col gap-6 overflow-y-auto border-l border-stone-200 bg-white p-6">
      <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-full bg-orange-50 text-sm font-bold text-orange-600 ring-1 ring-orange-100">
            {initials || '?'}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-stone-900">{userName}</p>
            {userEmail ? (
              <p className="truncate text-xs text-stone-500">{userEmail}</p>
            ) : null}
          </div>
          <button
            type="button"
            className="inline-flex size-9 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-50 hover:text-stone-800"
            aria-label="Notificações"
            title="Notificações"
          >
            <Bell className="size-4" aria-hidden />
          </button>
        </div>
        <button
          type="button"
          onClick={() => logout()}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-stone-200 px-3 py-2 text-xs font-semibold text-stone-500 transition hover:bg-stone-50 hover:text-stone-800"
        >
          <LogOut className="size-3.5" aria-hidden />
          Sair
        </button>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-bold text-stone-900">Insights</h2>
        {loading ? (
          <p className="text-xs text-stone-400">Carregando…</p>
        ) : posts.length === 0 ? (
          <p className="rounded-xl border border-dashed border-stone-200 bg-stone-50 px-3 py-6 text-center text-xs text-stone-400">
            Conteúdos do ActionHub aparecerão aqui.
          </p>
        ) : (
          <ul className="space-y-2">
            {posts.map((post) => {
              const short =
                (post.resumo && post.resumo.trim()) ||
                post.titulo ||
                'Abrir conteúdo';
              return (
                <li key={post.id}>
                  <button
                    type="button"
                    onClick={() => setActive(post)}
                    className="w-full rounded-xl border border-stone-200 bg-white p-3 text-left shadow-sm transition hover:border-orange-200 hover:bg-orange-50"
                  >
                    <span className="block text-sm font-semibold text-stone-900">
                      {post.titulo}
                    </span>
                    <span className="mt-1 block text-xs leading-snug text-stone-500 line-clamp-2">
                      {short}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {active ? (
        <div
          className="fixed inset-0 z-[80] flex items-center justify-center bg-stone-950/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cms-insight-title"
          onClick={() => setActive(null)}
        >
          <div
            className="relative max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-stone-200 bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setActive(null)}
              className="absolute right-3 top-3 inline-flex size-9 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-100 hover:text-stone-800"
              aria-label="Fechar"
            >
              <X className="size-4" aria-hidden />
            </button>
            <h3
              id="cms-insight-title"
              className="pr-10 text-lg font-bold tracking-tight text-stone-900"
            >
              {active.titulo}
            </h3>
            {active.resumo ? (
              <p className="mt-2 text-sm text-stone-500">{active.resumo}</p>
            ) : null}
            <div
              className="prose prose-sm prose-stone mt-4 max-w-none"
              dangerouslySetInnerHTML={{
                __html:
                  (active.conteudo_html && active.conteudo_html.trim()) ||
                  `<p>${active.resumo || active.titulo}</p>`,
              }}
            />
          </div>
        </div>
      ) : null}
    </aside>
  );
}

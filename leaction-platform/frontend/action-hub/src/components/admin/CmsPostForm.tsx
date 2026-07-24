'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  createCmsPost,
  type CmsPostStatus,
  type CmsSistemaDestino,
} from '@/lib/admin-api';

const DESTINOS: { value: CmsSistemaDestino; label: string }[] = [
  { value: 'actionhub', label: 'ActionHub (painel logado — coluna direita)' },
  { value: 'hub-publico', label: 'Hub público' },
  { value: 'paneldx', label: 'PanelDX' },
  { value: 'inove4us', label: 'Inove4us' },
  { value: 'todos', label: 'Todos os sistemas' },
];

function slugify(input: string) {
  return input
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 240);
}

export function CmsPostForm() {
  const router = useRouter();
  const { token } = useHubSession();
  const [titulo, setTitulo] = useState('');
  const [slugManual, setSlugManual] = useState(false);
  const [slug, setSlug] = useState('');
  const [resumo, setResumo] = useState('');
  const [imagemCapa, setImagemCapa] = useState('');
  const [sistemaDestino, setSistemaDestino] =
    useState<CmsSistemaDestino>('actionhub');
  const [status, setStatus] = useState<CmsPostStatus>('rascunho');
  const [conteudoHtml, setConteudoHtml] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const slugAuto = useMemo(() => slugify(titulo), [titulo]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      await createCmsPost(token, {
        titulo: titulo.trim(),
        slug: (slugManual ? slug : slugAuto).trim() || slugAuto,
        resumo: resumo.trim(),
        imagem_capa: imagemCapa.trim() || null,
        sistema_destino: sistemaDestino,
        status,
        conteudo_html: conteudoHtml,
      });
      router.push('/dashboard/cms');
      router.refresh();
    } catch (err) {
      let msg = '';
      if (err && typeof err === 'object' && 'response' in err) {
        const data = (err as { response?: { data?: { error?: string } } })
          .response?.data;
        msg = String(data?.error || '');
      }
      setError(msg || (err instanceof Error ? err.message : 'Falha ao salvar'));
    } finally {
      setSaving(false);
    }
  }

  const field =
    'w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-sm text-stone-800 outline-none ring-orange-400/30 transition focus:border-orange-400 focus:ring-2';

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href="/dashboard/cms"
            className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold text-stone-500 hover:text-stone-800"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            Voltar à listagem
          </Link>
          <h1 className="text-xl font-bold text-stone-900">Novo Post</h1>
          <p className="text-sm text-stone-500">
            Conteúdo headless para distribuição aos satélites.
          </p>
        </div>
        <button
          type="submit"
          disabled={saving || !titulo.trim()}
          className="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-orange-400 disabled:opacity-50"
        >
          {saving ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Save className="size-4" aria-hidden />
          )}
          Salvar
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block space-y-1.5 md:col-span-2">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Título
          </span>
          <input
            className={field}
            value={titulo}
            onChange={(e) => {
              setTitulo(e.target.value);
              if (!slugManual) setSlug(slugify(e.target.value));
            }}
            required
            placeholder="Ex: Como acelerar a maturidade digital"
          />
        </label>

        <label className="block space-y-1.5 md:col-span-2">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Slug (URL amigável)
          </span>
          <input
            className={`${field} font-mono text-xs`}
            value={slugManual ? slug : slugAuto}
            onChange={(e) => {
              setSlugManual(true);
              setSlug(e.target.value);
            }}
            placeholder="como-acelerar-maturidade-digital"
          />
        </label>

        <label className="block space-y-1.5 md:col-span-2">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Resumo (texto curto do card)
          </span>
          <textarea
            className={`${field} min-h-[88px]`}
            value={resumo}
            onChange={(e) => setResumo(e.target.value)}
            placeholder="ActionHub painel: 1–2 linhas no card. O conteúdo completo vai no campo abaixo (modal)."
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Imagem capa (URL)
          </span>
          <input
            className={field}
            value={imagemCapa}
            onChange={(e) => setImagemCapa(e.target.value)}
            placeholder="https://..."
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Sistema destino
          </span>
          <select
            className={field}
            value={sistemaDestino}
            onChange={(e) =>
              setSistemaDestino(e.target.value as CmsSistemaDestino)
            }
          >
            {DESTINOS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Status
          </span>
          <select
            className={field}
            value={status}
            onChange={(e) => setStatus(e.target.value as CmsPostStatus)}
          >
            <option value="rascunho">Rascunho</option>
            <option value="publicado">Publicado</option>
          </select>
        </label>

        <label className="block space-y-1.5 md:col-span-2">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Conteúdo (HTML / Markdown)
          </span>
          <textarea
            className={`${field} min-h-[280px] font-mono text-xs leading-relaxed`}
            value={conteudoHtml}
            onChange={(e) => setConteudoHtml(e.target.value)}
            placeholder="<p>Conteúdo rico do post...</p>"
          />
        </label>
      </div>
    </form>
  );
}

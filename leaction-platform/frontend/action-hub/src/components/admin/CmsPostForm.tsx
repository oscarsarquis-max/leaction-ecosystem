'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  createCmsPost,
  fetchCmsPostsAdmin,
  type CmsIdioma,
  type CmsPost,
  type CmsPostStatus,
  type CmsRightNowTipo,
  type CmsSecao,
  type CmsSentido,
  type CmsSistemaDestino,
} from '@/lib/admin-api';
import { CmsImageUploadField } from '@/components/admin/CmsImageUploadField';

const DESTINOS: { value: CmsSistemaDestino; label: string }[] = [
  { value: 'actionhub', label: 'ActionHub (painel logado — coluna direita)' },
  { value: 'hub-publico', label: 'Hub público' },
  { value: 'paneldx', label: 'PanelDX' },
  { value: 'inove4us', label: 'Inove4us' },
  { value: 'lepain', label: 'LePain' },
  { value: 'todos', label: 'Todos os sistemas' },
];

const SENTIDOS: { key: CmsSentido; label: string; bg: string; fg: string }[] = [
  { key: 'olhar', label: 'Olhar', bg: '#3D6FD6', fg: '#ffffff' },
  { key: 'toque', label: 'Toque', bg: '#C0392B', fg: '#ffffff' },
  { key: 'aroma', label: 'Aroma', bg: '#F0A202', fg: '#1B1712' },
  { key: 'sabor', label: 'Sabor', bg: '#0E7A4B', fg: '#ffffff' },
  { key: 'som', label: 'Som', bg: '#C42F6A', fg: '#ffffff' },
  { key: 'memoria', label: 'Memória', bg: '#6B3FA0', fg: '#ffffff' },
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
  const searchParams = useSearchParams();
  const grupoParam = searchParams.get('grupo_id');
  const secaoParam = searchParams.get('secao');
  const { token } = useHubSession();
  const [titulo, setTitulo] = useState('');
  const [slugManual, setSlugManual] = useState(false);
  const [slug, setSlug] = useState('');
  const [resumo, setResumo] = useState('');
  const [imagemCapa, setImagemCapa] = useState('');
  const [sistemaDestino, setSistemaDestino] = useState<CmsSistemaDestino>(
    grupoParam ? 'lepain' : 'actionhub'
  );
  const [status, setStatus] = useState<CmsPostStatus>('rascunho');
  const [conteudoHtml, setConteudoHtml] = useState('');
  const [secao, setSecao] = useState<CmsSecao>(
    secaoParam === 'right_now' ? 'right_now' : 'insights'
  );
  const [idioma, setIdioma] = useState<CmsIdioma>(grupoParam ? 'en' : 'pt');
  const [grupoId, setGrupoId] = useState(grupoParam || '');
  const [sentidos, setSentidos] = useState<CmsSentido[]>([]);
  const [resumoInstagram, setResumoInstagram] = useState('');
  const [rightNowTipo, setRightNowTipo] = useState<CmsRightNowTipo | ''>('');
  const [dataEvento, setDataEvento] = useState('');
  const [validoAte, setValidoAte] = useState('');
  const [ptPosts, setPtPosts] = useState<CmsPost[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const slugAuto = useMemo(() => slugify(titulo), [titulo]);
  const lepain = sistemaDestino === 'lepain';

  useEffect(() => {
    if (!token || !lepain || idioma !== 'en') {
      setPtPosts([]);
      return;
    }
    let cancelled = false;
    fetchCmsPostsAdmin(token)
      .then((rows) => {
        if (cancelled) return;
        setPtPosts(
          rows.filter((p) => p.sistema_destino === 'lepain' && p.idioma === 'pt')
        );
      })
      .catch(() => {
        if (!cancelled) setPtPosts([]);
      });
    return () => {
      cancelled = true;
    };
  }, [token, lepain, idioma]);

  function toggleSentido(key: CmsSentido) {
    setSentidos((current) =>
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key]
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    if (lepain) {
      if (sentidos.length < 1) {
        setError('Escolha ao menos um sentido.');
        return;
      }
      if (secao === 'right_now' && !rightNowTipo) {
        setError('Escolha o tipo do Right Now.');
        return;
      }
      if (idioma === 'en' && !grupoId) {
        setError('Escolha o post em português que esta versão traduz.');
        return;
      }
    }
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
        ...(lepain
          ? {
              secao,
              idioma,
              grupo_id: idioma === 'en' ? Number(grupoId) : null,
              sentidos,
              resumo_instagram: resumoInstagram.trim() || null,
              right_now_tipo: secao === 'right_now' ? rightNowTipo || null : null,
              data_evento: secao === 'right_now' ? dataEvento || null : null,
              valido_ate: secao === 'right_now' ? validoAte || null : null,
            }
          : {}),
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
    'w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-sm text-stone-800 outline-none ring-emerald-400/30 transition focus:border-emerald-400 focus:ring-2';

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
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-400 disabled:opacity-50"
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

        <div className="space-y-1.5">
          <CmsImageUploadField
            label="Imagem de capa"
            value={imagemCapa}
            onChange={setImagemCapa}
            token={token}
            preferPublicUrl
            helpText="Upload S3 (modelo PanelDX). A URL pública é gravada no post."
          />
        </div>

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

        {lepain ? (
          <>
            <label className="block space-y-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                Seção
              </span>
              <select
                className={field}
                value={secao}
                onChange={(e) => setSecao(e.target.value as CmsSecao)}
              >
                <option value="insights">Insights</option>
                <option value="right_now">Right Now</option>
              </select>
            </label>

            <label className="block space-y-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                Idioma
              </span>
              <select
                className={field}
                value={idioma}
                onChange={(e) => setIdioma(e.target.value as CmsIdioma)}
              >
                <option value="pt">Português</option>
                <option value="en">English</option>
              </select>
            </label>

            {idioma === 'en' ? (
              <label className="block space-y-1.5 md:col-span-2">
                <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                  Tradução de
                </span>
                <select
                  className={field}
                  value={grupoId}
                  onChange={(e) => setGrupoId(e.target.value)}
                  required
                >
                  <option value="">Escolha o post em português</option>
                  {ptPosts.map((post) => (
                    <option key={post.id} value={post.id}>
                      {post.titulo}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <div className="space-y-1.5 md:col-span-2">
              <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                Sentidos
              </span>
              <div className="flex flex-wrap gap-2">
                {SENTIDOS.map((sentido) => {
                  const on = sentidos.includes(sentido.key);
                  return (
                    <button
                      key={sentido.key}
                      type="button"
                      aria-pressed={on}
                      onClick={() => toggleSentido(sentido.key)}
                      className="rounded-full px-3 py-1 text-xs font-bold ring-1 transition"
                      style={
                        on
                          ? {
                              backgroundColor: sentido.bg,
                              color: sentido.fg,
                              borderColor: sentido.bg,
                            }
                          : {
                              backgroundColor: '#ffffff',
                              color: sentido.bg,
                              boxShadow: `inset 0 0 0 1px ${sentido.bg}`,
                            }
                      }
                    >
                      {sentido.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <label className="block space-y-1.5 md:col-span-2">
              <span className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-stone-500">
                Resumo do Instagram
                <span className="font-mono normal-case tracking-normal">
                  {resumoInstagram.length} caracteres
                </span>
              </span>
              <textarea
                className={`${field} min-h-[88px]`}
                value={resumoInstagram}
                onChange={(e) => setResumoInstagram(e.target.value)}
                placeholder="Texto do card do Instagram."
              />
            </label>

            {secao === 'right_now' ? (
              <>
                <label className="block space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                    Tipo
                  </span>
                  <select
                    className={field}
                    value={rightNowTipo}
                    onChange={(e) => setRightNowTipo(e.target.value as CmsRightNowTipo | '')}
                  >
                    <option value="">Escolha</option>
                    <option value="promocao">Promoção</option>
                    <option value="evento">Evento</option>
                    <option value="noticia">Notícia</option>
                  </select>
                </label>
                <label className="block space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                    Data do evento
                  </span>
                  <input
                    type="date"
                    className={field}
                    value={dataEvento}
                    onChange={(e) => setDataEvento(e.target.value)}
                  />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                    Válido até
                  </span>
                  <input
                    type="date"
                    className={field}
                    value={validoAte}
                    onChange={(e) => setValidoAte(e.target.value)}
                  />
                </label>
              </>
            ) : null}
          </>
        ) : null}

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
          {lepain ? (
            <p className="text-xs text-stone-500">
              Vídeo e áudio entram por link (YouTube/Vimeo ou <code>&lt;audio src&gt;</code>).
            </p>
          ) : null}
        </label>
      </div>
    </form>
  );
}

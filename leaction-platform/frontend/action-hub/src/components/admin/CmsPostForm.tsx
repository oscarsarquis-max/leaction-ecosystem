'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Copy, Loader2, Save } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  createCmsPost,
  fetchCmsPostAdmin,
  fetchCmsPostsAdmin,
  updateCmsPost,
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

function blogSection(secao: string) {
  return secao === 'right_now' ? 'right-now' : 'insights';
}

function blogPostUrl(idioma: string, secao: string, slug: string) {
  const lang = idioma === 'en' ? 'en' : 'pt';
  return `https://lepain.lojadepaes.com.br/${lang}/${blogSection(secao)}/${slug}`;
}

function blogCardUrl(idioma: string, slug: string, modelo: 'tipografico' | 'foto') {
  const lang = idioma === 'en' ? 'en' : 'pt';
  return `https://lepain.lojadepaes.com.br/${lang}/card/${slug}?modelo=${modelo}`;
}

function readyCaption(resumo: string, idioma: string, secao: string, slug: string) {
  return `${resumo.trim()}\n\nLeia o ensaio completo: ${blogPostUrl(idioma, secao, slug)}\n\n@loja.de.paes`;
}

type Draft = {
  titulo: string;
  slug: string;
  resumo: string;
  imagemCapa: string;
  sistemaDestino: string;
  status: string;
  conteudoHtml: string;
  secao: string;
  idioma: string;
  grupoId: string;
  sentidos: string[];
  resumoInstagram: string;
  instagramUrl: string;
  rightNowTipo: string;
  dataEvento: string;
  validoAte: string;
};

function draftKey(draft: Draft) {
  return JSON.stringify(draft);
}

export function CmsPostForm({ postId }: { postId?: number }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const grupoParam = searchParams.get('grupo_id');
  const secaoParam = searchParams.get('secao');
  const { token } = useHubSession();
  const [titulo, setTitulo] = useState('');
  const [slugManual, setSlugManual] = useState(Boolean(postId));
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
  const [instagramUrl, setInstagramUrl] = useState('');
  const [rightNowTipo, setRightNowTipo] = useState<CmsRightNowTipo | ''>('');
  const [dataEvento, setDataEvento] = useState('');
  const [validoAte, setValidoAte] = useState('');
  const [ptPosts, setPtPosts] = useState<CmsPost[]>([]);
  const [versions, setVersions] = useState<{
    pt?: { slug: string; cover: boolean };
    en?: { slug: string; cover: boolean };
  }>({});
  const [saving, setSaving] = useState(false);
  const [loadingPost, setLoadingPost] = useState(Boolean(postId));
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [baseline, setBaseline] = useState<string | null>(null);
  const [origin, setOrigin] = useState<{ slug: string; status: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [slugAsk, setSlugAsk] = useState<boolean | null>(null);
  const [leaveHref, setLeaveHref] = useState<string | null>(null);

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

  const currentSlug = (slugManual ? slug : slugAuto).trim() || slugAuto;
  const draft = useMemo<Draft>(
    () => ({
      titulo,
      slug: currentSlug,
      resumo,
      imagemCapa,
      sistemaDestino,
      status,
      conteudoHtml,
      secao,
      idioma,
      grupoId,
      sentidos,
      resumoInstagram,
      instagramUrl,
      rightNowTipo,
      dataEvento,
      validoAte,
    }),
    [
      titulo,
      currentSlug,
      resumo,
      imagemCapa,
      sistemaDestino,
      status,
      conteudoHtml,
      secao,
      idioma,
      grupoId,
      sentidos,
      resumoInstagram,
      instagramUrl,
      rightNowTipo,
      dataEvento,
      validoAte,
    ]
  );
  const dirty = Boolean(postId && baseline && draftKey(draft) !== baseline);

  useEffect(() => {
    if (!postId || !token) return;
    let cancelled = false;
    setLoadingPost(true);
    setMissing(false);
    Promise.all([fetchCmsPostAdmin(token, postId), fetchCmsPostsAdmin(token)])
      .then(([post, rows]) => {
        if (cancelled) return;
        const next: Draft = {
          titulo: post.titulo || '',
          slug: post.slug || '',
          resumo: post.resumo || '',
          imagemCapa: post.imagem_capa || '',
          sistemaDestino: post.sistema_destino || 'actionhub',
          status: post.status === 'publicado' ? 'publicado' : 'rascunho',
          conteudoHtml: post.conteudo_html || '',
          secao: post.secao === 'right_now' ? 'right_now' : 'insights',
          idioma: post.idioma === 'en' ? 'en' : 'pt',
          grupoId: post.grupo_id ? String(post.grupo_id) : '',
          sentidos: Array.isArray(post.sentidos) ? post.sentidos : [],
          resumoInstagram: post.resumo_instagram || '',
          instagramUrl: post.instagram_url || '',
          rightNowTipo: post.right_now_tipo || '',
          dataEvento: post.data_evento || '',
          validoAte: post.valido_ate || '',
        };
        setTitulo(next.titulo);
        setSlug(next.slug);
        setSlugManual(true);
        setResumo(next.resumo);
        setImagemCapa(next.imagemCapa);
        setSistemaDestino(next.sistemaDestino as CmsSistemaDestino);
        setStatus(next.status as CmsPostStatus);
        setConteudoHtml(next.conteudoHtml);
        setSecao(next.secao as CmsSecao);
        setIdioma(next.idioma as CmsIdioma);
        setGrupoId(next.grupoId);
        setSentidos(next.sentidos as CmsSentido[]);
        setResumoInstagram(next.resumoInstagram);
        setInstagramUrl(next.instagramUrl);
        setRightNowTipo(next.rightNowTipo as CmsRightNowTipo | '');
        setDataEvento(next.dataEvento);
        setValidoAte(next.validoAte);
        setBaseline(draftKey(next));
        setOrigin({ slug: next.slug, status: next.status });
        const links: { pt?: { slug: string; cover: boolean }; en?: { slug: string; cover: boolean } } = {};
        if (post.sistema_destino === 'lepain') {
          const own = { slug: next.slug, cover: Boolean(next.imagemCapa.trim()) };
          if (next.idioma === 'pt') links.pt = own;
          if (next.idioma === 'en') links.en = own;
          for (const row of rows) {
            if (row.sistema_destino !== 'lepain') continue;
            if (next.idioma === 'pt' && row.idioma === 'en' && row.grupo_id === post.id) {
              links.en = { slug: row.slug, cover: Boolean(row.imagem_capa) };
            }
            if (next.idioma === 'en' && row.idioma === 'pt' && row.id === post.grupo_id) {
              links.pt = { slug: row.slug, cover: Boolean(row.imagem_capa) };
            }
          }
        }
        setVersions(links);
      })
      .catch(() => {
        if (!cancelled) setMissing(true);
      })
      .finally(() => {
        if (!cancelled) setLoadingPost(false);
      });
    return () => {
      cancelled = true;
    };
  }, [postId, token]);

  useEffect(() => {
    if (!dirty) return;
    function onBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = '';
    }
    function onClick(event: MouseEvent) {
      const anchor = (event.target as HTMLElement | null)?.closest?.('a');
      if (!anchor || anchor.target === '_blank') return;
      const href = anchor.getAttribute('href') || '';
      if (!href || href.startsWith('#')) return;
      event.preventDefault();
      event.stopPropagation();
      setLeaveHref(href);
    }
    window.addEventListener('beforeunload', onBeforeUnload);
    document.addEventListener('click', onClick, true);
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload);
      document.removeEventListener('click', onClick, true);
    };
  }, [dirty]);

  function toggleSentido(key: CmsSentido) {
    setSentidos((current) =>
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key]
    );
  }

  function bodyFor(nextStatus: CmsPostStatus) {
    return {
      titulo: titulo.trim(),
      slug: currentSlug,
      resumo: resumo.trim(),
      imagem_capa: imagemCapa.trim() || null,
      sistema_destino: sistemaDestino,
      status: nextStatus,
      conteudo_html: conteudoHtml,
      ...(lepain
        ? {
            secao,
            idioma,
            grupo_id: idioma === 'en' ? Number(grupoId) : null,
            sentidos,
            resumo_instagram: resumoInstagram.trim() || null,
            instagram_url: instagramUrl.trim() || null,
            right_now_tipo: secao === 'right_now' ? rightNowTipo || null : null,
            data_evento: secao === 'right_now' ? dataEvento || null : null,
            valido_ate: secao === 'right_now' ? validoAte || null : null,
          }
        : {}),
    };
  }

  async function persist(publish: boolean) {
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
    const nextStatus: CmsPostStatus = publish ? 'publicado' : status;
    if (
      postId &&
      origin?.status === 'publicado' &&
      currentSlug !== origin.slug &&
      slugAsk === null
    ) {
      setSlugAsk(publish);
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = postId
        ? await updateCmsPost(token, postId, bodyFor(nextStatus))
        : await createCmsPost(token, bodyFor(nextStatus));
      if (!postId) {
        router.push('/dashboard/cms');
        router.refresh();
        return;
      }
      const next: Draft = { ...draft, slug: saved.slug, status: saved.status };
      setSlug(saved.slug);
      setStatus(saved.status === 'publicado' ? 'publicado' : 'rascunho');
      setBaseline(draftKey(next));
      setOrigin({ slug: saved.slug, status: saved.status });
      setVersions((current) => ({
        ...current,
        ...(saved.idioma === 'en'
          ? { en: { slug: saved.slug, cover: Boolean((saved.imagem_capa || imagemCapa).trim()) } }
          : { pt: { slug: saved.slug, cover: Boolean((saved.imagem_capa || imagemCapa).trim()) } }),
      }));
      setNotice('Salvo. No blog, aparece em até 5 minutos.');
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
      setSlugAsk(null);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    const publish = submitter instanceof HTMLButtonElement && submitter.dataset.publish === '1';
    void persist(publish);
  }

  async function copyCaption() {
    const caption = readyCaption(resumoInstagram, idioma, secao, currentSlug);
    await navigator.clipboard.writeText(caption);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  const field =
    'w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-sm text-stone-800 outline-none ring-emerald-400/30 transition focus:border-emerald-400 focus:ring-2';

  if (loadingPost) {
    return (
      <div className="px-4 py-10 text-sm text-stone-500">
        <Loader2 className="mr-2 inline size-4 animate-spin" aria-hidden />
        Carregando post…
      </div>
    );
  }

  if (missing) {
    return (
      <div className="space-y-3">
        <Link
          href="/dashboard/cms"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-stone-500 hover:text-stone-800"
        >
          <ArrowLeft className="size-3.5" aria-hidden />
          Voltar à listagem
        </Link>
        <p className="text-sm text-stone-600">Post não encontrado.</p>
      </div>
    );
  }

  const showInstagram = Boolean(postId && lepain && origin?.status === 'publicado');
  const caption = readyCaption(resumoInstagram, idioma, secao, currentSlug);

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
          <h1 className="text-xl font-bold text-stone-900">
            {postId ? 'Editar post' : 'Novo Post'}
          </h1>
          <p className="text-sm text-stone-500">
            Conteúdo headless para distribuição aos satélites.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
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
          {postId ? (
            <button
              type="submit"
              data-publish="1"
              disabled={saving || !titulo.trim()}
              className="inline-flex items-center gap-2 rounded-xl border border-emerald-600 bg-white px-4 py-2.5 text-sm font-bold text-emerald-800 transition hover:bg-emerald-50 disabled:opacity-50"
            >
              Salvar e publicar
            </button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800" role="status">
          {notice}
        </div>
      ) : null}
      {showInstagram ? (
        <section className="space-y-3 rounded-2xl border border-stone-200 bg-stone-50 p-4">
          <h2 className="text-sm font-bold text-stone-900">Instagram</h2>
          <div className="flex flex-wrap gap-3">
            {versions.pt ? (
              <a
                href={blogCardUrl('pt', versions.pt.slug, 'tipografico')}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-emerald-700 underline-offset-2 hover:underline"
              >
                Card PT · Tipográfico
              </a>
            ) : null}
            {versions.pt?.cover ? (
              <a
                href={blogCardUrl('pt', versions.pt.slug, 'foto')}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-emerald-700 underline-offset-2 hover:underline"
              >
                Card PT · Com foto
              </a>
            ) : null}
            {versions.en ? (
              <a
                href={blogCardUrl('en', versions.en.slug, 'tipografico')}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-emerald-700 underline-offset-2 hover:underline"
              >
                Card EN · Tipográfico
              </a>
            ) : null}
            {versions.en?.cover ? (
              <a
                href={blogCardUrl('en', versions.en.slug, 'foto')}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-emerald-700 underline-offset-2 hover:underline"
              >
                Card EN · Com foto
              </a>
            ) : null}
          </div>
          <label className="block space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
              Link do post no Instagram
            </span>
            <input
              className={field}
              value={instagramUrl}
              onChange={(e) => setInstagramUrl(e.target.value)}
              placeholder="https://www.instagram.com/p/…"
              inputMode="url"
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
              Legenda pronta
            </span>
            <textarea className={`${field} min-h-[120px]`} readOnly value={caption} />
          </label>
          <button
            type="button"
            onClick={() => void copyCaption()}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50"
          >
            <Copy className="size-4" aria-hidden />
            {copied ? 'Copiado' : 'Copiar'}
          </button>
        </section>
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
      {slugAsk !== null ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 px-4" role="alertdialog" aria-labelledby="slug-warn-title" aria-modal="true">
          <div className="w-full max-w-md space-y-4 rounded-2xl bg-white p-5 shadow-xl">
            <h2 id="slug-warn-title" className="text-lg font-bold text-stone-900">
              O endereço no blog muda
            </h2>
            <p className="text-sm text-stone-600">
              O slug deste post publicado vai mudar. O endereço no blog muda. Quer continuar?
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setSlugAsk(null)}
                className="rounded-xl border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void persist(slugAsk)}
                className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white"
              >
                Continuar
              </button>
            </div>
          </div>
        </div>
      ) : null}
      {leaveHref ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 px-4" role="alertdialog" aria-labelledby="leave-title" aria-modal="true">
          <div className="w-full max-w-md space-y-4 rounded-2xl bg-white p-5 shadow-xl">
            <h2 id="leave-title" className="text-lg font-bold text-stone-900">
              Alterações não salvas
            </h2>
            <p className="text-sm text-stone-600">
              Há alterações não salvas. Sair mesmo assim?
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setLeaveHref(null)}
                className="rounded-xl border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700"
              >
                Ficar
              </button>
              <button
                type="button"
                onClick={() => {
                  const href = leaveHref;
                  setLeaveHref(null);
                  setBaseline(draftKey(draft));
                  router.push(href);
                }}
                className="rounded-xl bg-stone-900 px-4 py-2 text-sm font-bold text-white"
              >
                Sair
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </form>
  );
}

'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import axios from 'axios';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  LogOut,
  Save,
  Search,
  Settings2,
  Shield,
} from 'lucide-react';
import { CurationLogin } from '@/components/Marketplace/CurationLogin';
import { PreviewMiniCard } from '@/components/Marketplace/PreviewMiniCard';
import {
  CATEGORY_IDS,
  type CurationRule,
  type PreviewOffer,
  fetchCurationRules,
  fetchPreviewOffers,
  labelForCategory,
  listToCommaText,
  listToMultilineText,
  rulesToMap,
  textToList,
  updateCurationRule,
} from '@/components/Marketplace/curationApi';
import { useAdminGate } from '@/lib/require-admin';

type Toast = { type: 'success' | 'error'; message: string } | null;
type AuthVia = 'hub_admin' | 'curation_cookie' | null;

export default function MarketplaceCurationPage() {
  const { canAccessAdmin, user: hubUser, token: hubToken, hydrated: hubHydrated } = useAdminGate();
  const [authChecked, setAuthChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [sessionUser, setSessionUser] = useState<string | null>(null);
  const [authVia, setAuthVia] = useState<AuthVia>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [curationData, setCurationData] = useState<Record<string, CurationRule>>({});
  const [activeCategory, setActiveCategory] = useState('formacao');

  const [globalNegativeText, setGlobalNegativeText] = useState('');
  const [searchTermsText, setSearchTermsText] = useState('');
  const [positiveKeywordsText, setPositiveKeywordsText] = useState('');

  const [savingGlobal, setSavingGlobal] = useState(false);
  const [savingCategory, setSavingCategory] = useState(false);
  const [toast, setToast] = useState<Toast>(null);

  const [previewItems, setPreviewItems] = useState<PreviewOffer[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [previewMeta, setPreviewMeta] = useState({ live: false, count: 0, query: '', notice: '' });

  const showToast = useCallback((next: Toast) => {
    setToast(next);
    if (next) window.setTimeout(() => setToast(null), 4500);
  }, []);

  const applyCategoryFields = useCallback((categoryId: string, data: Record<string, CurationRule>) => {
    const rule = data[categoryId];
    setSearchTermsText(listToMultilineText(rule?.search_terms));
    setPositiveKeywordsText(listToCommaText(rule?.positive_keywords));
  }, []);

  const loadCurationData = useCallback(async () => {
    setIsLoading(true);
    setLoadError('');
    try {
      const rules = await fetchCurationRules();
      const map = rulesToMap(rules);
      setCurationData(map);
      setGlobalNegativeText(listToCommaText(map.global?.negative_keywords));
      const defaultCategory = CATEGORY_IDS.find((id) => map[id]) ?? CATEGORY_IDS[0];
      setActiveCategory(defaultCategory);
      applyCategoryFields(defaultCategory, map);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        setAuthenticated(false);
        setSessionUser(null);
        return;
      }
      setLoadError(err instanceof Error ? err.message : 'Erro ao carregar curadoria.');
    } finally {
      setIsLoading(false);
    }
  }, [applyCategoryFields]);

  useEffect(() => {
    if (!hubHydrated) return;

    let cancelled = false;
    (async () => {
      // Admin já logado no Action Hub — sem segundo login
      if (canAccessAdmin && hubToken) {
        if (!cancelled) {
          setAuthenticated(true);
          setAuthVia('hub_admin');
          setSessionUser(hubUser?.email || null);
          setAuthChecked(true);
        }
        return;
      }

      try {
        const headers: Record<string, string> = {};
        if (hubToken) headers.Authorization = `Bearer ${hubToken}`;
        const { data } = await axios.get('/api/marketplace/curation-auth/session', {
          timeout: 10000,
          headers,
        });
        if (cancelled) return;
        setAuthenticated(Boolean(data?.authenticated));
        setSessionUser(data?.user || null);
        setAuthVia(
          data?.via === 'hub_admin' || data?.via === 'curation_cookie' ? data.via : null
        );
      } catch {
        if (!cancelled) {
          setAuthenticated(false);
          setSessionUser(null);
          setAuthVia(null);
        }
      } finally {
        if (!cancelled) setAuthChecked(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [hubHydrated, canAccessAdmin, hubToken, hubUser?.email]);

  useEffect(() => {
    if (authenticated) loadCurationData();
  }, [authenticated, loadCurationData]);

  async function handleLogout() {
    if (authVia === 'curation_cookie') {
      await axios.post('/api/marketplace/curation-auth/logout').catch(() => undefined);
    }
    setAuthenticated(false);
    setSessionUser(null);
    setAuthVia(null);
    setCurationData({});
    setPreviewItems([]);
  }

  function handleLoginSuccess() {
    setAuthenticated(true);
    setAuthVia('curation_cookie');
    axios
      .get('/api/marketplace/curation-auth/session')
      .then(({ data }) => setSessionUser(data?.user || null))
      .catch(() => undefined);
  }

  function handleSelectCategory(categoryId: string) {
    setActiveCategory(categoryId);
    applyCategoryFields(categoryId, curationData);
    setToast(null);
    setPreviewError('');
  }

  async function handleSaveGlobal() {
    setSavingGlobal(true);
    try {
      const updated = await updateCurationRule('global', {
        negative_keywords: textToList(globalNegativeText),
      });
      setCurationData((c) => ({ ...c, global: updated }));
      setGlobalNegativeText(listToCommaText(updated.negative_keywords));
      showToast({ type: 'success', message: 'Regras globais salvas com sucesso.' });
    } catch (err) {
      showToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Erro ao salvar regras globais.',
      });
    } finally {
      setSavingGlobal(false);
    }
  }

  async function handleSaveCategory() {
    setSavingCategory(true);
    try {
      const updated = await updateCurationRule(activeCategory, {
        search_terms: textToList(searchTermsText),
        positive_keywords: textToList(positiveKeywordsText),
      });
      setCurationData((c) => ({ ...c, [activeCategory]: updated }));
      applyCategoryFields(activeCategory, { [activeCategory]: updated });
      showToast({
        type: 'success',
        message: `Regras de "${labelForCategory(activeCategory)}" salvas.`,
      });
    } catch (err) {
      showToast({
        type: 'error',
        message: err instanceof Error ? err.message : 'Erro ao salvar categoria.',
      });
    } finally {
      setSavingCategory(false);
    }
  }

  async function handlePreview() {
    setPreviewLoading(true);
    setPreviewError('');
    setPreviewItems([]);
    try {
      const result = await fetchPreviewOffers(activeCategory, 4);
      setPreviewItems(result.offers);
      setPreviewMeta({
        live: result.live,
        count: result.count,
        query: result.query,
        notice: result.notice,
      });
      if (!result.offers.length) {
        setPreviewError(
          'Nenhum produto retornado. Ajuste os termos de busca ou palavras-chave positivas.'
        );
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : 'Falha ao testar a busca.');
    } finally {
      setPreviewLoading(false);
    }
  }

  if (!authChecked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-red-950/60">
        <Loader2 className="size-6 animate-spin text-orange-500" aria-hidden />
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-slate-50">
        {hubHydrated && !hubUser ? (
          <div className="mx-auto max-w-lg px-4 pt-10 text-center">
            <p className="text-sm text-red-950/70">
              Faça login no Action Hub como admin para abrir a curadoria sem segundo login.
            </p>
            <Link
              href="/"
              className="mt-3 inline-block text-sm font-semibold text-orange-600 hover:text-orange-700"
            >
              Ir para o Action Hub
            </Link>
            <p className="mt-8 text-xs font-semibold uppercase tracking-wider text-slate-400">
              ou use o login dedicado da curadoria
            </p>
          </div>
        ) : null}
        <CurationLogin onSuccess={handleLoginSuccess} />
      </div>
    );
  }

  const activeRule = curationData[activeCategory];
  const globalRule = curationData.global;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-10 md:px-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-medium text-red-950/70 hover:text-orange-500"
          >
            <ArrowLeft className="size-4 text-orange-500" aria-hidden />
            Voltar ao Action Hub
          </Link>
          <div className="flex items-center gap-3">
            {sessionUser ? (
              <span className="text-xs font-medium text-red-950/60">
                {authVia === 'hub_admin' ? 'Admin Hub · ' : ''}
                {sessionUser}
              </span>
            ) : null}
            {authVia === 'hub_admin' ? (
              <Link
                href="/"
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-red-950 hover:border-orange-300"
              >
                <ArrowLeft className="size-4 text-orange-500" aria-hidden />
                Início
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-red-950 hover:border-orange-300"
              >
                <LogOut className="size-4 text-orange-500" aria-hidden />
                Sair
              </button>
            )}
          </div>
        </div>

        <header className="mb-8">
          <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-500">
            <Settings2 className="size-4" aria-hidden />
            Marketplace
          </p>
          <h1 className="text-3xl font-extrabold tracking-tight text-red-950">Painel de Curadoria</h1>
          <p className="mt-2 max-w-2xl text-sm text-red-950/70">
            Edite as regras da tabela <code className="text-xs">marketplace_curation</code>.
          </p>
        </header>

        {toast ? (
          <div
            role="status"
            className={`mb-6 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium ${
              toast.type === 'success'
                ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                : 'border-red-200 bg-red-50 text-red-800'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="size-4 shrink-0" aria-hidden />
            ) : (
              <AlertCircle className="size-4 shrink-0" aria-hidden />
            )}
            {toast.message}
          </div>
        ) : null}

        {isLoading ? (
          <div className="flex min-h-[320px] items-center justify-center gap-2 text-red-950/60">
            <Loader2 className="size-5 animate-spin text-orange-500" aria-hidden />
            <span className="text-sm font-medium">Carregando curadoria…</span>
          </div>
        ) : null}

        {!isLoading && loadError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {loadError}
          </div>
        ) : null}

        {!isLoading && !loadError ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-6">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6">
                <div className="mb-4 flex items-center gap-2">
                  <Shield className="size-5 text-orange-500" aria-hidden />
                  <h2 className="text-lg font-bold text-red-950">Card Global</h2>
                </div>
                <label htmlFor="global-negative" className="mb-1 block text-sm font-semibold text-red-950">
                  negative_keywords (global)
                </label>
                <p className="mb-2 text-xs text-red-950/60">Separadas por vírgula.</p>
                <input
                  id="global-negative"
                  type="text"
                  value={globalNegativeText}
                  onChange={(e) => setGlobalNegativeText(e.target.value)}
                  placeholder="gamer, brinquedo, infantil, smart tv"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-red-950 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-200"
                  spellCheck={false}
                />
                {globalRule?.updated_at ? (
                  <p className="mt-2 text-xs text-red-950/50">
                    Atualizado: {new Date(globalRule.updated_at).toLocaleString('pt-BR')}
                  </p>
                ) : null}
                <button
                  type="button"
                  onClick={handleSaveGlobal}
                  disabled={savingGlobal}
                  className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
                >
                  {savingGlobal ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                  Salvar Global
                </button>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6">
                <h2 className="mb-4 text-lg font-bold text-red-950">Card por Categoria</h2>
                <div className="mb-4 flex flex-wrap gap-2" role="tablist">
                  {CATEGORY_IDS.map((categoryId) => (
                    <button
                      key={categoryId}
                      type="button"
                      role="tab"
                      aria-selected={activeCategory === categoryId}
                      onClick={() => handleSelectCategory(categoryId)}
                      className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                        activeCategory === categoryId
                          ? 'bg-red-600 text-white shadow-sm'
                          : 'bg-slate-100 text-red-950 hover:bg-orange-50'
                      }`}
                    >
                      {labelForCategory(categoryId)}
                    </button>
                  ))}
                </div>
                <div className="mb-4">
                  <label htmlFor="category-select" className="mb-1 block text-xs font-medium text-red-950/70">
                    Ou selecione:
                  </label>
                  <select
                    id="category-select"
                    value={activeCategory}
                    onChange={(e) => handleSelectCategory(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-red-950"
                  >
                    {CATEGORY_IDS.map((categoryId) => (
                      <option key={categoryId} value={categoryId}>
                        {labelForCategory(categoryId)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="search-terms" className="mb-1 block text-sm font-semibold text-red-950">
                      search_terms
                    </label>
                    <textarea
                      id="search-terms"
                      rows={6}
                      value={searchTermsText}
                      onChange={(e) => setSearchTermsText(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm text-red-950"
                      spellCheck={false}
                    />
                  </div>
                  <div>
                    <label htmlFor="positive-keywords" className="mb-1 block text-sm font-semibold text-red-950">
                      positive_keywords
                    </label>
                    <textarea
                      id="positive-keywords"
                      rows={4}
                      value={positiveKeywordsText}
                      onChange={(e) => setPositiveKeywordsText(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-red-950"
                      spellCheck={false}
                    />
                  </div>
                  {activeRule?.updated_at ? (
                    <p className="text-xs text-red-950/50">
                      Atualizado: {new Date(activeRule.updated_at).toLocaleString('pt-BR')}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    onClick={handleSaveCategory}
                    disabled={savingCategory}
                    className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
                  >
                    {savingCategory ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                    Salvar Regras da Categoria
                  </button>
                </div>
              </section>
            </div>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6 lg:sticky lg:top-6 lg:self-start">
              <h2 className="text-lg font-bold text-red-950">Preview ao Vivo</h2>
              <p className="mt-1 text-sm text-red-950/70">
                Categoria:{' '}
                <span className="font-semibold text-orange-500">{labelForCategory(activeCategory)}</span>
              </p>
              <button
                type="button"
                onClick={handlePreview}
                disabled={previewLoading}
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-4 text-base font-bold text-white shadow-md hover:bg-red-700 disabled:opacity-60"
              >
                {previewLoading ? (
                  <Loader2 className="size-5 animate-spin" aria-hidden />
                ) : (
                  <Search className="size-5 text-orange-200" aria-hidden />
                )}
                Testar Busca (Preview)
              </button>
              {previewMeta.query ? (
                <p className="mt-4 text-xs text-red-950/60">
                  Query: <span className="font-mono">{previewMeta.query}</span>
                </p>
              ) : null}
              {!previewLoading && previewError ? (
                <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="alert">
                  <AlertCircle className="mb-1 inline size-4 text-orange-500" />
                  {previewError}
                </div>
              ) : null}
              {!previewLoading && !previewError && previewItems.length > 0 ? (
                <ul className="mt-6 space-y-3">
                  {previewItems.map((offer) => (
                    <li key={offer.id || offer.title}>
                      <PreviewMiniCard offer={offer} />
                    </li>
                  ))}
                </ul>
              ) : null}
              {!previewLoading && !previewError && previewItems.length === 0 ? (
                <p className="mt-6 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-red-950/60">
                  Clique em &quot;Testar Busca (Preview)&quot; para ver até 4 produtos.
                </p>
              ) : null}
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}

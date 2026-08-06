'use client';

import Link from 'next/link';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  fetchCmsSiteAdmin,
  saveCmsSiteAdmin,
  type CmsSiteConfigKey,
} from '@/lib/admin-api';
import { CmsImageUploadField } from '@/components/admin/CmsImageUploadField';

type TabId = 'landing' | 'instructions';

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function str(value: unknown): string {
  return value == null ? '' : String(value);
}

function bool(value: unknown, fallback = true): boolean {
  if (typeof value === 'boolean') return value;
  if (value == null) return fallback;
  return String(value).toLowerCase() !== 'false';
}

/** Extrai #rrggbb para o input type=color; rgba/outros ficam só no texto. */
function toColorInputValue(value: unknown, fallback: string): string {
  const s = str(value).trim();
  if (/^#[0-9a-fA-F]{6}$/.test(s)) return s;
  if (/^#[0-9a-fA-F]{3}$/.test(s)) {
    const r = s[1];
    const g = s[2];
    const b = s[3];
    return `#${r}${r}${g}${g}${b}${b}`;
  }
  return fallback;
}

function ColorField({
  label,
  value,
  fallback,
  onChange,
  allowRgba = false,
  fieldClass,
}: {
  label: string;
  value: unknown;
  fallback: string;
  onChange: (next: string) => void;
  allowRgba?: boolean;
  fieldClass: string;
}) {
  const text = str(value) || fallback;
  const picker = toColorInputValue(value, fallback);

  return (
    <label className="block space-y-1">
      <span className="text-xs font-semibold text-stone-500">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="color"
          className="h-10 w-12 shrink-0 cursor-pointer rounded-lg border border-stone-300 bg-white p-1"
          value={picker}
          onChange={(e) => onChange(e.target.value)}
          title={label}
        />
        <input
          className={fieldClass}
          value={text}
          onChange={(e) => onChange(e.target.value)}
          placeholder={allowRgba ? 'hex ou rgba(...)' : fallback}
        />
      </div>
    </label>
  );
}

type BannerColorField = {
  key: string;
  label: string;
  fallback: string;
  allowRgba?: boolean;
};

const COLUNA1_COLOR_FIELDS: BannerColorField[] = [
  { key: 'bg_color_start', label: 'Fundo — gradiente início', fallback: '#0b0c10' },
  { key: 'bg_color_end', label: 'Fundo — gradiente fim', fallback: '#1a0b2e' },
  {
    key: 'border_color',
    label: 'Borda (hex ou rgba)',
    fallback: 'rgba(0, 191, 255, 0.2)',
    allowRgba: true,
  },
  { key: 'title_color', label: 'Cor do título', fallback: '#ffffff' },
  {
    key: 'subtitle_color',
    label: 'Cor do subtítulo (hex ou rgba)',
    fallback: 'rgba(255, 255, 255, 0.82)',
    allowRgba: true,
  },
  { key: 'pill_bg_color', label: 'Fundo da pill', fallback: '#FF6B00' },
  { key: 'pill_text_color', label: 'Texto da pill', fallback: '#ffffff' },
  { key: 'accent_color', label: 'Destaque (ex: "Gratuito")', fallback: '#FF6B00' },
  { key: 'button_bg_color', label: 'Fundo do botão CTA', fallback: '#FF6B00' },
  { key: 'button_text_color', label: 'Texto do botão CTA', fallback: '#ffffff' },
  { key: 'button_shadow_color', label: 'Sombra 3D do botão', fallback: '#b34700' },
];

const HERO_CTA_COLOR_FIELDS: BannerColorField[] = [
  { key: 'bg_color_start', label: 'Fundo — gradiente início', fallback: '#0f172a' },
  { key: 'bg_color_end', label: 'Fundo — gradiente fim', fallback: '#1e1b4b' },
  {
    key: 'border_color',
    label: 'Borda (hex ou rgba)',
    fallback: 'rgba(99, 102, 241, 0.35)',
    allowRgba: true,
  },
  { key: 'title_color', label: 'Cor do título', fallback: '#ffffff' },
  {
    key: 'subtitle_color',
    label: 'Cor do subtítulo (hex ou rgba)',
    fallback: 'rgba(255, 255, 255, 0.78)',
    allowRgba: true,
  },
  { key: 'pill_bg_color', label: 'Fundo da pill / badge', fallback: '#6366f1' },
  { key: 'pill_text_color', label: 'Texto da pill / badge', fallback: '#ffffff' },
  { key: 'accent_color', label: 'Destaque (ex: "Gratuito")', fallback: '#FF6B00' },
  { key: 'button_bg_color', label: 'Fundo do botão CTA', fallback: '#FF6B00' },
  { key: 'button_text_color', label: 'Texto do botão CTA', fallback: '#ffffff' },
  { key: 'button_shadow_color', label: 'Sombra 3D do botão', fallback: '#b34700' },
];

function BannerColorPreview({
  data,
  pillText,
  title,
  subtitle,
  ctaText,
}: {
  data: Record<string, unknown>;
  pillText: string;
  title: string;
  subtitle: string;
  ctaText: string;
}) {
  return (
    <div
      className="overflow-hidden rounded-xl border p-4"
      style={{
        background: `linear-gradient(135deg, ${str(data.bg_color_start) || '#0f172a'}, ${str(data.bg_color_end) || '#1e1b4b'})`,
        borderColor: str(data.border_color) || 'rgba(99, 102, 241, 0.35)',
      }}
    >
      <span
        className="inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold"
        style={{
          background: str(data.pill_bg_color) || '#6366f1',
          color: str(data.pill_text_color) || '#ffffff',
        }}
      >
        {pillText || 'Badge'}
      </span>
      <p
        className="mt-2 text-sm font-bold"
        style={{ color: str(data.title_color) || '#ffffff' }}
      >
        {title || 'Prévia do título'}
      </p>
      <p
        className="mt-1 text-xs"
        style={{ color: str(data.subtitle_color) || 'rgba(255,255,255,0.78)' }}
      >
        {subtitle || 'Prévia do subtítulo'}
      </p>
      <button
        type="button"
        className="mt-3 rounded-lg px-3 py-1.5 text-xs font-bold"
        style={{
          background: str(data.button_bg_color) || '#FF6B00',
          color: str(data.button_text_color) || '#ffffff',
          boxShadow: `0 3px 0 ${str(data.button_shadow_color) || '#b34700'}`,
        }}
      >
        {ctaText || 'CTA'}
      </button>
    </div>
  );
}

export function CmsSiteForm() {
  const { token } = useHubSession();
  const [tab, setTab] = useState<TabId>('landing');
  const [configKey, setConfigKey] = useState<CmsSiteConfigKey>('default');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [okMsg, setOkMsg] = useState<string | null>(null);
  const [landing, setLanding] = useState<Record<string, unknown>>({});
  const [instructions, setInstructions] = useState('');

  /** Satélites /acesso (2 colunas) — distinto do Micro-CMS PanelDX (default). */
  const isAcessoSatellite =
    configKey === 'inove4us' || configKey === 'inove4us-school';
  const isSchool = configKey === 'inove4us-school';

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCmsSiteAdmin(token, configKey);
      setLanding(asRecord(data.landing_page_data));
      setInstructions(String(data.instructions_data || ''));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao carregar Micro-CMS');
    } finally {
      setLoading(false);
    }
  }, [token, configKey]);

  useEffect(() => {
    void load();
  }, [load]);

  function patchHeroCta(patch: Record<string, unknown>) {
    setLanding((prev) => {
      const heroCta = { ...asRecord(prev.hero_cta), ...patch };
      return { ...prev, hero_cta: heroCta, cta_consultor: {
        title: heroCta.title,
        button_text: heroCta.button_text,
        visible: heroCta.visible,
      } };
    });
  }

  function patchColuna1(patch: Record<string, unknown>) {
    setLanding((prev) => {
      const nextColuna1 = { ...asRecord(prev.coluna1), ...patch };
      const media = String(
        nextColuna1.image_path || nextColuna1.image_url || ''
      ).trim();
      nextColuna1.image_path = media;
      nextColuna1.image_url = media;
      const columns = Array.isArray(prev.columns) ? [...prev.columns] : [{}, {}, {}, {}];
      while (columns.length < 4) columns.push({});
      // Espelha coluna esquerda em columns[0] (School/inove4us leem coluna1 || columns[0]).
      columns[0] = {
        ...asRecord(columns[0]),
        visible: nextColuna1.visibility !== false,
        visibility: nextColuna1.visibility !== false,
        image_url: media,
        image_path: media,
        title: nextColuna1.title || '',
        description: nextColuna1.subtitle || '',
        subtitle: nextColuna1.subtitle || '',
        pill_text: nextColuna1.pill_text || '',
        badge_text: nextColuna1.pill_text || '',
        cta_text: nextColuna1.cta_text || '',
        cta_url: nextColuna1.cta_url || '',
        button_text: nextColuna1.cta_text || '',
        button_url: nextColuna1.cta_url || '',
        bg_color_start: nextColuna1.bg_color_start,
        bg_color_end: nextColuna1.bg_color_end,
        border_color: nextColuna1.border_color,
        title_color: nextColuna1.title_color,
        subtitle_color: nextColuna1.subtitle_color,
        pill_bg_color: nextColuna1.pill_bg_color,
        pill_text_color: nextColuna1.pill_text_color,
        accent_color: nextColuna1.accent_color,
        button_bg_color: nextColuna1.button_bg_color,
        button_text_color: nextColuna1.button_text_color,
        button_shadow_color: nextColuna1.button_shadow_color,
      };
      return { ...prev, coluna1: nextColuna1, columns };
    });
  }

  function patchColumn1(patch: Record<string, unknown>) {
    setLanding((prev) => {
      const columns = Array.isArray(prev.columns) ? [...prev.columns] : [{}, {}, {}, {}];
      while (columns.length < 4) columns.push({});
      columns[1] = { ...asRecord(columns[1]), ...patch };
      return { ...prev, columns };
    });
  }

  function patchInsight(index: number, patch: Record<string, unknown>) {
    setLanding((prev) => {
      const insights = Array.isArray(prev.insights) ? [...prev.insights] : [{}, {}, {}];
      while (insights.length < 3) insights.push({});
      insights[index] = { ...asRecord(insights[index]), ...patch };
      return { ...prev, insights };
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    setOkMsg(null);
    try {
      const saved = await saveCmsSiteAdmin(token, {
        config_key: configKey,
        landing_page_data: landing,
        instructions_data: instructions,
      });
      setLanding(asRecord(saved.landing_page_data));
      setInstructions(String(saved.instructions_data || ''));
      setOkMsg(
        isAcessoSatellite
          ? isSchool
            ? 'Micro-CMS School salvo — colunas de /acesso atualizadas.'
            : 'Micro-CMS inove4us salvo — colunas de /acesso atualizadas.'
          : 'Micro-CMS salvo no Action Hub.'
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao salvar');
    } finally {
      setSaving(false);
    }
  }

  const field =
    'w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-sm text-stone-800 outline-none ring-orange-400/30 transition focus:border-orange-400 focus:ring-2';

  const heroCta = asRecord(landing.hero_cta);
  const coluna1 = asRecord(landing.coluna1);
  const columns = Array.isArray(landing.columns) ? landing.columns : [];
  const col2 = asRecord(columns[1]);
  const insights = Array.isArray(landing.insights) ? landing.insights : [];
  const insightsSection = asRecord(landing.insights_section);
  const blogSync = asRecord(landing.blog_sync);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-stone-500">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Carregando estrutura do Micro-CMS…
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href="/dashboard/cms"
            className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold text-stone-500 hover:text-stone-800"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            Voltar aos posts
          </Link>
          <h1 className="text-xl font-bold text-stone-900">
            {isSchool
              ? 'Micro-CMS — inove4us School (/acesso)'
              : isAcessoSatellite
                ? 'Micro-CMS — inove4us (/acesso)'
                : 'Micro-CMS (estrutura PanelDX)'}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-stone-500">
            {isAcessoSatellite
              ? 'Colunas laterais da página de acesso do satélite. O satélite só lê — sem gestão local.'
              : 'Landing + instruções migradas para o Hub. O PanelDX continua ativo até autorização explícita de cutover.'}
          </p>
          <label className="mt-3 block max-w-sm space-y-1">
            <span className="text-xs font-semibold text-stone-500">Site / satélite</span>
            <select
              className={field}
              value={configKey}
              onChange={(e) => {
                setOkMsg(null);
                setConfigKey(e.target.value as CmsSiteConfigKey);
              }}
            >
              <option value="default">PanelDX (default)</option>
              <option value="inove4us">inove4us — página /acesso</option>
              <option value="inove4us-school">inove4us School — página /acesso</option>
            </select>
          </label>
        </div>
        <button
          type="submit"
          disabled={saving}
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

      <div className="flex gap-2 border-b border-stone-200">
        {(
          [
            ['landing', 'Página inicial'],
            ['instructions', 'Instruções'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`px-3 py-2 text-sm font-semibold transition ${
              tab === id
                ? 'border-b-2 border-orange-500 text-orange-700'
                : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {okMsg ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {okMsg}
        </div>
      ) : null}

      {tab === 'instructions' ? (
        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
            Conteúdo HTML (página de instruções)
          </span>
          <textarea
            className={`${field} min-h-[360px] font-mono text-xs leading-relaxed`}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
        </label>
      ) : (
        <div className="space-y-6">
          <section className="space-y-3 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-bold text-stone-900">Hero CTA</h2>
            <label className="flex items-center gap-2 text-sm text-stone-700">
              <input
                type="checkbox"
                checked={bool(heroCta.visible)}
                onChange={(e) => patchHeroCta({ visible: e.target.checked })}
              />
              Visível
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="block space-y-1">
                <span className="text-xs font-semibold text-stone-500">Badge</span>
                <input
                  className={field}
                  value={str(heroCta.badge_text)}
                  onChange={(e) => patchHeroCta({ badge_text: e.target.value })}
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-semibold text-stone-500">Botão — texto</span>
                <input
                  className={field}
                  value={str(heroCta.button_text)}
                  onChange={(e) => patchHeroCta({ button_text: e.target.value })}
                />
              </label>
              <label className="block space-y-1 md:col-span-2">
                <span className="text-xs font-semibold text-stone-500">Título</span>
                <input
                  className={field}
                  value={str(heroCta.title)}
                  onChange={(e) => patchHeroCta({ title: e.target.value })}
                />
              </label>
              <label className="block space-y-1 md:col-span-2">
                <span className="text-xs font-semibold text-stone-500">Subtítulo</span>
                <textarea
                  className={`${field} min-h-[72px]`}
                  value={str(heroCta.subtitle)}
                  onChange={(e) => patchHeroCta({ subtitle: e.target.value })}
                />
              </label>
              <label className="block space-y-1 md:col-span-2">
                <span className="text-xs font-semibold text-stone-500">URL do botão</span>
                <input
                  className={field}
                  value={str(heroCta.button_url)}
                  onChange={(e) => patchHeroCta({ button_url: e.target.value })}
                />
              </label>
              <div className="md:col-span-2">
                <CmsImageUploadField
                  label="Imagem do hero"
                  value={str(heroCta.image_url)}
                  onChange={(url) => patchHeroCta({ image_url: url })}
                  token={token}
                  preferPublicUrl={false}
                />
              </div>
            </div>

            <div className="space-y-3 border-t border-stone-100 pt-4">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <h3 className="text-sm font-bold text-stone-900">Cores do hero</h3>
                <p className="text-xs text-stone-500">
                  Gradiente, badge, tipografia e botão CTA do banner superior.
                </p>
              </div>
              <BannerColorPreview
                data={heroCta}
                pillText={str(heroCta.badge_text)}
                title={str(heroCta.title)}
                subtitle={str(heroCta.subtitle)}
                ctaText={str(heroCta.button_text)}
              />
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {HERO_CTA_COLOR_FIELDS.map((item) => (
                  <ColorField
                    key={item.key}
                    label={item.label}
                    value={heroCta[item.key]}
                    fallback={item.fallback}
                    allowRgba={item.allowRgba}
                    fieldClass={field}
                    onChange={(next) => patchHeroCta({ [item.key]: next })}
                  />
                ))}
              </div>
            </div>
          </section>

          <section className="space-y-3 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-bold text-stone-900">
              {isAcessoSatellite
                ? 'Coluna esquerda — conceito (/acesso)'
                : 'Coluna 1 — Mesa / banner'}
            </h2>
            <label className="flex items-center gap-2 text-sm text-stone-700">
              <input
                type="checkbox"
                checked={bool(coluna1.visibility)}
                onChange={(e) => patchColuna1({ visibility: e.target.checked })}
              />
              Visível
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="block space-y-1">
                <span className="text-xs font-semibold text-stone-500">Pill</span>
                <input
                  className={field}
                  value={str(coluna1.pill_text)}
                  onChange={(e) => patchColuna1({ pill_text: e.target.value })}
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-semibold text-stone-500">CTA — texto</span>
                <input
                  className={field}
                  value={str(coluna1.cta_text)}
                  onChange={(e) => patchColuna1({ cta_text: e.target.value })}
                />
              </label>
              <label className="block space-y-1 md:col-span-2">
                <span className="text-xs font-semibold text-stone-500">Título</span>
                <input
                  className={field}
                  value={str(coluna1.title)}
                  onChange={(e) => patchColuna1({ title: e.target.value })}
                />
              </label>
              <label className="block space-y-1 md:col-span-2">
                <span className="text-xs font-semibold text-stone-500">Subtítulo</span>
                <textarea
                  className={`${field} min-h-[72px]`}
                  value={str(coluna1.subtitle)}
                  onChange={(e) => patchColuna1({ subtitle: e.target.value })}
                />
              </label>
              <label className="block space-y-1 md:col-span-2">
                <span className="text-xs font-semibold text-stone-500">CTA — URL</span>
                <input
                  className={field}
                  value={str(coluna1.cta_url)}
                  onChange={(e) => patchColuna1({ cta_url: e.target.value })}
                />
              </label>
              <div className="md:col-span-2">
                <CmsImageUploadField
                  label="Imagem da coluna 1"
                  value={str(coluna1.image_path || coluna1.image_url)}
                  onChange={(url) =>
                    patchColuna1({ image_path: url, image_url: url })
                  }
                  token={token}
                  preferPublicUrl={isAcessoSatellite}
                  helpText={
                    isAcessoSatellite
                      ? 'URL pública do Hub (satélites leem em outra origem).'
                      : undefined
                  }
                />
              </div>
            </div>

            <div className="space-y-3 border-t border-stone-100 pt-4">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <h3 className="text-sm font-bold text-stone-900">Cores do banner</h3>
                <p className="text-xs text-stone-500">
                  Mesmos campos do Micro-CMS PanelDX (gradiente, pill, CTA, sombra).
                </p>
              </div>
              <BannerColorPreview
                data={coluna1}
                pillText={str(coluna1.pill_text)}
                title={str(coluna1.title)}
                subtitle={str(coluna1.subtitle)}
                ctaText={str(coluna1.cta_text)}
              />
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {COLUNA1_COLOR_FIELDS.map((item) => (
                  <ColorField
                    key={item.key}
                    label={item.label}
                    value={coluna1[item.key]}
                    fallback={item.fallback}
                    allowRgba={item.allowRgba}
                    fieldClass={field}
                    onChange={(next) => patchColuna1({ [item.key]: next })}
                  />
                ))}
              </div>
            </div>
          </section>

          <section className="space-y-3 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-bold text-stone-900">
              {isAcessoSatellite
                ? 'Coluna direita — como começar (/acesso)'
                : 'Coluna 2 — YouTube / metodologia'}
            </h2>
            <label className="flex items-center gap-2 text-sm text-stone-700">
              <input
                type="checkbox"
                checked={bool(col2.visible)}
                onChange={(e) => patchColumn1({ visible: e.target.checked })}
              />
              Visível
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              {isAcessoSatellite ? (
                <>
                  <label className="block space-y-1">
                    <span className="text-xs font-semibold text-stone-500">Pill</span>
                    <input
                      className={field}
                      value={str(col2.pill_text || col2.badge_text)}
                      onChange={(e) =>
                        patchColumn1({
                          pill_text: e.target.value,
                          badge_text: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-xs font-semibold text-stone-500">CTA — texto</span>
                    <input
                      className={field}
                      value={str(col2.cta_text || col2.button_text || col2.link_text)}
                      onChange={(e) =>
                        patchColumn1({
                          cta_text: e.target.value,
                          button_text: e.target.value,
                          link_text: e.target.value,
                        })
                      }
                    />
                  </label>
                </>
              ) : (
                <label className="block space-y-1 md:col-span-2">
                  <span className="text-xs font-semibold text-stone-500">URL do YouTube</span>
                  <input
                    className={field}
                    value={str(col2.video_url)}
                    onChange={(e) => patchColumn1({ video_url: e.target.value })}
                  />
                </label>
              )}
              <label className="block space-y-1 md:col-span-2">
                <span className="text-xs font-semibold text-stone-500">Título</span>
                <input
                  className={field}
                  value={str(col2.title)}
                  onChange={(e) => patchColumn1({ title: e.target.value })}
                />
              </label>
              <label className="block space-y-1 md:col-span-2">
                <span className="text-xs font-semibold text-stone-500">
                  {isAcessoSatellite ? 'Subtítulo / descrição' : 'Descrição'}
                </span>
                <textarea
                  className={`${field} min-h-[72px]`}
                  value={str(col2.description || col2.subtitle)}
                  onChange={(e) =>
                    patchColumn1({
                      description: e.target.value,
                      subtitle: e.target.value,
                    })
                  }
                />
              </label>
              {isAcessoSatellite ? (
                <>
                  <label className="block space-y-1 md:col-span-2">
                    <span className="text-xs font-semibold text-stone-500">CTA — URL</span>
                    <input
                      className={field}
                      value={str(col2.cta_url || col2.button_url || col2.link_url)}
                      onChange={(e) =>
                        patchColumn1({
                          cta_url: e.target.value,
                          button_url: e.target.value,
                          link_url: e.target.value,
                        })
                      }
                    />
                  </label>
                  <div className="md:col-span-2">
                    <CmsImageUploadField
                      label="Imagem da coluna direita"
                      value={str(col2.image_url || col2.image_path)}
                      onChange={(url) =>
                        patchColumn1({ image_url: url, image_path: url })
                      }
                      token={token}
                      preferPublicUrl={isAcessoSatellite}
                    />
                  </div>
                </>
              ) : null}
            </div>
            {isAcessoSatellite ? (
              <div className="space-y-3 border-t border-stone-100 pt-4">
                <div className="flex flex-wrap items-end justify-between gap-2">
                  <h3 className="text-sm font-bold text-stone-900">Cores da coluna</h3>
                  <p className="text-xs text-stone-500">
                    Gradiente, pill e CTA da coluna direita em /acesso.
                  </p>
                </div>
                <BannerColorPreview
                  data={col2}
                  pillText={str(col2.pill_text || col2.badge_text)}
                  title={str(col2.title)}
                  subtitle={str(col2.description || col2.subtitle)}
                  ctaText={str(col2.cta_text || col2.button_text)}
                />
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {COLUNA1_COLOR_FIELDS.map((item) => (
                    <ColorField
                      key={item.key}
                      label={item.label}
                      value={col2[item.key]}
                      fallback={item.fallback}
                      allowRgba={item.allowRgba}
                      fieldClass={field}
                      onChange={(next) => patchColumn1({ [item.key]: next })}
                    />
                  ))}
                </div>
              </div>
            ) : null}
          </section>

          {!isAcessoSatellite ? (
          <section className="space-y-3 rounded-2xl border border-orange-100 bg-orange-50/50 p-4 shadow-sm">
            <h2 className="text-sm font-bold text-stone-900">
              Destaques do blog (fixos — 3 cards)
            </h2>
            <p className="text-sm text-stone-600">
              Os três cards da segunda linha da home do PanelDX vêm sempre dos posts mais
              recentes de{' '}
              <a
                href="https://leaction.com.br/blog"
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-orange-700 underline-offset-2 hover:underline"
              >
                leaction.com.br/blog
              </a>
              . Não são editáveis aqui (regra fixa). O antigo card “Versão da aplicação”
              foi substituído pelo 3º destaque.
            </p>
            {str(blogSync.synced_at) ? (
              <p className="text-xs text-stone-500">
                Último sync: {str(blogSync.synced_at)} · {str(blogSync.posts_count) || '0'}{' '}
                post(s)
              </p>
            ) : null}
            <div className="grid gap-2 sm:grid-cols-3">
              {[2, 3, 4].map((idx) => {
                const item = asRecord(columns[idx]);
                return (
                  <div
                    key={idx}
                    className="rounded-xl border border-stone-200 bg-white p-3 text-xs text-stone-600"
                  >
                    <p className="font-bold text-stone-800">
                      #{idx - 1} {str(item.title) || '(aguardando sync)'}
                    </p>
                    <p className="mt-1 line-clamp-3">{str(item.description)}</p>
                  </div>
                );
              })}
            </div>
          </section>
          ) : null}

          <section className="space-y-3 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-bold text-stone-900">Insights (3 cards)</h2>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="block space-y-1">
                <span className="text-xs font-semibold text-stone-500">Seção — título</span>
                <input
                  className={field}
                  value={str(insightsSection.title)}
                  onChange={(e) =>
                    setLanding((prev) => ({
                      ...prev,
                      insights_section: {
                        ...asRecord(prev.insights_section),
                        title: e.target.value,
                      },
                    }))
                  }
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-semibold text-stone-500">Seção — subtítulo</span>
                <input
                  className={field}
                  value={str(insightsSection.subtitle)}
                  onChange={(e) =>
                    setLanding((prev) => ({
                      ...prev,
                      insights_section: {
                        ...asRecord(prev.insights_section),
                        subtitle: e.target.value,
                      },
                    }))
                  }
                />
              </label>
            </div>
            {[0, 1, 2].map((i) => {
              const item = asRecord(insights[i]);
              return (
                <div
                  key={i}
                  className="space-y-2 rounded-xl border border-stone-100 bg-stone-50/80 p-3"
                >
                  <p className="text-xs font-bold uppercase tracking-wider text-stone-400">
                    Insight {i + 1}
                  </p>
                  <input
                    className={field}
                    placeholder="Título"
                    value={str(item.title)}
                    onChange={(e) => patchInsight(i, { title: e.target.value })}
                  />
                  <textarea
                    className={`${field} min-h-[64px]`}
                    placeholder="Resumo"
                    value={str(item.summary)}
                    onChange={(e) => patchInsight(i, { summary: e.target.value })}
                  />
                  <div className="grid gap-2 md:grid-cols-2">
                    <input
                      className={field}
                      placeholder="URL"
                      value={str(item.link_url)}
                      onChange={(e) => patchInsight(i, { link_url: e.target.value })}
                    />
                    <input
                      className={field}
                      placeholder="Texto do link"
                      value={str(item.link_text)}
                      onChange={(e) => patchInsight(i, { link_text: e.target.value })}
                    />
                  </div>
                </div>
              );
            })}
          </section>
        </div>
      )}
    </form>
  );
}

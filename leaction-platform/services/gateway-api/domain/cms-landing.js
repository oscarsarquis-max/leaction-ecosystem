'use strict';

/**
 * Estrutura de landing do Micro-CMS PanelDX — portada para o Hub.
 * (Blog scrape runtime permanece no PanelDX até cutover autorizado.)
 */

function defaultColuna1() {
  return {
    visibility: true,
    pill_text: 'Mesa de Inovação',
    title: 'Leve sua escola ao próximo nível',
    subtitle: 'Transforme o plano gratuito em um Roadmap executável',
    cta_text: 'Conhecer a Mesa',
    cta_url: '',
    image_path: '',
    bg_color_start: '#0b0c10',
    bg_color_end: '#1a0b2e',
    border_color: 'rgba(0, 191, 255, 0.2)',
    title_color: '#ffffff',
    subtitle_color: 'rgba(255, 255, 255, 0.82)',
    pill_bg_color: '#FF6B00',
    pill_text_color: '#ffffff',
    accent_color: '#FF6B00',
    button_bg_color: '#FF6B00',
    button_text_color: '#ffffff',
    button_shadow_color: '#b34700',
  };
}

function defaultHeroCta() {
  return {
    visible: true,
    badge_text: 'Novo Agent IA',
    title: 'Descubra como resolver seu maior desafio de gestão em segundos.',
    subtitle:
      'Consultor IA 100% Gratuito — cruzamos seu desafio com o framework LeAction em segundos.',
    button_text: 'Falar com Consultor IA',
    button_url: '/consultor-leaction',
    image_url: '',
    // Cores do banner (mesmo conjunto da Coluna 1 / Mesa)
    bg_color_start: '#0f172a',
    bg_color_end: '#1e1b4b',
    border_color: 'rgba(99, 102, 241, 0.35)',
    title_color: '#ffffff',
    subtitle_color: 'rgba(255, 255, 255, 0.78)',
    pill_bg_color: '#6366f1',
    pill_text_color: '#ffffff',
    accent_color: '#FF6B00',
    button_bg_color: '#FF6B00',
    button_text_color: '#ffffff',
    button_shadow_color: '#b34700',
  };
}

const HERO_CTA_COLOR_KEYS = [
  'bg_color_start',
  'bg_color_end',
  'border_color',
  'title_color',
  'subtitle_color',
  'pill_bg_color',
  'pill_text_color',
  'accent_color',
  'button_bg_color',
  'button_text_color',
  'button_shadow_color',
];

function defaultAppVersion() {
  return {
    version_label: 'v1.0',
    image_url: '',
    title: 'Versão da aplicação',
    summary: 'Notas e detalhes da versão atual do PanelDX.',
    link_text: 'Ver detalhes',
    details_html: '',
  };
}

function defaultCmsLanding() {
  return {
    hero: {
      leaction_title: 'LeAction System',
      paneldx_title: 'PanelDX',
      subtitle: 'Transformação Digital Educacional DX',
      description:
        'Inteligência, metodologia e execução para escolas e redes de ensino.',
    },
    columns: [
      {
        image_url: '',
        title: 'Leve sua escola ao próximo nível',
        description: 'Transforme o plano gratuito em um Roadmap executável',
        visible: true,
        layout: 'premium_banner',
      },
      {
        video_url: '',
        image_url: '',
        title: 'Metodologia CTDI',
        description:
          'Framework integrado para diagnóstico, planejamento e execução da transformação digital educacional.',
        visible: true,
      },
      {
        image_url: '',
        title: '',
        description: '',
        link_url: '',
        link_text: 'Leia mais →',
        source: 'blog',
      },
      {
        image_url: '',
        title: '',
        description: '',
        link_url: '',
        link_text: 'Leia mais →',
        source: 'blog',
      },
      {
        image_url: '',
        title: '',
        description: '',
        link_url: '',
        link_text: 'Leia mais →',
        source: 'blog',
      },
    ],
    // Mantido por compatibilidade; a home usa o 3º destaque do blog no lugar deste card.
    app_version: defaultAppVersion(),
    hero_cta: defaultHeroCta(),
    coluna1: defaultColuna1(),
    cta_consultor: {
      title: 'Descubra como resolver seu maior desafio de gestão em segundos.',
      button_text: 'Falar com Consultor IA (Gratuito)',
      visible: true,
    },
    insights_section: {
      title: 'Insights e Casos de Uso',
      subtitle:
        'Conteúdo estratégico para gestores e tomadores de decisão na educação digital.',
    },
    insights: [
      {
        title: 'Diagnóstico As-Is gratuito',
        summary:
          'Avalie a maturidade tecnológica da sua instituição com o framework LeAction e receba um roadmap inicial.',
        link_url: '/cadastro',
        link_text: 'Iniciar diagnóstico →',
      },
      {
        title: 'Framework LeAction F na prática',
        summary:
          'Conheça como as 105 competências do framework orientam a transformação digital centrada no aluno.',
        link_url: 'https://leactionf.com.br/index.html',
        link_text: 'Explorar o framework →',
      },
      {
        title: 'Agilidade na gestão educacional',
        summary:
          'Metodologia CTDI: ciclos iterativos para alinhar diretoria, pedagogia e tecnologia na rede de ensino.',
        link_url: 'https://leaction.com.br/blog',
        link_text: 'Ler no blog LeAction →',
      },
    ],
  };
}

function defaultCmsInstructions() {
  return (
    '<h2>Guia Rápido: Diagnóstico de Maturidade Digital</h2>' +
    '<p>A <strong>Transformação Digital</strong> é um imperativo no setor educacional. ' +
    'A <strong>Avaliação de Maturidade LeAction</strong> oferece um diagnóstico preciso ' +
    'da situação atual de sua organização.</p>' +
    '<h3>1. Oportunidade e Estratégia</h3>' +
    '<p>Use o framework LeActionF como espinha dorsal do processo.</p>' +
    '<h3>2. Sobre a Avaliação</h3>' +
    '<ul><li><strong>90 questões</strong> estratégicas (escala 1 a 5)</li>' +
    '<li>Respostas completas são essenciais para a precisão do diagnóstico</li></ul>' +
    '<h3>3. Fluxo de Acesso</h3>' +
    '<ol><li>Cadastre-se em <strong>Iniciar Diagnóstico</strong></li>' +
    '<li>Aceite o Termo de Privacidade</li><li>Obtenha o código por e-mail</li>' +
    '<li>Faça login e preencha o questionário</li><li>Exporte o relatório em PDF</li></ol>' +
    '<p><strong>Suporte:</strong> ' +
    '<a href="mailto:conhecer@leaction.com.br">conhecer@leaction.com.br</a></p>'
  );
}

function coerceVisible(value, defaultValue = true) {
  if (value == null) return defaultValue;
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return Boolean(value);
  const normalized = String(value).trim().toLowerCase();
  if (['false', '0', 'nao', 'não', 'no', 'oculto', 'hidden', 'off'].includes(normalized)) {
    return false;
  }
  if (['true', '1', 'sim', 'yes', 'visivel', 'visível', 'on'].includes(normalized)) {
    return true;
  }
  return defaultValue;
}

function coerceColor(value, fallback) {
  const s = String(value || '').trim();
  if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(s)) return s;
  if (/^rgba?\([^)]+\)$/i.test(s)) return s;
  return fallback;
}

function normalizeColuna1(landing) {
  const defaults = defaultColuna1();
  if (!landing || typeof landing !== 'object') return { ...defaults };

  const raw = landing.coluna1 && typeof landing.coluna1 === 'object' ? landing.coluna1 : {};
  let legacy = {};
  if (Array.isArray(landing.columns) && landing.columns[0] && typeof landing.columns[0] === 'object') {
    legacy = landing.columns[0];
  }
  const merged = { ...defaults, ...legacy, ...raw };

  if (legacy.title && !raw.title) merged.title = legacy.title;
  if (legacy.description && !raw.subtitle) merged.subtitle = legacy.description;
  if (legacy.image_url && !raw.image_path) merged.image_path = legacy.image_url;

  let visSrc = raw.visibility;
  if (visSrc == null && raw.visible != null) visSrc = raw.visible;
  if (visSrc == null && legacy.visible != null) visSrc = legacy.visible;
  merged.visibility = coerceVisible(visSrc, true);

  merged.pill_text = String(merged.pill_text || merged.badge_text || defaults.pill_text).trim() || defaults.pill_text;
  merged.title = String(merged.title || defaults.title).trim() || defaults.title;
  merged.subtitle = String(merged.subtitle || merged.description || defaults.subtitle).trim();
  merged.cta_text = String(merged.cta_text || merged.button_text || defaults.cta_text).trim() || defaults.cta_text;
  merged.cta_url = String(merged.cta_url || merged.button_url || '').trim();
  merged.image_path = String(merged.image_path || merged.image_url || defaults.image_path).trim();

  for (const key of [
    'bg_color_start',
    'bg_color_end',
    'border_color',
    'title_color',
    'subtitle_color',
    'pill_bg_color',
    'pill_text_color',
    'accent_color',
    'button_bg_color',
    'button_text_color',
    'button_shadow_color',
  ]) {
    merged[key] = coerceColor(merged[key], defaults[key]);
  }
  return merged;
}

function coluna1ToColumnSlot(coluna1) {
  return {
    visible: coluna1.visibility !== false,
    visibility: coluna1.visibility !== false,
    image_url: coluna1.image_path || '',
    image_path: coluna1.image_path || '',
    title: coluna1.title || '',
    description: coluna1.subtitle || '',
    subtitle: coluna1.subtitle || '',
    pill_text: coluna1.pill_text || '',
    badge_text: coluna1.pill_text || '',
    cta_text: coluna1.cta_text || '',
    cta_url: coluna1.cta_url || '',
    button_text: coluna1.cta_text || '',
    button_url: coluna1.cta_url || '',
    layout: 'premium_banner',
    bg_color_start: coluna1.bg_color_start,
    bg_color_end: coluna1.bg_color_end,
    border_color: coluna1.border_color,
    title_color: coluna1.title_color,
    subtitle_color: coluna1.subtitle_color,
    pill_bg_color: coluna1.pill_bg_color,
    pill_text_color: coluna1.pill_text_color,
    accent_color: coluna1.accent_color,
    button_bg_color: coluna1.button_bg_color,
    button_text_color: coluna1.button_text_color,
    button_shadow_color: coluna1.button_shadow_color,
  };
}

function normalizeHeroCta(landing) {
  const defaults = defaultHeroCta();
  const legacy =
    landing && typeof landing.cta_consultor === 'object' ? landing.cta_consultor : {};
  const raw = landing && typeof landing.hero_cta === 'object' ? landing.hero_cta : {};
  const merged = { ...defaults, ...legacy, ...raw };
  if (legacy.title && !raw.title) merged.title = legacy.title;
  if (legacy.button_text && !raw.button_text) merged.button_text = legacy.button_text;
  merged.visible = coerceVisible(
    raw.visible != null ? raw.visible : legacy.visible != null ? legacy.visible : merged.visible,
    true
  );
  merged.button_url = String(merged.button_url || '/consultor-leaction').trim() || '/consultor-leaction';
  merged.image_url = String(merged.image_url || '').trim();
  merged.badge_text = String(merged.badge_text || defaults.badge_text).trim() || defaults.badge_text;
  for (const key of HERO_CTA_COLOR_KEYS) {
    merged[key] = coerceColor(merged[key], defaults[key]);
  }
  return merged;
}

function normalizeInsights(insights, defaults) {
  const baseDefaults = Array.isArray(defaults) ? defaults : defaultCmsLanding().insights;
  const result = [];
  for (let i = 0; i < 3; i += 1) {
    const base = baseDefaults[i] && typeof baseDefaults[i] === 'object' ? baseDefaults[i] : {};
    const stored =
      Array.isArray(insights) && insights[i] && typeof insights[i] === 'object' ? insights[i] : {};
    const merged = { ...base, ...stored };
    result.push({
      title: String(merged.title || '').trim(),
      summary: String(merged.summary || '').trim(),
      link_url: String(merged.link_url || '').trim(),
      link_text: String(merged.link_text || 'Leia mais →').trim(),
    });
  }
  return result;
}

function normalizeCmsLanding(landing) {
  const defaults = defaultCmsLanding();
  if (!landing || typeof landing !== 'object') return defaults;

  const hero = { ...defaults.hero, ...(landing.hero || {}) };
  const heroCta = normalizeHeroCta(landing);
  const coluna1 = normalizeColuna1(landing);
  const appVersion = { ...defaults.app_version, ...(landing.app_version || {}) };
  const insightsSection = {
    ...defaults.insights_section,
    ...(landing.insights_section || {}),
  };
  const insights = normalizeInsights(landing.insights, defaults.insights);

  const storedCols = Array.isArray(landing.columns) ? landing.columns : [];
  const defaultCols = defaults.columns || [];
  const columns = [];
  for (let i = 0; i < defaultCols.length; i += 1) {
    // Slots 2–4: preenchidos em runtime pelo sync do blog (não editáveis).
    if (i >= 2) {
      columns.push({ ...defaultCols[i] });
      continue;
    }
    if (i === 0) {
      columns.push(coluna1ToColumnSlot(coluna1));
      continue;
    }
    const stored =
      i < storedCols.length && storedCols[i] && typeof storedCols[i] === 'object'
        ? storedCols[i]
        : {};
    const merged = { ...defaultCols[i], ...stored };
    for (const [key, defaultVal] of Object.entries(defaultCols[i])) {
      if (key === 'visible') continue;
      if (!String(merged[key] || '').trim()) merged[key] = defaultVal;
    }
    merged.visible = coerceVisible(
      stored.visible != null ? stored.visible : merged.visible,
      defaultCols[i].visible !== false
    );
    columns.push(merged);
  }

  return {
    hero,
    columns,
    coluna1,
    app_version: appVersion,
    hero_cta: heroCta,
    cta_consultor: {
      title: heroCta.title,
      button_text: heroCta.button_text,
      visible: heroCta.visible,
    },
    insights_section: insightsSection,
    insights,
  };
}

function serializeCmsRow(row) {
  if (!row) {
    return {
      landing_page_data: normalizeCmsLanding(defaultCmsLanding()),
      instructions_data: defaultCmsInstructions(),
      updated_at: null,
    };
  }
  let landing = row.landing_page_data || {};
  if (typeof landing === 'string') {
    try {
      landing = JSON.parse(landing);
    } catch {
      landing = defaultCmsLanding();
    }
  }
  if (!landing || typeof landing !== 'object') landing = defaultCmsLanding();
  landing = normalizeCmsLanding(landing);
  const updated = row.updated_at;
  return {
    landing_page_data: landing,
    instructions_data: row.instructions_data || defaultCmsInstructions(),
    updated_at:
      updated && typeof updated.toISOString === 'function'
        ? updated.toISOString()
        : updated || null,
  };
}

module.exports = {
  defaultCmsLanding,
  defaultCmsInstructions,
  normalizeCmsLanding,
  serializeCmsRow,
};

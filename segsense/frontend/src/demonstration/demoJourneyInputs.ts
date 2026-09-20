export const FAMILY_SOURCE_PATH = '/demonstracao/fontes/continuidade-familiar';
export const INCOME_SOURCE_PATH = '/demonstracao/fontes/interrupcao-renda';
export const FIRES_SOURCE_PATH = '/demonstracao/fontes/proximidade-incendios';
export const REVOKED_SOURCE_PATH = '/demonstracao/fontes/revogada';

export function governedSourceUrl(path: string): string {
  return `${window.location.origin}${path}`;
}

export const FAMILY_SOURCE_URL = governedSourceUrl(FAMILY_SOURCE_PATH);
export const INCOME_SOURCE_URL = governedSourceUrl(INCOME_SOURCE_PATH);
export const FIRES_SOURCE_URL = governedSourceUrl(FIRES_SOURCE_PATH);
export const REVOKED_SOURCE_URL = governedSourceUrl(REVOKED_SOURCE_PATH);

export const INTENT_UNDERSTAND = 'UNDERSTAND_PROTECTION_OPTIONS';
export const INTENT_COMPARE = 'COMPARE_COVERAGE_GAPS';
export const INTENT_HOME = 'SIMULATE_HOME_QUOTE';
export const INTENT_EFFECTIVE = 'REQUEST_EFFECTIVE_CONTRACT';
export const INTENT_UNRECOGNIZED = 'UNRECOGNIZED';

const THEME_LABELS: Record<string, string> = {
  family_continuity: 'continuidade familiar',
  income_interruption: 'interrupção de renda',
  nearby_fires: 'incêndios próximos (editorial, não prova de risco do imóvel)',
  home_protection: 'proteção residencial declarada',
  crop_production_loss: 'quebra de safra',
};

const CAPTURE_FIELD_LABELS: Record<string, string> = {
  theme: 'Tema',
  event: 'Evento',
  crop: 'Cultura',
  region: 'Região',
  period: 'Período',
};

const PUBLIC_CAPTURE_KEYS = new Set(Object.keys(CAPTURE_FIELD_LABELS));

const ELEMENT_LABELS: Record<string, string> = {
  dependents_need_continuity: 'dependentes precisam de continuidade',
  income_gap_if_work_stops: 'a renda pode parar se o trabalho parar',
  nearby_fires_hypothetical_region: 'incêndios próximos de uma região hipotética',
  understand_options: 'entender opções',
  compare_gaps: 'comparar lacunas',
  simulate_home_quote: 'avaliar proteção residencial em simulação',
  years: 'horizonte em anos',
  months: 'horizonte em meses',
  no_quote: 'sem cotação nesta fatia',
  editorial_not_risk: 'fonte editorial, não prova de risco do imóvel',
  crop_failure: 'quebra de safra',
  crop_failure_reported: 'relato de quebra de safra na página',
  editorial_not_eligibility: 'não é elegibilidade nem prova de que a pessoa sofreu a perda',
};

export function humanThemeLabel(theme: string | null | undefined): string | null {
  if (!theme) {
    return null;
  }
  if (theme === 'conflict') {
    return 'mais de um tema';
  }
  return THEME_LABELS[theme] ?? null;
}

export function humanElementLabel(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  return ELEMENT_LABELS[value] ?? null;
}

export function isPublicCaptureElement(key: string | null | undefined): boolean {
  return Boolean(key && PUBLIC_CAPTURE_KEYS.has(key));
}

export function humanCaptureFieldLabel(key: string | null | undefined): string | null {
  if (!key) {
    return null;
  }
  return CAPTURE_FIELD_LABELS[key] ?? null;
}

export function humanCaptureValueLabel(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  return THEME_LABELS[value] ?? ELEMENT_LABELS[value] ?? value;
}

export function classifyIntention(text: string): string {
  const normalized = text.toLowerCase();
  if (!normalized.trim()) {
    return INTENT_UNRECOGNIZED;
  }
  if (
    containsAny(normalized, [
      'emitir apólice',
      'emitir apolice',
      'pagar agora',
      'assinar contrato',
      'contratação efetiva',
      'contratacao efetiva',
      'proposta vinculante',
      'cotação vinculante',
      'cotacao vinculante',
    ])
  ) {
    return INTENT_EFFECTIVE;
  }
  if (containsAny(normalized, ['comparar lacunas', 'comparar cobertura', 'lacunas ilustrativas'])) {
    return INTENT_COMPARE;
  }
  if (
    containsAny(normalized, [
      'seguro residencial',
      'proteção residencial',
      'protecao residencial',
      'proteger a casa',
      'proteger o imóvel',
      'proteger o imovel',
      'cotar residencial',
      'contratar um seguro residencial',
      'contratar seguro residencial',
    ])
  ) {
    return INTENT_HOME;
  }
  if (
    containsAny(normalized, [
      'entender opções',
      'entender opcoes',
      'opções ilustrativas',
      'opcoes ilustrativas',
      'opções de proteção para perda',
      'opcoes de protecao para perda',
      'perda de produção',
      'perda de producao',
    ])
  ) {
    return INTENT_UNDERSTAND;
  }
  return INTENT_UNRECOGNIZED;
}

export function intentionInterpretation(code: string): string {
  if (code === INTENT_HOME) {
    return 'Entendi que você quer avaliar uma proteção residencial.';
  }
  if (code === INTENT_UNDERSTAND) {
    return 'Entendi que você quer entender opções ilustrativas de proteção.';
  }
  if (code === INTENT_COMPARE) {
    return 'Entendi que você quer comparar opções ilustrativas deste contexto.';
  }
  if (code === INTENT_EFFECTIVE) {
    return 'Contratar de verdade depende de seguradora e produto autorizados. Esta fatia só simula.';
  }
  return 'Não reconheci o que você deseja. Diga, por exemplo, que quer avaliar uma proteção residencial.';
}

export function humanIntentionLabel(code: string | null | undefined): string | null {
  if (code === INTENT_UNDERSTAND) {
    return 'entender opções ilustrativas de proteção';
  }
  if (code === INTENT_COMPARE) {
    return 'comparar opções ilustrativas deste contexto';
  }
  if (code === INTENT_HOME) {
    return 'avaliar uma proteção residencial em simulação';
  }
  if (code === INTENT_EFFECTIVE) {
    return 'contratação efetiva (bloqueada nesta fatia)';
  }
  return null;
}

export function declaredThemeFromText(
  text: string,
): 'family_continuity' | 'income_interruption' | 'nearby_fires' | 'conflict' | null {
  const normalized = text.toLowerCase();
  const family =
    normalized.includes('continuidade familiar') ||
    normalized.includes('dependentes') ||
    normalized.includes('família') ||
    normalized.includes('familia');
  const income =
    normalized.includes('interrupção de renda') ||
    normalized.includes('interrupcao de renda') ||
    normalized.includes('parar de trabalhar') ||
    normalized.includes('renda do trabalho');
  const fires =
    normalized.includes('incêndios nas proximidades') ||
    normalized.includes('incendios nas proximidades') ||
    normalized.includes('incêndios próximos') ||
    normalized.includes('incendios proximos') ||
    normalized.includes('incêndios perto') ||
    normalized.includes('houve incêndios') ||
    normalized.includes('houve incendios');
  if ((family && income) || (family && fires) || (income && fires)) {
    return 'conflict';
  }
  if (family) {
    return 'family_continuity';
  }
  if (income) {
    return 'income_interruption';
  }
  if (fires) {
    return 'nearby_fires';
  }
  return null;
}

function containsAny(haystack: string, needles: string[]): boolean {
  return needles.some((needle) => haystack.includes(needle));
}

export function reaisToCents(reais: string): string | undefined {
  const normalized = reais.replace(/\s/g, '').replace(/\./g, '').replace(',', '.');
  if (!normalized) {
    return undefined;
  }
  const amount = Number(normalized);
  if (!Number.isFinite(amount) || amount <= 0) {
    return undefined;
  }
  return String(Math.round(amount * 100));
}

export function centsToReais(cents: number): string {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100);
}

export function dwellingTypeLabel(code: string | null | undefined): string | null {
  if (code === 'APARTMENT') {
    return 'apartamento';
  }
  if (code === 'HOUSE') {
    return 'casa';
  }
  return null;
}

export function publicQuoteExplanation(quote: {
  premiumAnnualCents?: number;
  insuredAmountCents?: number;
  coverPeriodMonths?: number;
  dwellingType?: string;
}): string | null {
  if (
    quote.premiumAnnualCents == null ||
    quote.insuredAmountCents == null ||
    quote.coverPeriodMonths == null
  ) {
    return null;
  }
  const dwelling = dwellingTypeLabel(quote.dwellingType);
  if (!dwelling) {
    return null;
  }
  return (
    `O simulador considerou o valor de proteção de ${centsToReais(quote.insuredAmountCents)}, o tipo de imóvel ${dwelling} e o período de ${String(quote.coverPeriodMonths)} meses. ` +
    `Aplicou a regra demonstrativa vigente para esse cenário e calculou um prêmio anual simulado de ${centsToReais(quote.premiumAnnualCents)}.`
  );
}

type SpeechCtor = new () => {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

export function speechRecognitionCtor(): SpeechCtor | null {
  const speechWindow = window as unknown as {
    SpeechRecognition?: SpeechCtor;
    webkitSpeechRecognition?: SpeechCtor;
  };
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

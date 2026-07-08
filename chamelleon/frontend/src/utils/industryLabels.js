/**
 * Rótulos dinâmicos por setor (industry_type).
 * Garante aderência semântica da UI ao negócio de cada tenant/unidade.
 */

const DEFAULT_LABELS = Object.freeze({
  unit: 'Unidade Operacional',
  unitPlural: 'Unidades Operacionais',
  manager: 'Gestor Responsável',
  unitArticle: 'a',
  nameColumn: 'Nome da Unidade',
  selectPrompt: 'Selecione a Unidade Operacional',
});

const INDUSTRY_LABELS = Object.freeze({
  Construcao: {
    unit: 'Canteiro',
    unitPlural: 'Canteiros',
    manager: 'Engenheiro/Mestre',
    unitArticle: 'o',
    nameColumn: 'Nome do Canteiro',
    selectPrompt: 'Selecione o Canteiro',
  },
  Varejo: {
    unit: 'Loja',
    unitPlural: 'Lojas',
    manager: 'Gerente de Loja',
    unitArticle: 'a',
    nameColumn: 'Nome da Loja',
    selectPrompt: 'Selecione a Loja',
  },
  TI: {
    unit: 'Projeto/Squad',
    unitPlural: 'Projetos/Squads',
    manager: 'Tech Lead',
    unitArticle: 'o',
    nameColumn: 'Nome do Projeto/Squad',
    selectPrompt: 'Selecione o Projeto/Squad',
  },
  Telecom: {
    unit: 'Site/Área',
    unitPlural: 'Sites/Áreas',
    manager: 'Coordenador de Campo',
    unitArticle: 'o',
    nameColumn: 'Nome do Site/Área',
    selectPrompt: 'Selecione o Site/Área',
  },
  Industrial: {
    unit: 'Planta',
    unitPlural: 'Plantas',
    manager: 'Supervisor de Produção',
    unitArticle: 'a',
    nameColumn: 'Nome da Planta',
    selectPrompt: 'Selecione a Planta',
  },
  Educacao: {
    unit: 'Unidade Escolar',
    unitPlural: 'Unidades Escolares',
    manager: 'Coordenador Pedagógico',
    unitArticle: 'a',
    nameColumn: 'Nome da Unidade Escolar',
    selectPrompt: 'Selecione a Unidade Escolar',
  },
  Saude: {
    unit: 'Unidade de Saúde',
    unitPlural: 'Unidades de Saúde',
    manager: 'Responsável Técnico',
    unitArticle: 'a',
    nameColumn: 'Nome da Unidade de Saúde',
    selectPrompt: 'Selecione a Unidade de Saúde',
  },
});

/** Opções amigáveis para o select de industry_type no cadastro. */
export const INDUSTRY_TYPE_OPTIONS = [
  { value: 'Construcao', label: 'Construção Civil' },
  { value: 'Varejo', label: 'Varejo' },
  { value: 'TI', label: 'TI / Software' },
  { value: 'Telecom', label: 'Telecomunicações' },
  { value: 'Industrial', label: 'Industrial' },
  { value: 'Educacao', label: 'Educação' },
  { value: 'Saude', label: 'Saúde' },
  { value: 'Outro', label: 'Outro / Genérico' },
];

/**
 * @param {string | null | undefined} industryType
 * @returns {{
 *   unit: string,
 *   unitPlural: string,
 *   manager: string,
 *   unitArticle: string,
 *   nameColumn: string,
 *   selectPrompt: string,
 * }}
 */
export function getIndustryLabels(industryType) {
  if (!industryType) return { ...DEFAULT_LABELS };

  const key = String(industryType).trim();
  const exact = INDUSTRY_LABELS[key];
  if (exact) return { ...exact };

  // Prefixos legados (ex.: "construcao-civil", "Construcao Civil")
  const lower = key.toLowerCase();
  if (lower.startsWith('constr')) return { ...INDUSTRY_LABELS.Construcao };
  if (lower.startsWith('varejo') || lower.startsWith('retail')) return { ...INDUSTRY_LABELS.Varejo };
  if (lower === 'ti' || lower.includes('software') || lower.includes('tech')) {
    return { ...INDUSTRY_LABELS.TI };
  }

  return { ...DEFAULT_LABELS };
}

/**
 * Resolve rótulos a partir de uma lista de sites (consenso ou default).
 * Se todos tiverem o mesmo industry_type, usa esse; senão default.
 */
export function getLabelsFromSites(sites = []) {
  const types = [...new Set((sites || []).map((s) => s?.industry_type).filter(Boolean))];
  if (types.length === 1) return getIndustryLabels(types[0]);
  return getIndustryLabels(null);
}

/**
 * Frase "Selecione a(o) {unit}" com artigo correto.
 */
export function selectUnitPrompt(industryType) {
  const labels = getIndustryLabels(industryType);
  return labels.selectPrompt || `Selecione ${labels.unitArticle} ${labels.unit}`;
}

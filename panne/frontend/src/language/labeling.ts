/** Catálogos humanos de rotulagem / conformidade (R026-004). */

export const DOSSIER_STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  evaluated: "Avaliado",
  reviewed: "Revisado",
  invalidated: "Invalidado",
};

export const COMPLETENESS_LABEL: Record<string, string> = {
  complete: "Completo",
  incomplete: "Incompleto",
  partial: "Parcial",
  unknown: "Indeterminado",
};

export const NUTRIENT_LABEL: Record<string, string> = {
  energy_kcal: "Valor energético",
  energy_kj: "Valor energético (kJ)",
  carbohydrate: "Carboidratos",
  total_sugars: "Açúcares totais",
  added_sugars: "Açúcares adicionados",
  total_fat: "Gorduras totais",
  saturated_fat: "Gorduras saturadas",
  trans_fat: "Gorduras trans",
  protein: "Proteínas",
  fiber: "Fibra alimentar",
  sodium: "Sódio",
  salt: "Sal",
};

export const EVIDENCE_RESULT_LABEL: Record<string, string> = {
  pass: "Atendido",
  fail: "Não atendido",
  warn: "Atenção",
  insufficient_context: "Contexto insuficiente",
  insufficient_evidence: "Evidência insuficiente",
  manual_review_required: "Revisão humana necessária",
  not_applicable: "Não aplicável",
  unknown: "Indeterminado",
  may_contain: "Possível presença de alergênicos",
};

/** Canais de venda admitidos no perfil (contrato Text / testes / demo). */
export const SALES_CHANNEL_LABEL: Record<string, string> = {
  retail: "Varejo",
  own_store: "Loja própria",
  food_service: "Serviço de alimentação",
  wholesale: "Atacado",
  e_commerce: "Comércio eletrônico",
  online: "Venda online",
  other: "Outro canal",
};

/**
 * Estados físicos usados na aplicabilidade da lupa (solid/semisolid) e demais
 * valores comuns do domínio alimentar — contrato Text é string livre.
 */
export const PHYSICAL_STATE_LABEL: Record<string, string> = {
  solid: "Sólido",
  semisolid: "Semissólido",
  liquid: "Líquido",
  powder: "Pó",
  gas: "Gasoso",
  other: "Outro estado físico",
};

/** Categorias do catálogo de porção (IN 75 / panificação). */
export const REGULATORY_CATEGORY_LABEL: Record<string, string> = {
  pao: "Pães",
  bolo: "Bolos e similares",
  biscoito: "Biscoitos e cookies",
  massa: "Massas e similares",
};

export const FINDING_RULE_LABEL: Record<string, string> = {
  applicability_complete: "Completude de aplicabilidade",
  fop_scope: "Escopo da lupa frontal",
  fop_added_sugars: "Lupa — açúcares adicionados",
  fop_saturated_fat: "Lupa — gordura saturada",
  fop_sodium: "Lupa — sódio",
  gluten_contains: "Glúten — contém",
  gluten_may_contain: "Glúten — pode conter",
  gluten_unknown: "Glúten — declaração pendente",
  may_contain: "Possível presença de alergênicos",
  lactose: "Lactose — evidência insuficiente",
  mandatory_advertencias: "Advertências obrigatórias",
  mandatory_origem: "Origem obrigatória",
  mandatory_registro: "Registro obrigatório",
  mandatory_denomination: "Denominação de venda",
  mandatory_ingredients: "Lista de ingredientes",
  mandatory_lote: "Lote obrigatório",
  mandatory_prazo_validade: "Prazo de validade obrigatório",
  mandatory_conservacao: "Conservação obrigatória",
  mandatory_preparo: "Instruções de preparo obrigatórias",
  mandatory_identificacao_responsavel: "Identificação do responsável obrigatória",
  nutrition_table: "Tabela nutricional",
  nutrient_energy_kcal: "Valor energético obrigatório",
  nutrient_energy_kj: "Valor energético (kJ) obrigatório",
  nutrient_carbohydrate: "Carboidratos obrigatórios",
  nutrient_total_sugars: "Açúcares totais obrigatórios",
  nutrient_added_sugars: "Açúcares adicionados obrigatórios",
  nutrient_total_fat: "Gorduras totais obrigatórias",
  nutrient_saturated_fat: "Gorduras saturadas obrigatórias",
  nutrient_trans_fat: "Gorduras trans obrigatórias",
  nutrient_protein: "Proteínas obrigatórias",
  nutrient_fiber: "Fibra alimentar obrigatória",
  nutrient_sodium: "Sódio obrigatório",
  nutrient_salt: "Sal obrigatório",
};

export const MANDATORY_CODE_LABEL: Record<string, string> = {
  mandatory_advertencias: "Advertências",
  mandatory_origem: "Origem",
  mandatory_registro: "Registro",
  mandatory_denomination: "Denominação de venda",
  mandatory_ingredients: "Lista de ingredientes",
  mandatory_lote: "Lote",
  mandatory_prazo_validade: "Prazo de validade",
  mandatory_conservacao: "Conservação",
  mandatory_preparo: "Instruções de preparo",
  mandatory_identificacao_responsavel: "Identificação do responsável",
  mandatory_conteudo_liquido: "Conteúdo líquido",
  advertencias: "Advertências",
  origem: "Origem",
  registro: "Registro",
  lote: "Lote",
  prazo_validade: "Prazo de validade",
  conservacao: "Conservação",
  preparo: "Instruções de preparo",
  identificacao_responsavel: "Identificação do responsável",
  conteudo_liquido: "Conteúdo líquido",
};

/** Fallback de proteção — não deve aparecer para códigos do cenário demo. */
export const UNCATALOGED_RULE_LABEL = "Regra ainda não catalogada";
export const UNCATALOGED_OPTION_LABEL = "Opção ainda não catalogada";
/** @deprecated Preferir UNCATALOGED_RULE_LABEL / UNCATALOGED_OPTION_LABEL na superfície. */
const UNKNOWN = "Código técnico não catalogado";

export function labelingLabel(map: Record<string, string>, value: string | null | undefined): string {
  if (!value) return "—";
  return map[value] ?? UNCATALOGED_OPTION_LABEL;
}

export function dossierStatusLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return DOSSIER_STATUS_LABEL[value] ?? labelingLabel(DOSSIER_STATUS_LABEL, value);
}

export function completenessLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return COMPLETENESS_LABEL[value] ?? labelingLabel(COMPLETENESS_LABEL, value);
}

export function nutrientLabel(value: string | null | undefined): string {
  if (!value) return "—";
  if (NUTRIENT_LABEL[value]) return NUTRIENT_LABEL[value];
  const stripped = value.startsWith("nutrient_") ? value.slice("nutrient_".length) : value;
  return NUTRIENT_LABEL[stripped] ?? labelingLabel(NUTRIENT_LABEL, value);
}

export function evidenceResultLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return EVIDENCE_RESULT_LABEL[value] ?? labelingLabel(EVIDENCE_RESULT_LABEL, value);
}

export function findingRuleLabel(value: string | null | undefined): string {
  if (!value) return "—";
  if (FINDING_RULE_LABEL[value]) return FINDING_RULE_LABEL[value];
  if (value.startsWith("allergen_")) {
    const code = value.slice("allergen_".length);
    const known = code.replaceAll("_", " ").trim();
    return known ? `Alérgeno — contém ${known}` : UNCATALOGED_RULE_LABEL;
  }
  if (value.startsWith("nutrient_")) {
    const nutrient = nutrientLabel(value);
    if (nutrient !== UNCATALOGED_OPTION_LABEL && nutrient !== "—") {
      return `${nutrient} obrigatório`;
    }
  }
  return FINDING_RULE_LABEL[value] ?? UNCATALOGED_RULE_LABEL;
}

export function mandatoryCodeLabel(value: string | null | undefined, fallbackLabel?: string | null): string {
  if (!value) return fallbackLabel?.trim() || "—";
  if (MANDATORY_CODE_LABEL[value]) return MANDATORY_CODE_LABEL[value];
  if (fallbackLabel?.trim() && !/^[a-z0-9]+(?:_[a-z0-9]+)+$/i.test(fallbackLabel.trim())) {
    return fallbackLabel.trim();
  }
  return MANDATORY_CODE_LABEL[value] ?? labelingLabel(MANDATORY_CODE_LABEL, value);
}

export function salesChannelLabel(value: string | null | undefined): string {
  if (value == null || value === "") return "Não informado";
  return SALES_CHANNEL_LABEL[value] ?? UNCATALOGED_OPTION_LABEL;
}

export function physicalStateLabel(value: string | null | undefined): string {
  if (value == null || value === "") return "Não informado";
  return PHYSICAL_STATE_LABEL[value] ?? UNCATALOGED_OPTION_LABEL;
}

export function regulatoryCategoryLabel(value: string | null | undefined): string {
  if (value == null || value === "") return "Não informado";
  return REGULATORY_CATEGORY_LABEL[value] ?? UNCATALOGED_OPTION_LABEL;
}

/** Booleano anulável: ausência ≠ falso. */
export function triStateLabel(value: unknown): string {
  if (value === true || value === "true") return "Sim";
  if (value === false || value === "false") return "Não";
  return "Não informado";
}

export function triStateFormValue(value: unknown): "" | "true" | "false" {
  if (value === true || value === "true") return "true";
  if (value === false || value === "false") return "false";
  return "";
}

export function parseTriStateFormValue(raw: FormDataEntryValue | null): boolean | null {
  if (raw === "true") return true;
  if (raw === "false") return false;
  return null;
}

export { UNKNOWN as UNKNOWN_LABELING_CODE };

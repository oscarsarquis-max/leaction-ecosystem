import { formatDecimal } from "../format";

/** Situação do produto. */
export const PRODUCT_STATUS_LABEL: Record<string, string> = {
  active: "Ativo",
  inactive: "Inativo",
};

/** Finalidade: o que o produto representa na operação. */
export const PRODUCT_PURPOSE_LABEL: Record<string, string> = {
  final: "Produto final",
  intermediate: "Preparo intermediário",
};

/** Como o produto chega à operação. */
export const PRODUCT_SUPPLY_MODE_LABEL: Record<string, string> = {
  produced: "Produzido na casa",
  purchased: "Comprado pronto",
  mixed: "Produzido e comprado",
  combo: "Combo de produtos",
};

/** Modalidades sem operação completa nesta fase. */
export const SUPPLY_MODES_IN_PREPARATION = ["mixed", "combo"];

export const SUPPLY_MODE_PREPARATION_NOTE =
  "Modalidade em preparação: produção, recebimento e composição ainda não estão completos nesta fase.";

export function productStatusLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return PRODUCT_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function productPurposeLabel(purpose: string | null | undefined): string {
  if (!purpose) return "—";
  return PRODUCT_PURPOSE_LABEL[purpose] ?? "Finalidade ainda não catalogada";
}

export function isSupplyModeInPreparation(mode: string | null | undefined): boolean {
  return Boolean(mode) && SUPPLY_MODES_IN_PREPARATION.includes(mode as string);
}

/** Rótulo humano da modalidade; mixed/combo saem marcados como em preparação. */
export function productSupplyModeLabel(mode: string | null | undefined): string {
  if (!mode) return "—";
  const label = PRODUCT_SUPPLY_MODE_LABEL[mode];
  if (!label) return "Modalidade ainda não catalogada";
  return isSupplyModeInPreparation(mode) ? `${label} (em preparação)` : label;
}

export function productStatusTone(
  status: string | null | undefined,
): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (status === "active") return "sucesso";
  if (status === "inactive") return "neutro";
  return "info";
}

export function productSupplyModeTone(
  mode: string | null | undefined,
): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (isSupplyModeInPreparation(mode)) return "atencao";
  return "info";
}

/**
 * Situação da receita do produto. A API já entrega a frase pronta;
 * o cálculo local só cobre listagens antigas sem o campo.
 */
export function productRecipeStatusLabel(product: {
  recipe_status_label?: string | null;
  has_published_recipe?: boolean;
  supply_mode?: string | null;
}): string {
  const given = product.recipe_status_label?.trim();
  if (given) return given;
  if (product.supply_mode === "purchased") return "Não se aplica";
  if (isSupplyModeInPreparation(product.supply_mode)) return "Modalidade em preparação";
  return product.has_published_recipe ? "Com receita vigente" : "Sem receita vigente";
}

export function productRecipeTone(product: {
  has_published_recipe?: boolean;
  has_process_steps?: boolean;
  current_recipe?: { steps?: Array<unknown> } | null;
  supply_mode?: string | null;
}): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (product.supply_mode === "purchased") return "neutro";
  if (isSupplyModeInPreparation(product.supply_mode)) return "atencao";
  if (!product.has_published_recipe) return "atencao";
  if (!productHasPrep(product)) return "atencao";
  return "sucesso";
}

export function productFamilyLabel(
  family: { display_name?: string | null; code?: string | null } | null | undefined,
): string {
  const name = family?.display_name?.trim();
  if (!name) return "Sem família";
  return name;
}

export function productUnitLabel(
  unit: { display_name?: string | null; code?: string | null } | null | undefined,
): string {
  const name = unit?.display_name?.trim() || unit?.code?.trim();
  return name || "Não informada";
}

/** Conteúdo líquido humano; sem unidade, mostra só o número formatado. */
export function productNetContentLabel(
  value: string | null | undefined,
  unit: { display_name?: string | null; code?: string | null } | null | undefined,
): string {
  if (value == null || value === "") return "Não informado";
  const amount = formatDecimal(value);
  const symbol = unit?.code?.trim() || unit?.display_name?.trim();
  return symbol ? `${amount} ${symbol}` : amount;
}

export function productShelfLifeLabel(days: number | null | undefined): string {
  if (days == null) return "Não informada";
  if (days === 0) return "Sem prazo padrão";
  return days === 1 ? "1 dia" : `${days} dias`;
}

/** Resumo da etapa Produtos no fluxo, em linguagem de operação. */
export function productsSummarySentence(summary: {
  total?: number;
  active: number;
  produced_without_recipe: number;
  purchased: number;
  intermediate: number;
}): string {
  if ((summary.total ?? summary.active) === 0) {
    return "Nenhum produto cadastrado ainda. Cadastre o primeiro produto para iniciar esta etapa.";
  }
  const primary = `${summary.active} produto(s) ativo(s)`;
  const secondary = [
    `${summary.produced_without_recipe} produzido(s) sem receita vigente`,
    `${summary.purchased} comprado(s) pronto(s)`,
    `${summary.intermediate} preparo(s) intermediário(s)`,
  ].join(" · ");
  return `${primary}. Detalhe: ${secondary}.`;
}

export function productHasPrep(product: {
  has_process_steps?: boolean;
  current_recipe?: { steps?: Array<unknown> } | null;
}): boolean {
  if (product.current_recipe) return (product.current_recipe.steps?.length ?? 0) > 0;
  return Boolean(product.has_process_steps);
}

export function productReadyToProduce(product: {
  supply_mode?: string | null;
  has_published_recipe?: boolean;
  has_process_steps?: boolean;
  current_recipe?: { steps?: Array<unknown> } | null;
}): boolean {
  if (product.supply_mode !== "produced") return false;
  return Boolean(product.has_published_recipe) && productHasPrep(product);
}

/** Prontidão produtiva — não mistura custo. */
export function productProductionLabel(product: {
  supply_mode?: string | null;
  has_published_recipe?: boolean;
  has_process_steps?: boolean;
  current_recipe?: { steps?: Array<unknown> } | null;
}): string {
  if (product.supply_mode === "purchased") return "Não se aplica";
  if (isSupplyModeInPreparation(product.supply_mode)) return "Modalidade em preparação";
  if (!product.has_published_recipe) return "Produção bloqueada";
  if (!productHasPrep(product)) return "Requer modo de preparo";
  return "Pronto para produzir";
}

export function productPendingLabel(product: {
  supply_mode?: string | null;
  has_published_recipe?: boolean;
  has_process_steps?: boolean;
  current_recipe?: { steps?: Array<unknown> } | null;
  status?: string | null;
}): string {
  if (product.status === "inactive") return "Produto inativo";
  if (product.supply_mode === "purchased") return "—";
  if (isSupplyModeInPreparation(product.supply_mode)) return "Modalidade em preparação";
  if (!product.has_published_recipe) return "Sem receita vigente";
  if (!productHasPrep(product)) return "Sem modo de preparo";
  return "—";
}

export function productNextActionLabel(product: {
  supply_mode?: string | null;
  has_published_recipe?: boolean;
  has_process_steps?: boolean;
  current_recipe?: { steps?: Array<unknown> } | null;
  status?: string | null;
}): string {
  if (product.status === "inactive") return "Revisar cadastro";
  if (product.supply_mode === "purchased") return "Abrir produto";
  if (isSupplyModeInPreparation(product.supply_mode)) return "Abrir produto";
  if (!product.has_published_recipe) return "Completar a receita";
  if (!productHasPrep(product)) return "Registrar etapas na receita";
  return "Abrir produto";
}

export function productQuantityLabel(
  quantity: string | null | undefined,
  unit: string | null | undefined,
): string {
  if (quantity == null || quantity === "") return "—";
  const amount = formatDecimal(quantity);
  const symbol = unit?.trim();
  return symbol ? `${amount} ${symbol}` : amount;
}

export function productComponentRoleLabel(item: {
  role?: string | null;
  is_flour_basis?: boolean;
}): string {
  if (item.is_flour_basis) return "Base farinha";
  const role = item.role?.trim();
  if (!role || role === "ingredient") return "Componente";
  return role;
}

export function productYieldLabel(massG: string | null | undefined): string {
  if (massG == null || massG === "") return "Rendimento não informado";
  return `${formatDecimal(massG)} g de massa`;
}

export function productInitials(name: string | null | undefined): string {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "P";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

/** Situação de rotulagem a partir do dossiê real — sem inventar aprovação. */
export function productLabelingStatusLabel(input: {
  supply_mode?: string | null;
  dossierStatus?: string | null;
  recipePublished?: boolean;
  recipeVersionMatches?: boolean | null;
}): string {
  if (input.supply_mode === "purchased") return "Não se aplica";
  if (!input.dossierStatus) return "Não iniciada";
  if (input.dossierStatus === "draft") return "Em elaboração";
  if (input.dossierStatus === "evaluated") return "Rotulagem: requer revisão";
  if (input.dossierStatus === "invalidated") return "Rotulagem: requer revisão";
  if (input.dossierStatus === "reviewed") {
    if (input.recipePublished && input.recipeVersionMatches === false) {
      return "Desatualizada em relação à receita";
    }
    return "Aprovada";
  }
  return "Em elaboração";
}

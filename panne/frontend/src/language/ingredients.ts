import { formatDecimal } from "../format";
import { formatOperationalQuantity, pluralize } from "./quantities";

/** Situação da identidade do ingrediente. */
export const INGREDIENT_IDENTITY_STATUS_LABEL: Record<string, string> = {
  active: "Ativa",
  inactive: "Inativa",
};

/** Situação da versão do ingrediente. */
export const INGREDIENT_VERSION_STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  published: "Publicada",
  retired: "Aposentada",
};

/** Tipo de ingrediente (códigos de contrato preservados no envio). */
export const INGREDIENT_TYPE_LABEL: Record<string, string> = {
  simple: "Simples",
  composite: "Composto",
  preparation: "Preparação",
};

/** Qualificador nutricional (value_status). */
export const NUTRIENT_STATUS_LABEL: Record<string, string> = {
  measured: "Medido",
  known_zero: "Zero conhecido",
  below_loq: "Abaixo do limite de quantificação",
  not_detected: "Não detectado",
  unknown: "Desconhecido",
};

/** Relação alergênica (presence). */
export const ALLERGEN_PRESENCE_LABEL: Record<string, string> = {
  contains: "Contém",
  may_contain: "Pode conter",
  not_declared: "Ausência conhecida",
};

export function ingredientIdentityLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return INGREDIENT_IDENTITY_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function ingredientVersionLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return INGREDIENT_VERSION_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function ingredientTypeLabel(type: string | null | undefined): string {
  if (!type) return "—";
  return INGREDIENT_TYPE_LABEL[type] ?? "Tipo ainda não catalogado";
}

export function nutrientStatusLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return NUTRIENT_STATUS_LABEL[status] ?? "Qualificador ainda não catalogado";
}

export function allergenPresenceLabel(presence: string | null | undefined): string {
  if (!presence) return "—";
  return ALLERGEN_PRESENCE_LABEL[presence] ?? "Relação ainda não catalogada";
}

export function ingredientStatusTone(
  status: string | null | undefined,
): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (status === "published" || status === "active") return "sucesso";
  if (status === "draft") return "atencao";
  if (status === "retired" || status === "inactive") return "neutro";
  return "info";
}

function unitSymbol(unit: { code?: string; symbol?: string } | null | undefined): string {
  if (!unit) return "";
  return (unit.symbol || unit.code || "").trim();
}

/** Linha nutricional humana; ausência ≠ zero; sem conversão de unidade. */
export function formatNutrientLine(row: {
  value?: string | null;
  value_status?: string | null;
  limit_of_quantification?: string | null;
  nutrient?: { name?: string; code?: string } | null;
  unit?: { code?: string; symbol?: string } | null;
  loq_unit?: { code?: string; symbol?: string } | null;
}): string {
  const name = row.nutrient?.name?.trim() || "Nutriente indisponível";
  const status = nutrientStatusLabel(row.value_status);
  const symbol = unitSymbol(row.unit) || "g";

  if (row.value_status === "below_loq") {
    const loqSymbol = unitSymbol(row.loq_unit) || symbol;
    const loq =
      row.limit_of_quantification != null && row.limit_of_quantification !== ""
        ? ` · LQ ${formatOperationalQuantity(row.limit_of_quantification, loqSymbol)}`
        : "";
    return `${name}: ${status}${loq}`;
  }

  if (row.value_status === "known_zero") {
    return `${name}: 0 ${symbol} por 100 g · ${status}`;
  }

  if (row.value_status === "not_detected" || row.value_status === "unknown") {
    return `${name}: ${status}`;
  }

  if (row.value == null || row.value === "") {
    return `${name}: valor não informado · ${status}`;
  }

  return `${name}: ${formatOperationalQuantity(row.value, symbol)} por 100 g · ${status}`;
}

export function formatAllergenLine(row: {
  presence?: string | null;
  evidence_note?: string | null;
  allergen?: { name?: string; code?: string } | null;
}): string {
  const name = row.allergen?.name?.trim() || "Alergênico indisponível";
  const relation = allergenPresenceLabel(row.presence);
  const evidence = row.evidence_note?.trim();
  return evidence ? `${name} · ${relation} · ${evidence}` : `${name} · ${relation}`;
}

/** Moeda humana (pt-BR); código ISO só se não houver locale conhecido. */
export function formatMoneyAmount(
  amount: string | null | undefined,
  currency: string | null | undefined,
): string {
  if (amount == null || amount === "" || !/^-?\d+(?:\.\d+)?$/.test(amount)) {
    return "—";
  }
  const code = (currency ?? "").trim().toUpperCase() || "BRL";
  const value = Number(amount);
  if (!Number.isFinite(value)) return formatDecimal(amount);
  try {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: code,
      currencyDisplay: "symbol",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${formatDecimal(amount)} ${code}`;
  }
}

export function formatPackageQuantity(
  quantity: string | null | undefined,
  unit: { code?: string; symbol?: string } | null | undefined,
): string {
  const symbol = unitSymbol(unit);
  if (!symbol) {
    return quantity == null || quantity === "" ? "—" : formatDecimal(quantity);
  }
  return formatOperationalQuantity(quantity, symbol);
}

export function globalSourcesSummary(count: number): string {
  if (count <= 0) return "Nenhuma fonte global disponível";
  if (count === 1) return "1 fonte global disponível";
  return `${pluralize(count, "fonte global disponível", "fontes globais disponíveis")}`;
}

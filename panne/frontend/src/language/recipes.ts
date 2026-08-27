import { formatDecimal } from "../format";
import { formatOperationalQuantity } from "./quantities";

/** Situação da identidade da receita (Formulation.status). */
export const RECIPE_IDENTITY_STATUS_LABEL: Record<string, string> = {
  development: "Em desenvolvimento",
  active: "Ativa",
  retired: "Aposentada",
};

/** Situação da versão (FormulationVersion.status). */
export const RECIPE_VERSION_STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  published: "Publicada",
  retired: "Aposentada",
};

/** Decisão de aprovação. */
export const RECIPE_APPROVAL_LABEL: Record<string, string> = {
  submitted: "Em revisão",
  approved: "Aprovado",
  rejected: "Rejeitado",
  revoked: "Revogado",
};

/** Estado do ensaio (Trial.status). */
export const RECIPE_TRIAL_STATUS_LABEL: Record<string, string> = {
  planned: "Pendente",
  in_progress: "Em andamento",
  completed: "Concluído",
  cancelled: "Cancelado",
};

export function recipeIdentityLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return RECIPE_IDENTITY_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function recipeVersionLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return RECIPE_VERSION_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function recipeApprovalLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return RECIPE_APPROVAL_LABEL[status] ?? "Situação ainda não catalogada";
}

export function recipeTrialLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return RECIPE_TRIAL_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function recipeStatusTone(
  status: string | null | undefined,
): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (status === "published" || status === "active" || status === "approved" || status === "completed") {
    return "sucesso";
  }
  if (
    status === "draft" ||
    status === "development" ||
    status === "submitted" ||
    status === "planned" ||
    status === "in_progress"
  ) {
    return "atencao";
  }
  if (status === "retired" || status === "cancelled") return "neutro";
  if (status === "rejected" || status === "revoked") return "erro";
  return "info";
}

export function unitDisplayCode(unit: { code?: string; symbol?: string } | null | undefined): string {
  if (!unit) return "g";
  return (unit.symbol || unit.code || "g").trim() || "g";
}

export function formatBakersPercentage(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  if (!/^-?\d+(?:\.\d+)?$/.test(value)) return value;
  const num = Number(value);
  if (!Number.isFinite(num)) return value;
  const trimmed = num.toFixed(3).replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
  return `${formatDecimal(trimmed)}%`;
}

/** Fator de escala com precisão operacional (padrão 4 casas, alinhado à apresentação útil). */
export function formatScaleFactor(
  value: string | null | undefined,
  places = 4,
): string {
  if (value == null || value === "") return "—";
  if (!/^-?\d+(?:\.\d+)?$/.test(value)) return value;
  const num = Number(value);
  if (!Number.isFinite(num)) return value;
  const fixed = num.toFixed(Math.max(0, places));
  const normalized = fixed.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
  return formatDecimal(normalized);
}

/** Taxa de perda 0–1 → percentual operacional. */
export function formatBakeLossRate(value: string | null | undefined): string {
  if (value == null || value === "") return "";
  if (!/^-?\d+(?:\.\d+)?$/.test(value)) return value;
  const num = Number(value);
  if (!Number.isFinite(num)) return value;
  const pct = num * 100;
  const trimmed = pct.toFixed(1).replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
  return `${formatDecimal(trimmed)}%`;
}

export function formatYieldSummary(input: {
  yieldUnits: string | number | null | undefined;
  unitWeightG: string | null | undefined;
  lossRate: string | null | undefined;
}): string {
  const parts: string[] = [];
  const unitsRaw = input.yieldUnits;
  const hasUnits =
    unitsRaw != null && unitsRaw !== "" && Number.isFinite(Number(unitsRaw));
  if (!hasUnits) parts.push("Rendimento não informado");
  else parts.push(`${Number(unitsRaw)} unidades`);

  if (!input.unitWeightG) parts.push("Peso por unidade não informado");
  else parts.push(`${formatOperationalQuantity(input.unitWeightG, "g")} por unidade`);

  const loss = formatBakeLossRate(input.lossRate);
  if (!loss) parts.push("Perda não informada");
  else parts.push(`perda prevista ${loss}`);

  return `${parts.join(". ")}.`;
}

export function ingredientLineLabel(item: {
  ingredient?: { display_name?: string; code?: string } | null;
}): string {
  const name = item.ingredient?.display_name?.trim();
  if (!name) return "Ingrediente indisponível";
  const code = item.ingredient?.code?.trim();
  return code ? `${name} · ${code}` : name;
}

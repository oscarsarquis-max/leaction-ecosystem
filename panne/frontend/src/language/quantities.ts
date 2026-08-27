import { formatDecimal } from "../format";

/**
 * Política de apresentação operacional (R026-004):
 * - massa (g): até 1 casa decimal na UI; valor integral preservado no dado;
 * - unidades discretas: 0 casas;
 * - demais unidades: até 2 casas.
 * Arredondamento é só visual — não altera o valor persistido.
 */
export function formatOperationalQuantity(
  quantity: string | null | undefined,
  unit?: string | null,
  options: { maxFractionDigits?: number } = {},
): string {
  if (quantity == null || quantity === "") return "—";
  if (!/^-?\d+(?:\.\d+)?$/.test(quantity)) return formatDecimal(quantity);

  const unitNorm = (unit ?? "").trim().toLowerCase();
  let maxDigits = options.maxFractionDigits;
  if (maxDigits == null) {
    if (unitNorm === "un" || unitNorm === "units" || unitNorm === "unidade" || unitNorm === "unidades") {
      maxDigits = 0;
    } else if (unitNorm === "g" || unitNorm === "kg" || unitNorm === "mass" || unitNorm === "") {
      maxDigits = 1;
    } else {
      maxDigits = 2;
    }
  }

  const num = Number(quantity);
  if (!Number.isFinite(num)) return formatDecimal(quantity);
  const fixed = num.toFixed(maxDigits);
  const normalized = fixed.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
  const amount = formatDecimal(normalized);

  if (!unit || unitNorm === "mass") return `${amount} g`;
  if (unitNorm === "units") return `${amount} un`;
  return `${amount} ${unit}`;
}

/** Valor integral para área técnica (sem alterar o dado). */
export function formatExactQuantity(quantity: string | null | undefined, unit?: string | null): string {
  const amount = formatDecimal(quantity);
  if (amount === "—") return amount;
  if (!unit) return amount;
  if (unit === "mass") return `${amount} g`;
  if (unit === "units") return `${amount} un`;
  return `${amount} ${unit}`;
}

export function integrityStatus(hash: string | null | undefined): string {
  return hash ? "versão registrada" : "ainda sem registro";
}

/** Pluralização humana simples (pt-BR). */
export function pluralize(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

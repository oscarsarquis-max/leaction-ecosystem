import type { FiscalDocumentItem } from "../api/types";
import { fiscalMoney } from "../language/fiscal";

function sameUnit(left: string | null | undefined, right: string | null | undefined): boolean {
  return (left ?? "").trim().toLocaleLowerCase("pt-BR") === (right ?? "").trim().toLocaleLowerCase("pt-BR");
}

function parsePositive(value: string): number | null {
  const parsed = Number(value.trim().replace(",", "."));
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

const COUNT_UNITS = new Set([
  "un",
  "und",
  "unid",
  "unidade",
  "unidades",
  "pc",
  "peca",
  "cx",
  "fd",
  "pct",
  "emb",
  "embalagem",
]);

const UNIT_ALIASES: Record<string, string> = {
  un: "un",
  und: "un",
  unid: "un",
  unidade: "un",
  unidades: "un",
  pc: "un",
  peca: "un",
  cx: "un",
  embalagem: "un",
  g: "g",
  gr: "g",
  grama: "g",
  gramas: "g",
  kg: "kg",
  quilo: "kg",
  quilos: "kg",
  ml: "ml",
  l: "l",
  litro: "l",
  litros: "l",
};

export type PackageHint = {
  amount: number;
  unit: string;
};

export type ControlChoice = "package" | "g" | "kg" | "ml" | "l";

export function canonicalUnit(unit: string | null | undefined): string {
  const key = (unit ?? "").trim().toLocaleLowerCase("pt-BR");
  return UNIT_ALIASES[key] || key;
}

export function isCountUnit(unit: string | null | undefined): boolean {
  return COUNT_UNITS.has((unit ?? "").trim().toLocaleLowerCase("pt-BR"));
}

export function spokenUnit(unit: string | null | undefined, quantity: number): string {
  if (isCountUnit(unit)) return quantity === 1 ? "unidade" : "unidades";
  const code = (unit ?? "").trim();
  return code || "unidade";
}

/** Um único conteúdo de embalagem no texto. Dois números, ou nenhum, não são evidência. */
export function packageHintFromName(description: string | null | undefined): PackageHint | null {
  const numbers = (description ?? "").match(/\d+(?:[.,]\d+)?/g) ?? [];
  if (numbers.length !== 1) return null;
  const found: PackageHint[] = [];
  const pattern = /(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l)\b/gi;
  for (const match of (description ?? "").matchAll(pattern)) {
    const amount = Number(match[1].replace(",", "."));
    const unit = match[2].toLocaleLowerCase("pt-BR");
    if (!Number.isFinite(amount) || amount <= 0) continue;
    found.push({ amount, unit });
  }
  if (found.length !== 1) return null;
  return found[0];
}

export function invoiceSays(item: {
  supplier_description: string;
  invoiced_quantity: string | null;
  unit_code: string | null;
  invoice_unit_price?: string | null;
  total_cost?: string | null;
  currency?: string | null;
}): string {
  const quantity = parsePositive(item.invoiced_quantity ?? "");
  const name = (item.supplier_description ?? "").trim() || "item sem descrição na nota";
  const amount =
    quantity == null
      ? "quantidade não informada"
      : `${formatAmount(quantity)} ${spokenUnit(item.unit_code, quantity)}`;
  let sentence = `A nota diz: ${amount} de ${name}`;
  if (item.total_cost) {
    sentence += `, total ${fiscalMoney(item.total_cost, item.currency)}`;
  } else if (item.invoice_unit_price) {
    sentence += `, a ${fiscalMoney(item.invoice_unit_price, item.currency)} por ${spokenUnit(item.unit_code, 1)}`;
  }
  return `${sentence}.`;
}

export function suggestControl(input: {
  invoiceUnit: string | null | undefined;
  existingUnit?: string | null;
  hint: PackageHint | null;
}): { unit: string; content: string | null; fromName: boolean; byPackage: boolean } {
  const invoice = (input.invoiceUnit ?? "").trim();
  const existing = (input.existingUnit ?? "").trim();
  if (existing) {
    if (sameUnit(existing, invoice)) {
      return { unit: existing, content: null, fromName: false, byPackage: isCountUnit(invoice) };
    }
    if (input.hint && sameUnit(input.hint.unit, existing)) {
      return {
        unit: existing,
        content: plainAmount(input.hint.amount),
        fromName: true,
        byPackage: false,
      };
    }
    return { unit: existing, content: null, fromName: false, byPackage: false };
  }
  if (input.hint && isCountUnit(invoice)) {
    return {
      unit: input.hint.unit,
      content: plainAmount(input.hint.amount),
      fromName: true,
      byPackage: false,
    };
  }
  return { unit: invoice || "un", content: null, fromName: false, byPackage: isCountUnit(invoice) };
}

export function controlChoices(invoiceUnit: string | null | undefined, hint: PackageHint | null): ControlChoice[] {
  const choices: ControlChoice[] = ["package"];
  const family = hint?.unit || canonicalUnit(invoiceUnit);
  if (family === "kg" || family === "g" || isCountUnit(invoiceUnit)) {
    choices.push("g", "kg");
  }
  if (family === "ml" || family === "l") choices.push("ml", "l");
  return choices;
}

export function choiceLabel(choice: ControlChoice): string {
  if (choice === "package") return "Por embalagem";
  if (choice === "g") return "Em gramas";
  if (choice === "kg") return "Em quilos";
  if (choice === "ml") return "Em mililitros";
  return "Em litros";
}

export function selectedChoice(stockUnit: string, invoiceUnit: string | null | undefined): ControlChoice {
  if (sameUnit(stockUnit, invoiceUnit)) return "package";
  const unit = canonicalUnit(stockUnit);
  if (unit === "g" || unit === "kg" || unit === "ml" || unit === "l") return unit;
  return "package";
}

export function unitForChoice(choice: ControlChoice, invoiceUnit: string | null | undefined): string {
  if (choice === "package") return (invoiceUnit ?? "").trim() || "un";
  return choice;
}

/** Aceita "1" ou "1 UN" na unidade do campo. Não devolve texto para gravar. */
export function parseArrived(
  text: string,
  fieldUnit: string,
): { amount: number; unit: string } | null {
  const match = String(text ?? "").trim().match(/^(\d+(?:[.,]\d+)?)\s*([A-Za-zÀ-ÿ]+)?$/);
  if (!match) return null;
  const amount = Number(match[1].replace(",", "."));
  if (!Number.isFinite(amount) || amount <= 0) return null;
  if (!match[2]) return { amount, unit: fieldUnit };
  const typed = canonicalUnit(match[2]);
  const expected = canonicalUnit(fieldUnit);
  if (typed !== expected && !sameUnit(match[2], fieldUnit)) return null;
  return { amount, unit: fieldUnit };
}

export function stockAmount(
  arrived: number,
  invoiceUnit: string | null | undefined,
  stockUnit: string,
  content: string,
): number | null {
  if (sameUnit(invoiceUnit, stockUnit)) return arrived;
  const factor = parseArrived(content, stockUnit)?.amount ?? null;
  if (factor == null || factor === 1) return null;
  return arrived * factor;
}

export function decimalText(amount: number): string {
  const fixed = amount.toFixed(6).replace(/\.?0+$/, "");
  return fixed === "" ? "0" : fixed;
}

export function movementSentence(
  arrived: number,
  invoiceUnit: string | null | undefined,
  stockUnit: string,
  content: string,
): string | null {
  if (sameUnit(invoiceUnit, stockUnit)) {
    return `${formatAmount(arrived)} ${spokenUnit(invoiceUnit, arrived)} no estoque`;
  }
  const stock = stockAmount(arrived, invoiceUnit, stockUnit, content);
  if (stock == null) return null;
  const received = isCountUnit(invoiceUnit)
    ? `${formatAmount(arrived)} ${arrived === 1 ? "embalagem recebida" : "embalagens recebidas"}`
    : `${formatAmount(arrived)} ${spokenUnit(invoiceUnit, arrived)}`;
  return `${received} → ${formatAmount(stock)} ${stockUnit} no estoque`;
}

export function principalStockName(establishmentName: string | null | undefined): string {
  const place = (establishmentName ?? "").trim();
  return place ? `Estoque principal de ${place}` : "Estoque principal";
}

export function previewStockUnitCost(lineTotal: string | null | undefined, stockQty: number | null): string | null {
  if (!lineTotal || stockQty == null || stockQty <= 0) return null;
  const total = Number(lineTotal);
  if (!Number.isFinite(total)) return null;
  return decimalText(total / stockQty);
}

export function notesBesideExpected(asExpected: boolean, notes: string): string | null {
  if (!asExpected || !String(notes ?? "").trim()) return null;
  return "A observação fica registrada. A conferência continua como “chegou como esperado”, a menos que você marque Não.";
}

function plainAmount(value: number): string {
  return String(value).replace(".", ",");
}

export function formatAmount(value: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 6 }).format(value);
}

export function linePlan(item: FiscalDocumentItem, draft: {
  stockUnit: string;
  packageContent: string;
  receivedText: string;
}) {
  const arrived = parseArrived(draft.receivedText, item.unit_code || "");
  const stock = arrived
    ? stockAmount(arrived.amount, item.unit_code, draft.stockUnit, draft.packageContent)
    : null;
  return { arrived, stock };
}

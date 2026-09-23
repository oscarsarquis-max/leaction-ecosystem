import type { FiscalDocument, FiscalDocumentItem } from "../api/types";
import { fiscalMoney } from "../language/fiscal";
import { parseArrived } from "./receiptOperation";

export type ReceiptGap = {
  key: string;
  text: string;
  anchor: string;
};

export function sameUnit(left: string | null | undefined, right: string | null | undefined): boolean {
  return (left ?? "").trim().toLocaleLowerCase("pt-BR") === (right ?? "").trim().toLocaleLowerCase("pt-BR");
}

export function parsePositive(value: string): number | null {
  const parsed = Number(value.trim().replace(",", "."));
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

/** Conta visível. Não lê número no nome do produto e não preenche a quantidade recebida. */
export function conversionPreview(
  invoicedQuantity: string | null | undefined,
  fiscalUnit: string | null | undefined,
  factorText: string,
  stockUnit: string,
): string | null {
  if (sameUnit(fiscalUnit, stockUnit)) return null;
  const quantity = parsePositive(invoicedQuantity ?? "");
  const factor = parsePositive(factorText);
  if (quantity == null || factor == null) return null;
  const result = quantity * factor;
  return `${formatAmount(quantity)} ${fiscalUnit} × ${formatAmount(factor)} = ${formatAmount(result)} ${stockUnit}`;
}

export function factorIsUsable(fiscalUnit: string | null | undefined, stockUnit: string, factorText: string): boolean {
  if (sameUnit(fiscalUnit, stockUnit)) return true;
  const factor = parseArrived(factorText, stockUnit)?.amount ?? null;
  return factor != null && factor !== 1;
}

function formatAmount(value: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 6 }).format(value);
}

export function reviewGaps(input: {
  document: FiscalDocument;
  drafts: Record<
    string,
    | {
        creating: boolean;
        ingredientId: string;
        newName: string;
        receivedText: string;
      }
    | undefined
  >;
}): ReceiptGap[] {
  const gaps: ReceiptGap[] = [];
  for (const item of input.document.items) {
    const title = item.supplier_description.trim() || `Item ${item.sequence}`;
    const draft = input.drafts[item.id];
    const hasName =
      Boolean(draft?.newName.trim()) ||
      Boolean(draft?.ingredientId) ||
      Boolean(item.review?.suggested_ingredient_name);
    if (!hasName) {
      gaps.push({
        key: `insumo-${item.id}`,
        text: `Falta dizer o que é “${title}”.`,
        anchor: `item-${item.id}-insumo`,
      });
    }
    if (!draft || !parseArrived(draft.receivedText, item.unit_code || "")) {
      gaps.push({
        key: `chegou-${item.id}`,
        text: `Falta a quantidade conferida de “${title}”, em ${item.unit_code || "unidade da nota"}.`,
        anchor: `item-${item.id}-chegou`,
      });
    }
  }
  return gaps;
}

export function receiptGaps(input: {
  document: FiscalDocument;
  locationId: string;
  locationName: string;
  drafts: Record<
    string,
    | {
        creating: boolean;
        ingredientId: string;
        newName: string;
        stockUnit: string;
        packageContent: string;
        receivedText: string;
        asExpected: boolean;
        issue: string;
      }
    | undefined
  >;
}): ReceiptGap[] {
  if (input.document.stock_applied) return [];
  const gaps: ReceiptGap[] = [];
  for (const item of input.document.items) {
    const title = item.supplier_description.trim() || `Item ${item.sequence}`;
    const draft = input.drafts[item.id];
    const hasIngredient =
      Boolean(draft?.ingredientId) ||
      (draft?.creating && Boolean(draft.newName.trim())) ||
      (item.match.status === "matched" && Boolean(item.match.target_id));
    if (!hasIngredient) {
      gaps.push({
        key: `insumo-${item.id}`,
        text: `Falta dizer o que é “${title}” no estoque.`,
        anchor: `item-${item.id}-insumo`,
      });
    }
    const stockUnit = draft?.stockUnit || item.stock_unit_code || item.unit_code || "";
    const content = draft?.packageContent || "";
    if (!sameUnit(item.unit_code, stockUnit) && !factorIsUsable(item.unit_code, stockUnit, content)) {
      gaps.push({
        key: `conteudo-${item.id}`,
        text: `Falta dizer quanto de ${stockUnit || "estoque"} cabe em cada ${item.unit_code || "unidade"} de “${title}”.`,
        anchor: `item-${item.id}-conteudo`,
      });
    }
    if (!draft || !parseArrived(draft.receivedText, item.unit_code || "")) {
      gaps.push({
        key: `chegou-${item.id}`,
        text: `Falta a quantidade conferida de “${title}”, em ${item.unit_code || "unidade da nota"}.`,
        anchor: `item-${item.id}-chegou`,
      });
    }
    if (draft && !draft.asExpected && !draft.issue) {
      gaps.push({
        key: `motivo-${item.id}`,
        text: `Diga o que veio diferente em “${title}”.`,
        anchor: `item-${item.id}-motivo`,
      });
    }
  }
  if (!input.locationId && !input.locationName.trim()) {
    gaps.push({
      key: "local",
      text: "Falta o nome do lugar onde esta compra será guardada.",
      anchor: "local-estoque",
    });
  }
  return gaps;
}

export function lineNeedsFactor(item: FiscalDocumentItem, stockUnit: string): boolean {
  return !sameUnit(item.unit_code, stockUnit);
}

export type PurchaseCostCaption = {
  note: string | null;
  stock: string | null;
};

/** A matemática do custo não muda. Só a unidade de cada número fica explícita. */
export function purchaseCostCaption(input: {
  invoiceUnitPrice?: string | null;
  invoiceUnit?: string | null;
  stockUnitCost?: string | null;
  stockUnit?: string | null;
  fallbackUnitCost?: string | null;
  currency?: string | null;
}): PurchaseCostCaption {
  const invoiceUnit = input.invoiceUnit?.trim() || "unidade da nota";
  const stockUnit = input.stockUnit?.trim() || "unidade de estoque";
  const note = input.invoiceUnitPrice
    ? `${fiscalMoney(input.invoiceUnitPrice, input.currency)} por ${invoiceUnit}`
    : null;
  const stock = input.stockUnitCost
    ? `${fiscalMoney(input.stockUnitCost, input.currency)} por ${stockUnit}`
    : null;
  if (note || stock) return { note, stock };
  if (input.fallbackUnitCost) {
    return {
      note: `${fiscalMoney(input.fallbackUnitCost, input.currency)} por ${invoiceUnit}`,
      stock: null,
    };
  }
  return { note: null, stock: null };
}

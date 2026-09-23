import type { FiscalDocument, FiscalDocumentItem } from "../api/types";
import { fiscalMoney } from "../language/fiscal";

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
  const factor = parsePositive(factorText);
  return factor != null && factor !== 1;
}

function formatAmount(value: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 6 }).format(value);
}

export function receiptGaps(input: {
  document: FiscalDocument;
  locationId: string;
  drafts: Record<string, { stockUnit: string; factor: string } | undefined>;
  acceptDivergence: boolean;
}): ReceiptGap[] {
  if (input.document.stock_applied) return [];
  const gaps: ReceiptGap[] = [];
  for (const item of input.document.items) {
    const title = item.supplier_description.trim() || `Item ${item.sequence}`;
    if (item.match.status !== "matched" || !item.match.target_id) {
      gaps.push({
        key: `insumo-${item.id}`,
        text: `Falta o insumo de destino de “${title}”.`,
        anchor: `item-${item.id}-insumo`,
      });
    }
    const stockUnit = input.drafts[item.id]?.stockUnit || item.stock_unit_code || item.converted_unit_code || item.unit_code || "";
    const factor = input.drafts[item.id]?.factor || item.conversion_factor || "";
    if (!sameUnit(item.unit_code, stockUnit) && !factorIsUsable(item.unit_code, stockUnit, factor)) {
      gaps.push({
        key: `fator-${item.id}`,
        text: `Falta o fator para converter ${item.unit_code || "a unidade da nota"} de “${title}” em ${stockUnit || "a unidade de estoque"}.`,
        anchor: `item-${item.id}-fator`,
      });
    }
    if (!item.physical?.received_quantity) {
      gaps.push({
        key: `chegou-${item.id}`,
        text: `Falta registrar quanto de “${title}” chegou.`,
        anchor: `item-${item.id}-chegou`,
      });
    }
  }
  if (!input.locationId) {
    gaps.push({
      key: "local",
      text: "Falta o local de estoque que vai receber esta entrada.",
      anchor: "local-estoque",
    });
  }
  if (input.document.divergence_count > 0 && !input.acceptDivergence && !input.document.stock_applied) {
    gaps.push({
      key: "divergencia",
      text: "Há divergência registrada. Ela permanece na nota; confirme que pode concluir assim.",
      anchor: "aceite-divergencia",
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

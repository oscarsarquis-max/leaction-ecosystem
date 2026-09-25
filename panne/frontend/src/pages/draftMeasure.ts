export const COMMERCIAL_UNITS = ["pacote", "unidade", "caixa", "kg", "g", "ml", "l"] as const;
export const CONTENT_UNITS = ["g", "kg", "ml", "l", "un"] as const;

const COUNT = new Set(["pacote", "pacotes", "unidade", "unidades", "un", "caixa", "caixas"]);

export function parseAmount(value: string): number | null {
  const parsed = Number(value.trim().replace(",", "."));
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

export function isCountUnit(unit: string | null | undefined): boolean {
  return COUNT.has((unit ?? "").trim().toLocaleLowerCase("pt-BR"));
}

export function commercialWord(unit: string, quantity: number): string {
  const key = unit.trim().toLocaleLowerCase("pt-BR");
  if (key === "pacote" || key === "pacotes") return quantity === 1 ? "pacote" : "pacotes";
  if (key === "unidade" || key === "unidades" || key === "un") return quantity === 1 ? "unidade" : "unidades";
  if (key === "caixa" || key === "caixas") return quantity === 1 ? "caixa" : "caixas";
  return unit.trim() || "unidade";
}

export function commercialLabels(unit: string): {
  quantity: string;
  purchaseUnit: string;
  price: string;
  content: string;
} {
  const word = commercialWord(unit || "pacote", 2);
  const one = commercialWord(unit || "pacote", 1);
  return {
    quantity: unit.trim() ? `Quantos ${word}?` : "Quantos foram comprados?",
    purchaseUnit: "Unidade de compra",
    price: unit.trim() ? `Preço por ${one} (R$)` : "Preço por embalagem (R$)",
    content: unit.trim() ? `Quantidade por ${one}` : "Quantidade por embalagem",
  };
}

export function formatAmount(value: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 6 }).format(value);
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

export function normalizeStock(amount: number, unit: string): { amount: number; unit: string } {
  const key = unit.trim().toLocaleLowerCase("pt-BR");
  if (key === "g" && amount >= 1000) return { amount: amount / 1000, unit: "kg" };
  if (key === "ml" && amount >= 1000) return { amount: amount / 1000, unit: "l" };
  return { amount, unit: unit.trim() || "un" };
}

export function lineMeasure(input: {
  quantity: string;
  unit: string;
  content: string;
  contentUnit: string;
  price: string;
}): { stockText: string | null; moneyText: string | null; formula: string | null } {
  const packs = parseAmount(input.quantity);
  const price = input.price.trim() === "" ? null : Number(input.price.replace(",", "."));
  const money =
    packs != null && price != null && Number.isFinite(price) ? formatMoney(packs * price) : null;
  const unit = input.unit.trim();
  const contentUnit = input.contentUnit.trim();
  if (packs == null || !unit) {
    return { stockText: null, moneyText: money, formula: money ? `Valor da linha: ${money}` : null };
  }
  if (!contentUnit || contentUnit === unit.toLocaleLowerCase("pt-BR") || !input.content.trim()) {
    const word = commercialWord(unit, packs);
    const formula = money
      ? `${formatAmount(packs)} ${word} · Valor da linha: ${money}`
      : `${formatAmount(packs)} ${word}`;
    return { stockText: null, moneyText: money, formula };
  }
  const content = parseAmount(input.content);
  if (content == null) {
    return { stockText: null, moneyText: money, formula: money ? `Valor da linha: ${money}` : null };
  }
  const raw = packs * content;
  const stock = normalizeStock(raw, contentUnit);
  const word = commercialWord(unit, packs);
  const stockText = `${formatAmount(stock.amount)} ${stock.unit}`;
  const math = `${formatAmount(packs)} ${word} × ${formatAmount(content)} ${contentUnit} = ${stockText}`;
  const formula = money ? `${math} no total · Valor da linha: ${money}` : `${math} no total`;
  return { stockText, moneyText: money, formula };
}

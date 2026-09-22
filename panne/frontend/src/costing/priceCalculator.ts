/**
 * Calculadora de preço (espelho local das fórmulas do motor).
 * Não persiste. Ausência ≠ zero. Divisão por zero / custo inválido → erro explícito.
 *
 * Preço = Custo × Markup
 * Markup = Preço ÷ Custo
 * Margem = (Preço − Custo) ÷ Preço
 * Margem monetária = Preço − Custo
 */

export type CostBaseOrigin =
  | "sellable_unit"
  | "produced_unit"
  | "batch_total"
  | "absent"
  | string;

export type CalculatorSnapshot = {
  costBase: string | null;
  costOrigin: CostBaseOrigin;
  costOriginLabel: string;
  incomplete: boolean;
  markupFactor: string | null;
  price: string | null;
  marginRate: string | null;
  marginPercent: string | null;
  marginMoney: string | null;
  error: string | null;
  warning: string | null;
};

const MONEY_PLACES = 6;

function parseDec(value: string | null | undefined): number | null {
  if (value == null || value === "") return null;
  const normalized = String(value)
    .trim()
    .replace(/\s/g, "")
    .replace(/\.(?=\d{3}(\D|$))/g, "")
    .replace(",", ".");
  if (!/^-?\d+(?:\.\d+)?$/.test(normalized)) return null;
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

function formatDec(value: number, places = MONEY_PLACES): string {
  if (!Number.isFinite(value)) return "";
  const fixed = value.toFixed(places);
  return fixed.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
}

function baseWarning(incomplete: boolean, origin: CostBaseOrigin): string | null {
  if (origin === "absent") return "Sem custo-base utilizável. Ausência não é zero.";
  if (incomplete) {
    return "Custo incompleto: a simulação usa o valor parcial disponível e não substitui os custos aplicáveis configurados.";
  }
  if (origin === "batch_total") {
    return "Base = total do recorte, não o custo por unidade vendável.";
  }
  return null;
}

export function emptyCalculator(): CalculatorSnapshot {
  return {
    costBase: null,
    costOrigin: "absent",
    costOriginLabel: "Custo-base ausente",
    incomplete: true,
    markupFactor: null,
    price: null,
    marginRate: null,
    marginPercent: null,
    marginMoney: null,
    error: "Custo-base ausente",
    warning: "Sem custo-base utilizável. Ausência não é zero.",
  };
}

function withMargins(
  cost: number,
  price: number,
  markup: number,
  meta: Omit<CalculatorSnapshot, "markupFactor" | "price" | "marginRate" | "marginPercent" | "marginMoney" | "error">,
): CalculatorSnapshot {
  if (price <= 0) {
    return {
      ...meta,
      markupFactor: formatDec(markup),
      price: formatDec(price),
      marginRate: null,
      marginPercent: null,
      marginMoney: formatDec(price - cost),
      error: "Preço inválido para calcular margem (denominador).",
    };
  }
  const marginRate = (price - cost) / price;
  return {
    ...meta,
    markupFactor: formatDec(markup),
    price: formatDec(price),
    marginRate: formatDec(marginRate, 6),
    marginPercent: formatDec(marginRate * 100, 2),
    marginMoney: formatDec(price - cost),
    error: null,
  };
}

function formatHumanMoney(value: number, places = 2): string {
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  });
}

function formatHumanMarkup(value: number): string {
  return `${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function initFromCostBase(input: {
  amount: string | null | undefined;
  origin: CostBaseOrigin;
  originLabel: string;
  incomplete?: boolean;
  initialMarkup?: string | null;
}): CalculatorSnapshot {
  const cost = parseDec(input.amount);
  const incomplete = Boolean(input.incomplete);
  const warning = baseWarning(incomplete, input.origin);
  if (cost == null || cost <= 0) {
    return {
      ...emptyCalculator(),
      costOrigin: input.origin,
      costOriginLabel: input.originLabel,
      incomplete,
      warning,
      error:
        cost != null && cost <= 0
          ? "Custo-base inválido (deve ser maior que zero)."
          : "Custo-base ausente",
    };
  }
  const markup = parseDec(input.initialMarkup) ?? 2;
  if (markup <= 0) {
    return {
      costBase: formatDec(cost),
      costOrigin: input.origin,
      costOriginLabel: input.originLabel,
      incomplete,
      markupFactor: null,
      price: null,
      marginRate: null,
      marginPercent: null,
      marginMoney: null,
      error: "Markup inválido (deve ser maior que zero).",
      warning,
    };
  }
  const price = cost * markup;
  // Inputs humanos (2 casas); precisão integral permanece no costBase canônico e na memória.
  return withMargins(cost, price, markup, {
    costBase: formatDec(cost),
    costOrigin: input.origin,
    costOriginLabel: input.originLabel,
    incomplete,
    warning,
  });
}

/** Formata fator/preço para exibição inicial amigável (pt-BR). */
export function humanInputMarkup(factor: string | null): string {
  const n = parseDec(factor);
  return n == null ? "" : formatHumanMarkup(n);
}

export function humanInputPrice(amount: string | null): string {
  const n = parseDec(amount);
  return n == null ? "" : formatHumanMoney(n, 2);
}

/** Ao alterar markup → recalcula preço e margem. */
export function applyMarkupFactor(state: CalculatorSnapshot, markupRaw: string): CalculatorSnapshot {
  const cost = parseDec(state.costBase);
  const markup = parseDec(markupRaw);
  const warning = baseWarning(state.incomplete, state.costOrigin);
  if (cost == null || cost <= 0) {
    return { ...state, markupFactor: markupRaw || null, price: null, marginRate: null, marginPercent: null, marginMoney: null, error: "Custo-base ausente ou inválido.", warning };
  }
  if (markup == null || markup <= 0) {
    return {
      ...state,
      markupFactor: markupRaw || null,
      price: null,
      marginRate: null,
      marginPercent: null,
      marginMoney: null,
      error: "Markup inválido (deve ser maior que zero).",
      warning,
    };
  }
  return withMargins(cost, cost * markup, markup, {
    costBase: state.costBase,
    costOrigin: state.costOrigin,
    costOriginLabel: state.costOriginLabel,
    incomplete: state.incomplete,
    warning,
  });
}

/** Ao alterar preço desejado → recalcula markup e margem. */
export function applyDesiredPrice(state: CalculatorSnapshot, priceRaw: string): CalculatorSnapshot {
  const cost = parseDec(state.costBase);
  const price = parseDec(priceRaw);
  const warning = baseWarning(state.incomplete, state.costOrigin);
  if (cost == null || cost <= 0) {
    return { ...state, price: priceRaw || null, markupFactor: null, marginRate: null, marginPercent: null, marginMoney: null, error: "Custo-base ausente ou inválido.", warning };
  }
  if (price == null || price < 0) {
    return {
      ...state,
      price: priceRaw || null,
      markupFactor: null,
      marginRate: null,
      marginPercent: null,
      marginMoney: null,
      error: "Preço desejado inválido.",
      warning,
    };
  }
  if (price === 0) {
    return {
      ...state,
      price: "0",
      markupFactor: "0",
      marginRate: null,
      marginPercent: null,
      marginMoney: formatDec(0 - cost),
      error: "Preço zero: margem percentual indefinida (divisão por zero).",
      warning,
    };
  }
  const markup = price / cost;
  return withMargins(cost, price, markup, {
    costBase: state.costBase,
    costOrigin: state.costOrigin,
    costOriginLabel: state.costOriginLabel,
    incomplete: state.incomplete,
    warning,
  });
}

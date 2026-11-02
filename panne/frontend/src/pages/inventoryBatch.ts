/**
 * Inventário inicial em lote: regras puras da tela (sem React, sem rede).
 * Colar da planilha, conferência por linha, resumo, corpo do envio e rascunho.
 */
import type { ApiLineError } from "../api/errors";

export type UnitChoice = "" | "kg" | "g" | "un" | "emb";
export type PackUnit = "g" | "kg" | "ml" | "l";
export type FieldKey = "ingredient" | "quantity" | "unit" | "packQty" | "expires" | "lot" | "cost";
export type FieldIssues = Partial<Record<FieldKey, string>>;

export type BatchRow = {
  id: string;
  ingredientId: string;
  name: string;
  isNew: boolean;
  quantity: string;
  unit: UnitChoice;
  packQty: string;
  packUnit: PackUnit;
  expires: string;
  lot: string;
  cost: string;
  /** Avisos que vieram da colagem e somem quando o campo é corrigido. */
  issues: FieldIssues;
};

export type IngredientRef = { id: string; display_name: string };
export type StockItemRef = { ingredient_id: string; unit_code: string };

export type BatchHeader = { locationId: string; date: string; reason: string };

export const DEFAULT_REASON = "Inventário inicial";
export const MAX_LINES = 200;

export const UNIT_LABEL: Record<Exclude<UnitChoice, "">, string> = {
  kg: "quilos (kg)",
  g: "gramas (g)",
  un: "unidade",
  emb: "embalagem",
};

const CONTROL_LABEL: Record<string, string> = {
  kg: "quilos",
  g: "gramas",
  un: "unidade ou embalagem",
};

let counter = 0;
export function newRowId(): string {
  counter += 1;
  return `row-${Date.now().toString(36)}-${counter}`;
}

export function emptyRow(): BatchRow {
  return {
    id: newRowId(),
    ingredientId: "",
    name: "",
    isNew: false,
    quantity: "",
    unit: "kg",
    packQty: "",
    packUnit: "g",
    expires: "",
    lot: "",
    cost: "",
    issues: {},
  };
}

/** Linha sem nada digitado. A unidade padrão não conta como digitação. */
export function isBlankRow(row: BatchRow): boolean {
  return (
    !row.name.trim() &&
    !row.ingredientId &&
    !row.quantity.trim() &&
    !row.packQty.trim() &&
    !row.expires &&
    !row.lot.trim() &&
    !row.cost.trim()
  );
}

export function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .replace(/\s+/g, " ")
    .trim();
}

export function parseNumber(raw: string): number | null {
  let text = raw.replace(/R\$/gi, "").replace(/\s/g, "");
  if (!text) return null;
  if (text.includes(",") && text.includes(".")) text = text.replace(/\./g, "").replace(",", ".");
  else if (text.includes(",")) text = text.replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(text)) return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

/** Texto numérico limpo para a API: ponto decimal, sem "R$" nem espaços. */
export function cleanNumber(raw: string): string {
  const value = parseNumber(raw);
  if (value === null) return raw.trim();
  return String(value);
}

export function todayIso(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/** "31/03/2027", "31/3/27" ou "2027-03-31" viram "2027-03-31". Data impossível vira null. */
export function parseDate(raw: string): string | null {
  const text = raw.trim();
  if (!text) return null;
  let year: number;
  let month: number;
  let day: number;
  const iso = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(text);
  const br = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})$/.exec(text);
  if (iso) {
    year = Number(iso[1]);
    month = Number(iso[2]);
    day = Number(iso[3]);
  } else if (br) {
    day = Number(br[1]);
    month = Number(br[2]);
    year = Number(br[3]);
    if (br[3].length === 2) year += 2000;
  } else {
    return null;
  }
  const probe = new Date(Date.UTC(year, month - 1, day));
  if (probe.getUTCFullYear() !== year || probe.getUTCMonth() !== month - 1 || probe.getUTCDate() !== day) {
    return null;
  }
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

const UNIT_WORDS: Record<string, UnitChoice> = {
  kg: "kg",
  kgs: "kg",
  kilo: "kg",
  kilos: "kg",
  quilo: "kg",
  quilos: "kg",
  quilograma: "kg",
  quilogramas: "kg",
  g: "g",
  gr: "g",
  grama: "g",
  gramas: "g",
  un: "un",
  und: "un",
  unid: "un",
  unidade: "un",
  unidades: "un",
  pc: "un",
  peca: "un",
  pecas: "un",
  emb: "emb",
  embalagem: "emb",
  embalagens: "emb",
  pct: "emb",
  pacote: "emb",
  pacotes: "emb",
  cx: "emb",
  caixa: "emb",
  caixas: "emb",
  fardo: "emb",
  fardos: "emb",
  saco: "emb",
  sacos: "emb",
  lata: "emb",
  latas: "emb",
  pote: "emb",
  potes: "emb",
  garrafa: "emb",
  garrafas: "emb",
  frasco: "emb",
  frascos: "emb",
};

export function parseUnit(raw: string): UnitChoice | null {
  const key = normalizeText(raw);
  if (!key) return null;
  return UNIT_WORDS[key] ?? null;
}

export function findIngredient(name: string, ingredients: IngredientRef[]): IngredientRef | undefined {
  const key = normalizeText(name);
  if (!key) return undefined;
  return ingredients.find((row) => normalizeText(row.display_name) === key);
}

export function controlUnitFor(
  ingredientId: string,
  items: StockItemRef[],
): "kg" | "g" | "un" | null {
  const found = items.find((row) => row.ingredient_id === ingredientId);
  if (!found) return null;
  const code = found.unit_code.toLowerCase();
  return code === "kg" || code === "g" || code === "un" ? code : null;
}

function unitMatchesControl(unit: UnitChoice, control: "kg" | "g" | "un"): boolean {
  if (unit === "") return true;
  if (control === "un") return unit === "un" || unit === "emb";
  return unit === control;
}

/** Linhas coladas do Excel ou do Sheets: nome, quantidade, unidade, validade, custo. */
export function parsePaste(
  text: string,
  ingredients: IngredientRef[],
  items: StockItemRef[],
): { rows: BatchRow[]; skippedHeader: boolean } {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.replace(/\s+$/, ""))
    .filter((line) => line.trim().length > 0);
  const rows: BatchRow[] = [];
  let skippedHeader = false;
  lines.forEach((line, position) => {
    const separator = line.includes("\t") ? "\t" : line.includes(";") ? ";" : "\t";
    const cells = line.split(separator).map((cell) => cell.trim());
    const [name = "", quantity = "", unitText = "", expiresText = "", costText = ""] = cells;
    if (position === 0 && /^(nome|ingrediente|item|produto|insumo)$/i.test(normalizeText(name)) && parseNumber(quantity) === null) {
      skippedHeader = true;
      return;
    }
    const row = emptyRow();
    row.quantity = quantity;
    const known = findIngredient(name, ingredients);
    if (known) {
      row.ingredientId = known.id;
      row.name = known.display_name;
    } else {
      row.name = name.replace(/\s+/g, " ").trim();
      row.isNew = row.name.length > 0;
    }
    if (unitText) {
      const unit = parseUnit(unitText);
      if (unit) {
        row.unit = unit;
      } else {
        row.unit = "";
        row.issues.unit = `A unidade "${unitText}" não foi entendida. Escolha quilos, gramas, unidade ou embalagem.`;
      }
    } else if (known) {
      const control = controlUnitFor(known.id, items);
      if (control) row.unit = control;
    }
    if (expiresText) {
      const iso = parseDate(expiresText);
      if (iso) row.expires = iso;
      else row.issues.expires = `A validade "${expiresText}" não foi entendida. Digite a data como dia/mês/ano.`;
    }
    if (costText) {
      const value = parseNumber(costText);
      if (value === null) row.issues.cost = `O custo "${costText}" não foi entendido. Digite só o valor em reais.`;
      else row.cost = costText.replace(/R\$/gi, "").replace(/\s/g, "");
    }
    rows.push(row);
  });
  return { rows, skippedHeader };
}

export type ValidationContext = {
  items: StockItemRef[];
  today: string;
};

/** Conferência de uma linha. Linha em branco não tem erro. */
export function rowIssues(row: BatchRow, ctx: ValidationContext): FieldIssues {
  if (isBlankRow(row)) return {};
  const issues: FieldIssues = { ...row.issues };
  if (!row.ingredientId && !row.isNew) {
    issues.ingredient = row.name.trim()
      ? `Escolha "${row.name.trim()}" na lista ou use "Criar" para cadastrar um ingrediente novo.`
      : "Escolha o ingrediente ou digite o nome do novo.";
  }
  if (row.isNew && !row.name.trim()) issues.ingredient = "Digite o nome do ingrediente novo.";
  const quantity = parseNumber(row.quantity);
  if (!row.quantity.trim()) issues.quantity = "Informe a quantidade encontrada.";
  else if (quantity === null || quantity <= 0) issues.quantity = "Use um número maior que zero.";
  if (!row.unit && !issues.unit) issues.unit = "Escolha a unidade.";
  if (row.unit === "emb") {
    const pack = parseNumber(row.packQty);
    if (!row.packQty.trim()) issues.packQty = "Informe quanto vem em cada embalagem.";
    else if (pack === null || pack <= 0) issues.packQty = "O conteúdo da embalagem deve ser maior que zero.";
  }
  if (row.cost.trim()) {
    const cost = parseNumber(row.cost);
    if (cost === null || cost < 0) issues.cost = "Digite só o valor em reais, por exemplo 4,80.";
  }
  if (row.ingredientId && row.unit) {
    const control = controlUnitFor(row.ingredientId, ctx.items);
    if (control && !unitMatchesControl(row.unit, control)) {
      issues.unit = `Este ingrediente já é controlado em ${CONTROL_LABEL[control]}. Use essa unidade.`;
    }
  }
  return issues;
}

export function headerIssues(header: BatchHeader, today: string): Partial<Record<"location" | "date" | "reason", string>> {
  const issues: Partial<Record<"location" | "date" | "reason", string>> = {};
  if (!header.locationId) issues.location = "Escolha o local onde o estoque está.";
  if (!header.date) issues.date = "Informe a data da contagem.";
  else if (header.date > today) issues.date = "A data da contagem não pode ser depois de hoje.";
  if (header.reason.trim().length > 200) issues.reason = "O motivo tem texto demais. Use até 200 caracteres.";
  return issues;
}

export type BatchSummary = { items: number; newIngredients: number; noCost: number; noExpiry: number };

export function summarize(rows: BatchRow[]): BatchSummary {
  const filled = rows.filter((row) => !isBlankRow(row));
  const newNames = new Set(
    filled.filter((row) => row.isNew && !row.ingredientId && row.name.trim()).map((row) => normalizeText(row.name)),
  );
  return {
    items: filled.length,
    newIngredients: newNames.size,
    noCost: filled.filter((row) => !row.cost.trim()).length,
    noExpiry: filled.filter((row) => !row.expires).length,
  };
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function summaryText(summary: BatchSummary): string {
  return [
    plural(summary.items, "item", "itens"),
    plural(summary.newIngredients, "ingrediente novo", "ingredientes novos"),
    `${summary.noCost} sem custo`,
    `${summary.noExpiry} sem validade`,
  ].join(" · ");
}

export type BuiltBatch = {
  body: Record<string, unknown>;
  /** Linha da tela que gerou cada linha enviada, na mesma ordem. */
  rowIds: string[];
};

export function buildBatch(header: BatchHeader, rows: BatchRow[]): BuiltBatch {
  const sent = rows.filter((row) => !isBlankRow(row));
  const lines = sent.map((row) => {
    const unitCode = row.unit === "emb" ? "embalagem" : row.unit;
    const line: Record<string, unknown> = {
      quantity: cleanNumber(row.quantity),
      unit_code: unitCode,
      lot_code: row.lot.trim() || null,
      expires_on: row.expires || null,
      no_expiry: !row.expires,
      unit_cost: row.cost.trim() ? cleanNumber(row.cost) : null,
      cost_unknown: !row.cost.trim(),
    };
    if (row.ingredientId) line.ingredient_id = row.ingredientId;
    else line.new_ingredient = { display_name: row.name.trim(), unit_code: unitCode };
    if (row.unit === "emb") {
      line.package_content_quantity = cleanNumber(row.packQty);
      line.package_content_unit = row.packUnit;
    }
    return line;
  });
  return {
    body: {
      inventory_location_id: header.locationId,
      counted_on: header.date,
      reason: header.reason.trim() || DEFAULT_REASON,
      lines,
    },
    rowIds: sent.map((row) => row.id),
  };
}

const SERVER_FIELD: Record<string, FieldKey> = {
  ingredient: "ingredient",
  quantity: "quantity",
  unit_code: "unit",
  package_content_quantity: "packQty",
  package_content_unit: "packQty",
  expires_on: "expires",
  unit_cost: "cost",
  lot_code: "lot",
  line: "ingredient",
};

export type ServerRowErrors = Record<string, FieldIssues>;

/** Erros devolvidos pela API, ligados à linha da tela. Os do topo (sem linha) vão à parte. */
export function mapServerErrors(
  errors: ApiLineError[],
  rowIds: string[],
): { rows: ServerRowErrors; general: string[] } {
  const rows: ServerRowErrors = {};
  const general: string[] = [];
  for (const error of errors) {
    const rowId = error.index === null ? undefined : rowIds[error.index];
    if (!rowId) {
      general.push(error.message);
      continue;
    }
    const field = SERVER_FIELD[error.field] ?? "ingredient";
    rows[rowId] = { ...rows[rowId], [field]: error.message };
  }
  return { rows, general };
}

export type Draft = { version: 1; header: BatchHeader; rows: BatchRow[]; savedAt: string };

export function draftKey(organizationId: string): string {
  return `panne.inventarioInicial.${organizationId}`;
}

export function saveDraft(key: string, header: BatchHeader, rows: BatchRow[]): void {
  try {
    const filled = rows.filter((row) => !isBlankRow(row));
    if (filled.length === 0) {
      localStorage.removeItem(key);
      return;
    }
    const draft: Draft = { version: 1, header, rows: filled, savedAt: new Date().toISOString() };
    localStorage.setItem(key, JSON.stringify(draft));
  } catch {
    /* sem espaço ou sem acesso: a tela segue funcionando sem rascunho */
  }
}

export function loadDraft(key: string): Draft | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Draft;
    if (parsed?.version !== 1 || !Array.isArray(parsed.rows)) return null;
    const rows = parsed.rows.map((row) => ({ ...emptyRow(), ...row, issues: row.issues ?? {} }));
    return { ...parsed, rows };
  } catch {
    return null;
  }
}

export function clearDraft(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* sem acesso */
  }
}

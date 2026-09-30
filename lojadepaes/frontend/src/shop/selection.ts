import { fetchBuilderCatalog } from "../features/bread-builder/builderApi";
import { lineTotalCents, sumCents } from "../lib/money";
import { fetchProduct } from "./catalogApi";
import type { AdaptationDraft, PublicProduct, ResolvedLine, SelectionLine } from "./types";

export type { AdaptationDraft };

export const SELECTION_KEY = "lojadepaes_selection_v1";
export const ADAPTATION_TEXT_MAX = 500;
/** Teto do contrato público `StorefrontItemIn.quantity` (le=20). */
export const LINE_QUANTITY_MAX = 20;

export function newLineKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `line-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function normalizedAdaptation(value?: AdaptationDraft | null): AdaptationDraft | null {
  const text = value?.text.trim() ?? "";
  if (!text) {
    return null;
  }
  return {
    text: text.slice(0, ADAPTATION_TEXT_MAX),
    reason: value?.reason === "dietary_restriction" || value?.reason === "preference" ? value.reason : "",
  };
}

function adaptationFingerprint(value?: AdaptationDraft | null): string {
  const clean = normalizedAdaptation(value);
  if (!clean) {
    return "";
  }
  return `${clean.reason}|${clean.text}`;
}

function asCustom(value: unknown): SelectionLine["custom"] {
  if (!value || typeof value !== "object") {
    return null;
  }
  const row = value as Record<string, unknown>;
  if (typeof row.doughTypeId !== "string" || typeof row.breadShapeId !== "string") {
    return null;
  }
  const unitCents = typeof row.unitCents === "number" ? row.unitCents : 0;
  const weightGrams = typeof row.weightGrams === "number" ? row.weightGrams : 0;
  if (unitCents <= 0 || weightGrams <= 0) {
    return null;
  }
  return {
    doughTypeId: row.doughTypeId,
    breadShapeId: row.breadShapeId,
    ingredientIds: Array.isArray(row.ingredientIds) ? row.ingredientIds.filter((id) => typeof id === "string") : [],
    doughName: typeof row.doughName === "string" ? row.doughName : "Pão personalizado",
    shapeName: typeof row.shapeName === "string" ? row.shapeName : "Formato",
    ingredientNames: Array.isArray(row.ingredientNames)
      ? row.ingredientNames.filter((name) => typeof name === "string")
      : [],
    flourId: typeof row.flourId === "string" ? row.flourId : undefined,
    flourName: typeof row.flourName === "string" ? row.flourName : undefined,
    weightGrams,
    unitCents,
  };
}

function asLine(row: Record<string, unknown>): SelectionLine | null {
  const custom = asCustom(row.custom);
  if (custom) {
    const quantity = typeof row.quantity === "number" ? row.quantity : 0;
    if (!Number.isInteger(quantity) || quantity < 1) {
      return null;
    }
    const adaptationRaw = row.adaptation;
    let adaptation: AdaptationDraft | null = null;
    if (adaptationRaw && typeof adaptationRaw === "object") {
      const item = adaptationRaw as Record<string, unknown>;
      adaptation = normalizedAdaptation({
        text: typeof item.text === "string" ? item.text : "",
        reason: item.reason === "dietary_restriction" || item.reason === "preference" ? item.reason : "",
      });
    }
    return {
      key: typeof row.key === "string" && row.key ? row.key : newLineKey(),
      slug: "pao-personalizado",
      variantId: "",
      quantity,
      adaptation,
      custom,
    };
  }
  if (typeof row.slug !== "string" || typeof row.variantId !== "string" || !row.variantId) {
    return null;
  }
  const quantity = typeof row.quantity === "number" ? row.quantity : 0;
  if (!Number.isInteger(quantity) || quantity < 1) {
    return null;
  }
  const adaptationRaw = row.adaptation;
  let adaptation: AdaptationDraft | null = null;
  if (adaptationRaw && typeof adaptationRaw === "object") {
    const item = adaptationRaw as Record<string, unknown>;
    adaptation = normalizedAdaptation({
      text: typeof item.text === "string" ? item.text : "",
      reason: item.reason === "dietary_restriction" || item.reason === "preference" ? item.reason : "",
    });
  }
  return {
    key: typeof row.key === "string" && row.key ? row.key : newLineKey(),
    slug: row.slug,
    variantId: row.variantId,
    quantity,
    adaptation,
  };
}

export function readSelection(): SelectionLine[] {
  try {
    const raw = localStorage.getItem(SELECTION_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .map((row) => (row && typeof row === "object" ? asLine(row as Record<string, unknown>) : null))
      .filter((row): row is SelectionLine => row !== null);
  } catch {
    return [];
  }
}

export function writeSelection(lines: SelectionLine[]): void {
  localStorage.setItem(SELECTION_KEY, JSON.stringify(lines));
}

export function additionMessage(previousQuantity: number, added: number): string {
  const total = previousQuantity + added;
  const verb = added === 1 ? "Adicionado 1 pão" : `Adicionados ${added} pães`;
  if (previousQuantity > 0) {
    return `${verb}. Você tem ${total} deste pão no carrinho.`;
  }
  return `${verb}.`;
}

export function addToSelection(
  lines: SelectionLine[],
  slug: string,
  variantId: string,
  quantity: number,
  adaptation?: AdaptationDraft | null,
): SelectionLine[] {
  return applyProductAddition(lines, slug, variantId, quantity, adaptation).lines;
}

export function applyProductAddition(
  lines: SelectionLine[],
  slug: string,
  variantId: string,
  quantity: number,
  adaptation?: AdaptationDraft | null,
): { lines: SelectionLine[]; message: string } {
  const clean = normalizedAdaptation(adaptation);
  const print = adaptationFingerprint(clean);
  const previous =
    lines.find((line) => !line.custom && line.variantId === variantId && adaptationFingerprint(line.adaptation) === print)
      ?.quantity ?? 0;
  const next = lines.map((line) => ({ ...line, adaptation: line.adaptation ? { ...line.adaptation } : null }));
  const existing = next.find(
    (line) => !line.custom && line.variantId === variantId && adaptationFingerprint(line.adaptation) === print,
  );
  if (existing) {
    existing.quantity += quantity;
    return { lines: next, message: additionMessage(previous, quantity) };
  }
  next.push({ key: newLineKey(), slug, variantId, quantity, adaptation: clean });
  return { lines: next, message: additionMessage(0, quantity) };
}

function customFingerprint(custom: NonNullable<SelectionLine["custom"]>, adaptation: AdaptationDraft | null): string {
  return [
    custom.doughTypeId,
    custom.breadShapeId,
    [...custom.ingredientIds].sort().join(","),
    adaptationFingerprint(adaptation),
  ].join("|");
}

export function addCustomToSelection(lines: SelectionLine[], custom: NonNullable<SelectionLine["custom"]>, quantity: number, adaptation?: AdaptationDraft | null): SelectionLine[] {
  const clean = normalizedAdaptation(adaptation);
  const print = customFingerprint(custom, clean);
  const next = lines.map((line) => ({ ...line, adaptation: line.adaptation ? { ...line.adaptation } : null }));
  const existing = next.find((line) => line.custom && customFingerprint(line.custom, line.adaptation ?? null) === print);
  if (existing) {
    existing.quantity += quantity;
    return next;
  }
  next.push({
    key: newLineKey(),
    slug: "pao-personalizado",
    variantId: "",
    quantity,
    adaptation: clean,
    custom,
  });
  return next;
}

export function setLineQuantity(lines: SelectionLine[], lineKey: string, quantity: number): SelectionLine[] {
  if (quantity < 1) {
    return lines.filter((line) => line.key !== lineKey);
  }
  const next = Math.min(LINE_QUANTITY_MAX, quantity);
  return lines.map((line) => (line.key === lineKey ? { ...line, quantity: next } : line));
}

export function setLineAdaptation(
  lines: SelectionLine[],
  lineKey: string,
  adaptation: AdaptationDraft | null,
): SelectionLine[] {
  const clean = normalizedAdaptation(adaptation);
  return lines.map((line) => (line.key === lineKey ? { ...line, adaptation: clean } : line));
}

export function removeLine(lines: SelectionLine[], lineKey: string): SelectionLine[] {
  return lines.filter((line) => line.key !== lineKey);
}

export function countItems(lines: SelectionLine[]): number {
  return lines.reduce((total, line) => total + line.quantity, 0);
}

export function packDescription(product: PublicProduct, variantId: string): string | null {
  const variant = product.variants.find((item) => item.id === variantId);
  if (!variant) {
    return null;
  }
  if (variant.pack_label && variant.pack_label !== variant.display_name) {
    return variant.pack_label;
  }
  if (variant.presentation_type === "weight" && variant.net_weight_grams) {
    const weight = `${variant.net_weight_grams} g`;
    if (variant.display_name.trim() === weight) {
      return null;
    }
    return `${weight} por pão`;
  }
  return null;
}

function unresolvedLine(line: SelectionLine, extra: Partial<ResolvedLine>): ResolvedLine {
  return {
    key: line.key,
    slug: line.slug,
    variantId: line.variantId,
    quantity: line.quantity,
    productName: extra.productName ?? "Pão indisponível",
    variantName: extra.variantName ?? "Opção removida",
    packLabel: extra.packLabel ?? null,
    unitCents: extra.unitCents ?? 0,
    lineCents: extra.lineCents ?? 0,
    available: extra.available ?? false,
    notice: extra.notice ?? "Este pão não está mais à venda.",
    reviewTarget: extra.reviewTarget ?? null,
    adaptation: line.adaptation ?? null,
    custom: line.custom ?? null,
  };
}

export async function resolveSelection(lines: SelectionLine[]): Promise<{ lines: ResolvedLine[]; totalCents: number }> {
  const slugs = [...new Set(lines.filter((line) => !line.custom).map((line) => line.slug))];
  const products = new Map<string, PublicProduct | null>();
  const hasCustom = lines.some((line) => line.custom);
  const [catalog] = await Promise.all([
    hasCustom
      ? fetchBuilderCatalog().catch(() => null)
      : Promise.resolve(null),
    ...slugs.map(async (slug) => {
      try {
        products.set(slug, await fetchProduct(slug));
      } catch {
        products.set(slug, null);
      }
    }),
  ]);
  const resolved: ResolvedLine[] = [];
  for (const line of lines) {
    if (line.custom) {
      const custom = line.custom;
      const unit = custom.unitCents;
      const inclusionNames = custom.ingredientNames.filter((name) => name !== custom.flourName);
      const packLabel = [
        `${custom.weightGrams} g`,
        custom.flourName,
        custom.doughName,
        inclusionNames.join(", ") || "Sem inclusões de catálogo",
      ]
        .filter(Boolean)
        .join(" · ");
      const doughOk = Boolean(catalog?.doughs.some((item) => item.id === custom.doughTypeId));
      const flourId =
        custom.flourId ||
        custom.ingredientIds.find((id) => catalog?.flours.some((item) => item.id === id));
      const flourOk = Boolean(flourId && catalog?.flours.some((item) => item.id === flourId));
      if (catalog && !doughOk) {
        resolved.push(
          unresolvedLine(line, {
            productName: custom.doughName,
            variantName: custom.shapeName,
            packLabel,
            unitCents: unit,
            lineCents: 0,
            available: false,
            notice:
              "O preparo desta seleção não está mais disponível. Revise só a fermentação e o preparo; farinha, complementos e texto livre foram mantidos.",
            reviewTarget: "preparation",
          }),
        );
        continue;
      }
      if (catalog && !flourOk) {
        resolved.push(
          unresolvedLine(line, {
            productName: custom.doughName,
            variantName: custom.shapeName,
            packLabel,
            unitCents: unit,
            lineCents: 0,
            available: false,
            notice:
              "A farinha desta seleção não está mais disponível. Revise só a farinha; o preparo, os complementos e o texto livre foram mantidos.",
            reviewTarget: "flour",
          }),
        );
        continue;
      }
      resolved.push({
        key: line.key,
        slug: line.slug,
        variantId: "",
        quantity: line.quantity,
        productName: custom.doughName,
        variantName: custom.shapeName,
        packLabel,
        unitCents: unit,
        lineCents: lineTotalCents(unit, line.quantity),
        available: unit > 0,
        notice: null,
        reviewTarget: null,
        adaptation: line.adaptation ?? null,
        custom: line.custom,
      });
      continue;
    }
    const product = products.get(line.slug);
    if (!product) {
      resolved.push(unresolvedLine(line, {}));
      continue;
    }
    const variant = product.variants.find((item) => item.id === line.variantId);
    const unit = variant?.price.cents ?? null;
    if (!variant || unit === null || unit <= 0) {
      resolved.push(
        unresolvedLine(line, {
          productName: product.name,
          variantName: "Opção indisponível",
          notice: "Esta opção saiu da venda. Remova-a da seleção.",
        }),
      );
      continue;
    }
    const available = product.is_available;
    resolved.push({
      key: line.key,
      slug: line.slug,
      variantId: line.variantId,
      quantity: line.quantity,
      productName: product.name,
      variantName: variant.display_name,
      packLabel: packDescription(product, variant.id),
      unitCents: unit,
      lineCents: available ? lineTotalCents(unit, line.quantity) : 0,
      available,
      notice: available ? null : "Temporariamente indisponível — não entra no total.",
      adaptation: line.adaptation ?? null,
    });
  }
  const totalCents = sumCents(resolved.filter((line) => line.available).map((line) => line.lineCents));
  return { lines: resolved, totalCents };
}

export function storefrontItemsFromLines(
  lines: Array<{
    variantId: string;
    quantity: number;
    adaptation?: AdaptationDraft | null;
    custom?: SelectionLine["custom"];
  }>,
) {
  return lines.map((line) => {
    const adaptation = normalizedAdaptation(line.adaptation);
    if (line.custom) {
      return {
        dough_type_id: line.custom.doughTypeId,
        bread_shape_id: line.custom.breadShapeId,
        ingredient_ids: line.custom.ingredientIds,
        free_ingredient_text: adaptation?.reason === "preference" ? adaptation.text : undefined,
        quantity: line.quantity,
        unit_cents: line.custom.unitCents,
        weight_grams: line.custom.weightGrams,
        adaptation_text: adaptation?.reason === "dietary_restriction" ? adaptation.text : undefined,
        adaptation_reason: adaptation?.reason === "dietary_restriction" ? adaptation.reason : undefined,
      };
    }
    return {
      variant_id: line.variantId,
      quantity: line.quantity,
      adaptation_text: adaptation?.text,
      adaptation_reason: adaptation?.reason || undefined,
    };
  });
}

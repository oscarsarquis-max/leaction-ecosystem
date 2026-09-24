import { lineTotalCents, sumCents } from "../lib/money";
import { fetchProduct } from "./catalogApi";
import type { AdaptationDraft, PublicProduct, ResolvedLine, SelectionLine } from "./types";

export type { AdaptationDraft };

export const SELECTION_KEY = "lojadepaes_selection_v1";
export const ADAPTATION_TEXT_MAX = 500;

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

function asLine(row: Record<string, unknown>): SelectionLine | null {
  if (typeof row.slug !== "string" || typeof row.variantId !== "string") {
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

export function addToSelection(
  lines: SelectionLine[],
  slug: string,
  variantId: string,
  quantity: number,
  adaptation?: AdaptationDraft | null,
): SelectionLine[] {
  const clean = normalizedAdaptation(adaptation);
  const print = adaptationFingerprint(clean);
  const next = lines.map((line) => ({ ...line, adaptation: line.adaptation ? { ...line.adaptation } : null }));
  const existing = next.find(
    (line) => line.variantId === variantId && adaptationFingerprint(line.adaptation) === print,
  );
  if (existing) {
    existing.quantity += quantity;
    return next;
  }
  next.push({ key: newLineKey(), slug, variantId, quantity, adaptation: clean });
  return next;
}

export function setLineQuantity(lines: SelectionLine[], lineKey: string, quantity: number): SelectionLine[] {
  if (quantity < 1) {
    return lines.filter((line) => line.key !== lineKey);
  }
  return lines.map((line) => (line.key === lineKey ? { ...line, quantity } : line));
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
  if (variant.pack_label) {
    return variant.pack_label;
  }
  if (variant.net_weight_grams) {
    return `${variant.net_weight_grams} g por pão`;
  }
  return variant.display_name;
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
    adaptation: line.adaptation ?? null,
  };
}

export async function resolveSelection(lines: SelectionLine[]): Promise<{ lines: ResolvedLine[]; totalCents: number }> {
  const slugs = [...new Set(lines.map((line) => line.slug))];
  const products = new Map<string, PublicProduct | null>();
  await Promise.all(
    slugs.map(async (slug) => {
      try {
        products.set(slug, await fetchProduct(slug));
      } catch {
        products.set(slug, null);
      }
    }),
  );
  const resolved: ResolvedLine[] = [];
  for (const line of lines) {
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

export function storefrontItemsFromLines(lines: Array<{ variantId: string; quantity: number; adaptation?: AdaptationDraft | null }>) {
  return lines.map((line) => {
    const adaptation = normalizedAdaptation(line.adaptation);
    return {
      variant_id: line.variantId,
      quantity: line.quantity,
      adaptation_text: adaptation?.text,
      adaptation_reason: adaptation?.reason || undefined,
    };
  });
}

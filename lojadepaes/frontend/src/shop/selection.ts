import { lineTotalCents, sumCents } from "../lib/money";
import { fetchProduct } from "./catalogApi";
import type { PublicProduct, ResolvedLine, SelectionLine } from "./types";

export const SELECTION_KEY = "lojadepaes_selection_v1";

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
      .map((row) => {
        if (!row || typeof row !== "object") {
          return null;
        }
        const item = row as Record<string, unknown>;
        if (typeof item.slug !== "string" || typeof item.variantId !== "string") {
          return null;
        }
        const quantity = typeof item.quantity === "number" ? item.quantity : 0;
        if (!Number.isInteger(quantity) || quantity < 1) {
          return null;
        }
        return { slug: item.slug, variantId: item.variantId, quantity };
      })
      .filter((row): row is SelectionLine => row !== null);
  } catch {
    return [];
  }
}

export function writeSelection(lines: SelectionLine[]): void {
  localStorage.setItem(SELECTION_KEY, JSON.stringify(lines));
}

export function addToSelection(lines: SelectionLine[], slug: string, variantId: string, quantity: number): SelectionLine[] {
  const next = lines.map((line) => ({ ...line }));
  const existing = next.find((line) => line.variantId === variantId);
  if (existing) {
    existing.quantity += quantity;
    return next;
  }
  next.push({ slug, variantId, quantity });
  return next;
}

export function setLineQuantity(lines: SelectionLine[], variantId: string, quantity: number): SelectionLine[] {
  if (quantity < 1) {
    return lines.filter((line) => line.variantId !== variantId);
  }
  return lines.map((line) => (line.variantId === variantId ? { ...line, quantity } : line));
}

export function removeLine(lines: SelectionLine[], variantId: string): SelectionLine[] {
  return lines.filter((line) => line.variantId !== variantId);
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
      resolved.push({
        slug: line.slug,
        variantId: line.variantId,
        quantity: line.quantity,
        productName: "Pão indisponível",
        variantName: "Opção removida",
        packLabel: null,
        unitCents: 0,
        lineCents: 0,
        available: false,
        notice: "Este pão não está mais à venda.",
      });
      continue;
    }
    const variant = product.variants.find((item) => item.id === line.variantId);
    const unit = variant?.price.cents ?? null;
    if (!variant || unit === null || unit <= 0) {
      resolved.push({
        slug: line.slug,
        variantId: line.variantId,
        quantity: line.quantity,
        productName: product.name,
        variantName: "Opção indisponível",
        packLabel: null,
        unitCents: 0,
        lineCents: 0,
        available: false,
        notice: "Esta opção saiu da venda. Remova-a da seleção.",
      });
      continue;
    }
    const available = product.is_available;
    resolved.push({
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
    });
  }
  const totalCents = sumCents(resolved.filter((line) => line.available).map((line) => line.lineCents));
  return { lines: resolved, totalCents };
}

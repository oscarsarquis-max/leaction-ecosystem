import { formatCents } from "../../lib/money";
import type { Partner } from "./types";

export const MARKETPLACE_API = "/api/v1/admin/marketplace";

export const CATEGORIES: Array<[string, string]> = [
  ["queijos", "Queijos"],
  ["frios", "Frios e charcutaria"],
  ["vinhos", "Vinhos"],
  ["cervejas", "Cervejas"],
  ["azeites", "Azeites"],
  ["manteigas", "Manteigas"],
  ["geleias", "Geleias e pastas"],
  ["cafe_cha", "Café e chá"],
  ["pratos", "Pratos e acompanhamentos"],
];

export const PARTNER_TYPES: Array<[string, string]> = [
  ["producer", "Produtor"],
  ["distributor", "Distribuidora"],
  ["restaurant", "Restaurante"],
];

export const LINK_TYPES: Array<[string, string]> = [
  ["exclusive", "Exclusivo"],
  ["partial", "Parcial"],
  ["none", "Sem exclusividade"],
];

type Tone = { label: string; tone: string };

const PARTNER_STATUS: Record<string, Tone> = {
  invited: { label: "Convidado", tone: "c-acc" },
  active: { label: "Ativo", tone: "c-prod" },
  paused: { label: "Pausado", tone: "c-open" },
};

const PRODUCT_STATUS: Record<string, Tone> = {
  draft: { label: "Rascunho", tone: "c-open" },
  pending: { label: "Em avaliação", tone: "c-acc" },
  approved: { label: "Publicado", tone: "c-prod" },
  returned: { label: "Devolvido", tone: "c-warn" },
  rejected: { label: "Recusado", tone: "c-can" },
  paused: { label: "Pausado", tone: "c-open" },
};

const LINK_TONE: Record<string, string> = {
  exclusive: "mkt-link-exclusive",
  partial: "c-acc",
  none: "c-none",
};

const DECISION: Record<string, string> = {
  approve: "Aprovado",
  return: "Devolvido",
  reject: "Recusado",
};

function pick(list: Array<[string, string]>, key: string): string {
  return list.find(([value]) => value === key)?.[1] ?? key;
}

export const categoryLabel = (key: string) => pick(CATEGORIES, key);
export const partnerTypeLabel = (key: string) => pick(PARTNER_TYPES, key);
export const linkTypeLabel = (key: string) => pick(LINK_TYPES, key);
export const linkTone = (key: string) => LINK_TONE[key] ?? "c-none";
export const partnerStatus = (key: string): Tone => PARTNER_STATUS[key] ?? { label: key, tone: "c-none" };
export const productStatus = (key: string): Tone => PRODUCT_STATUS[key] ?? { label: key, tone: "c-none" };
export const decisionLabel = (key: string) => DECISION[key] ?? key;

export function feeLabel(cents: number): string {
  return formatCents(cents);
}

export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter((word) => !/^(d[aeo]s?|e)$/i.test(word));
  const letters = words.length >= 2 ? words[0].charAt(0) + words[words.length - 1].charAt(0) : (words[0] ?? "").slice(0, 2);
  return letters.toUpperCase() || "?";
}

export function houseName(slug: string, name?: string | null): string {
  if (name) {
    return name;
  }
  const text = slug.replace(/-/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const DATE = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "UTC" });
const DATE_TIME = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});

export function dayLabel(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return DATE.format(new Date(Date.UTC(year, month - 1, day)));
}

export function stampLabel(iso: string): string {
  return DATE_TIME.format(new Date(iso));
}

export function periodLabel(starts: string, ends: string | null): string {
  return ends ? `${dayLabel(starts)} a ${dayLabel(ends)}` : `desde ${dayLabel(starts)}`;
}

export function linkActive(starts: string, ends: string | null, today: string): boolean {
  return starts <= today && (ends === null || ends >= today);
}

export function todayIso(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
}

export function partnerById(partners: Partner[]): Map<string, Partner> {
  return new Map(partners.map((partner) => [partner.id, partner]));
}

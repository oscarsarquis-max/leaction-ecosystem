import type { LoginEditorialColumn, LoginEditorialPayload } from "./schema";
import { EDITORIAL_SCHEMA_VERSION } from "./schema";

const DANGEROUS = /^(javascript|data|vbscript):/i;

export function sanitizePlain(value: unknown, max = 400): string {
  return String(value ?? "")
    .replace(/<[^>]*>/g, "")
    .split("")
    .filter((ch) => {
      const code = ch.charCodeAt(0);
      return code === 9 || code === 10 || code === 13 || code >= 32;
    })
    .join("")
    .trim()
    .slice(0, max);
}

export function sanitizeHref(value: unknown): string {
  const raw = sanitizePlain(value, 240);
  if (!raw || DANGEROUS.test(raw)) return "";
  if (raw.startsWith("/") && !raw.startsWith("//")) return raw;
  if (/^https:\/\//i.test(raw)) return raw;
  return "";
}

export function sanitizeColumn(raw: unknown): LoginEditorialColumn | null {
  if (!raw || typeof raw !== "object") return null;
  const row = raw as Record<string, unknown>;
  const image = row.image && typeof row.image === "object" ? (row.image as Record<string, unknown>) : {};
  const cta = row.cta && typeof row.cta === "object" ? (row.cta as Record<string, unknown>) : null;
  const placement = row.placement === "right" ? "right" : row.placement === "left" ? "left" : null;
  if (!placement) return null;
  const title = sanitizePlain(row.title, 120);
  if (!title) return null;
  const href = cta ? sanitizeHref(cta.url) : "";
  return {
    schema_version: EDITORIAL_SCHEMA_VERSION,
    placement,
    locale: "pt-BR",
    eyebrow: sanitizePlain(row.eyebrow, 40),
    title,
    summary: sanitizePlain(row.summary, 280),
    sections: Array.isArray(row.sections)
      ? row.sections.map((item) => sanitizePlain(item, 180)).filter(Boolean).slice(0, 4)
      : [],
    image: {
      url: sanitizeHref(image.url),
      alt: sanitizePlain(image.alt, 120) || title,
    },
    cta: cta && sanitizePlain(cta.label, 40) && href ? { label: sanitizePlain(cta.label, 40), url: href } : undefined,
    published_from: sanitizePlain(row.published_from, 32) || undefined,
    published_until: sanitizePlain(row.published_until, 32) || undefined,
    priority: Number.isFinite(Number(row.priority)) ? Number(row.priority) : 0,
    hash: sanitizePlain(row.hash, 64),
  };
}

export function sanitizePayload(raw: unknown): LoginEditorialPayload | null {
  if (!raw || typeof raw !== "object") return null;
  const row = raw as Record<string, unknown>;
  if (Number(row.schema_version) !== EDITORIAL_SCHEMA_VERSION) return null;
  const columns = Array.isArray(row.columns)
    ? row.columns.map(sanitizeColumn).filter((item): item is LoginEditorialColumn => Boolean(item))
    : [];
  if (!columns.length) return null;
  return {
    schema_version: EDITORIAL_SCHEMA_VERSION,
    columns,
    source: row.source === "fallback" ? "fallback" : "static",
  };
}

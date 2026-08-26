export const EDITORIAL_SCHEMA_VERSION = 1 as const;

export type EditorialPlacement = "left" | "right";

export type LoginEditorialColumn = {
  schema_version: typeof EDITORIAL_SCHEMA_VERSION;
  placement: EditorialPlacement;
  locale: "pt-BR";
  eyebrow: string;
  title: string;
  summary: string;
  sections: string[];
  image: { url: string; alt: string };
  cta?: { label: string; url: string };
  published_from?: string;
  published_until?: string;
  priority: number;
  hash: string;
};

export type LoginEditorialPayload = {
  schema_version: typeof EDITORIAL_SCHEMA_VERSION;
  columns: LoginEditorialColumn[];
  source: "static" | "fallback";
};

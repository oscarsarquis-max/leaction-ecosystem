import type { RouteGuide } from "./routes";

export const FALLBACK_GUIDE: RouteGuide = {
  id: "fallback",
  pattern: "*",
  domain: "geral",
  section: "minimo",
  title: "Esta página",
  goal: "Orientação mínima até existir um guia específico.",
  entity: "página",
  permissions: [],
  actions: ["Voltar ao início"],
  pending: "Guia específico em falta.",
  blocks: "",
  next: "Usar o menu ou voltar ao início.",
  related: [],
  destinations: [{ to: "/inicio", label: "Início" }],
  version: 1,
};

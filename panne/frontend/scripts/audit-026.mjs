import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-026");
mkdirSync(out, { recursive: true });

const API = "http://127.0.0.1:5080";
const FE = "http://127.0.0.1:5180";
const PROFILES = [
  "demo-owner",
  "demo-manager",
  "demo-formulator",
  "demo-baker",
  "demo-reviewer",
  "demo-buyer",
  "demo-reader",
];

async function get(url, headers = {}) {
  const response = await fetch(url, { headers });
  const text = await response.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    body = text.slice(0, 200);
  }
  return { status: response.status, body };
}

const health = await get(`${API}/health`);
const ready = await get(`${API}/ready`);
const profiles = {};
for (const subject of PROFILES) {
  profiles[subject] = await get(`${API}/api/v1/me`, { Authorization: `Bearer panne-demo:${subject}` });
}
const owner = profiles["demo-owner"].body;
const orgId = owner?.associations?.find((row) => row.slug === "panne-demonstracao")?.organization_id;
const auth = {
  Authorization: "Bearer panne-demo:demo-owner",
  "X-Panne-Organization-Id": orgId,
};

const lists = {
  ingredientes: `/api/v1/organizations/${orgId}/ingredients`,
  receitas: `/api/v1/organizations/${orgId}/recipes`,
  ordens: `/api/v1/organizations/${orgId}/production/orders`,
  planos: `/api/v1/organizations/${orgId}/production/plans`,
  quadro: `/api/v1/organizations/${orgId}/production/board`,
  dossies: `/api/v1/organizations/${orgId}/labeling/dossiers`,
  custos: `/api/v1/organizations/${orgId}/costing/calculations`,
  lotes: `/api/v1/organizations/${orgId}/inventory/lots`,
  posicao: `/api/v1/organizations/${orgId}/inventory/balances`,
  reservas: `/api/v1/organizations/${orgId}/inventory/reservations`,
  requisicoes: `/api/v1/organizations/${orgId}/procurement/requisitions`,
  cotacoes: `/api/v1/organizations/${orgId}/procurement/quotations`,
  pedidos: `/api/v1/organizations/${orgId}/procurement/orders`,
  recebimentos: `/api/v1/organizations/${orgId}/procurement/receipts`,
  devolucoes: `/api/v1/organizations/${orgId}/procurement/returns`,
  relatorios: `/api/v1/organizations/${orgId}/reporting/catalog`,
};

const live = {};
for (const [name, path] of Object.entries(lists)) {
  live[name] = await get(`${API}${path}`, auth);
}

const first = (payload, key = "items") => {
  const items = payload?.body?.[key] || payload?.body?.data || [];
  return Array.isArray(items) ? items[0] : items;
};

const ids = {
  ingredientId: first(live.ingredientes)?.id,
  recipeId: first(live.receitas)?.id,
  orderId: first(live.ordens)?.id || first(live.quadro, "data")?.order?.id,
  planId: first(live.planos)?.id,
  dossierId: first(live.dossies)?.id,
};

const routes = [
  ["/entrar", "Entrar na Panne", "público"],
  ["/inicio", "Início", "autenticado"],
  ["/producao", "Quadro de produção", "production.board.read"],
  ["/planejamento", "Planejamento", "production.plan.read"],
  ["/ordens", "Ordens", "production.order.read"],
  ["/rastreabilidade", "Rastreabilidade", "production.traceability.read"],
  ["/componentes/ingredientes", "Ingredientes", "ingredient.read"],
  ["/componentes/estoque", "Estoque", "inventory.read"],
  ["/componentes/estoque/posicao", "Posição de estoque", "inventory.read"],
  ["/componentes/lotes", "Lotes e validade", "inventory.read"],
  ["/componentes/fornecedores", "Fornecedores", "supplier.read"],
  ["/receitas", "Receitas", "recipe.read"],
  ["/conformidade", "Conformidade", "labeling.read"],
  ["/gestao/custos", "Custos", "costing.read"],
  ["/gestao/compras/necessidades", "Necessidades", "procurement.read"],
  ["/gestao/compras/requisicoes", "Requisições", "procurement.read"],
  ["/gestao/compras/cotacoes", "Cotações", "procurement.read"],
  ["/gestao/compras/pedidos", "Pedidos", "procurement.read"],
  ["/gestao/compras/recebimentos", "Recebimentos", "procurement.receive"],
  ["/gestao/compras/devolucoes", "Devoluções", "procurement.return"],
  ["/gestao/inventarios", "Inventários", "inventory.count"],
  ["/gestao/relatorios", "Relatórios", "reporting"],
];

const map = [
  "# Mapa de rotas auditadas — CURSOR-026",
  "",
  `- Saúde: ${health.status} ambiente=${health.body?.ambiente}`,
  `- Prontidão: ${ready.status}`,
  `- Organização: Panne Demonstração (${orgId})`,
  `- IDs reais: ingrediente=${ids.ingredientId || "ausente"} receita=${ids.recipeId || "ausente"} ordem=${ids.orderId || "ausente"}`,
  "",
  "## Perfis",
  "",
];
for (const [subject, payload] of Object.entries(profiles)) {
  const name = payload.body?.display_name || payload.body?.detail || payload.status;
  map.push(`- ${subject}: HTTP ${payload.status} — ${name}`);
}
map.push("", "## Domínios vivos", "");
for (const [name, payload] of Object.entries(live)) {
  const count = Array.isArray(payload.body?.items)
    ? payload.body.items.length
    : Array.isArray(payload.body?.data)
      ? payload.body.data.length
      : payload.status;
  map.push(`- ${name}: HTTP ${payload.status} · ${count} registros`);
}
map.push("", "## Rotas abertas no produto", "");
for (const [path, title, role] of routes) {
  const page = await get(`${FE}${path}`);
  map.push(`- \`${path}\` — ${title} (${role}) — frontend HTTP ${page.status}`);
}
writeFileSync(resolve(out, "mapa-rotas-auditadas.md"), map.join("\n") + "\n", "utf8");
writeFileSync(resolve(out, "live-api.json"), JSON.stringify({ health, ready, profiles, live, ids }, null, 2), "utf8");

const browser = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((path) => existsSync(path));

if (browser) {
  for (const [name, width, height] of [
    ["login-desktop-1440", 1440, 900],
    ["login-notebook-1366", 1366, 768],
    ["login-tablet-1024", 1024, 768],
    ["login-tablet-768", 768, 1024],
  ]) {
    const dest = resolve(out, `${name}.png`);
    spawnSync(browser, [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      `--window-size=${width},${height}`,
      `--screenshot=${dest}`,
      `${FE}/entrar`,
    ]);
  }
}

console.log(`evidências em ${out}`);
console.log(`rotas=${routes.length} perfis=${PROFILES.length} org=${orgId}`);

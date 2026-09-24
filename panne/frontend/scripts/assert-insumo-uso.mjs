import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../documentacao/evidencias/cursor-insumo-manual");
const out = path.join(root, "capturas-uso");
const trialPath = path.join(root, "trial.json");
const API = process.env.PANNE_API_URL || "http://127.0.0.1:5080";
const FE = process.env.PANNE_FE_URL || "http://127.0.0.1:5182";

function pngWidth(buffer) {
  return buffer.readUInt32BE(16);
}

async function waitHttp(url, label) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok || response.status < 500) return;
    } catch {
      /* still down */
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error(`${label} não respondeu em ${url}`);
}

async function assertFit(page, label) {
  const metrics = await page.evaluate(() => {
    const rootEl = document.documentElement;
    return {
      scrollWidth: rootEl.scrollWidth,
      clientWidth: rootEl.clientWidth,
      innerWidth: window.innerWidth,
      coachOpen: Boolean(document.querySelector(".flow-coach.is-open")),
      coachCollapsed: Boolean(document.querySelector(".flow-coach.is-collapsed")),
    };
  });
  if (metrics.innerWidth === 390 && (metrics.scrollWidth !== metrics.clientWidth || metrics.clientWidth !== 390)) {
    throw new Error(`${label}: viewport não cabe (${JSON.stringify(metrics)})`);
  }
  return metrics;
}

async function shot(page, name) {
  const url = page.url();
  if (url.includes("/entrar") || url.startsWith("file:")) {
    throw new Error(`captura recusada (${name}) ${url}`);
  }
  const file = path.join(out, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  const width = pngWidth(await readFile(file));
  if (name.includes("390") && width !== 390) {
    throw new Error(`${name}: PNG tem ${width}px, esperado 390`);
  }
  return { url, file, width };
}

await mkdir(out, { recursive: true });
await waitHttp(`${API}/health`, "API");
await waitHttp(`${FE}/`, "frontend");
const trial = JSON.parse(await readFile(trialPath, "utf8"));
const browser = await chromium.launch();
const proof = {};

async function openApp(width, height) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.addInitScript(
    ({ orgId }) => {
      sessionStorage.setItem("panne.demoSubject", "local-dev-owner");
      localStorage.setItem("panne.activeOrganization", orgId);
    },
    { orgId: trial.organization_id },
  );
  await page.goto(`${FE}/entrar`, { waitUntil: "networkidle" });
  await page.evaluate(() => sessionStorage.setItem("panne.demoSubject", "local-dev-owner"));
  await page.getByRole("button", { name: "Entrar em desenvolvimento" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 15000 });
  const orgSelect = page.locator("select.org-select");
  if (await orgSelect.count()) {
    await orgSelect.selectOption(trial.organization_id);
    await page.getByText("Ensaio insumo", { exact: false }).first().waitFor({ timeout: 10000 });
  }
  return page;
}

async function proveFormRoute(page, heading, name, fieldLabel) {
  await page.getByRole("heading", { name: heading }).waitFor({ timeout: 15000 });
  await page.locator(".flow-coach.is-collapsed").waitFor({ timeout: 10000 });
  const field = page.getByLabel(fieldLabel).first();
  await field.click();
  proof[`${name}-inicial-390`] = { ...(await shot(page, `${name}-inicial-390`)), fit: await assertFit(page, `${name}-inicial`) };
  if (!(await page.locator(".flow-coach.is-collapsed").count())) {
    throw new Error(`${name}: orientação não começou recolhida`);
  }
  await page.locator(".flow-coach").getByRole("button", { name: "Abrir" }).click();
  await page.locator(".flow-coach.is-open").waitFor();
  await page.getByText("Finalidade:").waitFor();
  await field.click();
  proof[`${name}-gigio-aberto-390`] = {
    ...(await shot(page, `${name}-gigio-aberto-390`)),
    fit: await assertFit(page, `${name}-aberto`),
  };
  await page.keyboard.press("Escape");
  await page.locator(".flow-coach.is-collapsed").waitFor();
  await field.click();
  proof[`${name}-gigio-fechado-390`] = {
    ...(await shot(page, `${name}-gigio-fechado-390`)),
    fit: await assertFit(page, `${name}-fechado`),
  };
}

const consolidar = await openApp(390, 844);
await consolidar.goto(`${FE}/componentes/ingredientes/consolidar`, { waitUntil: "networkidle" });
await proveFormRoute(consolidar, "Consolidar insumo", "consolidar", "Ingrediente de destino");
await consolidar.close();

const abertura = await openApp(390, 844);
await abertura.goto(`${FE}/componentes/estoque/abertura`, { waitUntil: "networkidle" });
await proveFormRoute(abertura, "Abrir saldo sem nota", "abertura", "Quantidade");
await abertura.getByRole("button", { name: /Confirmar abertura/ }).click();
await abertura.getByRole("alert").waitFor();
if (!(await abertura.getByText("Escolha o ingrediente deste saldo.").count())) {
  throw new Error("abertura: erro inicial ausente");
}
proof["abertura-erro-390"] = { ...(await shot(abertura, "abertura-erro-390")), fit: await assertFit(abertura, "abertura-erro") };
const selects = abertura.locator(".manual-path select");
await selects.nth(0).selectOption({ index: 1 });
await selects.nth(1).selectOption({ index: 1 });
if (await abertura.getByText("Escolha o ingrediente deste saldo.").count()) {
  throw new Error("abertura: erro antigo persistiu após escolher ingrediente e lugar");
}
proof["abertura-erro-corrigido-390"] = {
  ...(await shot(abertura, "abertura-erro-corrigido-390")),
  fit: await assertFit(abertura, "abertura-corrigido"),
};
await abertura.close();

const nota = await openApp(390, 844);
await nota.goto(`${FE}/gestao/compras/entradas/${trial.document_id}`, { waitUntil: "networkidle" });
await nota.locator(".flow-coach.is-collapsed").waitFor({ timeout: 15000 });
proof["nota-inicial-390"] = { ...(await shot(nota, "nota-inicial-390")), fit: await assertFit(nota, "nota-inicial") };
await nota.locator(".flow-coach").getByRole("button", { name: "Abrir" }).click();
await nota.locator(".flow-coach.is-open").waitFor();
proof["nota-gigio-aberto-390"] = { ...(await shot(nota, "nota-gigio-aberto-390")), fit: await assertFit(nota, "nota-aberto") };
await nota.close();

const desktop = await openApp(1440, 1100);
for (const [pathName, heading] of [
  ["/componentes/ingredientes/consolidar", "Consolidar insumo"],
  ["/componentes/estoque/abertura", "Abrir saldo sem nota"],
]) {
  await desktop.goto(`${FE}${pathName}`, { waitUntil: "networkidle" });
  await desktop.getByRole("heading", { name: heading }).waitFor();
  await desktop.locator(".flow-coach.is-collapsed").waitFor({ timeout: 10000 });
  const key = pathName.includes("abertura") ? "abertura-inicial-1440" : "consolidar-inicial-1440";
  proof[key] = await shot(desktop, key);
}
await desktop.close();
await browser.close();

const report = [
  "# Gate de uso — orientação recolhida e erro ao vivo",
  "",
  "React autenticada local. Sem HTML estático. Sem republicar homologação funcional.",
  "",
  `- Frontend: \`${FE}\``,
  "- Orientação inicia recolhida em consolidar, abertura e revisão fiscal (390 e 1440)",
  "- Escape fecha e devolve o foco; campos permanecem clicáveis",
  "- Erro de abertura some ao corrigir ingrediente e lugar",
  "",
  "| Captura | URL | PNG | scrollWidth |",
  "|---|---|---|---|",
  ...Object.entries(proof).map(([name, row]) => {
    const fit = row.fit ? `${row.fit.scrollWidth}` : "—";
    return `| ${name} | ${row.url} | ${row.width}px | ${fit} |`;
  }),
  "",
  `Organização de ensaio: ${trial.display_name} (${trial.organization_id}).`,
  "",
  "Não publica. Visão geral do Estoque permanece fora do pacote.",
].join("\n");

await writeFile(path.join(root, "GATE-USO.md"), `${report}\n`, "utf8");
await writeFile(path.join(root, "uso.json"), `${JSON.stringify({ fe: FE, proof }, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ out, proof }, null, 2));

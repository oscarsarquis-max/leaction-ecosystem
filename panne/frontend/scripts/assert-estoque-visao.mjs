import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../documentacao/evidencias/cursor-insumo-manual");
const out = path.join(root, "capturas-estoque");
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
    return { scrollWidth: rootEl.scrollWidth, clientWidth: rootEl.clientWidth, innerWidth: window.innerWidth };
  });
  if (metrics.innerWidth === 390 && (metrics.scrollWidth !== metrics.clientWidth || metrics.clientWidth !== 390)) {
    throw new Error(`${label}: viewport não cabe (${JSON.stringify(metrics)})`);
  }
  return metrics;
}

async function shot(page, name) {
  const url = page.url();
  if (url.includes("/entrar") || url.startsWith("file:")) throw new Error(`captura recusada (${name}) ${url}`);
  const file = path.join(out, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  const width = pngWidth(await readFile(file));
  if (name.includes("390") && width !== 390) throw new Error(`${name}: PNG ${width}px`);
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

const desktop = await openApp(1440, 1100);
await desktop.goto(`${FE}/componentes/estoque`, { waitUntil: "networkidle" });
await desktop.getByRole("heading", { name: "Estoque", exact: true }).waitFor();
await desktop.getByRole("heading", { name: "O que está no estoque" }).waitFor();
proof["estoque-1440"] = await shot(desktop, "estoque-1440");
if (await desktop.getByRole("button", { name: "Ver lotes" }).count()) {
  await desktop.getByRole("button", { name: "Ver lotes" }).first().click();
  proof["estoque-lotes-1440"] = await shot(desktop, "estoque-lotes-1440");
}
await desktop.close();

const mobile = await openApp(390, 844);
await mobile.goto(`${FE}/componentes/estoque`, { waitUntil: "networkidle" });
await mobile.getByRole("heading", { name: "Estoque", exact: true }).waitFor();
await mobile.getByRole("heading", { name: "O que está no estoque" }).waitFor();
const coach = mobile.getByRole("complementary", { name: "Orientação do processo" });
await coach.waitFor();
if (await coach.evaluate((node) => !node.classList.contains("is-collapsed"))) {
  throw new Error("estoque-390: orientação deveria iniciar recolhida");
}
proof["estoque-390"] = { ...(await shot(mobile, "estoque-390")), fit: await assertFit(mobile, "estoque-390") };
await mobile.getByRole("button", { name: "Ver lotes" }).first().click();
await mobile.getByRole("button", { name: "Ocultar lotes" }).first().waitFor();
if (await coach.evaluate((node) => !node.classList.contains("is-collapsed"))) {
  throw new Error("estoque-lotes-390: Ver lotes abriu a orientação");
}
if ((await mobile.getByText(/Finalidade/).count()) > 0) {
  throw new Error("estoque-lotes-390: corpo do Gigio visível após Ver lotes");
}
proof["estoque-lotes-390"] = {
  ...(await shot(mobile, "estoque-lotes-390")),
  fit: await assertFit(mobile, "estoque-lotes-390"),
};
await coach.getByRole("button", { name: "Abrir" }).click();
await coach.getByRole("button", { name: "Fechar" }).waitFor();
proof["estoque-gigio-390"] = {
  ...(await shot(mobile, "estoque-gigio-390")),
  fit: await assertFit(mobile, "estoque-gigio-390"),
};
await coach.getByRole("button", { name: "Fechar" }).click();
await coach.getByRole("button", { name: "Abrir" }).waitFor();
if (await coach.evaluate((node) => !node.classList.contains("is-collapsed"))) {
  throw new Error("estoque-gigio-fechado-390: Fechar não recolheu a orientação");
}
proof["estoque-gigio-fechado-390"] = {
  ...(await shot(mobile, "estoque-gigio-fechado-390")),
  fit: await assertFit(mobile, "estoque-gigio-fechado-390"),
};
await mobile.close();
await browser.close();

const report = [
  "# Visão geral do Estoque — prova visual para o Cortex",
  "",
  "React autenticada local. Sem publicação. Sem mutação de dados reais.",
  "",
  `- Frontend: \`${FE}\``,
  "- Rota: `/componentes/estoque`",
  "- Prévia aprovada: `previa-estoque/estoque-util.html`",
  "- 1440: tabela; 390: cartões, Ver lotes sem abrir Gigio, abertura explícita; scrollWidth = 390",
  "",
  "| Captura | URL | PNG |",
  "|---|---|---|",
  ...Object.entries(proof).map(([name, row]) => `| ${name} | ${row.url} | ${row.width}px |`),
  "",
  `Organização de ensaio: ${trial.display_name} (${trial.organization_id}).`,
].join("\n");

await writeFile(path.join(root, "GATE-ESTOQUE.md"), `${report}\n`, "utf8");
await writeFile(path.join(root, "estoque.json"), `${JSON.stringify({ fe: FE, proof }, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ out, proof }, null, 2));

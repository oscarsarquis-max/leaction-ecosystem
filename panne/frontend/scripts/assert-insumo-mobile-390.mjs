import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../documentacao/evidencias/cursor-insumo-manual");
const out = path.join(root, "capturas-mobile-390");
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
    const root = document.documentElement;
    const offenders = [...document.querySelectorAll("body *")]
      .filter((node) => node.getBoundingClientRect().right > root.clientWidth + 1)
      .slice(0, 8)
      .map((node) => {
        const box = node.getBoundingClientRect();
        return `${node.tagName.toLowerCase()}.${node.className}`.replace(/\s+/g, ".") + `@${Math.round(box.right)}`;
      });
    return {
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      innerWidth: window.innerWidth,
      offenders,
    };
  });
  if (metrics.scrollWidth !== metrics.clientWidth || metrics.clientWidth !== 390) {
    throw new Error(
      `${label}: viewport não cabe (${JSON.stringify(metrics)}). Não usar scale; refluir o chrome.`,
    );
  }
  return metrics;
}

async function shot(page, name) {
  const url = page.url();
  if (url.includes("/entrar")) {
    throw new Error(`captura recusada: caiu em /entrar (${name}) ${url}`);
  }
  if (url.startsWith("file:")) {
    throw new Error(`captura recusada: HTML estático (${name}) ${url}`);
  }
  const file = path.join(out, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  const width = pngWidth(await readFile(file));
  if (name.includes("390") && width !== 390) {
    throw new Error(`${name}: PNG tem ${width}px, esperado 390. url=${url}`);
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
  const page = await browser.newPage({
    viewport: { width, height },
    deviceScaleFactor: 1,
  });
  await page.addInitScript(
    ({ orgId }) => {
      sessionStorage.setItem("panne.demoSubject", "local-dev-owner");
      localStorage.setItem("panne.activeOrganization", orgId);
    },
    { orgId: trial.organization_id },
  );
  await page.goto(`${FE}/entrar`, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    sessionStorage.setItem("panne.demoSubject", "local-dev-owner");
  });
  await page.getByRole("button", { name: "Entrar em desenvolvimento" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 15000 });
  const orgSelect = page.locator("select.org-select");
  if (await orgSelect.count()) {
    await orgSelect.selectOption(trial.organization_id);
    await page.getByText("Ensaio insumo", { exact: false }).first().waitFor({ timeout: 10000 });
  } else if (page.url().includes("/organizacao") || (await page.getByRole("heading", { name: "Escolha a organização" }).count())) {
    await page.getByRole("button", { name: /Ensaio insumo/ }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 10000 });
  }
  return page;
}

const consolidar = await openApp(390, 844);
await consolidar.goto(`${FE}/componentes/ingredientes/consolidar`, { waitUntil: "networkidle" });
await consolidar.getByRole("heading", { name: "Consolidar insumo" }).waitFor({ timeout: 15000 });
proof["consolidar-390"] = { ...(await shot(consolidar, "consolidar-390")), fit: await assertFit(consolidar, "consolidar-390") };

const dest = consolidar.locator(".manual-path select").first();
await dest.locator('option:not([value=""])').first().waitFor({ state: "attached", timeout: 15000 });
await dest.selectOption(await dest.locator('option:not([value=""])').first().getAttribute("value"));
await consolidar.locator('input[type="checkbox"]').first().waitFor({ timeout: 10000 });
await consolidar.locator('input[type="checkbox"]').first().check();
proof["consolidar-selecao-390"] = {
  ...(await shot(consolidar, "consolidar-selecao-390")),
  fit: await assertFit(consolidar, "consolidar-selecao-390"),
};
await consolidar.getByRole("button", { name: "Confirmar vínculos" }).click();
await consolidar.locator(".manual-success, [role='alert']").first().waitFor({ timeout: 15000 });
const consolidarAfter = (await consolidar.locator(".manual-success").count()) ? "consolidar-sucesso-390" : "consolidar-erro-390";
proof[consolidarAfter] = { ...(await shot(consolidar, consolidarAfter)), fit: await assertFit(consolidar, consolidarAfter) };
await consolidar.close();

const abertura = await openApp(390, 844);
await abertura.goto(`${FE}/componentes/estoque/abertura`, { waitUntil: "networkidle" });
await abertura.getByRole("heading", { name: "Abrir saldo sem nota" }).waitFor();
proof["abertura-390"] = { ...(await shot(abertura, "abertura-390")), fit: await assertFit(abertura, "abertura-390") };
await abertura.getByRole("button", { name: /Confirmar abertura|Registrar abertura/ }).click();
await abertura.getByRole("alert").waitFor();
proof["abertura-erro-390"] = { ...(await shot(abertura, "abertura-erro-390")), fit: await assertFit(abertura, "abertura-erro-390") };
const aberturaSelects = abertura.locator(".manual-path select");
await aberturaSelects.nth(0).locator('option:not([value=""])').first().waitFor({ state: "attached" });
await aberturaSelects.nth(0).selectOption({ index: 1 });
await aberturaSelects.nth(1).selectOption({ index: 1 });
await abertura.locator(".manual-path input[inputMode='decimal']").first().fill("1");
await abertura.getByPlaceholder("Ex.: contagem física da despensa").fill("ensaio visual descartável");
await abertura.getByLabel("Custo desconhecido").check();
await abertura.getByLabel(/Confirmo esta abertura|Revise/).check();
proof["abertura-selecao-390"] = {
  ...(await shot(abertura, "abertura-selecao-390")),
  fit: await assertFit(abertura, "abertura-selecao-390"),
};
await abertura.getByRole("button", { name: /Confirmar abertura|Registrar abertura/ }).click();
await abertura.locator(".manual-success, [role='alert']").first().waitFor({ timeout: 15000 });
const aberturaAfter = (await abertura.locator(".manual-success").count()) ? "abertura-sucesso-390" : "abertura-pos-selecao-390";
proof[aberturaAfter] = { ...(await shot(abertura, aberturaAfter)), fit: await assertFit(abertura, aberturaAfter) };
await abertura.close();

const nota = await openApp(390, 844);
await nota.goto(`${FE}/gestao/compras/entradas/${trial.document_id}`, { waitUntil: "networkidle" });
if (nota.url().includes("/entrar")) throw new Error("revisão da nota caiu em /entrar");
await nota.getByRole("heading", { name: /Nota|Revisão|Documento/ }).first().waitFor({ timeout: 15000 });
proof["nota-revisao-390"] = { ...(await shot(nota, "nota-revisao-390")), fit: await assertFit(nota, "nota-revisao-390") };
await nota.close();

const desktop = await openApp(1440, 1100);
await desktop.goto(`${FE}/componentes/ingredientes/consolidar`, { waitUntil: "networkidle" });
await desktop.getByRole("heading", { name: "Consolidar insumo" }).waitFor();
const compose = await desktop.evaluate(() => {
  const paper = document.querySelector(".manual-path");
  const box = paper?.getBoundingClientRect();
  return {
    paperWidth: box ? Math.round(box.width) : null,
    paperLeft: box ? Math.round(box.x) : null,
    viewport: window.innerWidth,
  };
});
const expectedLeft = Math.round((1440 - (compose.paperWidth || 0)) / 2);
if (!compose.paperWidth || compose.paperWidth > 960 || Math.abs((compose.paperLeft ?? 0) - expectedLeft) > 24) {
  throw new Error(`1440: composição não está centrada em 960 px (${JSON.stringify({ ...compose, expectedLeft })})`);
}
proof["consolidar-1440"] = { ...(await shot(desktop, "consolidar-1440")), compose };
await desktop.goto(`${FE}/componentes/estoque/abertura`, { waitUntil: "networkidle" });
await desktop.getByRole("heading", { name: "Abrir saldo sem nota" }).waitFor();
proof["abertura-1440"] = await shot(desktop, "abertura-1440");
await desktop.goto(`${FE}/gestao/compras/entradas/${trial.document_id}`, { waitUntil: "networkidle" });
proof["nota-revisao-1440"] = await shot(desktop, "nota-revisao-1440");
await desktop.close();

await browser.close();

const report = [
  "# Gate mobile 390 — caminho manual de insumo",
  "",
  "Prova dirigida do ajuste visual. Aplicação React autenticada (fake local), não HTML estático.",
  "",
  `- Frontend: \`${FE}\``,
  `- Viewport 390: \`document.documentElement.scrollWidth === clientWidth === 390\``,
  "- PNG full-page das rotas 390 com largura intrínseca 390 px",
  "- Desktop 1440: \`.manual-path\` centrado com largura ≤ 960 px",
  "- Sem `transform: scale`",
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
  "Não publica. Não altera dados reais. Visão geral do Estoque permanece a atual.",
].join("\n");

await writeFile(path.join(root, "GATE-MOBILE-390.md"), `${report}\n`, "utf8");
await writeFile(path.join(root, "mobile-390.json"), `${JSON.stringify({ fe: FE, proof }, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ out, proof }, null, 2));

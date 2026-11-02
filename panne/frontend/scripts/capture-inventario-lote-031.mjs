import { mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.resolve(here, "../../documentacao/evidencias/cursor-031/capturas");
const trialPath = process.env.PANNE_TRIAL || path.join(os.tmpdir(), "c031-trial.json");
const FE = process.env.PANNE_FE_URL || "http://127.0.0.1:5183";

const PASTED = [
  "Farinha de trigo tipo 1\t25\tkg\t15/03/2027\t4,80",
  "Açúcar cristal\t10\tkg",
  "Fermento biológico\t3\tpacote\t01/12/2026",
  "Sal marinho\t5\tkg",
  "Manteiga sem sal\t2\tun\t\t32,50",
].join("\n");

const trial = JSON.parse(await readFile(trialPath, "utf8"));
await mkdir(out, { recursive: true });
const browser = await chromium.launch();
const report = {};

async function openApp(width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.addInitScript(
    ({ orgId }) => {
      sessionStorage.setItem("panne.demoSubject", "local-dev-owner");
      localStorage.setItem("panne.activeOrganization", orgId);
    },
    { orgId: trial.organization_id },
  );
  await page.goto(`${FE}/entrar`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Entrar em desenvolvimento" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 15000 });
  const orgSelect = page.locator("select.org-select");
  if (await orgSelect.count()) await orgSelect.selectOption(trial.organization_id);
  return page;
}

async function shot(page, name, width) {
  if (page.url().includes("/entrar")) throw new Error(`captura recusada: caiu em /entrar (${name})`);
  const file = `${width}-${name}.png`;
  await page.screenshot({ path: path.join(out, file), fullPage: true });
  report[file] = page.url();
}

async function run(width, height) {
  const page = await openApp(width, height);
  await page.goto(`${FE}/componentes/estoque/inventario`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Inventário inicial" }).waitFor({ timeout: 15000 });
  await page.waitForFunction(() => {
    const select = document.querySelector(".inv-batch__top select");
    return select && select.value !== "";
  });

  // Medidas: nada pode estourar a largura da tela.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  report[`${width}-estouro-horizontal-px`] = overflow;

  await shot(page, "1-vazia", width);

  await page.getByRole("textbox", { name: "Colar da planilha" }).fill(PASTED);
  await page.getByRole("button", { name: "Preencher a tabela" }).click();
  await page.getByText(/5 linhas preenchidas/).waitFor();
  await shot(page, "2-cinco-linhas-coladas", width);

  // Erro numa linha: a quantidade do açúcar some e o conteúdo do fermento ainda falta.
  const rows = page.locator("li[data-row-id]");
  await rows.nth(1).getByLabel(/^Quantidade/).fill("");
  await page.getByRole("button", { name: "Gravar inventário" }).click();
  await page.getByRole("alert").first().waitFor();
  await shot(page, "3-erro-numa-linha", width);
  await rows.nth(1).screenshot({ path: path.join(out, `${width}-3b-erro-detalhe-linha.png`) });

  // Corrige e mostra a revisão antes de gravar.
  await rows.nth(1).getByLabel(/^Quantidade/).fill("10");
  await rows.nth(2).getByLabel(/^Conteúdo de cada embalagem/).fill("500");
  await page.getByTestId("resumo-inventario").scrollIntoViewIfNeeded();
  await shot(page, "4-revisao", width);
  report[`${width}-resumo`] = await page.getByTestId("resumo-inventario").innerText();

  const sizes = await page.evaluate(() => {
    const smallest = (selector) =>
      Math.min(...Array.from(document.querySelectorAll(selector)).map((el) => el.getBoundingClientRect().height));
    return {
      inputs: smallest(".inv-row input, .inv-row select"),
      buttons: smallest(".inv-row button"),
    };
  });
  report[`${width}-menor-alvo-px`] = sizes;

  if (width === 1440) {
    // Grava de verdade na organização descartável: prova de ponta a ponta.
    await page.getByRole("button", { name: "Gravar inventário" }).click();
    await page.getByTestId("inventario-gravado").waitFor({ timeout: 20000 });
    report["gravado-texto"] = await page.getByTestId("inventario-gravado").innerText();
    await shot(page, "5-gravado", width);
    await page.getByRole("link", { name: "Abrir a Visão geral do estoque" }).click();
    await page.getByRole("heading", { name: "Estoque", exact: true }).waitFor({ timeout: 15000 });
    await shot(page, "6-visao-geral-depois", width);
  }
  await page.close();
}

const only = (process.env.WIDTHS || "1440,390").split(",").map(Number);
if (only.includes(1440)) await run(1440, 1000);
if (only.includes(390)) await run(390, 844);
await browser.close();
await writeFile(path.join(out, "..", `capturas-${(process.env.WIDTHS || "1440-390").replace(",", "-")}.json`), `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));

import { mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.resolve(here, "../../documentacao/evidencias/cursor-033/capturas");
const trialPath = process.env.PANNE_TRIAL || path.join(os.tmpdir(), "c033-trial.json");
const FE = process.env.PANNE_FE_URL || "http://127.0.0.1:5193";

const PASTED = [
  "Farinha de trigo tipo 1\t25\tkg\t15/03/2027\t4,80",
  "Açucar cristalino\t10\tkg\t\t3,90",
  "Fermento biológico\t3\tpacote\t01/12/2026\t9,90",
  "Manteiga\t2\tun\t\t32,50",
  "Leite longa vida\t4\tl",
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

async function shot(page, name, width, fullPage = true) {
  if (page.url().includes("/entrar")) throw new Error(`captura recusada: caiu em /entrar (${name})`);
  const file = `${width}-${name}.png`;
  await page.screenshot({ path: path.join(out, file), fullPage });
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
  const rows = page.locator("li[data-row-id]");

  await page.getByRole("textbox", { name: "Colar da planilha" }).fill(PASTED);
  await page.getByRole("button", { name: "Preencher a tabela" }).click();
  await page.getByText(/5 linhas preenchidas/).waitFor();

  // Fermento: embalagem sem conteúdo, marcada na hora. Celular: abre os detalhes para ver o campo.
  if (width < 721) await rows.nth(2).getByRole("button", { name: /^Detalhes da linha 3/ }).click();

  // 1) Um parecido a decidir + uma linha incompleta + Gravar desligado com o motivo.
  await shot(page, "1-parecido-e-incompleta", width, width >= 721);
  if (width < 721) await shot(page, "1b-rodape-fixo-viewport", width, false);
  await rows.nth(1).screenshot({ path: path.join(out, `${width}-1c-parecido-detalhe.png`) });
  await rows.nth(2).screenshot({ path: path.join(out, `${width}-1d-incompleta-detalhe.png`) });
  report[`${width}-gravar-desabilitado`] = await page.getByRole("button", { name: "Gravar inventário" }).isDisabled();
  report[`${width}-motivo`] = await page.getByTestId("motivo-bloqueio").innerText();
  report[`${width}-resumo-antes`] = await page.getByTestId("resumo-inventario").innerText();

  // Medidas: nada estoura a largura e os alvos de toque têm 44 px.
  report[`${width}-estouro-horizontal-px`] = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  report[`${width}-menor-alvo-px`] = await page.evaluate(() => {
    const visible = (el) => {
      const box = el.getBoundingClientRect();
      return box.width > 0 && box.height > 0;
    };
    const heights = (selector) =>
      Array.from(document.querySelectorAll(selector))
        .filter(visible)
        .map((el) => el.getBoundingClientRect().height);
    return {
      campos: Math.min(...heights(".inv-row input, .inv-row select")),
      botoes: Math.min(...heights(".inv-row button, .inv-decision__btn, .inv-batch__save")),
    };
  });
  if (width >= 1101) {
    // Título de cada coluna alinhado ao campo da linha (diferença da borda esquerda, em px).
    report[`${width}-alinhamento-titulo-campo-px`] = await page.evaluate(() => {
      const head = Array.from(document.querySelectorAll(".inv-grid__head > span"));
      const row = document.querySelector("li[data-row-id]");
      const cells = [
        [".inv-field--ingredient", 1],
        [".inv-field--qty", 2],
        [".inv-field--unit", 3],
        [".inv-field--pack", 4],
        [".inv-field--expires", 5],
        [".inv-field--lot", 6],
        [".inv-field--cost", 7],
      ];
      const result = {};
      for (const [selector, index] of cells) {
        const field = row.querySelector(selector);
        if (!field || !head[index]) continue;
        result[`${selector} / ${head[index].textContent.trim()}`] = Math.round(
          head[index].getBoundingClientRect().left - field.getBoundingClientRect().left,
        );
      }
      return result;
    });
    // Menu ⋯
    await rows.nth(0).getByRole("button", { name: /^Mais ações da linha 1/ }).click();
    await shot(page, "1e-menu-reticencias", width, false);
    await page.keyboard.press("Escape");
  }

  // Litro e ml: oferta e conversão.
  await rows.nth(4).screenshot({ path: path.join(out, `${width}-1f-litro-oferta.png`) });
  await rows.nth(4).getByRole("button", { name: /^Lançar como embalagem/ }).click();
  report[`${width}-litro-convertido`] = {
    unidade: await rows.nth(4).getByLabel(/^Unidade da linha/).inputValue(),
    conteudo: await rows.nth(4).getByLabel(/^Conteúdo de cada embalagem/).inputValue(),
  };

  // Decide: Açúcar usa o do cadastro; Manteiga vira novo; fermento ganha o conteúdo.
  await rows.nth(1).getByRole("button", { name: /^Usar este/ }).click();
  await rows.nth(3).getByRole("button", { name: /^Criar novo/ }).click();
  await rows.nth(2).getByLabel(/^Conteúdo de cada embalagem/).fill("500");

  // 2) Revisão com o total.
  await page.getByTestId("valor-total").scrollIntoViewIfNeeded();
  await shot(page, "2-revisao-com-total", width, false);
  if (width >= 721) await page.locator(".inv-batch__review").screenshot({ path: path.join(out, `${width}-2b-revisao-detalhe.png`) });
  report[`${width}-resumo-depois`] = await page.getByTestId("resumo-inventario").innerText();
  report[`${width}-valor-total`] = await page.getByTestId("valor-total").innerText();
  report[`${width}-gravar-habilitado`] = await page.getByRole("button", { name: "Gravar inventário" }).isEnabled();
  report[`${width}-rodape-fixo`] = await page.evaluate(() => {
    const box = document.querySelector(".inv-batch__review").getBoundingClientRect();
    return { fimDoRodape: Math.round(box.bottom), alturaDaTela: window.innerHeight, sticky: getComputedStyle(document.querySelector(".inv-batch__review")).position };
  });

  if (width === 1440) {
    // Grava de verdade na organização descartável.
    await page.getByRole("button", { name: "Gravar inventário" }).click();
    await page.getByTestId("inventario-gravado").waitFor({ timeout: 20000 });
    report["gravado-texto"] = await page.getByTestId("inventario-gravado").innerText();
    await shot(page, "3-gravado", width, false);
  }
  await page.close();
}

const only = (process.env.WIDTHS || "1440,390").split(",").map(Number);
// 390 primeiro: o 1440 grava de verdade e depois "Manteiga" deixaria de ser parecido.
if (only.includes(390)) await run(390, 844);
if (only.includes(1440)) await run(1440, 1000);
await browser.close();
await writeFile(
  path.join(out, "..", `capturas-${(process.env.WIDTHS || "1440-390").replace(",", "-")}.json`),
  `${JSON.stringify(report, null, 2)}\n`,
  "utf8",
);
console.log(JSON.stringify(report, null, 2));

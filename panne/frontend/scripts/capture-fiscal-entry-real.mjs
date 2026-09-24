import { mkdirSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, "../../documentacao/evidencias/fiscal-entry-real");
mkdirSync(outDir, { recursive: true });

const base = process.env.PANNE_CAPTURE_URL || "http://127.0.0.1:5197";
const orgId = process.env.PANNE_TRIAL_ORG_ID || "";
const orgName = process.env.PANNE_TRIAL_ORG_NAME || "Ensaio fiscal";
const stamp = String(Date.now()).slice(-6);
const notes = [];

const JPEG = Buffer.from(
  "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBwgHBgkIBwgKCgkLDRYPDQwMDRsUFRAWIB0iIiAdHx8kKDQsJCYxJx8fLT0tMTU3Ojo6Iys/RD84QzQ5OjcBCgoKDQwNGg8PGjclHyU3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3Nzc3N//AABEIAAEAAQMBIgACEQEDEQH/xAGiAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgsQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCqpNDQ2Nzo5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7O0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCqpNDQ2Nzo5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7O0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCqpNDQ2Nzo5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7O0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIQAxAAAAH/2Q==",
  "base64",
);

function log(message) {
  notes.push(message);
  console.log(message);
}

async function shot(page, name) {
  const dest = resolve(outDir, `${name}.png`);
  const url = page.url();
  if (url.includes("/entrar")) {
    throw new Error(`captura recusada: caiu em /entrar (${name}) ${url}`);
  }
  await page.screenshot({ path: dest, fullPage: true });
  log(`${name} ${url} ${dest}`);
}

async function chooseOrg(page) {
  if (orgId) {
    await page.evaluate((id) => localStorage.setItem("panne.activeOrganization", id), orgId);
  }
  const picker = page.getByRole("heading", { name: "Escolha a organização" });
  if (await picker.isVisible().catch(() => false)) {
    const named = page.getByRole("button", { name: new RegExp(orgName, "i") });
    if (await named.count()) {
      await named.first().click();
    } else if (orgId) {
      await page.locator("select.org-select").selectOption(orgId).catch(() => {});
    }
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 15000 });
  }
}

async function login(page) {
  await page.goto(`${base}/entrar`, { waitUntil: "domcontentloaded" });
  const enter = page.getByRole("button", { name: "Entrar em desenvolvimento" });
  await enter.waitFor({ timeout: 20000 });
  await enter.click();
  await page.waitForURL((url) => !url.pathname.endsWith("/entrar"), { timeout: 20000 });
  await chooseOrg(page);
}

async function openEntry(page) {
  await page.goto(`${base}/gestao/compras/entradas/nova`, { waitUntil: "domcontentloaded" });
  await chooseOrg(page);
  try {
    await page.getByRole("heading", { name: "Registrar entrada" }).waitFor({ timeout: 20000 });
  } catch (error) {
    await page.screenshot({ path: resolve(outDir, "debug-falha.png"), fullPage: true });
    log(`url=${page.url()}`);
    log(`h1=${JSON.stringify(await page.locator("h1,h2,[role=status],[role=alert]").allTextContents())}`);
    throw error;
  }
}

async function fillValidNote(page, { withKey }) {
  if (withKey) {
    await page.getByLabel("Chave de acesso").fill(`35260812345678000190550010005066121${stamp.padStart(9, "0")}`);
  }
  await page.getByLabel("Número da nota").fill(withKey ? `50${stamp.slice(-3)}` : `41${stamp.slice(-3)}`);
  await page.getByLabel("Série").fill("1");
  await page.getByLabel("Data de emissão").fill("2026-09-18");
  await page.getByLabel("Fornecedor", { exact: true }).fill("Moinho Real do Ensaio");
  await page.getByLabel("CNPJ do fornecedor").fill("12345678000190");
  await page.getByLabel("Descrição").fill("Farinha tipo 1");
  await page.getByLabel("Quantidade").fill("25");
  await page.getByLabel("Unidade").fill("KG");
  await page.getByLabel("Valor unitário").fill("4.10");
}

async function runViewport(browser, width, height, suffix) {
  const page = await browser.newPage({ viewport: { width, height } });
  if (orgId) {
    await page.addInitScript((id) => {
      try {
        localStorage.setItem("panne.activeOrganization", id);
      } catch {
        /* ignore */
      }
    }, orgId);
  }
  page.on("pageerror", (error) => log(`pageerror ${suffix}: ${error.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") log(`console.error ${suffix}: ${msg.text()}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) {
      log(`http ${suffix} ${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  await login(page);
  await openEntry(page);
  await shot(page, `inicial-${suffix}`);

  await page.getByRole("button", { name: "Revisar e gravar" }).click();
  await page.getByText("Informe o fornecedor.").waitFor();
  await shot(page, `erro-${suffix}`);

  await fillValidNote(page, { withKey: suffix.startsWith("1440") });
  await page.getByRole("button", { name: "Revisar e gravar" }).click();
  await page.getByRole("heading", { name: "Revisão" }).waitFor();
  await shot(page, `revisao-${suffix}`);

  if (suffix.startsWith("390")) {
    await page.getByLabel("Quero guardar o arquivo com esta nota").check();
    await page.getByLabel("Arquivo de referência").setInputFiles({
      name: "danfe-ensaio.jpeg",
      mimeType: "image/jpeg",
      buffer: JPEG,
    });
    await shot(page, `anexo-${suffix}`);
    await page.getByRole("button", { name: "Gravar nota" }).click();
    await page.getByText(/Nota gravada · estoque pendente/).waitFor({ timeout: 20000 });
    await page.getByText(/Referência guardada/).waitFor({ timeout: 20000 });
    await shot(page, `gravada-${suffix}`);
  } else {
    await page.getByRole("button", { name: "Gravar nota" }).click();
    await page.getByText(/Nota gravada · estoque pendente/).waitFor({ timeout: 20000 });
    await shot(page, `gravada-${suffix}`);
    await page.getByLabel("Arquivo de referência").setInputFiles({
      name: "danfe-ensaio.jpeg",
      mimeType: "image/jpeg",
      buffer: JPEG,
    });
    await page.getByRole("button", { name: "Guardar referência" }).click();
    await page.getByText(/Referência guardada/).waitFor({ timeout: 20000 });
    await shot(page, `anexo-${suffix}`);
  }
  await page.close();
}

const browser = await chromium.launch({ headless: true });
try {
  await runViewport(browser, 1440, 900, "1440");
  await runViewport(browser, 390, 844, "390");
  writeFileSync(resolve(outDir, "captura-log.txt"), notes.join("\n"), "utf8");
} finally {
  await browser.close();
}

import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, "../../documentacao/evidencias/cursor-028-r3-executive-dashboard");
mkdirSync(outDir, { recursive: true });

const base = process.env.PANNE_FE_URL || "http://127.0.0.1:5180";

async function login(page, subject = "demo-owner") {
  await page.goto(`${base}/entrar`, { waitUntil: "networkidle" });
  const select = page.locator("select").first();
  if (await select.count()) await select.selectOption(subject);
  await page.getByRole("button", { name: /Entrar/ }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 20000 });
  await chooseOrg(page, "Panne Demonstração");
}

async function chooseOrg(page, label) {
  const heading = page.getByRole("heading", { name: "Escolha a organização" });
  try {
    await heading.waitFor({ timeout: 4000 });
    await page.getByRole("button", { name: label }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 20000 });
  } catch {
    /* já autenticado */
  }
}

async function openInicio(page) {
  await page.goto(`${base}/inicio`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 20000 });
}

async function attachConsole(page) {
  await page.addInitScript(() => {
    window.__panneConsoleErrors = [];
    const orig = console.error;
    console.error = (...args) => {
      window.__panneConsoleErrors.push(String(args[0] ?? "error"));
      orig.apply(console, args);
    };
  });
  page.on("pageerror", (err) => console.log("pageerror", err.message));
}

async function shot(page, name, fullPage = true) {
  const dest = resolve(outDir, `${name}.png`);
  await page.screenshot({ path: dest, fullPage });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  const errors = await page.evaluate(() => window.__panneConsoleErrors || []);
  console.log(dest, overflow ? "scrollWidth_ok" : "OVERFLOW", errors.length ? `console:${errors.length}` : "console_ok");
}

const browser = await chromium.launch();
const page = await browser.newPage();
await attachConsole(page);

try {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page, "demo-owner");
  await openInicio(page);
  await page.screenshot({
    path: resolve(outDir, "01-desktop-1440-primeira-dobra.png"),
    clip: { x: 0, y: 0, width: 1440, height: 900 },
  });
  console.log("01 primeira dobra");
  await shot(page, "02-desktop-agenda-custos");

  await page.locator("label").filter({ hasText: "Últimos 7 dias" }).click();
  await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 20000 });
  await shot(page, "12-periodo-7-dias");
  await page.locator("label").filter({ hasText: /^Hoje$/ }).click();

  await page.setViewportSize({ width: 768, height: 1024 });
  await openInicio(page);
  await shot(page, "09-tablet-768");

  await page.setViewportSize({ width: 390, height: 844 });
  await openInicio(page);
  await shot(page, "10-mobile-390");
  await page.getByRole("button", { name: "Abrir Gigio" }).click();
  await page.getByRole("dialog", { name: "Gigio" }).waitFor();
  await shot(page, "11-gigio-aberto-mobile", false);
  await page.getByRole("button", { name: "Fechar" }).click();

  await page.setViewportSize({ width: 1440, height: 900 });
  await openInicio(page);
  const org = page.locator("select[aria-label='Organização ativa']");
  const horizonte = await org.evaluate((el) => {
    const opt = [...el.options].find((o) => /Horizonte/i.test(o.textContent || ""));
    return opt ? opt.value : "";
  });
  if (horizonte) {
    await org.selectOption(horizonte);
    await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 20000 });
    await shot(page, "03-movimentacoes-vazio");
    await shot(page, "04-ontem-vazio-consolidado");
    await shot(page, "08-horizonte-vazio");
  }

  await page.goto(`${base}/entrar`, { waitUntil: "networkidle" });
  await login(page, "demo-owner");
  await openInicio(page);
  await shot(page, "05-custos-cinco-produtos");
  await shot(page, "06-produto-comprado");

  await page.goto(`${base}/entrar`, { waitUntil: "networkidle" });
  await login(page, "demo-baker");
  await page.goto(`${base}/inicio`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 20000 });
  await shot(page, "07-padeiro-sem-economia");
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}

import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-028-r3-executive-dashboard/nav-hotfix-matrix.json");
const base = process.env.PANNE_FE_URL || "https://demo.panne.ia.br";

const MENU = [
  { name: "Fluxo produtivo", expect: "/fluxo" },
  { name: "Produção", expect: "/producao" },
  { name: "Estoque e insumos", expect: "/componentes/estoque" },
  { name: "Produtos e receitas", expect: "/produtos" },
  { name: "Conformidade", expect: "/conformidade" },
  { name: "Gestão", expect: "/gestao/custos" },
  { name: "Relatórios", expect: "/gestao/relatorios" },
];

const CTAS = [
  { name: "Abrir produção", expect: "/producao" },
  { name: "Abrir custos e preços", expect: "/gestao/custos" },
  { name: "Abrir Fluxo produtivo", expect: "/fluxo" },
  { name: "Ver todas as pendências", expect: "/gestao/relatorios" },
];

async function login(page) {
  await page.goto(`${base}/entrar`, { waitUntil: "networkidle" });
  const select = page.locator("select").first();
  if (await select.count()) await select.selectOption("demo-owner");
  await page.getByRole("button", { name: /Entrar/ }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 20000 });
  try {
    await page.getByRole("heading", { name: "Escolha a organização" }).waitFor({ timeout: 4000 });
    await page.getByRole("button", { name: "Panne Demonstração" }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 20000 });
  } catch {
    /* already in */
  }
}

async function goInicio(page) {
  await page.goto(`${base}/inicio`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 20000 });
}

async function openMenuIfNeeded(page, width) {
  if (width > 1120) return "inline";
  await page.locator("button.nav-toggle").click();
  await page.locator("nav.shell-nav.is-open").waitFor({ timeout: 5000 });
  return "open";
}

async function setGigio(page, open) {
  const dialog = page.getByRole("dialog", { name: "Gigio" });
  const visible = await dialog.isVisible().catch(() => false);
  if (open && !visible) {
    await page.getByRole("button", { name: "Abrir Gigio" }).click();
    await dialog.waitFor({ timeout: 8000 });
  }
  if (!open && visible) {
    await dialog.getByRole("button", { name: "Fechar" }).click();
    await dialog.waitFor({ state: "hidden", timeout: 8000 });
  }
}

async function clickLink(page, name) {
  const link = page.getByRole("link", { name, exact: true }).first();
  await link.scrollIntoViewIfNeeded();
  const box = await link.boundingBox();
  if (!box) throw new Error(`no box: ${name}`);
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(600);
  return new URL(page.url()).pathname.replace(/\/$/, "") || "/";
}

const rows = [];
let failed = false;
const browser = await chromium.launch();

try {
  for (const viewport of [
    { w: 1440, h: 900 },
    { w: 390, h: 844 },
  ]) {
    const page = await browser.newPage({ viewport: { width: viewport.w, height: viewport.h } });
    await login(page);

    for (const gigio of ["closed", "open"]) {
      for (const item of MENU) {
        await goInicio(page);
        await setGigio(page, gigio === "open");
        const menu = await openMenuIfNeeded(page, viewport.w);
        const path = await clickLink(page, item.name);
        const ok = path === item.expect || path.startsWith(item.expect);
        rows.push({ viewport: `${viewport.w}x${viewport.h}`, gigio, menu, target: item.name, expect: item.expect, got: path, ok });
        if (!ok) failed = true;
        console.log(`${viewport.w} gigio=${gigio} menu ${item.name} -> ${path} ${ok ? "PASS" : "FAIL"}`);
      }
    }

    await goInicio(page);
    await setGigio(page, false);
    for (const item of CTAS) {
      await goInicio(page);
      const path = await clickLink(page, item.name);
      const ok = path === item.expect || path.startsWith(item.expect);
      rows.push({ viewport: `${viewport.w}x${viewport.h}`, gigio: "closed", menu: "n/a", target: item.name, expect: item.expect, got: path, ok });
      if (!ok) failed = true;
      console.log(`${viewport.w} CTA ${item.name} -> ${path} ${ok ? "PASS" : "FAIL"}`);
    }

    await goInicio(page);
    await setGigio(page, true);
    await page.getByRole("dialog", { name: "Gigio" }).getByRole("button", { name: "Fechar" }).click();
    await openMenuIfNeeded(page, viewport.w);
    const pathAfterClose = await clickLink(page, "Produção");
    const okClose = pathAfterClose === "/producao";
    rows.push({ viewport: `${viewport.w}x${viewport.h}`, gigio: "closed-after-open", target: "Produção", expect: "/producao", got: pathAfterClose, ok: okClose });
    if (!okClose) failed = true;
    await page.close();
  }
} catch (error) {
  console.error(error);
  failed = true;
} finally {
  writeFileSync(out, JSON.stringify({ browser: "chromium", base, rows }, null, 2));
  await browser.close();
}
process.exit(failed ? 1 : 0);

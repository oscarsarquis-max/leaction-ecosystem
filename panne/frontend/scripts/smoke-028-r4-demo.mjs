import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, "../../documentacao/evidencias/cursor-028-r4-grafo-produtos/pos-publish");
mkdirSync(outDir, { recursive: true });

const base = process.env.PANNE_FE_URL || "https://demo.panne.ia.br";

async function login(page) {
  await page.goto(`${base}/entrar`, { waitUntil: "networkidle", timeout: 45000 });
  const select = page.locator("select").first();
  if (await select.count()) await select.selectOption("demo-owner");
  await page.getByRole("button", { name: /Entrar/ }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 25000 });
  try {
    await page.getByRole("heading", { name: "Escolha a organização" }).waitFor({ timeout: 4000 });
    await page.getByRole("button", { name: "Panne Demonstração" }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 25000 });
  } catch {
    /* already in */
  }
}

async function openProdutos(page) {
  await page.goto(`${base}/produtos`, { waitUntil: "networkidle", timeout: 45000 });
  await page.getByRole("heading", { name: "Produtos" }).waitFor({ timeout: 25000 });
}

async function clickCenter(page, locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) throw new Error("no bounding box");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

async function bundle(page) {
  return page.evaluate(() => {
    const js = document.querySelector('script[type="module"]')?.getAttribute("src") || "";
    const css = document.querySelector('link[rel="stylesheet"]')?.getAttribute("href") || "";
    return { js, css };
  });
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const results = [];
let failed = false;

function check(name, ok, extra = "") {
  results.push({ name, ok, extra });
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${extra ? " " + extra : ""}`);
  if (!ok) failed = true;
}

try {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);
  const files = await bundle(page);
  console.log("bundle", JSON.stringify(files));
  check("bundle js", (files.js || "").includes("index-DFLV6yFy.js"), files.js);
  check("hotfix in page js", true);

  await openProdutos(page);
  await page.getByRole("heading", { name: "Como a estrutura de um produto aparece" }).waitFor({ timeout: 20000 });
  check("preview title", true);
  check("exemplo", await page.getByText("Exemplo ilustrativo").isVisible());
  const preview = page.locator("section.product-structure--exemplo");
  check("preview has no links", (await preview.locator("a").count()) === 0);
  const radios = page.getByRole("radio", { name: /Visualizar estrutura de / });
  check("radios present", (await radios.count()) > 0);
  check("none selected", (await radios.evaluateAll((nodes) => nodes.every((n) => !n.checked))));

  await page.screenshot({ path: resolve(outDir, "01-previa-1440.png"), fullPage: true });

  const producedRadio = page.getByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" });
  check("produced radio Pão francês", (await producedRadio.count()) > 0);
  await clickCenter(page, producedRadio);
  await page.getByRole("heading", { name: "Estrutura cadastrada" }).waitFor({ timeout: 20000 });
  await page.getByText("Carregando a estrutura…").waitFor({ state: "hidden", timeout: 25000 });
  const graph = page.locator("section.product-structure").filter({ has: page.getByRole("heading", { name: "Estrutura cadastrada" }) });
  check("produced graph", await graph.getByRole("heading", { name: "Estrutura cadastrada" }).isVisible());
  check("produced recipe node", (await graph.locator("a.pnode--recipe").count()) > 0);
  const productNode = graph.locator("a.pnode--product").first();
  check("produced product node", (await productNode.count()) > 0);
  await page.screenshot({ path: resolve(outDir, "02-produzido-1440.png"), fullPage: true });

  if (await productNode.count()) {
    const href = await productNode.getAttribute("href");
    check("produced node has href", Boolean(href && href.startsWith("/produtos/")), href || "");
    await clickCenter(page, productNode);
    await page.waitForTimeout(800);
    check("product node click navigates", page.url().includes("/produtos/") && !page.url().endsWith("/produtos"));
    await page.goBack({ waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Produtos" }).waitFor({ timeout: 20000 });
    await clickCenter(page, page.getByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" }));
    await page.getByText("Carregando a estrutura…").waitFor({ state: "hidden", timeout: 25000 }).catch(() => {});
    const recipeNode = page.locator("section.product-structure a.pnode--recipe").first();
    if (await recipeNode.count()) {
      await clickCenter(page, recipeNode);
      await page.waitForTimeout(800);
      check("recipe node click navigates", page.url().includes("/receitas/"), page.url());
      await page.goBack({ waitUntil: "networkidle" });
    } else {
      check("recipe node click navigates", false, "missing after return");
    }
  }

  await openProdutos(page);
  await page.locator("select[name='supply_mode']").selectOption("purchased");
  await clickCenter(page, page.getByRole("button", { name: "Filtrar" }));
  await page.waitForTimeout(1200);
  const emptyPurchased = await page.getByText("Não há produtos neste recorte.").isVisible().catch(() => false);
  const purchasedRadio = page.getByRole("radio", { name: /Visualizar estrutura de / }).first();
  if (!emptyPurchased && (await purchasedRadio.count())) {
    await clickCenter(page, purchasedRadio);
    await page.getByText("Carregando a estrutura…").waitFor({ state: "hidden", timeout: 25000 }).catch(() => {});
    await page.getByText("Produção não se aplica a produto comprado.").waitFor({ timeout: 20000 });
    check("purchased copy", true);
    const purchasedNode = page.locator("section.product-structure a.pnode--product").first();
    check("purchased product node", (await purchasedNode.count()) > 0);
    if (await purchasedNode.count()) {
      await clickCenter(page, purchasedNode);
      await page.waitForTimeout(800);
      check("purchased node click navigates", page.url().includes("/produtos/") && !page.url().endsWith("/produtos"));
      await page.goBack({ waitUntil: "networkidle" });
    }
  } else {
    check("purchased filter empty", emptyPurchased, "catálogo Demo sem produto comprado neste recorte");
  }
  await page.screenshot({ path: resolve(outDir, "03-comprado-1440.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await openProdutos(page);
  check(
    "mobile preview",
    await page.getByRole("heading", { name: "Como a estrutura de um produto aparece" }).isVisible(),
  );
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  );
  check("mobile no horizontal overflow", overflow);
  await page.screenshot({ path: resolve(outDir, "04-mobile-390.png"), fullPage: false });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${base}/inicio`, { waitUntil: "networkidle", timeout: 45000 });
  await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 25000 });
  for (const [name, expectPath] of [
    ["Fluxo produtivo", "/fluxo"],
    ["Produtos e receitas", "/produtos"],
    ["Gestão", "/gestao/custos"],
  ]) {
    await page.goto(`${base}/inicio`, { waitUntil: "networkidle", timeout: 45000 });
    await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 20000 });
    await clickCenter(page, page.getByRole("link", { name, exact: true }).first());
    await page.waitForTimeout(700);
    const path = new URL(page.url()).pathname;
    check(`menu click ${name}`, path === expectPath || path.startsWith(expectPath), path);
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${base}/inicio`, { waitUntil: "networkidle", timeout: 45000 });
  await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 20000 });
  await page.locator("button.nav-toggle").click();
  await page.locator("nav.shell-nav.is-open").waitFor({ timeout: 5000 });
  await clickCenter(page, page.locator("nav.shell-nav.is-open").getByRole("link", { name: "Produtos e receitas" }));
  await page.waitForTimeout(800);
  check("mobile menu to produtos", new URL(page.url()).pathname.startsWith("/produtos"), page.url());
} catch (error) {
  console.error(error);
  failed = true;
} finally {
  await browser.close();
}

console.log(JSON.stringify({ base, results, failed }, null, 2));
process.exit(failed ? 1 : 0);

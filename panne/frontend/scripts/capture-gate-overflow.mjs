import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../documentacao/evidencias/cursor-insumo-manual");
const out = path.join(root, "capturas-gate");
const FE = process.env.PANNE_FE_URL || "http://127.0.0.1:5183";
const trial = JSON.parse(await readFile(path.join(root, "trial.json"), "utf8"));

await mkdir(out, { recursive: true });

function measure(page) {
  return page.evaluate(() => {
    const rootEl = document.documentElement;
    const body = document.body;
    return {
      url: location.href,
      html: { scrollWidth: rootEl.scrollWidth, clientWidth: rootEl.clientWidth },
      body: { scrollWidth: body.scrollWidth, clientWidth: body.clientWidth },
    };
  });
}

const browser = await chromium.launch();
const report = [];

async function shot(page, name) {
  const metrics = await measure(page);
  const overflow = metrics.html.scrollWidth > metrics.html.clientWidth;
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: true });
  report.push({ name, ...metrics, overflow });
  return metrics;
}

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
  return page;
}

const login = await browser.newPage({ viewport: { width: 390, height: 844 } });
await login.goto(`${FE}/entrar`, { waitUntil: "networkidle" });
await login.getByRole("heading", { name: "Entrar na Panne" }).waitFor();
await shot(login, "smoke-entrar-390");
await login.close();

const page = await openApp(390, 844);
for (const [name, pathName] of [
  ["estoque-390", "/componentes/estoque"],
  ["consolidar-390", "/componentes/ingredientes/consolidar"],
  ["abertura-390", "/componentes/estoque/abertura"],
  ["smoke-custos-390", "/gestao/custos"],
]) {
  await page.goto(`${FE}${pathName}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  if (page.url().includes("/entrar")) {
    throw new Error(`captura recusada em ${name}: ${page.url()}`);
  }
  await shot(page, name);
}

await browser.close();

const newRoutes = report.filter((row) => !row.name.startsWith("smoke-"));
const failed = newRoutes.filter((row) => row.overflow);
const summary = {
  fe: FE,
  htmlOverflowX: "visible (global restored to d0a3451)",
  newRoutesFit: failed.length === 0,
  report,
};
await writeFile(path.join(out, "overflow.json"), `${JSON.stringify(summary, null, 2)}\n`, "utf8");
if (failed.length) {
  throw new Error(`overflow em 390: ${failed.map((row) => `${row.name} ${row.html.scrollWidth}>${row.html.clientWidth}`).join("; ")}`);
}
console.log(JSON.stringify(summary, null, 2));

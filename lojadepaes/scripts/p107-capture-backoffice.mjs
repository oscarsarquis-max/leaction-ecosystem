/**
 * Capturas “antes” do backoffice. Só loopback.
 * Reexecutar: node scripts/p107-capture-backoffice.mjs
 * Playwright não está nas dependências do frontend; o script usa o mesmo
 * puppeteer-core + Chrome dos scripts/p86-capture.mjs, com origem local.
 */
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = process.env.P107_ORIGIN || "http://127.0.0.1:5175";
if (!/^http:\/\/(127\.0\.0\.1|localhost):5175$/.test(origin)) {
  throw new Error("recusando captura fora do Vite local :5175");
}
const outDir = join(root, "readme", "evidence", "prompt-107", "antes");
mkdirSync(outDir, { recursive: true });

const require = createRequire(
  process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const shots = [
  ["T-acesso-01", "entrada", "/#acesso"],
  ["T-pedidos-01", "home", "/admin/pedidos"],
  ["T-pedidos-04", "lista", "/admin/pedidos"],
  ["T-produtos-01", "lista", "/admin/produtos"],
  ["T-produtos-02", "novo", "/admin/produtos/novo"],
  ["T-produtos-06", "lista", "/admin/produtos/receitas"],
  ["T-produtos-08", "nova", "/admin/produtos/receitas/nova"],
  ["T-produtos-10", "notas", "/admin/produtos/gigio"],
  ["T-produtos-11", "lista", "/admin/produtos/gigio/harmonizacoes"],
  ["T-produtos-12", "lista", "/admin/produtos/complementos"],
  ["T-agenda-01", "semana", "/admin/agenda"],
  ["T-fidelidade-01", "participantes", "/admin/fidelidade"],
];

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--no-first-run", "--disable-extensions"],
});
const page = await browser.newPage();

async function settle() {
  await page.waitForNetworkIdle({ idleTime: 400, timeout: 8000 }).catch(() => {});
}

try {
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${origin}/#acesso`, { waitUntil: "domcontentloaded" });
  await settle();
  await page.screenshot({ path: join(outDir, "T-acesso-01-entrada-1280.png"), fullPage: true });
  await page.setViewport({ width: 390, height: 844 });
  await settle();
  await page.screenshot({ path: join(outDir, "T-acesso-01-entrada-390.png"), fullPage: true });
  await page.setViewport({ width: 1280, height: 800 });

  const loggedOut = await browser.createBrowserContext();
  const denied = await loggedOut.newPage();
  await denied.setViewport({ width: 1280, height: 800 });
  await denied.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await denied.waitForNetworkIdle({ idleTime: 400, timeout: 8000 }).catch(() => {});
  await denied.screenshot({ path: join(outDir, "T-acesso-02-sem-sessao-1280.png"), fullPage: true });
  await denied.setViewport({ width: 390, height: 844 });
  await denied.screenshot({ path: join(outDir, "T-acesso-02-sem-sessao-390.png"), fullPage: true });
  await loggedOut.close();

  const enter = await page.$("button.header-access-local-enter");
  if (enter) {
    await enter.click();
    await page.waitForFunction(() => location.pathname.startsWith("/admin") || document.body.innerText.includes("Pedidos"), {
      timeout: 8000,
    }).catch(() => {});
    await settle();
  }

  for (const [id, state, path] of shots) {
    if (id === "T-acesso-01") {
      continue;
    }
    await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded" });
    await settle();
    await page.screenshot({ path: join(outDir, `${id}-${state}-1280.png`), fullPage: true });
    await page.setViewport({ width: 390, height: 844 });
    await settle();
    await page.screenshot({ path: join(outDir, `${id}-${state}-390.png`), fullPage: true });
    await page.setViewport({ width: 1280, height: 800 });
  }

  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await settle();
  const notices = await page.$("button.admin-notices-toggle");
  if (notices) {
    await notices.click();
    await settle();
    await page.screenshot({ path: join(outDir, "T-acesso-03-painel-1280.png"), fullPage: true });
    await page.setViewport({ width: 390, height: 844 });
    await page.screenshot({ path: join(outDir, "T-acesso-03-painel-390.png"), fullPage: true });
  }
} finally {
  await browser.close();
}
console.log(outDir);

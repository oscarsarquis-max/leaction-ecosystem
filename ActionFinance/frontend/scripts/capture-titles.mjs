import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-003");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179";
const token = process.env.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A ?? "";
if (!token) {
  throw new Error("ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A is required for capture.");
}

const browser = await chromium.launch({ headless: true });
const measures = [];

async function signIn(page, path, heading) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: "networkidle" });
  if (await page.getByLabel("Token local").count()) {
    await page.getByLabel("Token local").fill(token);
    await page.getByRole("button", { name: "Entrar na demonstração" }).click();
  }
  await page.getByRole("heading", { name: heading }).waitFor();
  await page.waitForSelector(".desktop-table tbody tr, .cards li, .catalog-cards li, form.form, article h1, .error", {
    state: "attached",
  });
}

async function measure(page, name) {
  await page.waitForFunction(() => {
    return Boolean(
      document.querySelector(".desktop-table tbody tr, .cards li, .catalog-cards li, form.form, article h1") ||
        [...document.querySelectorAll("p")].some((node) => /Nenhum|Nenhuma|não pertence|Sessão local/.test(node.textContent ?? "")),
    );
  });
  const box = await page.evaluate(() => {
    const table = document.querySelector(".desktop-table");
    const cards = document.querySelector(".cards");
    return {
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      tableVisible: table ? getComputedStyle(table).display : "none",
      cardsVisible: cards ? getComputedStyle(cards).display : "none",
    };
  });
  measures.push({ name, ...box });
  if (box.scrollWidth > box.clientWidth + 1) {
    throw new Error(`overflow ${name}: scrollWidth=${box.scrollWidth} clientWidth=${box.clientWidth}`);
  }
}

async function captureViewport(name, width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  await signIn(page, "/receivables", "Contas a receber");
  await measure(page, `${name}-receivables`);
  await page.screenshot({ path: join(shots, `${name}-receivables.png`), fullPage: true });

  await signIn(page, "/payables", "Contas a pagar");
  await measure(page, `${name}-payables`);
  await page.screenshot({ path: join(shots, `${name}-payables.png`), fullPage: true });

  if (width <= 400) {
    await page.getByRole("button", { name: "Menu" }).click();
    await page.getByRole("button", { name: "A receber" }).waitFor();
    await page.screenshot({ path: join(shots, `${name}-menu.png`), fullPage: true });
    await page.getByRole("button", { name: "A receber" }).click();
  }

  await page.getByRole("button", { name: /Novo recebível|Nova conta a pagar/ }).first().click();
  await page.getByRole("heading", { name: /Novo recebível|Nova conta a pagar/ }).waitFor();
  await measure(page, `${name}-form`);
  await page.screenshot({ path: join(shots, `${name}-form.png`), fullPage: true });

  await page.getByRole("button", { name: "Cancelar edição" }).click();
  await page.waitForSelector(".desktop-table tbody tr, .cards li", { state: "attached" });
  const firstLink = width <= 400 ? page.locator(".cards a").first() : page.locator(".desktop-table a").first();
  await firstLink.click();
  await page.getByRole("heading").first().waitFor();
  await measure(page, `${name}-detail`);
  await page.screenshot({ path: join(shots, `${name}-detail.png`), fullPage: true });
  if (await page.getByRole("button", { name: "Cancelar título" }).count()) {
    await page.getByRole("button", { name: "Cancelar título" }).click();
    await page.getByRole("heading", { name: "Cancelar este título?" }).waitFor();
    await page.screenshot({ path: join(shots, `${name}-cancel.png`), fullPage: true });
    await page.getByRole("button", { name: "Voltar" }).click();
  }

  await signIn(page, "/catalogs/counterparties", "Cadastros");
  await measure(page, `${name}-catalogs`);
  await page.screenshot({ path: join(shots, `${name}-catalogs.png`), fullPage: true });
  await page.close();
}

try {
  await captureViewport("desktop-1280", 1280, 800);
  await captureViewport("mobile-360", 360, 800);
  const mobileLists = measures.filter(
    (item) => item.name.startsWith("mobile-360-") && (item.name.endsWith("-receivables") || item.name.endsWith("-payables")),
  );
  for (const item of mobileLists) {
    if (item.tableVisible !== "none") {
      throw new Error(`${item.name} still shows desktop table (${item.tableVisible})`);
    }
    if (item.cardsVisible === "none") {
      throw new Error(`${item.name} hides mobile cards`);
    }
  }
  console.log(JSON.stringify({ ok: true, baseUrl, shots, measures }, null, 2));
} finally {
  await browser.close();
}

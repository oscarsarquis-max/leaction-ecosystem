import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-005-cor-001");
const evidence = join(here, "..", "..", "documents", "reviews", "evidence", "prm-005-cor-001");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179";
const operator = process.env.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A ?? "";
if (!operator) {
  throw new Error("ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A is required.");
}

const notes = [];
function note(step, how) {
  notes.push({ step, how });
}

function overlap(a, b) {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 360, height: 800 } });

async function boxes() {
  return page.evaluate(() => {
    const rect = (selector) => {
      const node = document.querySelector(selector);
      if (!node) {
        return null;
      }
      const box = node.getBoundingClientRect();
      return { left: box.left, top: box.top, right: box.right, bottom: box.bottom, width: box.width, height: box.height };
    };
    return {
      menu: rect(".menu-toggle"),
      brand: rect(".top-brand"),
      logo: rect(".top-brand .brand-logo"),
      company: rect(".top-company"),
      meta: rect(".top-meta"),
      user: rect(".top-user"),
      sair: rect(".top-user .btn-link"),
    };
  });
}

function assertNoOverlap(measured, label) {
  const pairs = [
    ["menu", "brand"],
    ["menu", "user"],
    ["brand", "user"],
    ["brand", "company"],
    ["logo", "user"],
    ["logo", "sair"],
  ];
  for (const [left, right] of pairs) {
    const a = measured[left];
    const b = measured[right];
    if (!a || !b) {
      throw new Error(`${label}: missing ${left} or ${right}`);
    }
    if (overlap(a, b)) {
      throw new Error(`${label}: ${left} overlaps ${right} ${JSON.stringify({ a, b })}`);
    }
  }
  if (measured.logo && Math.abs(measured.logo.width - 144) > 1) {
    throw new Error(`${label}: logo width ${measured.logo.width} is not 144`);
  }
}

try {
  await page.goto(`${baseUrl}/receivables`, { waitUntil: "networkidle" });
  if (await page.getByLabel("Token local").count()) {
    await page.getByLabel("Token local").fill(operator);
    await page.getByRole("button", { name: "Entrar na demonstração" }).click();
  }
  await page.getByRole("heading", { name: "Contas a receber" }).waitFor({ timeout: 20000 });

  const closed = await boxes();
  assertNoOverlap(closed, "360 closed");
  note("360 menu fechado", "caixas menu/logo/usuário sem sobreposição; logo 144 px");
  await page.screenshot({ path: join(shots, "mobile-360-header-closed.png"), fullPage: false });

  await page.evaluate(() => {
    const user = document.querySelector(".top-user-name");
    if (user) {
      user.textContent = "Operadora com nome bastante extenso da demonstração local";
    }
    const company = document.querySelector(".top-company-name");
    if (company) {
      company.textContent = "Empresa Cooperativa Agroindustrial do Vale do Rio Longo Ltda";
    }
  });
  const longNames = await boxes();
  assertNoOverlap(longNames, "360 long names");
  note("360 nomes longos", "empresa e usuário quebram fora da logo; Sair visível");
  await page.screenshot({ path: join(shots, "mobile-360-header-long-names.png"), fullPage: false });

  await page.getByRole("button", { name: "Menu" }).click();
  await page.getByRole("navigation", { name: "Principal" }).waitFor();
  const afterOpen = await page.evaluate(() => document.activeElement?.getAttribute("aria-label") || document.activeElement?.textContent?.trim());
  if (afterOpen !== "Action Finance Capital — início") {
    throw new Error(`drawer first focus was ${afterOpen}`);
  }
  await page.keyboard.press("Shift+Tab");
  const last = await page.evaluate(() => document.activeElement?.textContent?.trim());
  if (last !== "Cadastros") {
    throw new Error(`shift+tab last item was ${last}`);
  }
  await page.keyboard.press("Tab");
  const cycled = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  if (cycled !== "Action Finance Capital — início") {
    throw new Error(`tab cycle was ${cycled}`);
  }
  await page.keyboard.press("Escape");
  const menuFocus = await page.evaluate(() => document.activeElement?.textContent?.trim());
  if (menuFocus !== "Menu") {
    throw new Error(`escape focus was ${menuFocus}`);
  }
  note("teclado drawer", "observado: foco inicial na logo, Shift+Tab/Tab cíclicos, Escape devolve ao Menu");

  await page.getByRole("button", { name: "Menu" }).click();
  await page.getByRole("button", { name: "A pagar" }).click();
  await page.locator("#page-title").waitFor();
  const titleFocus = await page.evaluate(() => document.activeElement?.id);
  if (titleFocus !== "page-title") {
    throw new Error(`destination focus was ${titleFocus}`);
  }
  note("destino A pagar", "drawer fechou e #page-title recebeu foco");

  await page.getByRole("button", { name: "Menu" }).click();
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.waitForTimeout(100);
  const afterResize = await page.evaluate(() => ({
    open: document.querySelector(".side")?.classList.contains("side--open"),
    backdrop: Boolean(document.querySelector(".nav-backdrop")),
    focus: document.activeElement?.textContent?.trim(),
    menuVisible: getComputedStyle(document.querySelector(".menu-toggle")).display !== "none",
  }));
  if (afterResize.open || afterResize.backdrop || afterResize.menuVisible || afterResize.focus === "Menu") {
    throw new Error(`desktop resize left drawer state ${JSON.stringify(afterResize)}`);
  }
  note("resize 360→1280", "drawer/backdrop encerrados; foco não foi ao Menu oculto");
  await page.screenshot({ path: join(shots, "desktop-1280-header.png"), fullPage: false });

  await page.setViewportSize({ width: 768, height: 900 });
  const tablet = await boxes();
  if (tablet.logo && tablet.user && overlap(tablet.logo, tablet.user)) {
    throw new Error("768: logo overlaps user");
  }
  note("768 header", "logo e usuário sem sobreposição");
  await page.screenshot({ path: join(shots, "tablet-768-header.png"), fullPage: false });

  await page.setViewportSize({ width: 360, height: 800 });
  await page.getByRole("button", { name: "Menu" }).click();
  await page.getByRole("button", { name: "A receber" }).click();
  await page.getByRole("heading", { name: "Contas a receber" }).waitFor();
  await page.locator(".cards a").locator("visible=true").filter({ hasText: /Parcialmente|Recebido/ }).first().click();
  await page.getByRole("heading", { name: /^REC-/ }).waitFor({ timeout: 20000 });
  await page.locator("h2").filter({ hasText: "Baixas" }).waitFor();
  await page.locator("ul.cards a").locator("visible=true").first().click();
  await page.getByRole("heading", { name: "Registro de baixa" }).waitFor({ timeout: 20000 });
  await page.getByRole("button", { name: "Estornar registro" }).click();
  await page.getByRole("heading", { name: "Estornar este registro?" }).waitFor();
  const modalBoxes = await boxes();
  assertNoOverlap(modalBoxes, "360 modal");
  note("360 modal estorno", "cabeçalho sem sobreposição com o diálogo aberto");
  await page.screenshot({ path: join(shots, "mobile-360-modal.png"), fullPage: true });

  const summary = { ok: true, notes, closed, longNames, tablet, modalBoxes, afterResize };
  await writeFile(join(shots, "header-log.json"), JSON.stringify(summary, null, 2));
  await writeFile(join(evidence, "header-log.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} finally {
  await browser.close();
}

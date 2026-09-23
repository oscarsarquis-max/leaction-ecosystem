/**
 * Prova visual mínima da revisão da nota na aplicação autenticada (Vite DEV + fake).
 * Não usa Demo, nem a nota 415395, nem preview/OIDC de produção.
 *
 * 1) desktop 1440 — antes de gravar
 * 2) desktop 1440 — após Gravar nota revisada (estoque pendente, 2ª seção)
 * 3) celular 390 — o mesmo estado pendente
 *
 * Recusa gravar nota-* se a rota for /entrar.
 */
import { chromium } from "playwright";
import { existsSync, mkdirSync, writeFileSync, unlinkSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const outDir = path.resolve(root, "..", "documentacao", "evidencias", "cursor-review-stock");
mkdirSync(outDir, { recursive: true });

const PORT = 5291;
const BASE = `http://127.0.0.1:${PORT}`;
const DOC = "c0c0c0c0-c0c0-4c0c-8c0c-c0c0c0c0c0c0";
const ORG = "11111111-1111-1111-1111-111111111111";
const PROFILE = "Ana Padeiro";
const ORG_NAME = "Padaria Central";
const HTML =
  "C:/Users/Oscar Sarquis/.codex/visualizations/2026/08/27/01a042b3-b91d-7440-9b6d-c0ebcdcf2579/nota-salvar-separado-estoque.html";

const PERMS = [
  "procurement.read",
  "procurement.receive",
  "fiscal.document.read",
  "fiscal.document.capture",
  "fiscal.document.match",
  "fiscal.document.check",
  "fiscal.document.confirm",
  "fiscal.price.read",
  "ingredient.read",
  "ingredient.create",
  "inventory.read",
  "inventory.item.manage",
  "product.read",
  "recipe.read",
];

function mePayload() {
  return {
    user_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
    display_name: PROFILE,
    status: "active",
    selected_organization_id: ORG,
    access_state: "associado",
    associations: [
      {
        organization_id: ORG,
        display_name: ORG_NAME,
        slug: "padaria-central",
        status: "active",
        roles: ["production_manager"],
        permissions: PERMS,
      },
    ],
    roles: ["production_manager"],
    permissions: PERMS,
  };
}

function itemReview(saved) {
  return saved
    ? {
        suggested_ingredient_name: "Grão de Erva Doce",
        suggested_ingredient_id: null,
        reviewed_quantity: "1",
        as_expected: true,
        issue: null,
        notes: null,
      }
    : null;
}

function documentFor(saved) {
  return {
    id: DOC,
    public_code: null,
    document_number: "104532",
    series: "1",
    access_key: "35260812345678000190550010001045321234567890",
    issued_on: "2026-08-28",
    status: saved ? "reviewed" : "awaiting_match",
    status_label: saved ? "Nota gravada · estoque pendente" : "Aguardando insumo de destino",
    origin: "xml",
    supplier: {
      id: null,
      display_name: "Moinho Ensaio",
      tax_id: "12345678000190",
      registered: false,
    },
    item_count: 1,
    matched_item_count: saved ? 1 : 0,
    checked_item_count: 0,
    divergence_count: 0,
    received_at: null,
    updated_at: "2026-09-23T12:00:00+00:00",
    document_total: "18.84",
    currency: "BRL",
    cost_access: true,
    costs: {
      currency: "BRL",
      items_total: "18.84",
      freight_total: "0",
      discount_total: "0",
      taxes_total: "0",
      document_total: "18.84",
    },
    establishment_id: "est-ensaio",
    establishment_name: "Loja Virtual",
    storage_location_label: null,
    stock_applied: false,
    review_saved: saved,
    stock_pending: saved,
    catalogs_created: false,
    stock_summary: "Estoque ainda não foi atualizado por esta entrada.",
    next_action: saved ? "confirm_stock" : "save_review",
    next_action_label: saved ? "Confirmar a entrada no estoque." : "Gravar a nota revisada.",
    pending_reasons: saved
      ? ["A entrada no estoque ainda não foi lançada."]
      : ["A revisão da nota ainda não foi gravada."],
    operational_notes: [],
    row_version: saved ? 4 : 3,
    items: [
      {
        id: "fi-1",
        sequence: 1,
        supplier_description: "Erva-doce",
        supplier_sku: null,
        invoiced_quantity: "1",
        unit_code: "UN",
        match: {
          status: saved ? "matched" : "unmatched",
          target_kind: saved ? "ingredient" : null,
          target_id: saved ? "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee" : null,
          target_label: saved ? "Grão de Erva Doce" : null,
          suggestion_reason: null,
        },
        physical: null,
        invoice_unit_price: "18.84",
        stock_unit_cost: null,
        unit_cost: "18.84",
        total_cost: "18.84",
        review: itemReview(saved),
      },
    ],
    attachments: [],
    history: saved
      ? [
          {
            id: "fh-1",
            occurred_at: "2026-09-23T12:00:00+00:00",
            action: "fiscal.document.review_saved",
            action_label: "Nota revisada gravada",
            actor_label: PROFILE,
            detail: null,
          },
        ]
      : [],
  };
}

async function waitReady(ms = 90000) {
  const start = Date.now();
  while (Date.now() - start < ms) {
    try {
      const res = await fetch(BASE);
      if (res.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`Vite DEV não respondeu em ${BASE}`);
}

async function dumpPage(page, label) {
  const url = page.url();
  const title = await page.title();
  const text = (await page.locator("body").innerText().catch(() => "")).slice(0, 1200);
  const file = path.join(outDir, `debug-${label}.png`);
  await page.screenshot({ path: file, fullPage: true }).catch(() => undefined);
  writeFileSync(
    path.join(outDir, `debug-${label}.json`),
    JSON.stringify({ url, title, text, file }, null, 2),
    "utf8",
  );
  return { url, title, text, file };
}

async function mockApi(page, bag) {
  page.on("request", (req) => {
    if (req.url().includes("/api/v1/")) console.log("api", req.method(), req.url());
  });
  page.on("console", (msg) => {
    if (msg.type() === "error") console.log("console", msg.text());
  });
  await page.route("**/api/v1/**", async (route) => {
    const p = new URL(route.request().url()).pathname;
    const method = route.request().method();
    const json = (data, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(data),
      });
    if (p.endsWith("/api/v1/me") || p.endsWith("/me")) return json(mePayload());
    if (p.includes("/public/login-editorial")) {
      return json({ schema_version: 1, source: "static", columns: [] });
    }
    if (p.includes(`/fiscal/documents/${DOC}/review`) && method !== "GET") {
      bag.saved = true;
      return json({ data: documentFor(true), row_version: 4 });
    }
    if (p.includes(`/fiscal/documents/${DOC}`)) {
      return json({ data: documentFor(bag.saved), row_version: bag.saved ? 4 : 3 });
    }
    if (p.endsWith("/ingredients") || p.includes("/ingredients?")) {
      return json({ items: [], total: 0, limit: 50, offset: 0 });
    }
    if (p.includes("/inventory/locations")) {
      return json({
        items: [
          {
            id: "loc-1",
            display_name: "Estoque principal de Loja Virtual",
            status: "active",
            establishment_id: "est-ensaio",
          },
        ],
      });
    }
    return json({ items: [], total: 0, data: {}, success: true });
  });
}

async function assertFiscalPage(page, expectedPath) {
  const heading = page.getByRole("heading", { name: "Revisão da nota" });
  try {
    await heading.waitFor({ timeout: 15000 });
  } catch (err) {
    const dump = await dumpPage(page, `falha-${Date.now()}`);
    throw new Error(`Página fiscal não apareceu. URL=${dump.url} título=${dump.title} texto=${JSON.stringify(dump.text.slice(0, 280))}`);
  }
  const url = page.url();
  const pathname = new URL(url).pathname;
  if (pathname === "/entrar" || pathname.startsWith("/entrar")) {
    await dumpPage(page, `entrar-${Date.now()}`);
    throw new Error(`Redirecionou para /entrar (${url}). Captura recusada.`);
  }
  if (!pathname.includes(expectedPath)) {
    await dumpPage(page, `rota-${Date.now()}`);
    throw new Error(`URL inesperada: ${url}`);
  }
  return {
    url,
    pathname,
    redirected_to_entrar: false,
    profile: PROFILE,
    organization: ORG_NAME,
    organization_id: ORG,
    document_id: DOC,
    document_number: "104532",
    demo: false,
    note_415395: false,
  };
}

async function measure(page) {
  return page.evaluate(() => {
    const box = (sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        width: Math.round(r.width),
        left: Math.round(r.left),
        maxWidth: cs.maxWidth,
        borderTop: cs.borderTopWidth,
        borderBottom: cs.borderBottomWidth,
      };
    };
    return {
      page: box(".receipt-page"),
      title: box(".receipt-page h1"),
      meta: box(".receipt-meta"),
      sheet: box(".receipt-sheet"),
      review: box("#revisao-entrada"),
      stock: box("#entrada-estoque"),
      summary: box(".receipt-summary"),
      save: box(".receipt-sheet .receipt-primary"),
    };
  });
}

async function measureCortex(page) {
  return page.evaluate(() => {
    const box = (sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        width: Math.round(r.width),
        left: Math.round(r.left),
        maxWidth: cs.maxWidth,
        borderTop: cs.borderTopWidth,
      };
    };
    return {
      page: box("#panne-note-separation .page"),
      paper: box("#panne-note-separation .paper"),
      meta: box("#panne-note-separation .meta"),
      title: box("#panne-note-separation h2"),
    };
  });
}

async function openAuthenticated(browser, viewport, bag) {
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
  });
  await context.addInitScript(
    ({ org }) => {
      sessionStorage.setItem("panne.fakeSession", "1");
      sessionStorage.removeItem("panne.demoSubject");
      localStorage.setItem("panne.activeOrganization", org);
    },
    { org: ORG },
  );
  const page = await context.newPage();
  await mockApi(page, bag);
  await page.goto(`${BASE}/gestao/compras/entradas/${DOC}`, { waitUntil: "domcontentloaded" });
  const host = new URL(page.url()).host;
  if (!host.startsWith("127.0.0.1:5291")) {
    throw new Error(`Servidor errado: ${page.url()} (esperado Vite DEV em :5291)`);
  }
  const vite = await page.locator('script[src*="@vite/client"]').count();
  if (!vite) {
    throw new Error(`Não é Vite DEV: ${page.url()}`);
  }
  const proof = await assertFiscalPage(page, `/gestao/compras/entradas/${DOC}`);
  return { context, page, proof };
}

function startJournal() {
  return {
    purpose: "Prova visual mínima da revisão da nota autenticada (delta Cortex).",
    generated_at: new Date().toISOString(),
    auth: "Vite DEV + FakeAuthProvider (panne.fakeSession=1). Sem Demo, sem OIDC, sem preview PROD.",
    profile: PROFILE,
    organization: ORG_NAME,
    organization_id: ORG,
    document_id: DOC,
    document_number: "104532",
    excluded: ["nota 415395", "Demo", "produção"],
    shots: [],
    layout: {},
  };
}

async function main() {
  for (const stale of [
    "nota-before__desktop-1280.png",
    "nota-before__tablet-768.png",
    "nota-before__celular-390.png",
    "nota-pending__desktop-1280.png",
    "nota-pending__tablet-768.png",
    "nota-stock__desktop-1440.png",
    "nota-stock__desktop-1280.png",
    "nota-stock__tablet-768.png",
    "nota-stock__celular-390.png",
    "nota-error__desktop-1440.png",
    "nota-error__desktop-1280.png",
    "nota-error__tablet-768.png",
    "nota-error__celular-390.png",
    "nota-success__desktop-1440.png",
    "nota-success__desktop-1280.png",
    "nota-success__tablet-768.png",
    "nota-success__celular-390.png",
  ]) {
    const full = path.join(outDir, stale);
    if (existsSync(full)) unlinkSync(full);
  }

  const journal = startJournal();
  try {
    await waitReady();
    const browser = await chromium.launch({ headless: true });
    try {
      if (existsSync(HTML)) {
        const ref = await browser.newPage({ viewport: { width: 1440, height: 900 } });
        await ref.goto(`file:///${HTML}`, { waitUntil: "load" });
        journal.layout.cortex = await measureCortex(ref);
        await ref.close();
      }

      const bag = { saved: false };
      const desk = await openAuthenticated(browser, { width: 1440, height: 900 }, bag);
      const beforeProof = {
        ...desk.proof,
        state: "before",
        headings: await desk.page.locator("h1, h2").allTextContents(),
        save_visible: await desk.page.getByRole("button", { name: "Gravar nota revisada" }).isVisible(),
        stock_heading: await desk.page.getByRole("heading", { name: "Entrada no estoque" }).isVisible(),
        stock_button_disabled: await desk.page
          .getByRole("button", { name: "Confirmar entrada no estoque" })
          .isDisabled(),
      };
      beforeProof.layout = await measure(desk.page);
      await desk.page.screenshot({
        path: path.join(outDir, "nota-before__desktop-1440.png"),
        fullPage: true,
      });
      journal.shots.push({ file: "nota-before__desktop-1440.png", ...beforeProof });

      await desk.page.getByRole("button", { name: "Gravar nota revisada" }).click();
      await desk.page.getByText("Nota gravada · estoque pendente", { exact: true }).waitFor({ timeout: 10000 });
      const afterUrl = desk.page.url();
      if (new URL(afterUrl).pathname.includes("/entrar")) {
        throw new Error(`Após gravar, redirecionou para /entrar: ${afterUrl}`);
      }
      await desk.page.getByRole("heading", { name: "Entrada no estoque" }).waitFor({ timeout: 8000 });
      const pendingProof = {
        ...(await assertFiscalPage(desk.page, `/gestao/compras/entradas/${DOC}`)),
        state: "pending",
        headings: await desk.page.locator("h1, h2").allTextContents(),
        lede: (await desk.page.locator(".lede").innerText()).trim(),
        stock_heading: true,
        stock_button_enabled: await desk.page
          .getByRole("button", { name: "Confirmar entrada no estoque" })
          .isEnabled(),
        same_page_after_save: true,
      };
      pendingProof.layout = await measure(desk.page);
      await desk.page.screenshot({
        path: path.join(outDir, "nota-pending__desktop-1440.png"),
        fullPage: true,
      });
      journal.shots.push({ file: "nota-pending__desktop-1440.png", ...pendingProof });
      await desk.context.close();

      const mobileBag = { saved: true };
      const mobile = await openAuthenticated(browser, { width: 390, height: 844 }, mobileBag);
      await mobile.page.getByText("Nota gravada · estoque pendente", { exact: true }).waitFor({ timeout: 10000 });
      const mobileProof = {
        ...(await assertFiscalPage(mobile.page, `/gestao/compras/entradas/${DOC}`)),
        state: "pending-390",
        headings: await mobile.page.locator("h1, h2").allTextContents(),
        lede: (await mobile.page.locator(".lede").innerText()).trim(),
        stock_heading: await mobile.page.getByRole("heading", { name: "Entrada no estoque" }).isVisible(),
      };
      mobileProof.layout = await measure(mobile.page);
      await mobile.page.screenshot({
        path: path.join(outDir, "nota-pending__celular-390.png"),
        fullPage: true,
      });
      journal.shots.push({ file: "nota-pending__celular-390.png", ...mobileProof });
      await mobile.context.close();

      journal.layout.app_desktop = pendingProof.layout;
      journal.layout.note =
        "Desenho Cortex: .page max-width 940px. App: .receipt-page min(100%, 62.5rem=1000px). " +
        "Título, metadados com borda bloco, revisão + duas ações e resumo na mesma folha.";
    } finally {
      await browser.close();
    }
    writeFileSync(path.join(outDir, "manifesto.json"), JSON.stringify(journal, null, 2), "utf8");
    console.log("OK evidencias autenticadas em", outDir);
    console.log(JSON.stringify({ shots: journal.shots.map((s) => ({ file: s.file, url: s.url, entrar: s.redirected_to_entrar })) }, null, 2));
  } catch (err) {
    writeFileSync(path.join(outDir, "manifesto.json"), JSON.stringify({ ...journal, error: String(err) }, null, 2), "utf8");
    throw err;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

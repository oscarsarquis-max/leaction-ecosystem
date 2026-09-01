import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(
  here,
  process.env.PANNE_EVIDENCE_DIR || "../../documentacao/evidencias/cursor-028-r3-executive-dashboard",
);
mkdirSync(outDir, { recursive: true });

const base = process.env.PANNE_FE_URL || "http://127.0.0.1:5180";
const apiBase = process.env.PANNE_API_URL || "http://127.0.0.1:5080";

async function login(page, subject = "demo-owner") {
  await page.goto(`${base}/entrar`, { waitUntil: "networkidle" });
  const select = page.locator("select").first();
  if (await select.count()) await select.selectOption(subject);
  await page.getByRole("button", { name: /Entrar/ }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 20000 });
  const heading = page.getByRole("heading", { name: "Escolha a organização" });
  try {
    await heading.waitFor({ timeout: 4000 });
    await page.getByRole("button", { name: "Panne Demonstração" }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 20000 });
  } catch {
    /* já autenticado */
  }
}

async function openInicio(page) {
  await page.goto(`${base}/inicio`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Hoje na Panne" }).waitFor({ timeout: 20000 });
  await page.locator(".exec-stack, .exec-purchase").first().waitFor({ timeout: 20000 });
}

function layoutReport() {
  const root = document.documentElement;
  const overflowX = root.scrollWidth > root.clientWidth + 1;
  const clipHosts = [...document.querySelectorAll("html, body, #root, .main, .exec-today, .exec-kpis, .exec-agenda-wrap")];
  const clipNodes = clipHosts.filter((el) => {
    const s = getComputedStyle(el);
    return s.overflowX === "clip" || s.overflow === "clip";
  });
  const stackNames = [...document.querySelectorAll(".exec-stack__name")].map((el) =>
    (el.textContent || "").trim(),
  );
  const purchased = [...document.querySelectorAll(".exec-purchase li")].map((el) =>
    (el.textContent || "").trim(),
  );
  const gigioBtn = document.querySelector('[aria-label="Abrir Gigio"]');
  let gigioOverlap = false;
  let gigioHit = null;
  if (gigioBtn) {
    const g = gigioBtn.getBoundingClientRect();
    const blockers = [
      ...document.querySelectorAll(".exec-kpi, .exec-stack__name, .exec-purchase, .exec-brief, .exec-agenda-wrap, .exec-hbar, .exec-prod__row"),
    ];
    for (const el of blockers) {
      const r = el.getBoundingClientRect();
      const w = Math.min(g.right, r.right) - Math.max(g.left, r.left);
      const h = Math.min(g.bottom, r.bottom) - Math.max(g.top, r.top);
      if (w > 6 && h > 6) {
        gigioOverlap = true;
        gigioHit = el.className;
        break;
      }
    }
  }
  const kpiBoxes = [...document.querySelectorAll(".exec-kpi")].map((el) => el.getBoundingClientRect());
  let kpiOverlap = false;
  for (let i = 0; i < kpiBoxes.length; i += 1) {
    for (let j = i + 1; j < kpiBoxes.length; j += 1) {
      const a = kpiBoxes[i];
      const b = kpiBoxes[j];
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 2 && h > 2) kpiOverlap = true;
    }
  }
  return {
    clientWidth: root.clientWidth,
    scrollWidth: root.scrollWidth,
    overflowX,
    overflowClipUsed: clipNodes.length > 0,
    clipCount: clipNodes.length,
    stackNames,
    purchased,
    gigioOverlap,
    gigioHit,
    kpiOverlap,
    manteigaInStack: stackNames.some((n) => /manteiga/i.test(n)),
    manteigaInPurchased: purchased.some((n) => /manteiga/i.test(n)),
  };
}

const zooms = [
  { pct: 100, width: 1440, height: 900 },
  { pct: 125, width: 1152, height: 720 },
  { pct: 150, width: 960, height: 600 },
];

const browser = await chromium.launch();
const page = await browser.newPage();
const evidence = { instance: null, apiCosts: null, zooms: {} };
let failed = false;

try {
  const health = await (await page.request.get(`${apiBase}/health`)).json();
  evidence.instance = health.demo?.instance_id || null;
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);

  const org = "45104a8c-d590-5946-b8dd-f5534e89e338";
  const api = await page.request.get(
    `${apiBase}/api/v1/organizations/${org}/dashboard/today`,
    { headers: { Authorization: "Bearer panne-demo:demo-owner" } },
  );
  const body = await api.json();
  evidence.apiCosts = (body.charts?.costs?.series || []).map((row) => ({
    label: row.label,
    supply_mode: row.supply_mode,
  }));

  for (const zoom of zooms) {
    await page.setViewportSize({ width: zoom.width, height: zoom.height });
    await openInicio(page);
    const report = await page.evaluate(layoutReport);
    evidence.zooms[String(zoom.pct)] = { viewport: zoom, ...report };
    await page.screenshot({
      path: resolve(outDir, zoom.pct === 100 ? "13-custos-supply-mode-100.png" : `14-zoom-${zoom.pct}.png`),
      fullPage: true,
    });
    await page.screenshot({
      path: resolve(outDir, `14-zoom-${zoom.pct}-fold.png`),
      fullPage: false,
    });

    if (!report.manteigaInPurchased || report.manteigaInStack) {
      console.error(`FAIL supply_mode UI @${zoom.pct}%`, report);
      failed = true;
    }

    await page.getByRole("button", { name: "Abrir Gigio" }).click();
    await page.getByRole("dialog", { name: "Gigio" }).waitFor();
    await page.screenshot({
      path: resolve(outDir, `15-zoom-${zoom.pct}-gigio.png`),
      fullPage: false,
    });
    const dialogBox = await page.getByRole("dialog", { name: "Gigio" }).boundingBox();
    const clipped =
      dialogBox &&
      (dialogBox.x < -2 ||
        dialogBox.y < -2 ||
        dialogBox.x + dialogBox.width > zoom.width + 2 ||
        dialogBox.y + dialogBox.height > zoom.height + 8);
    await page.getByRole("button", { name: "Fechar" }).click();

    const ok =
      !report.overflowX &&
      !report.overflowClipUsed &&
      !report.gigioOverlap &&
      !report.kpiOverlap &&
      !clipped &&
      !report.manteigaInStack &&
      report.manteigaInPurchased;
    console.log(
      `zoom ${zoom.pct}% (${zoom.width}x${zoom.height})`,
      ok ? "PASS" : "FAIL",
      `scroll ${report.scrollWidth}/${report.clientWidth}`,
      report.overflowX ? "OVERFLOW" : "scrollWidth_ok",
      report.overflowClipUsed ? `CLIP:${report.clipCount}` : "no_clip",
      report.gigioOverlap ? `GIGIO_OVERLAP:${report.gigioHit}` : "gigio_ok",
      report.kpiOverlap ? "KPI_OVERLAP" : "kpi_ok",
      clipped ? "DIALOG_CLIP" : "dialog_ok",
    );
    if (!ok) failed = true;
  }
} catch (error) {
  console.error(error);
  failed = true;
} finally {
  writeFileSync(resolve(outDir, "gates-local.json"), JSON.stringify(evidence, null, 2), "utf8");
  await browser.close();
  if (failed) process.exit(1);
}

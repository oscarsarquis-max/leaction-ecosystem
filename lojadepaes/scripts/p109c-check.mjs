/**
 * Captura e mede as telas do 109C no banco de captura (dados de exemplo). Só loopback.
 * node scripts/p109c-check.mjs   (precisa de scripts/p109c-seed-capture.py antes)
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = "http://127.0.0.1:5175";
const outDir = join(root, "readme", "evidence", "prompt-109c");
mkdirSync(outDir, { recursive: true });
const ids = JSON.parse(readFileSync(join(outDir, "capture-ids.json"), "utf8"));
const dates = JSON.parse(ids.dates);

const require = createRequire(
  process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const widths = [390, 1440];
const measures = {};
const rows = [];

async function settle(page) {
  await page.waitForNetworkIdle({ idleTime: 300, timeout: 8000 }).catch(() => {});
}

function addDays(iso, days) {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

async function clickText(page, selector, text) {
  const ok = await page.evaluate(
    (sel, label) => {
      const node = [...document.querySelectorAll(sel)].find((n) => (n.textContent || "").trim().startsWith(label));
      if (!node) return false;
      node.scrollIntoView({ block: "center" });
      node.click();
      return true;
    },
    selector,
    text,
  );
  if (!ok) throw new Error(`botão não encontrado: ${text}`);
}

async function setDate(page, value) {
  await page.evaluate((v) => {
    const input = document.querySelector(".admin-cancel input[type=date]");
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(input, v);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
  await settle(page);
  await new Promise((r) => setTimeout(r, 400));
}

async function fillReason(page, text) {
  const area = await page.$(".admin-cancel textarea");
  if (area) {
    await area.click({ clickCount: 3 });
    await area.type(text);
  }
}

async function measure(page, width, scopeSelector) {
  return page.evaluate(
    (viewport, scopeSel) => {
      const problems = [];
      const doc = document.documentElement;
      const scroll = doc.scrollWidth > window.innerWidth + 1;
      if (scroll) problems.push(`rolagem ${doc.scrollWidth}>${window.innerWidth}`);
      const scopes = scopeSel ? [...document.querySelectorAll(scopeSel)] : [document.querySelector("main") || document.body];
      const scope = { querySelectorAll: (sel) => scopes.flatMap((s) => [...(s.matches(sel) ? [s] : []), ...s.querySelectorAll(sel)]) };
      const min = viewport < 960 ? 44 : 40;
      const controls = scope
        ? [...scope.querySelectorAll("input:not([type=checkbox]):not([type=radio]), select, textarea, button, a.admin-primary, a.admin-secondary")]
            .filter((n) => {
              const r = n.getBoundingClientRect();
              return r.width > 1 && r.height > 1;
            })
        : [];
      const short = controls
        .filter((n) => n.getBoundingClientRect().height + 0.5 < min)
        .map((n) => `${(n.textContent || n.getAttribute("aria-label") || n.tagName).trim().slice(0, 28)} ${Math.round(n.getBoundingClientRect().height)}`);
      if (short.length) problems.push(`altura ${short.join(", ")}`);
      const overlaps = []; const same = (a, b) => a.contains(b) || b.contains(a);
      for (let i = 0; i < controls.length; i += 1) {
        for (let j = i + 1; j < controls.length; j += 1) {
          const a = controls[i].getBoundingClientRect();
          const b = controls[j].getBoundingClientRect();
          const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (w > 1 && h > 1 && !same(controls[i], controls[j])) {
            overlaps.push(`${(controls[i].textContent || "").trim().slice(0, 16)}×${(controls[j].textContent || "").trim().slice(0, 16)}`);
          }
        }
      }
      if (overlaps.length) problems.push(`sobreposição ${overlaps.slice(0, 3).join("; ")}`);
      const fonts = new Set();
      const bad = [];
      if (scope) {
        for (const n of scope.querySelectorAll("*")) {
          const r = n.getBoundingClientRect();
          if (r.width < 2 || r.height < 2) continue;
          const family = (getComputedStyle(n).fontFamily || "").split(",")[0].replace(/["']/g, "").trim();
          fonts.add(family);
          if (/playfair/i.test(family)) bad.push((n.textContent || "").trim().slice(0, 24));
        }
      }
      if (bad.length) problems.push(`Playfair ${[...new Set(bad)].slice(0, 3).join(", ")}`);
      const outside = [];
      if (scope) {
        for (const n of scope.querySelectorAll("button, input, select, textarea, label, p, h1, h2")) {
          const r = n.getBoundingClientRect();
          if (!n.closest(".queue-lenses") && r.width > 1 && (r.right > window.innerWidth + 1 || r.left < -1)) {
            outside.push((n.textContent || n.tagName).trim().slice(0, 20));
          }
        }
      }
      if (outside.length) problems.push(`fora da tela ${outside.slice(0, 3).join(", ")}`);
      const mark = document.querySelector(".queue-exception");
      let markStyle = null;
      if (mark) {
        const css = getComputedStyle(mark);
        markStyle = { size: css.fontSize, weight: css.fontWeight, color: css.color };
      }
      const panel = document.querySelector(".admin-cancel");
      let panelBox = null;
      if (panel) {
        const r = panel.getBoundingClientRect();
        panelBox = { left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width) };
      }
      return {
        scroll,
        scrollWidth: doc.scrollWidth,
        innerWidth: window.innerWidth,
        controls: controls.length,
        minHeight: controls.length ? Math.round(Math.min(...controls.map((n) => n.getBoundingClientRect().height))) : null,
        fonts: [...fonts].slice(0, 6),
        markStyle,
        panelBox,
        problems,
      };
    },
    width,
    scopeSelector || null,
  );
}

function record(file, m) {
  measures[file] = m;
  const note = m.problems.length ? m.problems.join("; ") : "ok";
  rows.push(
    `| ${file} | ${m.controls} | ${m.minHeight ?? "—"} | ${m.fonts.join(", ")} | ${m.scroll ? `sim (${m.scrollWidth}>${m.innerWidth})` : "não"} | ${note} |`,
  );
  console.log(file, note);
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--no-first-run", "--disable-extensions"],
});
const page = await browser.newPage();

async function shot(name, width, scope) {
  await page.setViewport({ width, height: width < 960 ? 900 : 1000 });
  await settle(page);
  const file = `${name}-${width}.png`;
  await page.screenshot({ path: join(outDir, file), fullPage: true });
  record(file, await measure(page, width, scope));
}

async function open(path, width) {
  await page.setViewport({ width, height: width < 960 ? 900 : 1000 });
  await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".admin-topbar", { timeout: 8000 });
  await settle(page);
  await new Promise((r) => setTimeout(r, 500));
}

let current = dates.quarta;
try {
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(`${origin}/#acesso`, { waitUntil: "domcontentloaded" });
  await settle(page);
  const enter = await page.waitForSelector("button.header-access-local-enter", { timeout: 8000 });
  await enter.click();
  await page.waitForFunction(() => location.pathname.startsWith("/admin"), { timeout: 8000 });
  await settle(page);

  // A data atual do pedido muda a cada execução (caminho feliz no fim); lê-la mantém o script repetível.
  current = await page.evaluate(async (id) => {
    const response = await fetch(`/api/v1/admin/orders/${id}`, { credentials: "include" });
    return (await response.json()).production_local_date;
  }, ids.LPC109NORMAL);

  for (const width of widths) {
    // Mudar a data: dia normal, dia fechado, capacidade cheia, erro.
    await open(`/admin/pedidos/${ids.LPC109NORMAL}`, width);
    await clickText(page, "button", "Mudar a data da fornada");
    await page.waitForSelector(".admin-cancel input[type=date]");
    await setDate(page, addDays(current, 7));
    await shot("reagendar-dia-normal", width, ".admin-cancel");

    await setDate(page, dates.sexta_fechada);
    await shot("reagendar-dia-fechado", width, ".admin-cancel");

    await setDate(page, dates.dia_cheio);
    await shot("reagendar-capacidade-cheia", width, ".admin-cancel");
    await fillReason(page, "Exemplo de exceção para a captura");
    await page.evaluate(() => {
      const customer = document.querySelector(".admin-cancel input[type=radio]");
      customer?.click();
    });
    await clickText(page, "button", "Confirmar exceção de data");
    await page.waitForSelector(".admin-cancel .admin-error", { timeout: 8000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 500));
    await shot("reagendar-erro", width, ".admin-cancel");

    // Corrigir a data registrada (concluído).
    await open(`/admin/pedidos/${ids.LPC109CONCL}`, width);
    await clickText(page, "button", "Corrigir a data registrada");
    await page.waitForSelector(".admin-cancel input[type=date]");
    await shot("corrigir-data-registrada", width, ".admin-cancel");

    // Caixa de pedido existente na solicitação.
    await open(`/admin/pedidos/solicitacao/${ids.date_request_existente}`, width);
    await shot("solicitacao-pedido-existente", width, ".admin-warning, .admin-attention, [data-existing-orders], .admin-actions");

    // Anular por duplicidade (candidato pré-selecionado).
    await open(`/admin/pedidos/${ids.LPC109DUPB}`, width);
    await shot("detalhe-possivel-duplicidade", width, ".admin-warning, .admin-actions, .admin-muted a");
    await clickText(page, "button", "Anular por duplicidade");
    await page.waitForSelector(".admin-cancel");
    await shot("anular-por-duplicidade", width, ".admin-cancel");

    // Detalhe do anulado e do original.
    await open(`/admin/pedidos/${ids.LPC109ANUL}`, width);
    await shot("detalhe-anulado", width, ".admin-warning, .admin-actions");
    await open(`/admin/pedidos/${ids.LPC109ORIG}`, width);
    await shot("detalhe-original", width, ".admin-actions, .admin-muted a");

    // Fila: lente de possível duplicidade e lente de anulados.
    for (const [lens, name] of [
      ["pending:possible_duplicate", "fila-possivel-duplicidade"],
      ["audit:duplicates", "fila-anulados-por-duplicidade"],
    ]) {
      await open("/admin/pedidos", width);
      await page.evaluate(() => {
        const toggle = document.querySelector(".queue-filters-toggle");
        if (toggle && !document.querySelector("select[aria-label='Situação']")) toggle.click();
      });
      await new Promise((r) => setTimeout(r, 300));
      await page.select("select[aria-label='Situação']", lens);
      await page.evaluate(() => {
        const form = document.querySelector(".queue-filters");
        const submit = form?.querySelector("button[type=submit]");
        submit?.click();
      });
      await settle(page);
      await new Promise((r) => setTimeout(r, 600));
      await shot(name, width, ".admin-queue");
    }

    // Fila com a marca "antecipada" (original com exceção registrada).
    await open("/admin/pedidos", width);
    await page.evaluate(() => {
      const button = [...document.querySelectorAll(".queue-lens")].find((n) => n.textContent?.startsWith("Entregues"));
      button?.click();
    });
    await settle(page);
    await new Promise((r) => setTimeout(r, 500));
    await shot("fila-entregues-com-marca", width, ".admin-queue");
  }
  // Caminho feliz 1: mudar a data pela tela (origem "pela loja", sem aviso).
  await open(`/admin/pedidos/${ids.LPC109NORMAL}`, 1440);
  await clickText(page, "button", "Mudar a data da fornada");
  await page.waitForSelector(".admin-cancel input[type=date]");
  await setDate(page, addDays(current, 14));
  await fillReason(page, "Cliente pediu outro sábado; exemplo");
  await page.evaluate(() => {
    const radios = [...document.querySelectorAll(".admin-cancel input[type=radio]")];
    radios[1]?.click();
    const notify = [...document.querySelectorAll(".admin-cancel input[type=checkbox]")].pop();
    if (notify?.checked) notify.click();
  });
  await clickText(page, "button", "Confirmar exceção de data");
  await page.waitForFunction(() => !document.querySelector(".admin-cancel input[type=date]"), { timeout: 8000 });
  await settle(page);
  await new Promise((r) => setTimeout(r, 500));
  const afterReschedule = await page.evaluate(() => document.body.innerText);
  const rescheduled = /Solicitado para/.test(afterReschedule) && /adiada/i.test(afterReschedule);
  measures["fluxo-reagendar"] = { ok: rescheduled, excerpt: (afterReschedule.match(/Solicitado para[^\n]*/) || [""])[0] };
  console.log("fluxo reagendar", rescheduled ? "ok" : "FALHOU", measures["fluxo-reagendar"].excerpt);
  await page.setViewport({ width: 1440, height: 1000 });
  await page.screenshot({ path: join(outDir, "reagendado-detalhe-1440.png"), fullPage: true });

  // Caminho feliz 2: mover o pedido existente pela solicitação.
  await open(`/admin/pedidos/solicitacao/${ids.date_request_mover}`, 1440);
  try {
    await clickText(page, "button", "Mover LPC109EXIST2");
  } catch {
    console.log("fluxo mover: solicitação já convertida em execução anterior");
  }
  await page.waitForFunction(() => /convertida|Convertida|converted/.test(document.body.innerText), { timeout: 8000 }).catch(() => {});
  await settle(page);
  await new Promise((r) => setTimeout(r, 600));
  const afterMove = await page.evaluate(() => document.body.innerText);
  measures["fluxo-mover"] = { text: afterMove.slice(0, 400) };
  await page.screenshot({ path: join(outDir, "solicitacao-movida-1440.png"), fullPage: true });
  console.log("fluxo mover", /LPC109EXIST/.test(afterMove) ? "mostra o pedido existente" : "sem referência");
} finally {
  await browser.close();
}

const head = "| Captura | Controles | Menor altura (px) | Fontes | Rolagem horizontal | Observação |\n| --- | --- | --- | --- | --- | --- |";
writeFileSync(join(outDir, "medidas.json"), JSON.stringify(measures, null, 2));
writeFileSync(join(outDir, "medidas-tabela.md"), `${head}\n${rows.join("\n")}\n`);



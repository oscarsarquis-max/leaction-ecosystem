/**
 * 109E: percorre a compra na vitrine no banco de captura (dados de exemplo, Hub simulado, sem pagar).
 * Pré-requisito: node scripts/p109e-capture-server.py rodando em :5176 (python scripts/p109e-capture-server.py).
 *   node scripts/p109e-purchase.mjs
 * Salva readme/evidence/prompt-109e/compra-{vitrine,carrinho,pagamento}-{390,1440}.png (6 capturas).
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = "http://127.0.0.1:5176";
const outDir = join(root, "readme", "evidence", "prompt-109e");
mkdirSync(outDir, { recursive: true });

const require = createRequire(
  process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = [];
function note(line) {
  log.push(line);
  console.log(line);
}

async function clickByText(page, selector, text, { exact = false } = {}) {
  const ok = await page.evaluate(
    (sel, wanted, strict) => {
      const nodes = [...document.querySelectorAll(sel)].filter((n) => {
        const r = n.getBoundingClientRect();
        return r.width > 1 && r.height > 1;
      });
      const hit = nodes.find((n) => {
        const t = (n.textContent || "").replace(/\s+/g, " ").trim();
        return strict ? t === wanted : t.includes(wanted);
      });
      if (!hit) return false;
      hit.scrollIntoView({ block: "center" });
      hit.click();
      return true;
    },
    selector,
    text,
    exact,
  );
  if (!ok) throw new Error(`não achei ${selector} com "${text}"`);
}

async function overflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
}

async function walk(width) {
  const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run", "--disable-extensions"] });
  const page = await browser.newPage();
  await page.setViewport({ width, height: width < 960 ? 900 : 1000 });
  const stamp = `${width}px`;
  try {
    // 1. vitrine
    await page.goto(`${origin}/#paes`, { waitUntil: "networkidle2" });
    await page.waitForSelector(".shelf-card, .shelf-card-media, a[href^='/paes/']", { timeout: 15000 });
    await page.evaluate(() => document.querySelector("a[href^='/paes/']")?.scrollIntoView({ block: "center" }));
    await sleep(600);
    await page.screenshot({ path: join(outDir, `compra-vitrine-${width}.png`), fullPage: false });
    note(`${stamp} vitrine ok, rolagem lateral: ${await overflow(page)}`);

    // 2. escolher pão
    await clickByText(page, "a", "Escolher meu pão");
    await page.waitForFunction(() => location.pathname.startsWith("/paes/"), { timeout: 8000 });
    await page.waitForFunction(
      () => [...document.querySelectorAll("button")].some((b) => b.textContent.includes("Adicionar ao carrinho")),
      { timeout: 10000 },
    );
    note(`${stamp} pão escolhido: ${page.url()}`);

    // 3. adicionar
    await clickByText(page, "button", "Adicionar ao carrinho");
    await sleep(500);
    const drawer = await page.evaluate(() => (document.querySelector(".selection-drawer, [role=dialog]")?.textContent || "").replace(/\s+/g, " ").slice(0, 160));
    note(`${stamp} após adicionar: ${drawer || "(sem gaveta)"}`);
    await clickByText(page, "button, a", "Ir ao carrinho para finalizar");
    await page.waitForFunction(() => location.pathname === "/pedido/novo", { timeout: 8000 });
    await page.waitForFunction(() => document.querySelector("main.checkout-page h1")?.textContent === "Seu carrinho", { timeout: 8000 });

    // 4. revisar: data, contato, endereço
    await page.waitForSelector(".bake-calendar button.bake-day.is-available", { timeout: 15000 });
    await sleep(800);
    const picked = await page.evaluate(() => {
      const days = [...document.querySelectorAll(".bake-calendar button.bake-day")].filter(
        (b) => !b.disabled && /\bis-(available|at-capacity)\b/.test(b.className) && !/\bis-full\b/.test(b.className),
      );
      const day = days[0];
      if (!day) return null;
      day.click();
      return (day.getAttribute("aria-label") || day.textContent || "").trim();
    });
    note(`${stamp} dia escolhido no calendário: ${picked}`);
    await sleep(1500);
    const fill = async (label, value) => {
      const ok = await page.evaluate(
        (text, v) => {
          const lab = [...document.querySelectorAll("main.checkout-page label")].find((l) => (l.textContent || "").trim().startsWith(text));
          const el = lab?.querySelector("input, select, textarea");
          if (!el) return false;
          const proto = el.tagName === "SELECT" ? HTMLSelectElement.prototype : el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
          Object.getOwnPropertyDescriptor(proto, "value").set.call(el, v);
          el.dispatchEvent(new Event(el.tagName === "SELECT" ? "change" : "input", { bubbles: true }));
          return true;
        },
        label,
        value,
      );
      if (!ok) throw new Error(`campo ${label} ausente`);
    };
    await fill("Nome de quem pede", "Cliente de Exemplo");
    await fill("E-mail para acompanhar o pedido", "cliente-109e@example.test");
    await fill("Rua", "Rua das Fornadas");
    await fill("Número", "100");
    await fill("Bairro", "Centro");
    await fill("Cidade", "Fortaleza");
    await fill("Estado", "CE");
    await fill("CEP", "60150-160");
    await sleep(600);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: join(outDir, `compra-carrinho-${width}.png`), fullPage: true });
    note(`${stamp} carrinho preenchido, rolagem lateral: ${await overflow(page)}`);

    // 5. enviar pedido
    await page.waitForFunction(
      () => {
        const b = [...document.querySelectorAll("main.checkout-page button.primary")].find((x) => x.textContent.includes("Finalizar compra"));
        return b && !b.disabled;
      },
      { timeout: 15000 },
    );
    await clickByText(page, "main.checkout-page button.primary", "Finalizar compra");
    await page.waitForFunction(() => location.pathname.startsWith("/pedido/") && location.pathname !== "/pedido/novo", { timeout: 15000 });
    await sleep(2500);
    const status = await page.evaluate(() => document.querySelector("main.checkout-page")?.innerText.slice(0, 700));
    note(`${stamp} pedido enviado: ${page.url()}\n${status}`);

    // 6. pagamento (sem pagar): confere se os botões de pagamento aparecem
    const paymentButtons = await page.evaluate(() => [...document.querySelectorAll("main.checkout-page button")].map((b) => b.textContent.trim()).filter((t) => /Pagar|Pix|cartão/i.test(t)));
    note(`${stamp} botões de pagamento: ${paymentButtons.join(" | ") || "(nenhum)"}`);
    await page.screenshot({ path: join(outDir, `compra-pagamento-${width}.png`), fullPage: true });
    note(`${stamp} pagamento alcançado, rolagem lateral: ${await overflow(page)}`);
  } finally {
    await browser.close();
  }
}

for (const width of [390, 1440]) {
  await walk(width);
}
writeFileSync(join(outDir, "compra-passos.txt"), `${log.join("\n")}\n`, "utf8");

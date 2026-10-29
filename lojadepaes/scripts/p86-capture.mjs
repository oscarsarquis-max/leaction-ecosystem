import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.env.P86_OUT || join(root, "readme", "evidence", "prompt-86", "prod");
mkdirSync(outDir, { recursive: true });
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const origin = "https://lojadepaes.com.br";
const hamburger =
  "queremos fazer um hamburguer bem legal, com batatas e molho. que sugestao de acompanhamento vc poderia me dar? que tipo de pao vc aconselha? e que bebidas ficariam bem?";
const intercepted = [];
const report = { origin, steps: [], images: [], intercepted: [] };

function dump(name, data) {
  writeFileSync(join(outDir, name), JSON.stringify(data, null, 2));
}

async function waitImages(page) {
  await page.evaluate(() =>
    Promise.race([
      Promise.all(
        [...document.images].map((img) =>
          img.complete
            ? null
            : new Promise((resolve) => {
                img.onload = img.onerror = resolve;
              }),
        ),
      ),
      new Promise((resolve) => setTimeout(resolve, 4000)),
    ]),
  );
}

async function waitVitrine(page) {
  await page.waitForFunction(
    () => {
      const loading = document.body.innerText.includes("Carregando a seleção");
      const cards = document.querySelectorAll(".acc-card").length;
      const empty = document.body.innerText.includes("Não há complementos disponíveis para essa sugestão");
      const off = document.body.innerText.includes("Esta seleção ainda não está publicada");
      return !loading && (cards > 0 || empty || off);
    },
    { timeout: 45000 },
  );
  await waitImages(page);
}

async function shot(page, name, fullPage = false) {
  const path = join(outDir, name);
  await page.screenshot({ path, fullPage });
  report.images.push(name);
  return path;
}

async function sendChat(page, text) {
  await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio']", { timeout: 10000 });
  await page.evaluate(() => {
    const clearBtn = document.querySelector(".gigio-tools .text-button");
    if (clearBtn && (clearBtn.textContent || "").includes("Limpar")) {
      clearBtn.click();
    }
  });
  await page.waitForFunction(() => !document.querySelector(".gigio-status")?.textContent?.includes("consultando"), {
    timeout: 10000,
  });
  await page.$eval(
    "textarea[aria-label='Mensagem para o Gigio']",
    (el, value) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
      setter?.call(el, value);
      el.dispatchEvent(new Event("input", { bubbles: true }));
    },
    text,
  );
  const before = await page.evaluate(() => document.querySelectorAll(".gigio-msg.is-assistant").length);
  const beforeHits = await page.evaluate(() => window.__p84Hits || 0);
  await page.click(".gigio-form button[type='submit']");
  await page.waitForFunction(
    (prev, hits) => {
      if ((window.__p84Hits || 0) > hits) {
        return true;
      }
      const status = document.querySelector(".gigio-status")?.textContent || "";
      if (status.includes("consultando")) {
        return false;
      }
      const assistants = [...document.querySelectorAll(".gigio-msg.is-assistant")];
      if (assistants.length <= prev) {
        return false;
      }
      const last = assistants.at(-1);
      return Boolean(last && ((last.innerText || "").length > 40 || last.querySelector("a.gigio-cta")));
    },
    { timeout: 90000 },
    before,
    beforeHits,
  );
  return page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    const box = last?.querySelector("a.gigio-cta")?.getBoundingClientRect();
    const form = document.querySelector(".gigio-form")?.getBoundingClientRect();
    return {
      reply: last?.innerText?.slice(0, 2200) || "",
      cta: last?.querySelector("a.gigio-cta")?.textContent?.trim() || "",
      href: last?.querySelector("a.gigio-cta")?.getAttribute("href") || "",
      recipe: [...(last?.querySelectorAll("a.gigio-msg-link") || [])].map((node) => node.textContent?.trim()),
      sources: [...(last?.querySelectorAll(".gigio-source-title") || [])].map((node) => node.textContent?.trim()),
      ctaVisible: Boolean(box && box.height > 0 && (!form || box.bottom <= form.top + 8)),
    };
  });
}

async function captureVitrine(page, href, name) {
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}${href}`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await waitVitrine(page);
  const cards = await page.evaluate(() => ({
    title: document.querySelector("h1, .acc-title, .vitrine-title")?.textContent?.trim() || "",
    filters: [...document.querySelectorAll(".acc-filter, .context-filter")].map((node) => node.textContent?.trim()),
    items: [...document.querySelectorAll(".acc-card")].slice(0, 10).map((card) => ({
      name: card.querySelector(".acc-card-name, h2, h3")?.textContent?.trim() || card.innerText.slice(0, 120),
      category: card.querySelector(".acc-card-cat, .acc-cat")?.textContent?.trim() || "",
    })),
  }));
  dump(`vitrine-${name}.json`, { href, ...cards });
  await shot(page, `vitrine-${name}-1440.png`, true);
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await shot(page, `vitrine-${name}-390.png`, true);
  return cards;
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "new",
  protocolTimeout: 180000,
  args: ["--hide-scrollbars", "--disable-gpu", "--no-first-run"],
});

try {
  const page = await browser.newPage();
  await page.evaluateOnNewDocument(() => {
    window.__p84Hits = 0;
  });
  page.on("response", async (res) => {
    try {
      if (res.url().includes("/api/v1/gigio/chat") && res.request().method() === "POST") {
        const body = await res.json();
        intercepted.push({
          url: res.url(),
          status: res.status(),
          sources: body.sources || [],
          cta: body.cta || null,
          links: body.links || [],
          notice: body.notice || "",
          reply: String(body.reply || "").slice(0, 2000),
        });
        await page.evaluate(() => {
          window.__p84Hits = (window.__p84Hits || 0) + 1;
        });
      }
    } catch {
      intercepted.push({ url: res.url(), status: res.status(), error: "parse" });
    }
  });
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForSelector("button.gigio-launch", { timeout: 20000 });
  await page.click("button.gigio-launch");
  await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio']", { timeout: 10000 });

  const burger = await sendChat(page, hamburger);
  report.steps.push({ step: "hamburguer", ...burger });
  dump("chat-hamburguer-ui.json", burger);
  await page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    last?.querySelector(".gigio-sources summary")?.click();
    last?.querySelector("a.gigio-cta")?.scrollIntoView({ block: "end" });
  });
  await shot(page, "chat-hamburguer-1440.png");
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    last?.querySelector("a.gigio-cta")?.scrollIntoView({ block: "end" });
  });
  await shot(page, "chat-hamburguer-390.png");

  if (burger.href && burger.href.startsWith("/acompanhar") && burger.cta !== "Explorar a vitrine") {
    const cards = await captureVitrine(page, burger.href, "hamburguer");
    report.steps.push({ step: "vitrine-hamburguer", ...cards });
    report.steps.push({ step: "listing-check", first: cards.items?.[0]?.name || "" });
  }

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForSelector("button.gigio-launch", { timeout: 20000 });
  await page.click("button.gigio-launch");
  await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio']", { timeout: 10000 });
  const sardine = await sendChat(page, "O que combina com a receita de sardinhas com homus de vocês?");
  report.steps.push({ step: "sardinhas", ...sardine });
  dump("chat-sardinhas-ui.json", sardine);
  await shot(page, "chat-sardinhas-1440.png");
} finally {
  await browser.close();
}

report.intercepted = intercepted;
dump("report.json", report);
dump("intercepted-chat.json", intercepted);
console.log(JSON.stringify(report, null, 2));

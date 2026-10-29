import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.env.P84_OUT || join(root, "readme", "evidence", "prompt-84", "prod");
mkdirSync(outDir, { recursive: true });
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const origin = "https://lojadepaes.com.br";
const intercepted = [];
const report = { origin, steps: [], images: [], intercepted: [] };

function dump(name, data) {
  writeFileSync(join(outDir, name), JSON.stringify(data, null, 2));
}

async function waitImages(page) {
  await page.evaluate(() =>
    Promise.all(
      [...document.images].map((img) =>
        img.complete
          ? null
          : new Promise((resolve) => {
              img.onload = img.onerror = resolve;
            }),
      ),
    ),
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

async function shot(page, name, fullPage = true) {
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
  await page.$eval("textarea[aria-label='Mensagem para o Gigio']", (el, value) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
    setter?.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }, text);
  const before = await page.evaluate(() => document.querySelectorAll(".gigio-msg.is-assistant").length);
  const beforeHits = intercepted.length;
  await page.click(".gigio-form button[type='submit']");
  await page.waitForFunction(
    (prev, hits) => {
      if (window.__p84Hits > hits) {
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
    { timeout: 60000 },
    before,
    beforeHits,
  );
  return page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    const sources = [...(last?.querySelectorAll(".gigio-source") || [])].map((node) => ({
      title: node.querySelector(".gigio-source-title")?.textContent?.trim() || "",
      href: node.querySelector("a")?.getAttribute("href") || "",
      note: node.querySelector(".gigio-source-note")?.textContent?.trim() || "",
    }));
    return {
      reply: last?.innerText?.slice(0, 1800) || "",
      cta: last?.querySelector("a.gigio-cta")?.textContent?.trim() || "",
      href: last?.querySelector("a.gigio-cta")?.getAttribute("href") || "",
      sources,
    };
  });
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "new",
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
          reply: String(body.reply || "").slice(0, 1600),
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
  await shot(page, "gigio-open-1440.png", false);

  const frios = await sendChat(
    page,
    "Vou receber amigos e quero montar uma mesa de frios. Que pães e acompanhamentos você sugere?",
  );
  report.steps.push({ step: "mesa-frios", ...frios });
  dump("chat-frios-ui.json", frios);
  await page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    last?.querySelector(".gigio-sources summary")?.click();
    last?.scrollIntoView({ block: "center" });
  });
  await shot(page, "chat-frios-1440.png", false);
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await shot(page, "chat-frios-390.png", false);

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  const sardine = await sendChat(page, "O que combina com a receita de sardinhas com homus de vocês?");
  report.steps.push({ step: "sardinhas-homus", ...sardine });
  dump("chat-sardine-ui.json", sardine);
  await page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    last?.querySelector(".gigio-sources summary")?.click();
    last?.scrollIntoView({ block: "center" });
  });
  await shot(page, "chat-sardine-1440.png", false);
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await shot(page, "chat-sardine-390.png", false);

  const journeys = [
    ["vitrine-frios-cta", frios.href],
    ["vitrine-sardine-cta", sardine.href],
  ];
  for (const [name, href] of journeys) {
    if (!href || !href.startsWith("/acompanhar?")) {
      continue;
    }
    await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
    await page.goto(`${origin}${href}`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitVitrine(page);
    const cards = await page.evaluate(() => {
      const title = document.querySelector("h1, .acc-title, .vitrine-title")?.textContent?.trim() || "";
      return {
        title,
        heading: document.body.innerText.split("\n").slice(0, 8),
        items: [...document.querySelectorAll(".acc-card")].slice(0, 8).map((card) => ({
          name: card.querySelector(".acc-card-name, h2, h3")?.textContent?.trim() || card.innerText.slice(0, 120),
          category: card.querySelector(".acc-card-cat, .acc-cat")?.textContent?.trim() || "",
        })),
      };
    });
    dump(`${name}.json`, { href, ...cards });
    await shot(page, `${name}-1440.png`, true);
    await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
    await shot(page, `${name}-390.png`, true);
  }
} finally {
  await browser.close();
}

report.intercepted = intercepted;
dump("report.json", report);
dump("intercepted-chat.json", intercepted);
console.log(JSON.stringify(report, null, 2));

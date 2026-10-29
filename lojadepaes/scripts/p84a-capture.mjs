import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.env.P84A_OUT || join(root, "readme", "evidence", "prompt-84a", "prod");
mkdirSync(outDir, { recursive: true });
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const origin = "https://lojadepaes.com.br";
const intercepted = [];
const report = { origin, steps: [], images: [], intercepted: [] };

function dump(name, data) {
  writeFileSync(join(outDir, name), JSON.stringify(data, null, 2));
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
      return Boolean(last && (last.innerText || "").length > 40);
    },
    { timeout: 60000 },
    before,
    beforeHits,
  );
  return page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    const sources = [...(last?.querySelectorAll(".gigio-source") || [])].map((node) => ({
      title: node.querySelector(".gigio-source-title")?.textContent?.trim() || "",
      score: node.querySelector(".gigio-source-score")?.textContent?.trim() || "",
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
  await shot(page, "gigio-open-1440.png");

  const evalChat = await sendChat(
    page,
    "O Sacramentos Sabina Entre Serras Sauvignon Blanc 2025 tem avaliação?",
  );
  report.steps.push({ step: "sacramentos", ...evalChat });
  dump("chat-sacramentos-ui.json", evalChat);
  await page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    last?.querySelector(".gigio-sources summary")?.click();
    last?.scrollIntoView({ block: "center" });
  });
  await shot(page, "chat-sacramentos-1440.png");
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await shot(page, "chat-sacramentos-390.png");

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  const fish = await sendChat(page, "Qual vinho combina com peixe grelhado?");
  report.steps.push({ step: "peixe", ...fish });
  dump("chat-peixe-ui.json", fish);
  await page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    last?.querySelector(".gigio-sources summary")?.click();
    last?.scrollIntoView({ block: "center" });
  });
  await shot(page, "chat-peixe-1440.png");
} finally {
  await browser.close();
}

report.intercepted = intercepted;
dump("report.json", report);
dump("intercepted-chat.json", intercepted);
console.log(JSON.stringify(report, null, 2));

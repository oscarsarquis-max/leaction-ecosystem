import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.env.P83_OUT || join(root, "readme", "evidence", "prompt-83", "prod");
mkdirSync(outDir, { recursive: true });
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const origin = "https://lojadepaes.com.br";
const report = { origin, steps: [], images: [] };

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
  const box = await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio']", { timeout: 10000 });
  await box.click({ clickCount: 3 });
  await page.keyboard.press("Backspace");
  await page.type("textarea[aria-label='Mensagem para o Gigio']", text);
  const before = await page.evaluate(() => document.querySelectorAll(".gigio-msg.is-assistant").length);
  await page.click(".gigio-form button[type='submit']");
  await page.waitForFunction(
    (prev) => {
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
  );
  return page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    const sources = [...(last?.querySelectorAll(".gigio-source") || [])].map((node) => ({
      title: node.querySelector(".gigio-source-title")?.textContent?.trim() || "",
      href: node.querySelector("a")?.getAttribute("href") || "",
      note: node.querySelector(".gigio-source-note")?.textContent?.trim() || "",
    }));
    return {
      reply: last?.innerText?.slice(0, 1600) || "",
      cta: last?.querySelector("a.gigio-cta")?.textContent?.trim() || "",
      href: last?.querySelector("a.gigio-cta")?.getAttribute("href") || "",
      sources,
      hasComplete: (last?.innerText || "").includes("Para completar a mesa"),
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
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForSelector("button.gigio-launch", { timeout: 20000 });
  await page.click("button.gigio-launch");
  await page.click("button.text-button");
  await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio']", { timeout: 10000 });

  const pork = await sendChat(page, "Vou fazer um churrasco de porco e linguiça. Qual vinho combina?");
  report.steps.push({ step: "churrasco-porco", ...pork });
  dump("chat-pork-ui.json", pork);
  await page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    last?.querySelector(".gigio-sources summary")?.click();
    last?.scrollIntoView({ block: "center" });
  });
  await shot(page, "chat-pork-1440.png", false);

  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await shot(page, "chat-pork-390.png", false);

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  const cheese = await sendChat(page, "Quero montar uma tábua de queijos. Qual vinho serve?");
  report.steps.push({ step: "tabua-queijos", ...cheese });
  dump("chat-cheese-ui.json", cheese);
  await page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    last?.querySelector(".gigio-sources summary")?.click();
    last?.scrollIntoView({ block: "center" });
  });
  await shot(page, "chat-cheese-1440.png", false);

  if (pork.href && pork.href.startsWith("/acompanhar?")) {
    await page.goto(`${origin}${pork.href}`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitVitrine(page);
    await shot(page, "vitrine-cta-1440.png", true);
    await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
    await shot(page, "vitrine-cta-390.png", true);
  }

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/acompanhar?cats=vinhos&mesa=leitao,salada`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await waitVitrine(page);
  await shot(page, "vitrine-preserved-1440.png", true);
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await shot(page, "vitrine-preserved-390.png", true);

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/pedido/novo`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await shot(page, "order-review-no-submit.png", true);
  report.steps.push({ step: "order-review", href: "/pedido/novo", submitted: false });
} finally {
  await browser.close();
}

dump("report.json", report);
console.log(JSON.stringify(report, null, 2));

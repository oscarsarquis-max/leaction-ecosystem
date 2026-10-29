import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.env.P80_OUT || join(root, "readme", "evidence", "prompt-80", "prod");
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
    { timeout: 120000 },
    before,
  );
  return page.evaluate(() => {
    const last = [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1);
    return {
      reply: last?.innerText?.slice(0, 1200) || "",
      cta: last?.querySelector("a.gigio-cta")?.textContent?.trim() || "",
      href: last?.querySelector("a.gigio-cta")?.getAttribute("href") || "",
      ctas: [...document.querySelectorAll("a.gigio-cta")].map((a) => ({
        label: a.textContent.trim(),
        href: a.getAttribute("href"),
      })),
      hasComplete: (last?.innerText || "").includes("Para completar a mesa"),
    };
  });
}

async function measureVitrine(page) {
  return page.evaluate(() => {
    const grid = document.querySelector(".acc-grid");
    const cards = [...document.querySelectorAll(".acc-card")];
    const style = grid ? getComputedStyle(grid) : null;
    const headings = [...document.querySelectorAll("h1, h2, h3")].map((el) => el.textContent.trim());
    const photos = [...document.querySelectorAll(".acc-card-media img")].map((img) => {
      const box = img.getBoundingClientRect();
      const wrap = img.parentElement ? getComputedStyle(img.parentElement) : null;
      const computed = getComputedStyle(img);
      return {
        alt: img.alt,
        src: img.currentSrc || img.src,
        naturalW: img.naturalWidth,
        naturalH: img.naturalHeight,
        boxW: Math.round(box.width),
        boxH: Math.round(box.height),
        fit: computed.objectFit,
        position: computed.objectPosition,
        width: computed.width,
        height: computed.height,
        maxW: computed.maxWidth,
        maxH: computed.maxHeight,
        wrapPad: wrap?.padding || "",
        wrapRatio: wrap?.aspectRatio || "",
      };
    });
    return {
      url: location.href,
      title: document.querySelector("h1")?.textContent?.trim() || "",
      headings,
      context: document.querySelector(".acc-context")?.innerText?.replace(/\s+/g, " ").trim() || "",
      priceSample: document.querySelector(".acc-price")?.textContent?.trim() || "",
      naMercado: document.body.innerText.includes("na Mercado Livre"),
      empty: document.body.innerText.includes("Não há complementos disponíveis para essa sugestão"),
      cards: cards.length,
      names: cards.map((card) => card.querySelector("h3")?.textContent?.trim() || ""),
      columns: style?.gridTemplateColumns.split(" ").filter(Boolean).length || 0,
      photos,
    };
  });
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "new",
  args: ["--hide-scrollbars", "--disable-gpu", "--no-first-run"],
});

try {
  const catalog = await (await fetch(`${origin}/api/v1/accompaniments`)).json();
  const wine = await (await fetch(`${origin}/api/v1/accompaniments?cats=vinhos&mesa=leitao,salada`)).json();
  dump("catalog-generic.json", {
    enabled: catalog.enabled,
    source: catalog.source_status,
    n: (catalog.items || []).length,
    title: catalog.title,
  });
  dump("catalog-wine.json", {
    n: (wine.items || []).length,
    title: wine.title,
    context: wine.context,
    names: (wine.items || []).map((item) => item.name),
    stories: (wine.stories || []).map((story) => ({ title: story.title, names: (story.items || []).map((item) => item.name) })),
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForSelector("button.gigio-launch", { timeout: 20000 });
  await page.click("button.gigio-launch");
  await page.click("button.text-button");
  await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio']", { timeout: 10000 });

  const first = await sendChat(page, "Vou servir leitão com saladas. Que pão e acompanhamentos você sugere?");
  report.steps.push({ step: "meal-ask", ...first });
  dump("chat-meal.json", first);
  await page.evaluate(() => [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1)?.scrollIntoView({ block: "center" }));
  await shot(page, "chat-meal-1440.png", false);

  const wineAsk = await sendChat(page, "E um vinho?");
  report.steps.push({ step: "wine-followup", ...wineAsk, previousHref: first.href });
  dump("chat-wine.json", wineAsk);
  await shot(page, "chat-wine-1440.png", false);

  const cheeseAsk = await sendChat(page, "Um queijo também faria sentido?");
  report.steps.push({ step: "cheese-followup", ...cheeseAsk, firstHref: first.href });
  dump("chat-cheese.json", cheeseAsk);
  await shot(page, "chat-cheese-1440.png", false);

  if (first.href && first.href.startsWith("/acompanhar?")) {
    await page.goto(`${origin}${first.href}`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitVitrine(page);
    const mealVitrine = await measureVitrine(page);
    report.steps.push({ step: "meal-vitrine", ...mealVitrine });
    dump("vitrine-meal.json", mealVitrine);
    await shot(page, "vitrine-meal-1440.png", true);
  }

  const viewports = [
    { name: "1440", width: 1440, height: 1100 },
    { name: "1024", width: 1024, height: 1100 },
    { name: "768", width: 768, height: 1100 },
    { name: "390", width: 390, height: 844 },
    { name: "320", width: 320, height: 720 },
  ];
  const photoReport = [];
  for (const viewport of viewports) {
    await page.setViewport({ width: viewport.width, height: viewport.height, deviceScaleFactor: 1 });
    await page.goto(`${origin}/acompanhar?cats=vinhos&mesa=leitao,salada`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitVitrine(page);
    const measured = await measureVitrine(page);
    await shot(page, `garrafas-${viewport.name}.png`, true);
    photoReport.push({ viewport: viewport.name, ...measured });
  }
  dump("photos.json", photoReport);

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  for (const [name, path] of [
    ["geral-1440", "/acompanhar"],
    ["queijos-1440", "/acompanhar?cats=queijos"],
    ["azeites-1440", "/acompanhar?cats=azeites"],
    ["frios-1440", "/acompanhar?cats=frios"],
  ]) {
    await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitVitrine(page);
    await shot(page, `${name}.png`, true);
  }
} finally {
  await browser.close();
}

dump("report.json", report);
console.log(JSON.stringify(report, null, 2));

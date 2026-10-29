import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.env.P77_OUT || join(root, "readme", "evidence", "prompt-77", "prod");
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
        img.complete ? null : new Promise((resolve) => {
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

async function measureVitrine(page) {
  return page.evaluate(() => {
    const grid = document.querySelector(".acc-grid");
    const cards = [...document.querySelectorAll(".acc-card")];
    const style = grid ? getComputedStyle(grid) : null;
    const media = document.querySelector(".acc-card-media img");
    const mediaStyle = media ? getComputedStyle(media) : null;
    const label = [...document.querySelectorAll("label")].find((item) =>
      item.textContent.includes("Data informada de entrega"),
    );
    const help = document.querySelector(".acc-plan p")?.textContent?.trim() || "";
    return {
      url: location.href,
      title: document.querySelector("h1")?.textContent?.trim() || "",
      context: document.querySelector(".acc-context")?.innerText?.replace(/\s+/g, " ").trim() || "",
      empty: document.body.innerText.includes("Não há complementos disponíveis para essa sugestão"),
      cards: cards.length,
      names: cards.slice(0, 12).map((card) => card.querySelector("h3")?.textContent?.trim() || ""),
      columns: style?.gridTemplateColumns.split(" ").filter(Boolean).length || 0,
      objectFit: mediaStyle?.objectFit || "",
      objectPosition: mediaStyle?.objectPosition || "",
      imgPadding: media ? getComputedStyle(media.parentElement).padding : "",
      deliveryLabel: label ? "Data informada de entrega" : "",
      help: help.slice(0, 220),
      oldLabel: document.body.innerText.includes("Data prevista que você viu no destino"),
      destino: document.body.innerText.includes("destino"),
      firstCta: document.querySelector("a.acc-outbound")?.textContent?.trim() || "",
      firstCtaHref: document.querySelector("a.acc-outbound")?.getAttribute("href") || "",
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
  const wine = await (await fetch(`${origin}/api/v1/accompaniments?cats=vinhos`)).json();
  dump("catalog-generic.json", {
    enabled: catalog.enabled,
    source: catalog.source_status,
    n: (catalog.items || []).length,
    cats: [...new Set((catalog.items || []).map((item) => item.category))],
  });
  dump("catalog-wine.json", {
    n: (wine.items || []).length,
    context: wine.context,
    names: (wine.items || []).map((item) => item.name),
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });

  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForSelector("button.gigio-launch", { timeout: 20000 });
  await page.click("button.gigio-launch");
  await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio']", { timeout: 10000 });
  await shot(page, "chat-open-1440.png", false);

  const firstQuestion =
    "Como servir um pão de fermentação natural? Sugira vinho e queijo para acompanhar.";
  await page.type("textarea[aria-label='Mensagem para o Gigio']", firstQuestion);
  await page.click(".gigio-form button[type='submit']");
  await page.waitForFunction(
    () => {
      const status = document.querySelector(".gigio-status")?.textContent || "";
      if (status.includes("consultando")) {
        return false;
      }
      const assistants = [...document.querySelectorAll(".gigio-msg.is-assistant")];
      return assistants.some((el) => el.querySelector("a.gigio-cta") || (el.innerText || "").length > 40);
    },
    { timeout: 120000 },
  );
  const firstChat = await page.evaluate(() => ({
    reply: [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1)?.innerText?.slice(0, 800) || "",
    cta: document.querySelector("a.gigio-cta")?.textContent?.trim() || "",
    href: document.querySelector("a.gigio-cta")?.getAttribute("href") || "",
    status: document.querySelector(".gigio-status")?.textContent?.trim() || "",
    ctas: [...document.querySelectorAll("a.gigio-cta")].map((a) => ({
      label: a.textContent.trim(),
      href: a.getAttribute("href"),
    })),
  }));
  report.steps.push({ step: "first-chat", ...firstChat });
  dump("chat-first.json", firstChat);
  await page.evaluate(() => document.querySelector("a.gigio-cta")?.scrollIntoView({ block: "center" }));
  await shot(page, "chat-cta-1440.png", false);

  if (!firstChat.href) {
    throw new Error("CTA contextual não apareceu na resposta do Gigio");
  }
  if (!firstChat.href.startsWith("/acompanhar?")) {
    throw new Error(`CTA não é contextual: ${firstChat.href}`);
  }

  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded", timeout: 45000 }),
    page.click("a.gigio-cta"),
  ]);
  await waitVitrine(page);
  const afterClick = await measureVitrine(page);
  report.steps.push({ step: "cta-click", ...afterClick });
  dump("vitrine-contextual.json", afterClick);
  await shot(page, "vitrine-contextual-1440.png", true);
  if (!afterClick.cards && !afterClick.empty) {
    throw new Error("Clique no CTA não abriu a vitrine contextual");
  }

  const incompatible = (afterClick.names || []).filter((name) => {
    const folded = name.toLowerCase();
    return folded.includes("azeite") || folded.includes("embalagem") || folded.includes("caixa");
  });
  report.steps.push({ step: "incompatible-names", incompatible });

  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await page.goto(`${origin}${firstChat.href}`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await waitVitrine(page);
  await shot(page, "vitrine-contextual-390.png", true);

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForSelector("button.gigio-launch", { timeout: 20000 });
  await page.click("button.gigio-launch");
  await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio']", { timeout: 10000 });

  const persisted = await page.evaluate(() =>
    [...document.querySelectorAll("a.gigio-cta")].map((a) => ({
      label: a.textContent.trim(),
      href: a.getAttribute("href"),
    })),
  );
  report.steps.push({ step: "cta-persisted", persisted });

  const secondQuestion = "Prefiro queijo, sem vinho.";
  await page.type("textarea[aria-label='Mensagem para o Gigio']", secondQuestion);
  await page.click(".gigio-form button[type='submit']");
  await page.waitForFunction(
    () => {
      const status = document.querySelector(".gigio-status")?.textContent || "";
      if (status.includes("consultando")) {
        return false;
      }
      return document.querySelectorAll(".gigio-msg.is-assistant").length >= 2;
    },
    { timeout: 120000 },
  );
  const secondChat = await page.evaluate(() => ({
    reply: [...document.querySelectorAll(".gigio-msg.is-assistant")].at(-1)?.innerText?.slice(0, 800) || "",
    ctas: [...document.querySelectorAll("a.gigio-cta")].map((a) => ({
      label: a.textContent.trim(),
      href: a.getAttribute("href"),
    })),
  }));
  report.steps.push({ step: "continuation", ...secondChat });
  dump("chat-continuation.json", secondChat);
  await page.evaluate(() => [...document.querySelectorAll("a.gigio-cta")].at(-1)?.scrollIntoView({ block: "center" }));
  await shot(page, "chat-continuation-1440.png", false);

  if (secondChat.ctas?.[0]?.href !== firstChat.href) {
    throw new Error("Link da primeira resposta mudou após a continuação");
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
    await page.goto(`${origin}/acompanhar?cats=vinhos`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitVitrine(page);
    const measured = await measureVitrine(page);
    await shot(page, `garrafas-${viewport.name}.png`, true);
    photoReport.push({ viewport: viewport.name, ...measured });
  }
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/acompanhar?cats=queijos`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await waitVitrine(page);
  await shot(page, "queijos-1440.png", true);
  await page.goto(`${origin}/acompanhar?cats=azeites`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await waitVitrine(page);
  await shot(page, "azeites-1440.png", true);
  await page.goto(`${origin}/acompanhar`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await waitVitrine(page);
  const generic = await measureVitrine(page);
  await shot(page, "vitrine-geral-1440.png", true);
  report.steps.push({ step: "generic", ...generic });
  dump("photos.json", photoReport);
} finally {
  await browser.close();
}

dump("report.json", report);
console.log(JSON.stringify(report, null, 2));

/**
 * Validação SPIDER-UX-001 — narrativa completa, superfícies e CampoAberto.
 */
import { chromium } from "playwright";

const UI = process.env.SPIDER_UI_URL || "http://127.0.0.1:5180";
const API = process.env.SPIDER_API_URL || "http://127.0.0.1:8080";
const ARTICLE = `${API}/demo/partner/agro-hoje`;
const CHAPTERS = [
  "hub-hero",
  "hub-problem",
  "hub-context-model",
  "hub-how",
  "hub-capabilities",
  "hub-integration",
  "hub-experiences",
  "hub-governance",
  "hub-architecture",
  "hub-closing",
];

async function main() {
  const failures = [];
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(`${UI}/`, { waitUntil: "networkidle" });
  const brand = await page.getByTestId("hub-brand").innerText();
  if (!/SPIDER/i.test(brand) || !/Plataforma Contextual/i.test(brand)) {
    failures.push("missing Spider platform brand");
  }
  const hero = await page.getByTestId("hub-hero").innerText();
  if (!/caminhos executáveis/i.test(hero)) failures.push("missing value proposition");
  if (/Passo 1|Roteiro da experiência|Sobre o Spider/i.test(hero)) {
    failures.push("script or stray section leaked into first fold");
  }
  if (await page.getByTestId("spiderbank-entry").count()) failures.push("root opened SpiderBank");
  if (await page.getByRole("heading", { name: "Home operacional" }).count()) {
    failures.push("root opened Console");
  }

  for (const id of CHAPTERS) {
    if (!(await page.getByTestId(id).count())) failures.push(`missing chapter ${id}`);
  }

  const tryHref = await page.getByTestId("hub-cta-try").getAttribute("href");
  if (tryHref !== ARTICLE) failures.push("Experimentar does not open CampoAberto");
  const journeyHref = await page.getByTestId("open-partner").getAttribute("href");
  if (journeyHref !== ARTICLE) failures.push("experience CTA lost CampoAberto");

  const story = await page.getByTestId("experience-hub").innerText();
  if (!/IA interpreta/i.test(story) || !/capacidade empresarial permanece/i.test(story)) {
    failures.push("mechanism story incomplete");
  }
  if ((story.match(/contexto é criado depois do clique/gi) || []).length !== 1) {
    failures.push("CampoAberto explanation is missing or repeated");
  }

  await page.getByRole("tab", { name: "Plano" }).click();
  if (!/Execution Plan/i.test(await page.getByTestId("pipeline-detail").innerText())) {
    failures.push("pipeline interaction missing");
  }

  await page.getByTestId("hub-expand-architecture").click();
  if (!(await page.getByTestId("hub-lightbox").count())) failures.push("lightbox missing");
  await page.keyboard.press("Escape");
  if (await page.getByTestId("hub-lightbox").count()) failures.push("lightbox did not close");

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) failures.push("desktop overflow");

  await page.setViewportSize({ width: 1440, height: 900 });
  const overflow1440 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow1440) failures.push("1440 overflow");
  await page.setViewportSize({ width: 1920, height: 1080 });

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  if (!(await page.getByTestId("experience-hub").count())) failures.push("legacy route lost hub");

  await page.goto(`${UI}/spiderbank`, { waitUntil: "networkidle" });
  if (!(await page.getByTestId("direct-entry").count())) failures.push("/spiderbank missing bank");
  if ((await page.innerText("body")).includes("CampoAberto")) failures.push("direct bank invented CampoAberto");

  await page.goto(`${UI}/console`, { waitUntil: "networkidle" });
  if (!(await page.getByTestId("spider-console").count())) failures.push("/console missing console");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${UI}/`, { waitUntil: "networkidle" });
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (mobileOverflow) failures.push("mobile overflow");
  if (!(await page.getByTestId("hub-hero").count())) failures.push("mobile lost hero");

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(ARTICLE, { waitUntil: "networkidle" });
  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  if (!bank.url().includes("/spiderbank?ctx=")) failures.push("/go did not land on SpiderBank");
  if (new URL(bank.url()).pathname === "/") failures.push("/go redirected to hub root");

  await browser.close();
  if (failures.length) {
    console.error(failures.join("\n"));
    process.exit(1);
  }
  console.log("Experience Hub checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

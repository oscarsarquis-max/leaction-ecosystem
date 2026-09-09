/**
 * Evidências visuais SPIDER-UX-001 — Home narrativa completa.
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..", "..");
const outDir = path.join(root, "docs", "technical", "screenshots");
fs.mkdirSync(outDir, { recursive: true });

const UI = process.env.SPIDER_UI_URL || "http://127.0.0.1:5180";

const CHAPTERS = [
  ["hub-hero", "SPIDER-UX-001-hero.png"],
  ["hub-problem", "SPIDER-UX-001-problem.png"],
  ["hub-context-model", "SPIDER-UX-001-context-model.png"],
  ["hub-how", "SPIDER-UX-001-how-it-works.png"],
  ["hub-capabilities", "SPIDER-UX-001-capabilities.png"],
  ["hub-integration", "SPIDER-UX-001-integration.png"],
  ["hub-experiences", "SPIDER-UX-001-experience.png"],
  ["hub-governance", "SPIDER-UX-001-governance.png"],
  ["hub-architecture", "SPIDER-UX-001-architecture.png"],
  ["hub-closing", "SPIDER-UX-001-closing.png"],
];

async function shot(page, name, fullPage = false) {
  await page.screenshot({ path: path.join(outDir, name), fullPage });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(`${UI}/`, { waitUntil: "networkidle" });
  await page.getByTestId("hub-hero").waitFor();

  for (const [id, file] of CHAPTERS) {
    await page.getByTestId(id).scrollIntoViewIfNeeded();
    await shot(page, file);
  }

  await page.getByTestId("hub-how").scrollIntoViewIfNeeded();
  await page.getByRole("tab", { name: "Plano" }).click();
  await shot(page, "SPIDER-UX-001A-pipeline.png");
  await page.getByTestId("hub-capabilities").scrollIntoViewIfNeeded();
  await page.getByRole("tab", { name: "Simular" }).click();
  await shot(page, "SPIDER-UX-001A-capabilities.png");
  await page.getByTestId("hub-experiences").scrollIntoViewIfNeeded();
  await shot(page, "SPIDER-UX-001A-experience.png");

  await page.goto(`${UI}/`, { waitUntil: "networkidle" });
  await shot(page, "SPIDER-UX-001-full-home.png", true);
  await shot(page, "SPIDER-UX-001A-full-home.png", true);
  await shot(page, "EXPERIENCE-HUB-full-page.png", true);
  await shot(page, "EXPERIENCE-HUB-home.png");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${UI}/`, { waitUntil: "networkidle" });
  await page.getByTestId("hub-hero").waitFor();
  await shot(page, "SPIDER-UX-001-mobile.png");
  await shot(page, "SPIDER-UX-001A-mobile.png");
  await shot(page, "EXPERIENCE-HUB-mobile.png");

  await browser.close();
  console.log("SPIDER-UX-001 screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

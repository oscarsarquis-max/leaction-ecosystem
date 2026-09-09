/**
 * Validação manual automatizada SPIDER-DEMO-001B (browser real via Playwright).
 */
import { chromium } from "playwright";

const UI = process.env.SPIDER_UI_URL || "http://127.0.0.1:5180";
const API = process.env.SPIDER_API_URL || "http://127.0.0.1:8080";
const TECH = /MOCK_ONLY|SIMULATED_INFRASTRUCTURE|fingerprint|Intent|Policy|Capabilities|Data Plane/i;

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const failures = [];

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  const ad = await page.getByTestId("partner-ad").innerText();
  if (!/SPIDERBANK/i.test(ad) || !/Banco Contextual/i.test(ad) || !/CONHEÇA SUAS OPÇÕES/i.test(ad)) {
    failures.push("CampoAberto ad missing premium copy");
  }
  if (!/Quebra de safra/i.test(await page.getByTestId("partner-article").innerText())) {
    failures.push("CampoAberto editorial missing");
  }

  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  await bank.getByTestId("fold-moment").waitFor();
  const hero = await bank.getByTestId("spiderbank-hero").innerText();
  if (!/SPIDERBANK|Banco Contextual/i.test(await bank.locator(".sb-nav").innerText())) {
    failures.push("wordmark missing");
  }
  if (!/UM BANCO QUE/i.test(hero) || !/ENTENDE PRIMEIRO/i.test(hero)) {
    failures.push("hero missing impact headline");
  }
  if (TECH.test(hero)) failures.push("technical terms on first fold");
  const momentBox = await bank.getByTestId("fold-moment").boundingBox();
  if (!momentBox || momentBox.x < 800) failures.push("context aside not on the right of 16:9 fold");

  const wine = await bank.locator(".sb-wordmark").evaluate((el) => getComputedStyle(el).color);
  if (wine !== "rgb(124, 39, 72)") failures.push(`wordmark color ${wine}`);

  const bankUrl = bank.url();
  await bank.getByTestId("origin-context").scrollIntoViewIfNeeded();
  const story = await bank.getByTestId("story-path").innerText();
  if (!/Seu momento/i.test(story) || !/Seu objetivo/i.test(story) || !/Seu caminho/i.test(story)) {
    failures.push("journey chapters missing");
  }

  await bank.getByTestId("open-provenance").click();
  await bank.getByTestId("provenance-panel").waitFor();
  if (!(await bank.getByTestId("fingerprint").textContent())) failures.push("drawer missing fingerprint");
  await bank.keyboard.press("Escape");

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  if (!(await page.getByTestId("experience-hub").count())) failures.push("hub missing on legacy route");
  if (!(await page.getByTestId("hub-hero").innerText()).includes("Plataforma Contextual")) {
    failures.push("hub missing positioning");
  }

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(bankUrl, { waitUntil: "networkidle" });
  await mobile.getByTestId("spiderbank-hero").waitFor();
  const stacked = await mobile.getByTestId("fold-moment").boundingBox();
  if (stacked && stacked.x > 80) failures.push("mobile first fold did not stack");
  await mobile.close();

  await browser.close();
  if (failures.length) {
    console.error(failures.join("\n"));
    process.exit(1);
  }
  console.log("DEMO-001B manual browser checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

/**
 * Validação manual automatizada SPIDER-DEMO-001C.
 */
import { chromium } from "playwright";

const UI = process.env.SPIDER_UI_URL || "http://127.0.0.1:5180";
const API = process.env.SPIDER_API_URL || "http://127.0.0.1:8080";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const failures = [];
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(`${UI}/`, { waitUntil: "networkidle" });
  const root = await page.innerText("body");
  if (!/Plataforma Contextual/i.test(root) || !/caminhos executáveis/i.test(root)) {
    failures.push("root is not Experience Hub");
  }
  if (await page.getByRole("heading", { name: "Home operacional" }).count()) {
    failures.push("root shows Home operacional as heading");
  }
  if (await page.getByTestId("spiderbank-entry").count()) failures.push("root opened SpiderBank");

  await page.reload({ waitUntil: "networkidle" });
  if (!(await page.getByTestId("experience-hub").count())) failures.push("refresh / lost Experience Hub");

  await page.goto(`${UI}/spiderbank`, { waitUntil: "networkidle" });
  if (!(await page.getByTestId("direct-entry").count())) failures.push("/spiderbank invented or missed direct entry");
  if ((await page.innerText("body")).includes("CampoAberto")) failures.push("direct entry invented CampoAberto");

  await page.goto(`${UI}/console`, { waitUntil: "networkidle" });
  if (!(await page.getByTestId("spider-console").count())) failures.push("/console missing console");
  if (!(await page.getByRole("heading", { name: "Home operacional" }).count())) {
    failures.push("/console missing Home operacional");
  }
  await page.reload({ waitUntil: "networkidle" });
  if (!(await page.getByRole("heading", { name: "Home operacional" }).count())) {
    failures.push("refresh /console lost console");
  }

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  const partnerHref = await page.getByTestId("open-partner").getAttribute("href");
  const bankHref = await page.getByTestId("open-spiderbank").getAttribute("href");
  const consoleHref = await page.getByTestId("open-console").getAttribute("href");
  if (!partnerHref?.includes("/demo/partner/agro-hoje")) failures.push("presentation partner href");
  if (!bankHref?.includes("/spiderbank")) failures.push("presentation bank href");
  if (!consoleHref?.includes("/console")) failures.push("presentation console href");
  await page.reload({ waitUntil: "networkidle" });
  if (!(await page.getByTestId("experience-hub").count())) {
    failures.push("refresh presentation lost");
  }

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  await bank.getByTestId("fold-moment").waitFor();
  await bank.getByTestId("spiderbank-hero").waitFor();
  const dest = bank.url();
  if (!dest.includes("ctx=ctx-")) failures.push("ctx not preserved");
  if (dest.includes("/console")) failures.push("redirect to console");
  const bankText = await bank.innerText("body");
  if (!/SPIDERBANK/i.test(bankText) || !/banco contextual/i.test(bankText) || !/entende primeiro/i.test(bankText)) {
    failures.push("redirect target is not SpiderBank");
  }
  if (await bank.getByRole("heading", { name: "Home operacional" }).count()) {
    failures.push("redirect target has Home operacional h1");
  }

  await browser.close();
  if (failures.length) {
    console.error(failures.join("\n"));
    process.exit(1);
  }
  console.log("DEMO-001C manual browser checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

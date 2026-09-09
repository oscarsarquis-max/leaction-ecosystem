/**
 * Validação automatizada SPIDER-DEMO-002 — reportagem, link genérico, CROP_FAILURE com provenance.
 */
import { chromium } from "playwright";

const UI = process.env.SPIDER_UI_URL || "http://127.0.0.1:5180";
const API = process.env.SPIDER_API_URL || "http://127.0.0.1:8080";
const SCENARIO_A =
  "Perdi parte da safra, tenho compromissos vencendo e preciso de recursos para preparar o próximo plantio.";
const DIRECT = "Preciso de recursos para manter minha produção.";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const failures = [];
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  const script = await page.innerText('[data-testid="experience-hub"]');
  if (!/Banco Contextual|Experimentar essa jornada|Experimentar/.test(script)) {
    failures.push("presentation missing CampoAberto experience");
  }

  const html = await (await fetch(`${API}/demo/partner/agro-hoje`)).text();
  if (!html.includes("CampoAberto")) failures.push("CampoAberto missing");
  if (!/Quebra de safra aperta o caixa/i.test(html)) failures.push("reportagem missing");
  if (!html.includes('href="http://127.0.0.1:8080/go"')) failures.push("generic /go missing");
  if (/intent=|campaign=|cropFailure=|contextId=/.test(html)) failures.push("link carries context");

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  if (/intent=|cropFailure=/.test(bank.url())) failures.push("redirect copied contextual query");
  await bank.getByTestId("objective-input").fill(SCENARIO_A);
  await bank.getByTestId("understand-objective").click();
  await bank.getByTestId("understanding-block").waitFor();
  if (!(await bank.getByTestId("crop-failure-human").count())) {
    failures.push("scenario A missing crop-failure human note");
  }
  await bank.getByTestId("open-understanding").click();
  const crop = await bank.getByTestId("economic-context").innerText();
  const source = await bank.getByTestId("crop-failure-source").innerText();
  const fromLink = await bank.getByTestId("crop-from-link").innerText();
  if (crop !== "CROP_FAILURE") failures.push(`expected CROP_FAILURE, got ${crop}`);
  if (!source.includes("PAGE_CONTEXT")) failures.push(`missing PAGE_CONTEXT provenance: ${source}`);
  if (fromLink !== "NÃO") failures.push("CROP_FAILURE marked as coming from the link");
  await bank.locator('[data-testid="understanding-panel"] .sb-ghost').click();
  await bank.getByTestId("understanding-panel").waitFor({ state: "detached" });
  await bank.getByTestId("amount-input").fill("80000");
  await bank.getByTestId("continue-with-amount").click();
  await bank.getByTestId("human-path").waitFor();

  await page.goto(`${UI}/spiderbank`, { waitUntil: "networkidle" });
  await page.getByTestId("objective-input").fill(DIRECT);
  await page.getByTestId("understand-objective").click();
  await page.getByTestId("understanding-block").waitFor();
  if (await page.getByTestId("crop-failure-human").count()) {
    failures.push("direct entry invented crop-failure copy");
  }
  await page.getByTestId("open-understanding").click();
  const directCrop = await page.getByTestId("economic-context").innerText();
  const provenance = await page.getByTestId("context-provenance").innerText();
  if (directCrop !== "AUSENTE") failures.push(`direct entry invented CROP_FAILURE: ${directCrop}`);
  if (provenance !== "DIRECT_ENTRY") failures.push(`expected DIRECT_ENTRY, got ${provenance}`);

  await browser.close();
  if (failures.length) {
    console.error(failures.join("\n"));
    process.exit(1);
  }
  console.log("DEMO-002 manual browser checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

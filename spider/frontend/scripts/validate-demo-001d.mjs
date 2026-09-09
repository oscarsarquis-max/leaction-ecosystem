/**
 * Validação SPIDER-DEMO-001D — reportagem completa, CTA genérico /go, contexto após o clique.
 */
import { chromium } from "playwright";

const UI = process.env.SPIDER_UI_URL || "http://127.0.0.1:5180";
const API = process.env.SPIDER_API_URL || "http://127.0.0.1:8080";
const ARTICLE = `${API}/demo/partner/agro-hoje`;
const GATEWAY = `${API}/go`;

async function main() {
  const failures = [];
  const html = await (await fetch(ARTICLE)).text();
  if (!html.includes("CampoAberto")) failures.push("masthead CampoAberto missing");
  if (!/Quebra de safra aperta o caixa/i.test(html)) failures.push("manchete missing");
  if (!/Receita cai, mas o próximo ciclo não espera/i.test(html)) failures.push("intertítulo missing");
  if (!/semente|fertilizante|defensivo/i.test(html)) failures.push("corpo econômico missing");
  if (!/SPIDERBANK/i.test(html) || !/publicidade/i.test(html)) failures.push("anúncio SpiderBank missing");
  if (!/Conheça suas opções/i.test(html)) failures.push("CTA missing");
  if (!html.includes(`href="${GATEWAY}"`)) failures.push("href is not exactly /go");
  if (html.includes(`href="${GATEWAY}?`)) failures.push("CTA has query string");
  if (/intent=|context=|campaign=|article=|purpose=|product=|cropFailure=/i.test(html)) {
    failures.push("page carries contextual query");
  }
  if (/MOCK_ONLY|SIMULATED_INFRASTRUCTURE/.test(html)) failures.push("technical flags on editorial page");

  const before = await fetch(`${API}/v1/demo/spiderbank/entry?ctx=ctx-before-click`);
  if (before.ok) failures.push("context existed before click");

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  const openHref = await page.getByTestId("hub-cta-try").getAttribute("href");
  if (openHref !== ARTICLE) failures.push("hub CTA href is not principal article URL");
  const hub = await page.getByTestId("experience-hub").innerText();
  if (/Passo 1|Roteiro da experiência/i.test(hub)) failures.push("hub still shows a presentation script");

  await page.goto(ARTICLE, { waitUntil: "networkidle" });
  await page.getByTestId("partner-article").waitFor();
  await page.getByTestId("partner-ad").waitFor();
  const href = await page.getByTestId("spiderbank-cta").getAttribute("href");
  if (href !== GATEWAY) failures.push(`CTA href=${href}`);
  const target = await page.getByTestId("spiderbank-cta").getAttribute("target");
  if (target !== "_blank") failures.push("CTA missing target=_blank");

  await page.getByTestId("demo-link-proof").locator("summary").click();
  const proof = await page.getByTestId("demo-link-proof").innerText();
  if (!proof.includes(GATEWAY)) failures.push("proof missing generic link");
  if (!/NENHUM/.test(proof) || !/INEXISTENTE ANTES DO CLIQUE/.test(proof)) {
    failures.push("proof missing empty context labels");
  }

  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  const dest = bank.url();
  if (!dest.includes("ctx=ctx-")) failures.push("redirect missing ctx");
  if (/intent=|campaign=|cropFailure=/.test(dest)) failures.push("redirect copied context query");
  if (dest.includes("/console")) failures.push("redirect to console");

  await bank.getByTestId("origin-name").waitFor();
  const origin = await bank.getByTestId("origin-name").innerText();
  const title = await bank.getByTestId("origin-title").innerText();
  if (!/CampoAberto/i.test(origin)) failures.push("SpiderBank origin is not CampoAberto");
  if (!/Quebra de safra aperta o caixa/i.test(title)) failures.push("acquired title differs from reportagem");

  await bank.getByTestId("open-provenance").click();
  await bank.getByTestId("provenance-panel").waitFor();
  const fingerprint = await bank.getByTestId("fingerprint").innerText();
  if (!fingerprint.startsWith("sha256:")) failures.push("fingerprint missing");
  const proofTitle = await bank.getByTestId("source-title").innerText();
  if (!/Quebra de safra aperta o caixa/i.test(proofTitle)) failures.push("proof title differs from reportagem");

  await browser.close();
  if (failures.length) {
    console.error(failures.join("\n"));
    process.exit(1);
  }
  console.log("DEMO-001D browser checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

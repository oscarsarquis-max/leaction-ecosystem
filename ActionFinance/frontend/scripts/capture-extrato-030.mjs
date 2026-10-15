import { mkdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "extrato-030");
await mkdir(shots, { recursive: true });
const base = process.env.ACTIONFINANCE_CAPTURE_URL ?? "http://127.0.0.1:5179";
const csv = `DATE,SOURCE_ID,RECORD_TYPE,EXTERNAL_REFERENCE,DESCRIPTION,NET_CREDIT_AMOUNT,NET_DEBIT_AMOUNT,GROSS_AMOUNT,MP_FEE_AMOUNT,CURRENCY,ACCOUNT_EXTERNAL_REF
2026-10-01,pay-sint-jornada,SETTLEMENT,order-sint-jornada,Venda da jornada isolada,85.00,,90.00,5.00,BRL,mp-conta-sintetica
2026-10-01,pay-sint-jornada,RELEASE,order-sint-jornada,Liberacao da jornada,90.00,,,,BRL,mp-conta-sintetica
`;
const noCurrency = `DATE,SOURCE_ID,RECORD_TYPE,NET_CREDIT_AMOUNT,ACCOUNT_EXTERNAL_REF
2026-10-02,pay-sint-sem-moeda,SETTLEMENT,10.00,mp-conta-sintetica
`;

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });

async function shot(name) {
  const box = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  if (box.scrollWidth > box.clientWidth + 1) {
    throw new Error(`overflow ${name}`);
  }
  const target = join(shots, `${name}.png`);
  await page.screenshot({ path: target, fullPage: false });
  const info = await stat(target);
  console.log(JSON.stringify({ name, bytes: info.size, ...box }));
}

async function signIn() {
  await page.goto(base + "/financial-accounts/statement", { waitUntil: "networkidle" });
  await page.getByLabel("Token local").fill("operator-demo-token-aaaaaaaaaaaaaaaaaaaa");
  await page.getByRole("button", { name: "Entrar na demonstração" }).click();
  await page.getByRole("heading", { name: "Extrato" }).waitFor();
}

const onlyCurrency = process.argv[2] === "moeda";
await signIn();
await page.getByLabel("Conta", { exact: true }).selectOption({ label: "Conta demonstrativa Banco Exemplo" });
if (onlyCurrency) {
  await page.getByText("Referência vinculada: mp-conta-sintetica").waitFor();
  await page.locator("input[type=file]").setInputFiles({ name: "sem-moeda.csv", mimeType: "text/csv", buffer: Buffer.from(noCurrency) });
  await page.getByText("Nenhuma moeda foi presumida").waitFor();
  await page.getByText("10,00 · moeda não informada").first().waitFor();
  if (await page.getByRole("button", { name: "Confirmar linhas selecionadas" }).isEnabled()) {
    throw new Error("confirmação habilitada sem moeda");
  }
  if (await page.getByText("R$ 10,00").count()) {
    throw new Error("valor sem moeda apareceu como real");
  }
  await page.locator(".statement-preview").scrollIntoViewIfNeeded();
  await shot("jornada-sem-moeda");
  await browser.close();
  console.log("currency-shot-ok");
  process.exit(0);
}
await page.getByLabel("Referência externa").fill("mp-conta-sintetica");
await page.getByLabel("Procedência").fill("vinculo sintetico de laboratorio");
await page.getByRole("button", { name: "Gravar vínculo" }).click();
await page.getByText("Referência vinculada: mp-conta-sintetica").waitFor();

await page.locator("input[type=file]").setInputFiles({ name: "jornada.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
await page.getByText("O efeito deste tipo ainda não foi lido").waitFor();
await page.getByRole("checkbox", { name: "Linha 3" }).waitFor();
const releaseDisabled = await page.getByRole("checkbox", { name: "Linha 3" }).isDisabled();
if (!releaseDisabled) {
  throw new Error("liberação ficou elegível");
}
await page.locator(".statement-preview").scrollIntoViewIfNeeded();
await shot("jornada-previa");
await page.getByRole("button", { name: "Confirmar linhas selecionadas" }).click();
await page.getByText("Criadas: 1.").waitFor();
await page.getByText("Não é variação do saldo total").waitFor();
await shot("jornada-lista");
await page.getByRole("button", { name: "Abrir" }).first().click();
await page.getByText("R$ 90,00").waitFor();
await page.getByText("R$ 5,00").waitFor();
await page.getByText("R$ 85,00").waitFor();
await page.getByText("Não classificada").waitFor();
await shot("jornada-detalhe");

await page.reload({ waitUntil: "networkidle" });
await signIn();
await page.getByLabel("Conta", { exact: true }).selectOption({ label: "Conta demonstrativa Banco Exemplo" });
await page.getByText("R$ 85,00").first().waitFor();
await page.getByText("Não é variação do saldo total").waitFor();
await shot("jornada-recarga");

await page.locator("input[type=file]").setInputFiles({ name: "jornada.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
await page.getByRole("button", { name: "Confirmar linhas selecionadas" }).click();
await page.getByText("Criadas: 0.").waitFor();
await page.getByText("Inalteradas: 1.").waitFor();

await page.locator("input[type=file]").setInputFiles({ name: "sem-moeda.csv", mimeType: "text/csv", buffer: Buffer.from(noCurrency) });
await page.getByText("Nenhuma moeda foi presumida").waitFor();
if (await page.getByRole("button", { name: "Confirmar linhas selecionadas" }).isEnabled()) {
  throw new Error("confirmação habilitada sem moeda");
}
await page.locator(".statement-preview").scrollIntoViewIfNeeded();
await shot("jornada-sem-moeda");

await browser.close();
console.log("journey-ok");

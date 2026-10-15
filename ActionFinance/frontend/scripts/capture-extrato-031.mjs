import { readFile, mkdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "extrato-031");
await mkdir(shots, { recursive: true });
const base = process.env.ACTIONFINANCE_CAPTURE_URL ?? "http://127.0.0.1:5179";
const fixture = join(here, "..", "..", "backend", "src", "test", "resources", "statement");
const mainFile = await readFile(join(fixture, "settlement-v2-sanitizado.csv"));
const overlapFile = await readFile(join(fixture, "settlement-v2-sanitizado-sobreposicao.csv"));

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
  await page.getByRole("heading", { name: "Extrato", level: 1 }).waitFor();
  await page.getByRole("combobox", { name: "Conta" }).waitFor();
}

await signIn();
const linksReady = page.waitForResponse((response) => response.url().includes("/statement-links") && response.url().includes("11111111-dddd-4111-a111-111111111401") && response.ok());
await page.getByRole("combobox", { name: "Conta" }).selectOption({ label: "Conta demonstrativa Banco Exemplo" });
await linksReady;
const linked = page.getByText("Referência vinculada: usr-sanitizado-031");
try {
  await linked.waitFor({ timeout: 5000 });
} catch {
  await page.getByLabel("Referência externa").fill("usr-sanitizado-031");
  await page.getByLabel("Procedência").fill("vinculo sintetico de laboratorio");
  await page.getByRole("button", { name: "Gravar vínculo" }).click();
  await linked.waitFor();
}

page.on("response", (response) => {
  if (response.url().includes("statement-previews") && response.request().method() === "POST") {
    console.log("preview-status", response.status());
  }
});
await page.locator("input[type=file]").setInputFiles({ name: "liquidacao-sanitizada.csv", mimeType: "text/csv", buffer: mainFile });
try {
  await page.getByText("sem coluna que separe as ocorrências").first().waitFor({ timeout: 15000 });
} catch (error) {
  console.log(await page.locator("body").innerText());
  throw error;
}
await page.getByText("mp-settlement-v2-csv-1").first().waitFor();
const blocked = page.getByRole("checkbox", { name: "Linha 4" });
await blocked.waitFor();
if (!(await blocked.isDisabled())) {
  throw new Error("par repetido ficou elegível");
}
await page.locator(".statement-preview").scrollIntoViewIfNeeded();
await shot("previa");
await page.getByRole("button", { name: "Confirmar linhas selecionadas" }).click();
await page.getByText("Criadas: 2.").waitFor();
await page.getByText("Não importadas: 2.").waitFor();
await page.getByText("Entradas de fluxo: R$ 176,00").waitFor();
await shot("lista");
await page.getByRole("row", { name: /R\$ 76,00/ }).getByRole("button", { name: "Abrir" }).click();
await page.getByText("R$ 80,00").waitFor();
await page.getByText("R$ 4,00").waitFor();
await page.getByText("Não classificada").waitFor();
await page.getByText("Não atribuída").waitFor();
if (await page.getByText("A diferença não foi ajustada.").count()) {
  throw new Error("tarifa compatível foi tratada como divergência");
}
await shot("detalhe");

await page.reload({ waitUntil: "networkidle" });
await signIn();
await page.getByRole("combobox", { name: "Conta" }).selectOption({ label: "Conta demonstrativa Banco Exemplo" });
await page.getByText("Entradas de fluxo: R$ 176,00").waitFor();

await page.locator("input[type=file]").setInputFiles({ name: "liquidacao-sanitizada.csv", mimeType: "text/csv", buffer: mainFile });
await page.getByRole("button", { name: "Confirmar linhas selecionadas" }).click();
await page.getByText("Criadas: 0.").waitFor();
await page.getByText("Inalteradas: 2.").waitFor();
await shot("reenvio");

await page.locator("input[type=file]").setInputFiles({ name: "liquidacao-sobreposicao.csv", mimeType: "text/csv", buffer: overlapFile });
await page.getByRole("button", { name: "Confirmar linhas selecionadas" }).click();
await page.getByText("Criadas: 1.").waitFor();
await page.getByText("Inalteradas: 1.").waitFor();
await page.getByText("Entradas de fluxo: R$ 186,00").waitFor();
await shot("sobreposicao");

await browser.close();
console.log("journey-ok");

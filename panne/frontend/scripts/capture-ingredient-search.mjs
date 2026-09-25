import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, "../../documentacao/evidencias/fiscal-draft-items");
mkdirSync(outDir, { recursive: true });

const FE = process.env.PANNE_FE_URL || "http://127.0.0.1:5198";
const trial = JSON.parse(readFileSync(resolve(outDir, "trial.json"), "utf8"));
const notes = [];

function log(message) {
  notes.push(message);
  console.log(message);
}

async function login(page) {
  await page.addInitScript(
    ({ orgId }) => {
      try {
        sessionStorage.setItem("panne.demoSubject", "local-dev-owner");
        localStorage.setItem("panne.activeOrganization", orgId);
      } catch {
        /* ignore */
      }
    },
    { orgId: trial.organization_id },
  );
  await page.goto(`${FE}/entrar`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Entrar em desenvolvimento" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 20000 });
  const picker = page.getByRole("heading", { name: "Escolha a organização" });
  if (await picker.isVisible().catch(() => false)) {
    await page.getByRole("button", { name: /Ensaio itens/ }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 15000 });
  }
}

async function ensureTwoFarinhas(page) {
  const listed = await page.evaluate(
    async ({ orgId }) => {
      const token = sessionStorage.getItem("panne.demoSubject")
        ? `panne-demo:${sessionStorage.getItem("panne.demoSubject")}`
        : "panne-fake-access-token";
      const headers = { Authorization: `Bearer ${token}` };
      const search = await fetch(`/api/v1/organizations/${orgId}/ingredients?q=far&limit=12&offset=0`, {
        headers,
      });
      const body = await search.json();
      return { status: search.status, items: body.items || [], token };
    },
    { orgId: trial.organization_id },
  );
  log(`busca_far ${listed.status} ${listed.items.length} ${listed.items.map((row) => row.display_name).join(" | ")}`);
  if (listed.items.length >= 2) return listed.items;
  const created = await page.evaluate(
    async ({ orgId, token }) => {
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
        "X-Correlation-Id": crypto.randomUUID(),
      };
      const units = await fetch(`/api/v1/organizations/${orgId}/catalog/units`, { headers });
      const unitBody = await units.json();
      const unit = (unitBody.data || unitBody.items || []).find((row) => (row.code || "").toLowerCase() === "g")
        || (unitBody.data || unitBody.items || [])[0];
      if (!unit) return { status: units.status, error: "sem unidade" };
      const response = await fetch(`/api/v1/organizations/${orgId}/ingredients`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          code: `FAR-MIL-${crypto.randomUUID().slice(0, 6)}`,
          display_name: "Farinha de milho ensaio",
          ingredient_type: "simple",
          nutrition_basis_unit_id: unit.id,
        }),
      });
      return { status: response.status, body: await response.json() };
    },
    { orgId: trial.organization_id, token: listed.token },
  );
  log(`segundo_ingrediente ${created.status}`);
  if (created.status >= 400) throw new Error(`não criou segundo ingrediente: ${JSON.stringify(created).slice(0, 240)}`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (error) => log(`pageerror ${error.message}`));
  await login(page);
  if (page.url().includes("/entrar")) throw new Error("não autenticou");
  await ensureTwoFarinhas(page);

  const documentId = trial.documents["1440"].id;
  if (documentId.includes("a3853554")) throw new Error("recusou nota 50661");
  await page.goto(`${FE}/gestao/compras/entradas/${documentId}`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Itens da nota" }).waitFor({ timeout: 20000 });

  if (await page.getByRole("button", { name: "Adicionar item" }).isVisible().catch(() => false)) {
    await page.getByRole("button", { name: "Adicionar item" }).click();
  } else if (await page.getByRole("button", { name: "Adicionar outro item" }).isVisible().catch(() => false)) {
    await page.getByRole("button", { name: "Adicionar outro item" }).click();
  }
  const item = page.locator(".draft-item").last();
  const description = item.getByLabel("Descrição na nota");
  await description.fill("Saco da nota de ensaio");
  await item.getByLabel("Buscar ingrediente existente").fill("far");
  await page.getByRole("option", { name: /Farinha/ }).first().waitFor({ timeout: 15000 });
  const options = await page.getByRole("option").allTextContents();
  if (options.length < 2) throw new Error(`esperava vários resultados: ${JSON.stringify(options)}`);
  const listBox = page.getByRole("listbox");
  const create = page.getByRole("button", { name: "Cadastrar novo ingrediente" }).last();
  const search = item.getByLabel("Buscar ingrediente existente");
  const order = await page.evaluate(
    ([searchEl, listEl, createEl]) => {
      const following = Node.DOCUMENT_POSITION_FOLLOWING;
      return {
        listAfterSearch: Boolean(searchEl.compareDocumentPosition(listEl) & following),
        createAfterList: Boolean(listEl.compareDocumentPosition(createEl) & following),
      };
    },
    [await search.elementHandle(), await listBox.elementHandle(), await create.elementHandle()],
  );
  if (!order.listAfterSearch || !order.createAfterList) throw new Error(`ordem da seção: ${JSON.stringify(order)}`);
  await page.screenshot({
    path: resolve(outDir, "07-busca-lista-1440.png"),
    fullPage: true,
  });
  log("captura 07-busca-lista-1440.png");

  await search.fill("zzz-inexistente");
  await page.getByText("Nenhum ingrediente com este nome ou código.").waitFor();
  if (await page.getByRole("listbox").count()) throw new Error("lista vazia no nenhum resultado");
  log("nenhum_resultado ok");

  await search.fill("far");
  await page.getByRole("option", { name: /Farinha de trigo ensaio/ }).waitFor();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await item.getByRole("button", { name: "Trocar" }).waitFor();
  const kept = await description.inputValue();
  if (kept !== "Saco da nota de ensaio") throw new Error(`descrição alterada: ${kept}`);
  await item.getByRole("button", { name: "Trocar" }).click();
  await search.waitFor();
  log("teclado_troca ok");
  await browser.close();
  writeFileSync(resolve(outDir, "busca-log.txt"), `${notes.join("\n")}\n`, "utf8");
}

await main();

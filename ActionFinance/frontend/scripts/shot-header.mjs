import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const dir = "C:/Projetos/ActionFinance/documents/reviews/screenshots/nova-interface";
await mkdir(dir, { recursive: true });
const me = {
  actorId: "a",
  displayName: "Operador A",
  accessState: "READY",
  permissions: ["titles:write", "financial-accounts:read"],
  authorizedCompanies: [{ id: "11111111-1111-1111-1111-111111111111", tenantId: "t", name: "Loja demonstração", active: true, demo: true }],
  authorizedCompanyDetails: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      tenantId: "t",
      name: "Loja demonstração",
      active: true,
      demo: true,
      permissions: ["titles:write", "financial-accounts:read"],
    },
  ],
};
const empty = {
  items: [],
  totalItems: 0,
  page: 0,
  size: 20,
  summary: { openCount: 0, openAmountMinor: "0", overdueCount: 0, overdueAmountMinor: "0", draftCount: 0 },
  businessDate: "2026-10-02",
};
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.route("**/api/v1/**", async (route) => {
  const u = route.request().url();
  if (u.includes("/system/info")) {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ accessMode: "DEMO", homologIntegration: true }) });
    return;
  }
  if (u.includes("/access/me")) {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(me) });
    return;
  }
  if (u.includes("/access/csrf")) {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ token: "t", headerName: "X-XSRF-TOKEN" }) });
    return;
  }
  if (u.includes("/receivables") || u.includes("/payables")) {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(empty) });
    return;
  }
  if (u.includes("/catalogs/")) {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    return;
  }
  await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
});
await page.goto("http://127.0.0.1:5179/receivables", { waitUntil: "networkidle" });
if (await page.getByLabel("Token local").count()) {
  await page.getByLabel("Token local").fill("t");
  await page.getByRole("button", { name: "Entrar na demonstração" }).click();
}
await page.getByRole("heading", { name: "Contas a receber" }).waitFor();
await page.screenshot({ path: `${dir}/1280-cabecalho-marca-azul.png`, clip: { x: 0, y: 0, width: 1280, height: 140 } });
await page.screenshot({ path: `${dir}/1280-receber-viewport.png` });
await browser.close();
console.log("ok");

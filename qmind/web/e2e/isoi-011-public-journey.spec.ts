import { test, expect, type Page, type Request } from "@playwright/test";

/**
 * ISOI-011 — hotpage pública V2.
 * Sem autenticação; falha se houver chamada tenant/OI.
 */

const FORBIDDEN_URL =
  /\/api\/v1\/(organizations|improvement-cases|assessments|cockpit|execution)|execution-intelligence|problem-analysis|memberships/i;

function attachPublicNetworkGuard(page: Page) {
  const violations: string[] = [];
  page.on("request", (req: Request) => {
    const url = req.url();
    if (FORBIDDEN_URL.test(url)) {
      violations.push(`${req.method()} ${url}`);
    }
  });
  return violations;
}

test.describe("ISOI-011 hotpage pública", () => {
  test("jornada V2, exemplo ilustrativo e login com return URL segura", async ({
    page,
  }) => {
    const violations = attachPublicNetworkGuard(page);
    await page.goto("/");

    await expect(page.getByTestId("qmind-hotpage")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Da compreensão à decisão/i }),
    ).toBeVisible();

    await page.getByTestId("journey-tab-execute").click();
    await expect(
      page.getByRole("heading", { name: /Executar com squads/i }),
    ).toBeVisible();

    await page.getByTestId("illustrative-example").getByRole("tab", { name: /Cockpit pede revisão/i }).click();
    await expect(page.getByText(/Exemplo ilustrativo/i).first()).toBeVisible();
    await expect(page.getByText(/fila do Cockpit/i)).toBeVisible();

    await page.getByTestId("hotpage-start-tour").click();
    await expect(page.getByTestId("login-page")).toBeVisible();
    await expect(page).toHaveURL(/return=/);
    const url = page.url();
    expect(url).toContain(encodeURIComponent("/guided-tour"));
    expect(url).not.toMatch(/https?:\/\/(?!127\.0\.0\.1|localhost)/i);

    expect(violations, violations.join("\n")).toEqual([]);
  });
});

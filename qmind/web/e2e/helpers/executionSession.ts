import { expect, type Page } from "@playwright/test";

const DEV_SUB = "dev-local-user";
const DEV_EMAIL = "dev@example.com";

/**
 * The shell never authenticates by itself: in dev mode the person has to say
 * who they are before any organization data is fetched. The identity and the
 * organization come from the running build, so the seed uses exactly the same
 * person the browser is — the spec stays valid whatever the local env says.
 */
export async function visit(page: Page, path: string) {
  await page.goto(path);
  const cta = page.getByTestId("login-cta");
  if (await cta.isVisible().catch(() => false)) await cta.click();
  await expect(page.getByLabel(/selecionar organização/i)).toBeVisible();
}

export async function signIn(page: Page, path: string) {
  const seen = page.waitForRequest(
    (req) => req.url().includes("/api/v1/") && !!req.headers()["x-organization-id"],
  );
  await visit(page, path);

  const headers = (await seen).headers();
  return {
    orgId: headers["x-organization-id"],
    sub: headers["x-dev-user-sub"] ?? DEV_SUB,
    email: headers["x-dev-user-email"] ?? DEV_EMAIL,
  };
}

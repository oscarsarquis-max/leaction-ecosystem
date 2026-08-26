import { test, expect, type Page, type Request } from "@playwright/test";
import { createApi, createSecondOrg } from "./helpers/api";
import { signIn } from "./helpers/executionSession";

/**
 * ISOI-011 — apresentação guiada autenticada V2 (gate conteúdo demonstrável).
 * Após login/setup, apenas GET; falha em POST/PATCH/PUT/DELETE do tour.
 */

const MUTATING = new Set(["POST", "PATCH", "PUT", "DELETE"]);

const FINAL_STATUS =
  "[data-testid=guided-tour-status-ready], [data-testid=guided-tour-status-unavailable], [data-testid=guided-tour-status-forbidden], [data-testid=guided-tour-status-error]";

function attachTourMutationGuard(page: Page) {
  const violations: string[] = [];
  let armed = false;
  page.on("request", (req: Request) => {
    if (!armed) return;
    if (!MUTATING.has(req.method())) return;
    const url = req.url();
    if (!url.includes("/api/v1/")) return;
    violations.push(`${req.method()} ${url}`);
  });
  return {
    arm() {
      armed = true;
    },
    disarm() {
      armed = false;
    },
    violations,
  };
}

async function waitFinalTourStatus(page: Page) {
  await expect(page.locator(FINAL_STATUS)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("guided-tour-status-loading")).toHaveCount(0);
}

test.describe("ISOI-011 guided tour autenticado", () => {
  test("conteúdo demonstrável, caso/Evolution, troca de org e zero mutação", async ({
    page,
  }) => {
    const guard = attachTourMutationGuard(page);

    const identity = await signIn(page, "/guided-tour");
    guard.arm();

    await expect(page.getByTestId("guided-tour-page")).toBeVisible();
    await expect(page.getByTestId("guided-tour-chapters")).toBeVisible();

    // Cockpit — síntese org; ready sem depender de caso.
    await page.getByRole("button", { name: /Controlar/i }).click();
    await waitFinalTourStatus(page);
    await expect(page.getByTestId("guided-tour-status-ready")).toBeVisible();
    await page.getByTestId("guided-tour-open-product").click();
    await expect(page).toHaveURL(/\/cockpit/);
    await expect(page.getByTestId("guided-tour-return-banner")).toBeVisible();
    await page.getByRole("link", { name: /Voltar à apresentação guiada/i }).click();
    await expect(page.getByTestId("guided-tour-page")).toBeVisible();

    // Interpretar: EI real (ready) ou indisponibilidade honesta — nunca loading eterno.
    await page.getByRole("button", { name: /Interpretar/i }).click();
    await waitFinalTourStatus(page);
    const interpretReady = await page
      .getByTestId("guided-tour-status-ready")
      .isVisible()
      .catch(() => false);
    if (interpretReady) {
      await page.getByTestId("guided-tour-open-product").click();
      await expect(page).toHaveURL(/\/improvement-cases\//);
      await expect(page.getByTestId("ic-section-evolution")).toBeVisible({
        timeout: 30_000,
      });
      // Conteúdo de EI persistido (não o estado "nunca interpretado").
      await expect(page.getByTestId("ic-ei-never")).toHaveCount(0);
      await expect(page.getByTestId("ic-evo-execution-intelligence")).toBeVisible();
      await expect(page.getByTestId("ic-ei-result")).toBeVisible();
      await page.getByRole("link", { name: /Voltar à apresentação guiada/i }).click();
      await expect(page.getByTestId("guided-tour-page")).toBeVisible();
    } else {
      await expect(page.getByTestId("guided-tour-status-unavailable")).toBeVisible();
      await expect(page.getByTestId("guided-tour-status-reason")).toContainText(
        /ainda não foi interpretada|Execution Intelligence/i,
      );
      await expect(page.getByTestId("guided-tour-open-product")).toBeDisabled();
    }

    // Reconhecer / abrir caso quando houver caso demonstrável.
    await page.getByRole("button", { name: /Reconhecer/i }).click();
    await waitFinalTourStatus(page);
    if (await page.getByTestId("guided-tour-status-ready").isVisible().catch(() => false)) {
      await page.getByTestId("guided-tour-open-product").click();
      await expect(page).toHaveURL(/\/improvement-cases\//);
      await page.getByRole("link", { name: /Voltar à apresentação guiada/i }).click();
      await expect(page.getByTestId("guided-tour-page")).toBeVisible();
    }

    // Troca de organização limpa progresso/contexto do tour.
    // createSecondOrg é setup do teste (POST); reload perde auth em memória (dev).
    guard.disarm();
    const origin = new URL(page.url()).origin;
    const orgB = await createSecondOrg(origin, {
      sub: identity.sub,
      email: identity.email,
    });
    await page.reload();
    await signIn(page, "/guided-tour");
    guard.arm();
    const orgSelect = page.getByLabel(/selecionar organização/i);
    await expect(orgSelect.locator(`option[value="${orgB.orgId}"]`)).toHaveCount(1);
    await orgSelect.selectOption(orgB.orgId);
    await expect(page.getByTestId("guided-tour-page")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page).toHaveURL(/chapter=understand/);
    await waitFinalTourStatus(page);
    // Capítulos dependentes de caso na org B (vazia) ficam unavailable.
    await page.getByRole("button", { name: /Interpretar/i }).click();
    await waitFinalTourStatus(page);
    await expect(page.getByTestId("guided-tour-status-unavailable")).toBeVisible();

    // Volta à org original — progresso reinicia (understand).
    await orgSelect.selectOption(identity.orgId);
    await expect(page).toHaveURL(/chapter=understand/);

    expect(guard.violations, guard.violations.join("\n")).toEqual([]);
  });
});

import { test, expect } from "@playwright/test";
import { createApi } from "./helpers/api";
import { seedExecutableAction, seedSprintWithCard } from "./helpers/executionSeed";
import { signIn, visit } from "./helpers/executionSession";

/**
 * ISOI-008 path: what proves the action happened (evidence) and what proves
 * the problem shrank (measurement). The spec walks the whole chain in the
 * browser — attach, plan, baseline, measure — and then asks the API whether
 * the action itself moved. It must not have: measuring a result is not the
 * same act as declaring the work done.
 */
test("execution measurement: evidence, plan, baseline and reading", async ({
  page,
  baseURL,
}) => {
  test.setTimeout(300_000);
  const origin = baseURL!;

  const who = await signIn(page, "/execution");
  const api = await createApi(origin, who.orgId, { sub: who.sub, email: who.email });
  const description = `Reduzir o retrabalho na linha 2 ${Date.now()}`;
  const { actionItemId } = await seedExecutableAction(api, description);
  await seedSprintWithCard(api, actionItemId);

  const statusBefore = (
    await api.request("GET", `/api/v1/action-items/${actionItemId}`)
  ).json.status;

  await visit(page, `/execution/cards/${actionItemId}`);
  await expect(page.getByRole("heading", { name: description })).toBeVisible();

  /* --- Evidence: nothing attached yet, then one file through the UI --- */
  const evidence = page.getByTestId("execution-evidence-section");
  await expect(evidence.getByTestId("execution-evidence-list")).toContainText(
    /Nenhuma evidência anexada/i,
  );

  await evidence.locator('input[type="file"]').setInputFiles({
    name: "procedimento-revisado.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Procedimento revisado após a mudança na linha 2.\n"),
  });
  await expect(evidence.getByTestId("execution-evidence-list")).toContainText(
    /Recebida, aguardando verificação/i,
  );

  // The list speaks of the document, never of where the bytes live.
  await expect(evidence).not.toContainText(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}/i);

  // Lifecycle approval is simulated and may be switched off by settings; when
  // the environment allows it, the person sees the situation change.
  const attachments = (
    await api.request(
      "GET",
      `/api/v1/organizations/current/evidence-links?target_type=action_item&target_id=${actionItemId}`,
    )
  ).json as Array<{ link: { evidence_id: string }; evidence: { status: string } }>;
  expect(attachments.length).toBe(1);
  // The attachment already carries the document, so nothing has to be re-read.
  expect(attachments[0].evidence.status).toBeTruthy();
  const pass = await api.request(
    "POST",
    `/api/v1/evidences/${attachments[0].link.evidence_id}/transitions/security_pass`,
  );
  if (pass.status < 400) {
    await visit(page, `/execution/cards/${actionItemId}`);
    await expect(page.getByTestId("execution-evidence-list")).toContainText(
      /Aprovada/i,
    );
  }

  /* --- Measurement: plan, indicator, baseline, first reading --- */
  const measurement = page.getByTestId("execution-measurement-section");
  await expect(measurement).toContainText(
    "Meta atingida não equivale, por si só, à eficácia confirmada.",
  );

  const planForm = measurement.getByTestId("measurement-plan-form");
  await planForm
    .getByLabel(/O que esta ação precisa provar\?/i)
    .fill("Reduzir o retrabalho na linha 2");
  await planForm.getByRole("button", { name: /Criar plano de medição/i }).click();

  await measurement.getByTestId("measurement-add-indicator").click();
  const indicatorForm = measurement.getByTestId("measurement-indicator-form");
  await indicatorForm.getByLabel(/O que será medido\?/i).fill("Retrabalho na linha 2");
  await indicatorForm
    .getByLabel(/Que pergunta este número responde\?/i)
    .fill("Quantas peças voltam para retrabalho por semana?");
  // Role+name: nested <label><select> makes exact getByLabel miss (options inflate label text).
  await indicatorForm.getByRole("combobox", { name: "Unidade" }).selectOption("custom");
  await indicatorForm
    .getByLabel(/Como esta unidade se chama/i)
    .fill("peças/semana");
  await indicatorForm.getByLabel(/Sentido desejado/i).selectOption("lower_is_better");
  await indicatorForm.getByLabel("Meta", { exact: true }).fill("4");
  await indicatorForm.getByLabel(/A cada quantos dias medir/i).fill("7");
  await indicatorForm.getByRole("button", { name: /Salvar indicador/i }).click();

  const indicator = measurement.locator('li[data-testid^="measurement-indicator-"]');
  await expect(indicator).toContainText("Retrabalho na linha 2");
  await expect(indicator).toContainText("peças/semana");

  const baselineForm = measurement.locator(
    '[data-testid^="measurement-baseline-form-"]',
  );
  await baselineForm.getByLabel(/Valor de partida/i).fill("12.5");
  await baselineForm
    .getByLabel(/Observação ou motivo da indisponibilidade/i)
    .fill("Média das quatro semanas anteriores à mudança");
  await baselineForm
    .getByRole("button", { name: /Registrar ponto de partida/i })
    .click();
  await expect(indicator).toContainText("12.5");

  await measurement.getByTestId("measurement-activate-plan").click();
  const recordForm = measurement.locator('[data-testid^="measurement-record-form-"]');
  await expect(recordForm).toBeVisible();

  await recordForm.getByLabel(/Valor medido/i).fill("9.75");
  await recordForm
    .getByLabel(/Observação sobre a medição/i)
    .fill("Primeira semana após o novo procedimento");
  await recordForm.getByRole("button", { name: /Registrar medição/i }).click();

  // One reading is a point, not a trend: the table shows it, no line is drawn.
  const history = measurement.locator('[data-testid^="measurement-history-"]');
  await expect(history).toContainText("9.75");
  await expect(history).toContainText(/Uma única medição/i);
  await expect(history.locator("svg")).toHaveCount(0);

  // The posture is stated in words, never as a code.
  const postures = measurement.getByTestId("measurement-postures");
  await expect(postures).toBeVisible();
  await expect(postures).not.toContainText(/_/);

  await visit(page, "/execution");
  const badges = page.getByTestId(`execution-result-badges-${actionItemId}`);
  await expect(badges).toContainText(/1 evidência/i);
  await expect(badges).not.toContainText(/_/);

  /* --- Measuring the result never moves the action by itself --- */
  const statusAfter = (
    await api.request("GET", `/api/v1/action-items/${actionItemId}`)
  ).json.status;
  expect(statusAfter).toBe(statusBefore);
});

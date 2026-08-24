import { test, expect, type Page } from "@playwright/test";
import { createApi } from "./helpers/api";
import {
  seedExecutableAction,
  seedSprintWithCard,
} from "./helpers/executionSeed";
import { signIn, visit } from "./helpers/executionSession";

function recordAgendaRequests(page: Page) {
  const urls: string[] = [];
  page.on("request", (req) => {
    if (req.method() !== "GET") return;
    const url = req.url();
    if (url.includes("agenda-events") || url.includes("/agenda/events")) urls.push(url);
  });
  return urls;
}

test.describe.configure({ mode: "serial" });

test("execution workspace: board → card → check-in → ceremonies", async ({
  page,
  baseURL,
}) => {
  test.setTimeout(300_000);
  const origin = baseURL!;
  const agendaRequests = recordAgendaRequests(page);

  const who = await signIn(page, "/execution");
  const api = await createApi(origin, who.orgId, { sub: who.sub, email: who.email });
  const description = `Padronizar o registro de ocorrências ${Date.now()}`;
  const { actionItemId } = await seedExecutableAction(api, description);
  const sprint = await seedSprintWithCard(api, actionItemId);

  await visit(page, "/execution");

  // The board is readable by what the action says, not by any identifier.
  const card = page.getByTestId(`execution-card-${actionItemId}`);
  await expect(card).toBeVisible();
  await expect(card).toContainText(description);
  await expect(card).toContainText(sprint.sprintName);

  // Open the card the way a person does: by clicking its human text.
  await card.getByRole("link", { name: description }).click();
  await expect(page).toHaveURL(new RegExp(`/execution/cards/${actionItemId}$`));
  await expect(page.getByRole("heading", { name: description })).toBeVisible();
  await expect(page.getByTestId("execution-check-in-form")).toBeVisible();

  // A check-in is the smallest honest unit of progress.
  const checkInForm = page.getByTestId("execution-check-in-form");
  await checkInForm.getByLabel(/Saúde/i).selectOption("attention");
  await checkInForm
    .getByLabel(/O que avançou\?/i)
    .fill("Piloto rodando em duas unidades.");
  await checkInForm.getByLabel(/Próximo passo/i).fill("Medir o tempo de resposta.");
  await checkInForm.getByRole("button", { name: /Registrar check-in/i }).click();

  await expect(page.getByText("Piloto rodando em duas unidades.")).toBeVisible();
  await expect(page.getByText("Próximo: Medir o tempo de resposta.")).toBeVisible();

  // The board reflects the check-in without a reload trick.
  await visit(page, "/execution");
  await expect(page.getByTestId(`execution-card-${actionItemId}`)).toContainText(
    /Check-in/i,
  );

  // Ceremonies: the sprint agenda arrives in one request, not one per day.
  await visit(page, "/execution/ceremonies");
  await expect(page.getByLabel("Squad")).toBeVisible();
  await page.getByLabel("Squad").selectOption(sprint.squadId);
  await page.getByLabel("Sprint").selectOption(sprint.sprintId);

  const eventPicker = page.getByLabel(/Compromisso da sprint/i);
  await expect(eventPicker).toContainText(sprint.ceremonyTitle);

  const sprintAgendaReads = agendaRequests.filter((u) => u.includes("agenda-events"));
  expect(sprintAgendaReads.length).toBeGreaterThan(0);
  expect(sprintAgendaReads.every((u) => u.includes(sprint.sprintId))).toBeTruthy();
  expect(agendaRequests.filter((u) => /\/agenda\/events\?/.test(u))).toEqual([]);
});

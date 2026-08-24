import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CeremoniesPage } from "@/execution/CeremoniesPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";
import {
  bodyOf,
  executionQueryKeys,
  expectNoVisibleUuid,
  jsonResponse,
  membershipResponse,
  methodOf,
  optionLabels,
  ORG_ID,
  renderExecution,
  sprintPayload,
  SPRINT_ID,
  squadPayload,
  SQUAD_ID,
  stubMatchMedia,
  urlOf,
} from "@/test/executionHarness";

const EVENT_ID = "77777777-7777-4777-8777-777777777777";
const NEW_EVENT_ID = "88888888-8888-4888-8888-888888888888";
const ROUTE = "/execution/ceremonies";

type Call = { url: string; method: string; body: unknown };
const calls: Call[] = [];

function agendaEvent(overrides: Record<string, unknown> = {}) {
  return {
    id: EVENT_ID,
    organization_id: ORG_ID,
    assessment_id: null,
    assessment_label: null,
    title: "Daily da Sprint 1",
    description: "",
    event_type: "daily_check_in",
    starts_at: new Date().toISOString(),
    ends_at: null,
    timezone: "America/Sao_Paulo",
    owner_membership_id: null,
    owner_label: null,
    participant_membership_ids: [],
    location_or_link: "",
    status: "scheduled",
    guidance: "",
    related_action: "",
    source_kind: null,
    source_id: null,
    sprint_id: SPRINT_ID,
    is_auto: false,
    is_overdue: false,
    primary_action_label: "Abrir",
    primary_action_href: null,
    why_it_matters: "",
    preparation: "",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

type Router = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Response | Promise<Response> | undefined;

function installFetch(
  router?: Router,
  options: { events?: unknown[]; records?: unknown[] } = {},
) {
  const events = options.events ?? [agendaEvent()];
  const records = options.records ?? [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      const method = methodOf(input, init);
      calls.push({ url, method, body: await bodyOf(input, init) });

      const custom = await router?.(input, init);
      if (custom) return custom;

      if (url.includes("/organizations/me/memberships")) return membershipResponse();
      if (url.includes("/agile/squads")) return jsonResponse([squadPayload()]);
      if (url.includes("/agile/sprints") && url.includes("/ceremony-records")) {
        return method === "POST"
          ? jsonResponse({ id: "cer-1" }, 201)
          : jsonResponse(records);
      }
      if (url.includes("/agile/sprints")) {
        return jsonResponse([sprintPayload({ status: "active" })]);
      }
      if (url.includes("/agenda/events")) {
        return method === "POST"
          ? jsonResponse(agendaEvent({ id: NEW_EVENT_ID, title: "Retro da Sprint 1" }), 201)
          : jsonResponse(events);
      }
      return jsonResponse({}, 404);
    }),
  );
}

async function selectSprint(user: ReturnType<typeof userEvent.setup>) {
  await waitFor(() => expect(screen.getByLabelText("Squad")).toBeInTheDocument());
  await user.selectOptions(screen.getByLabelText("Squad"), SQUAD_ID);
  await waitFor(() =>
    expect(optionLabels(screen.getByLabelText("Sprint")).join(" ")).toContain("Sprint 1"),
  );
  await user.selectOptions(screen.getByLabelText("Sprint"), SPRINT_ID);
}

describe("CeremoniesPage", () => {
  beforeEach(() => {
    calls.length = 0;
    resetConfigCache();
    resetQmindClient();
    vi.stubGlobal("matchMedia", vi.fn(stubMatchMedia(false)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("asks for a sprint before offering ceremony registration", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CeremoniesPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText(/Escolha uma sprint/i)).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("ceremony-form")).toBeNull();
  });

  it("lists sprint ceremony events by title, date and type without any identifier field", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CeremoniesPage />, { path: ROUTE });
    await enterApp(user);
    await selectSprint(user);

    await waitFor(() =>
      expect(screen.getByTestId("ceremony-form")).toBeInTheDocument(),
    );
    const select = await waitFor(() => {
      const el = screen.getByLabelText(/Compromisso da sprint/i);
      expect(optionLabels(el).join(" ")).toContain("Daily da Sprint 1");
      return el;
    });

    const labels = optionLabels(select).join(" ");
    expect(labels).toContain("Check-in diário");
    expect(labels).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}/i);
    expect(screen.queryByPlaceholderText(/agenda_event_id/i)).toBeNull();
    expect(screen.queryByText(/Usar ID de evento existente/i)).toBeNull();
    expectNoVisibleUuid();
  });

  it("records a ceremony against the selected event and derives its type", async () => {
    installFetch(undefined, {
      events: [agendaEvent({ event_type: "retrospective", title: "Retro da Sprint 1" })],
    });
    const user = userEvent.setup();
    renderExecution(<CeremoniesPage />, { path: ROUTE });
    await enterApp(user);
    await selectSprint(user);

    const select = await waitFor(() => {
      const el = screen.getByLabelText(/Compromisso da sprint/i);
      expect(optionLabels(el).join(" ")).toContain("Retro da Sprint 1");
      return el;
    });
    await user.selectOptions(select, EVENT_ID);
    await user.click(screen.getByRole("button", { name: /Salvar registro/i }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/ceremony-records") && c.method === "POST"),
      ).toBe(true),
    );
    const posted = calls.find(
      (c) => c.url.includes("/ceremony-records") && c.method === "POST",
    );
    expect(posted?.body).toMatchObject({
      agenda_event_id: EVENT_ID,
      ceremony_type: "retrospective",
    });
    // No agenda event was created — the existing one was reused.
    expect(
      calls.some((c) => c.url.includes("/agenda/events") && c.method === "POST"),
    ).toBe(false);
  });

  it("creates a ceremony agenda event bound to the sprint and the ceremony type", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CeremoniesPage />, { path: ROUTE });
    await enterApp(user);
    await selectSprint(user);

    await waitFor(() =>
      expect(screen.getByTestId("ceremony-form")).toBeInTheDocument(),
    );
    await user.click(
      screen.getByRole("radio", { name: /Agendar um novo compromisso/i }),
    );
    await user.selectOptions(
      screen.getByLabelText(/Tipo de cerimônia/i),
      "retrospective",
    );
    await user.type(
      screen.getByLabelText(/Título do compromisso/i),
      "Retro da Sprint 1",
    );
    await user.type(screen.getByLabelText(/Data e hora/i), "2026-09-10T15:00");
    await user.click(screen.getByRole("button", { name: /Salvar registro/i }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/agenda/events") && c.method === "POST"),
      ).toBe(true),
    );
    const createdEvent = calls.find(
      (c) => c.url.includes("/agenda/events") && c.method === "POST",
    );
    expect(createdEvent?.body).toMatchObject({
      title: "Retro da Sprint 1",
      event_type: "retrospective",
      sprint_id: SPRINT_ID,
    });

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/ceremony-records") && c.method === "POST"),
      ).toBe(true),
    );
    const record = calls.find(
      (c) => c.url.includes("/ceremony-records") && c.method === "POST",
    );
    expect(record?.body).toMatchObject({
      agenda_event_id: NEW_EVENT_ID,
      ceremony_type: "retrospective",
    });
  });

  it("keeps submission disabled until an event is chosen", async () => {
    installFetch(undefined, { events: [] });
    const user = userEvent.setup();
    renderExecution(<CeremoniesPage />, { path: ROUTE });
    await enterApp(user);
    await selectSprint(user);

    await waitFor(() =>
      expect(screen.getByTestId("ceremony-form")).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: /Salvar registro/i })).toBeDisabled();
    await waitFor(() =>
      expect(
        screen.getByText(/Nenhuma cerimônia agendada nesta sprint/i),
      ).toBeInTheDocument(),
    );
  });

  it("shows history with the linked event title instead of its identifier", async () => {
    installFetch(undefined, {
      records: [
        {
          id: "cer-1",
          organization_id: ORG_ID,
          sprint_id: SPRINT_ID,
          agenda_event_id: EVENT_ID,
          ceremony_type: "daily_check_in",
          summary: "Time alinhado nos bloqueios",
          decisions: "Priorizar calibração",
          follow_up: "",
          recorded_by: "mem-1",
          recorded_at: new Date().toISOString(),
          revision: 1,
        },
      ],
    });
    const user = userEvent.setup();
    renderExecution(<CeremoniesPage />, { path: ROUTE });
    await enterApp(user);
    await selectSprint(user);

    await waitFor(() =>
      expect(screen.getByText(/Time alinhado nos bloqueios/i)).toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByText(/Compromisso: Daily da Sprint 1/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Priorizar calibração/i)).toBeInTheDocument();
    expectNoVisibleUuid();
  });

  it("hides the registration form for reader-only profiles", async () => {
    installFetch((input) => {
      if (urlOf(input).includes("/organizations/me/memberships")) {
        return membershipResponse(["reader"]);
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderExecution(<CeremoniesPage />, { path: ROUTE });
    await enterApp(user);
    await selectSprint(user);

    await waitFor(() =>
      expect(screen.getByText(/Histórico/i)).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("ceremony-form")).toBeNull();
    expect(screen.queryByRole("button", { name: /Salvar registro/i })).toBeNull();
  });

  it("scopes ceremony cache keys to the active organization", async () => {
    installFetch();
    const user = userEvent.setup();
    const { queryClient } = renderExecution(<CeremoniesPage />, { path: ROUTE });
    await enterApp(user);
    await selectSprint(user);

    await waitFor(() =>
      expect(screen.getByTestId("ceremony-form")).toBeInTheDocument(),
    );

    const keys = executionQueryKeys(queryClient);
    for (const key of keys) {
      expect(key[1]).toBe(ORG_ID);
    }
    expect(
      keys.some((key) => (key as unknown[]).includes("ceremonies")),
    ).toBe(true);
    expect(
      keys.some((key) => (key as unknown[]).includes("ceremony-events")),
    ).toBe(true);
  });
});

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SprintsPage } from "@/execution/SprintsPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";
import {
  ACTION_ID,
  boardCard,
  boardPayload,
  bodyOf,
  executionQueryKeys,
  expectNoVisibleUuid,
  jsonResponse,
  membershipResponse,
  methodOf,
  ORG_ID,
  renderExecution,
  sprintMetricsPayload,
  sprintPayload,
  SPRINT_ID,
  squadPayload,
  SQUAD_ID,
  stubMatchMedia,
  urlOf,
} from "@/test/executionHarness";

const ROUTE = "/execution/sprints";

type Call = { url: string; method: string; body: unknown };
const calls: Call[] = [];

type Router = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Response | Promise<Response> | undefined;

function installFetch(
  router?: Router,
  options: {
    sprints?: unknown[];
    metrics?: ReturnType<typeof sprintMetricsPayload>;
    board?: ReturnType<typeof boardPayload>;
  } = {},
) {
  const sprints = options.sprints ?? [sprintPayload()];
  const metrics = options.metrics ?? sprintMetricsPayload();
  const board = options.board ?? boardPayload();
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
      if (url.includes("/metrics")) return jsonResponse(metrics);
      if (url.includes("/activate")) {
        return jsonResponse(sprintPayload({ status: "active" }));
      }
      if (url.includes("/complete")) {
        return jsonResponse(sprintPayload({ status: "completed" }));
      }
      if (url.includes("/agile/board")) return jsonResponse(board);
      if (url.includes("/agile/sprints")) {
        return method === "POST"
          ? jsonResponse(sprintPayload(), 201)
          : jsonResponse(sprints);
      }
      return jsonResponse({}, 404);
    }),
  );
}

describe("SprintsPage", () => {
  beforeEach(() => {
    calls.length = 0;
    resetConfigCache();
    resetQmindClient();
    vi.stubGlobal("matchMedia", vi.fn(stubMatchMedia(false)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates a sprint from squad name and dates", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() => expect(screen.getByText("Nova sprint")).toBeInTheDocument());

    await user.selectOptions(
      screen.getByLabelText(/Squad responsável/i),
      SQUAD_ID,
    );
    await user.type(screen.getByLabelText(/Nome da sprint/i), "Sprint 2");
    await user.type(screen.getByLabelText("Início"), "2026-09-01T09:00");
    await user.type(screen.getByLabelText("Término"), "2026-09-15T18:00");
    await user.click(screen.getByRole("button", { name: /Criar sprint/i }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/agile/sprints") && c.method === "POST"),
      ).toBe(true),
    );
    const posted = calls.find(
      (c) => c.url.includes("/agile/sprints") && c.method === "POST",
    );
    expect(posted?.body).toMatchObject({ squad_id: SQUAD_ID, name: "Sprint 2" });
  });

  it("activates a planned sprint", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() => expect(screen.getByText(/Sprint 1/)).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Ativar" }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/activate") && c.method === "POST"),
      ).toBe(true),
    );
  });

  it("renders cycle time, blocked time and stale check-in metrics", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    const metrics = await waitFor(() =>
      screen.getByTestId(`sprint-metrics-${SPRINT_ID}`),
    );
    expect(metrics).toHaveTextContent("Tempo de ciclo (média)");
    expect(metrics).toHaveTextContent("18.0 h");
    expect(metrics).toHaveTextContent("Tempo de ciclo (mediana)");
    expect(metrics).toHaveTextContent("1.3 d");
    expect(metrics).toHaveTextContent("Card mais antigo em execução");
    expect(metrics).toHaveTextContent("5.0 d");
    expect(metrics).toHaveTextContent("Tempo bloqueado");
    expect(metrics).toHaveTextContent("12.0 h");
    expect(metrics).toHaveTextContent("Sem check-in há mais de 72h");
    expect(metrics).toHaveTextContent("Carry-over");
    expect(metrics).toHaveTextContent("Meta parcialmente atingida");
    expectNoVisibleUuid();
  });

  it("renders em dash for metrics the backend could not compute", async () => {
    installFetch(undefined, {
      metrics: sprintMetricsPayload({
        average_cycle_time_hours: null,
        median_cycle_time_hours: null,
        oldest_in_progress_age_hours: null,
        blocked_time_hours: null,
        review_outcome: null,
      }),
    });
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    const metrics = await waitFor(() =>
      screen.getByTestId(`sprint-metrics-${SPRINT_ID}`),
    );
    expect(metrics).toHaveTextContent("—");
    expect(metrics).not.toHaveTextContent("NaN");
  });

  it("warns when the sprint exceeds the WIP limit", async () => {
    installFetch(undefined, {
      board: boardPayload({}, {
        wip_signal: true,
        wip_limit_in_progress: 3,
        in_progress_count: 5,
      }),
    });
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    const banner = await waitFor(() =>
      screen.getByTestId(`sprint-wip-banner-${SPRINT_ID}`),
    );
    expect(banner).toHaveTextContent("Limite WIP em execução (3) ultrapassado");
    expect(banner).toHaveTextContent("5 cards em andamento");
  });

  it("collects carry-over decisions by card description before completing", async () => {
    installFetch(undefined, {
      sprints: [sprintPayload({ status: "active" })],
      board: boardPayload({
        in_progress: [
          boardCard({
            action_item_id: ACTION_ID,
            description: "Concluir treinamento da equipe",
            status: "in_progress",
          }),
        ],
      }),
    });
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Concluir sprint/i })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /Concluir sprint/i }));

    await waitFor(() =>
      expect(screen.getByText("Concluir treinamento da equipe")).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /Confirmar conclusão/i }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/complete") && c.method === "POST"),
      ).toBe(true),
    );
    const posted = calls.find((c) => c.url.includes("/complete") && c.method === "POST");
    expect(posted?.body).toMatchObject({
      carry_decisions: [{ action_item_id: ACTION_ID, decision: "backlog" }],
    });
  });

  it("surfaces a rejected completion without leaving the panel", async () => {
    installFetch(
      (input) => {
        if (urlOf(input).includes("/complete")) {
          return jsonResponse(
            {
              code: "carry_decision_missing",
              message: "Defina o destino de todos os cards",
              correlation_id: "11111111-2222-4333-8444-555555555555",
            },
            409,
          );
        }
        return undefined;
      },
      {
        sprints: [sprintPayload({ status: "active" })],
        board: boardPayload({
          in_progress: [
            boardCard({ description: "Concluir treinamento da equipe" }),
          ],
        }),
      },
    );
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /Concluir sprint/i })),
    );
    await user.click(
      await waitFor(() => screen.getByRole("button", { name: /Confirmar conclusão/i })),
    );

    await waitFor(() =>
      expect(screen.getByText(/Erro ao concluir sprint/i)).toBeInTheDocument(),
    );
    expect(screen.getByText("Concluir treinamento da equipe")).toBeInTheDocument();
  });

  it("hides lifecycle actions for reader-only profiles", async () => {
    installFetch((input) => {
      if (urlOf(input).includes("/organizations/me/memberships")) {
        return membershipResponse(["reader"]);
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() => expect(screen.getByText(/Sprint 1/)).toBeInTheDocument());
    expect(screen.queryByText("Nova sprint")).toBeNull();
    expect(screen.queryByRole("button", { name: "Ativar" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Concluir sprint/i })).toBeNull();
  });

  it("scopes sprint and metrics cache keys to the active organization", async () => {
    installFetch();
    const user = userEvent.setup();
    const { queryClient } = renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId(`sprint-metrics-${SPRINT_ID}`)).toBeInTheDocument(),
    );

    const keys = executionQueryKeys(queryClient);
    for (const key of keys) {
      expect(key[1]).toBe(ORG_ID);
    }
    const sprintKeys = keys.filter((key) => key[3] === "sprints");
    expect(sprintKeys.length).toBeGreaterThan(0);
    expect(
      sprintKeys.some((key) => (key as unknown[]).includes("metrics")),
    ).toBe(true);
  });

  it("lists sprints by name and goal, never by identifier", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<SprintsPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() => expect(screen.getByText(/Sprint 1/)).toBeInTheDocument());
    const row = screen.getByText(/Sprint 1/).closest("li");
    expect(row).not.toBeNull();
    expect(within(row as HTMLElement).getByText(/Fechar achados críticos/)).toBeInTheDocument();
    expectNoVisibleUuid();
  });
});

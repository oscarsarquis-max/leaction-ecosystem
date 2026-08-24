import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CardDetailPage } from "@/execution/CardDetailPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";
import {
  ACTION_ID,
  boardCard,
  boardPayload,
  bodyOf,
  expectNoVisibleUuid,
  jsonResponse,
  membershipResponse,
  methodOf,
  noContentResponse,
  optionLabels,
  ORG_ID,
  OWNER_ID,
  PLAN_ID,
  renderExecution,
  SPRINT_ID,
  stubMatchMedia,
  urlOf,
} from "@/test/executionHarness";

const PREDECESSOR_ID = "44444444-4444-4444-8444-444444444444";
const DEPENDENCY_ID = "55555555-5555-4555-8555-555555555555";
const ROUTE = "/execution/cards/:actionItemId";

type Call = { url: string; method: string; body: unknown };

const calls: Call[] = [];

function actionItemPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: ACTION_ID,
    organization_id: ORG_ID,
    action_plan_id: PLAN_ID,
    finding_id: null,
    source_evolution_suggestion_id: null,
    source_analysis_run_id: null,
    source_finding_code: null,
    action_kind: "improvement",
    description: "Ação de teste para check-in",
    owner_membership_id: OWNER_ID,
    due_at: new Date().toISOString(),
    status: "in_progress",
    is_overdue: false,
    efficacy_required: false,
    source_finding_withdrawn: false,
    validated_by: null,
    efficacy_confirmed_by: null,
    cancel_reason: null,
    reject_reason: null,
    efficacy_fail_reason: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

function defaultBoard() {
  return boardPayload(
    {
      in_progress: [
        boardCard({
          action_item_id: ACTION_ID,
          description: "Ação de teste para check-in",
          sprint_id: SPRINT_ID,
          sprint_name: "Sprint 1",
        }),
      ],
      backlog: [
        boardCard({
          action_item_id: PREDECESSOR_ID,
          description: "Revisar procedimento de calibração",
          status: "open",
          owner_display_name: "Bruno Costa",
          owner_email: "bruno@example.com",
          sprint_id: null,
          sprint_name: null,
        }),
      ],
    },
    { active_sprint_id: SPRINT_ID },
  );
}

type Router = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Response | Promise<Response> | undefined;

function installFetch(
  router?: Router,
  options: { board?: ReturnType<typeof defaultBoard>; dependencies?: unknown[] } = {},
) {
  const board = options.board ?? defaultBoard();
  const dependencies = options.dependencies ?? [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      calls.push({ url, method: methodOf(input, init), body: await bodyOf(input, init) });

      const custom = await router?.(input, init);
      if (custom) return custom;

      if (url.includes("/organizations/me/memberships")) return membershipResponse();
      if (url.includes("/action-items/")) return jsonResponse(actionItemPayload());
      if (url.includes("/agile/board")) return jsonResponse(board);
      if (url.includes("/check-ins")) {
        return methodOf(input, init) === "POST"
          ? jsonResponse({ id: "chk-1" }, 201)
          : jsonResponse([]);
      }
      if (url.includes("/impediments")) return jsonResponse([]);
      if (url.includes("/dependencies")) {
        if (methodOf(input, init) === "DELETE") return noContentResponse();
        if (methodOf(input, init) === "POST") {
          return jsonResponse({ id: DEPENDENCY_ID }, 201);
        }
        return jsonResponse(dependencies);
      }
      return jsonResponse({}, 404);
    }),
  );
}

describe("CardDetailPage", () => {
  beforeEach(() => {
    calls.length = 0;
    resetConfigCache();
    resetQmindClient();
    vi.stubGlobal("matchMedia", vi.fn(stubMatchMedia(false)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows check-in form for mutating users", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-check-in-form")).toBeInTheDocument(),
    );
    expect(screen.getByLabelText(/O que avançou/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Registrar check-in/i })).toBeInTheDocument();
  });

  it("posts a check-in against the sprint the card is allocated to", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-check-in-form")).toBeInTheDocument(),
    );
    await user.type(screen.getByLabelText(/O que avançou/i), "Procedimento revisado");
    await user.click(screen.getByRole("button", { name: /Registrar check-in/i }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/check-ins") && c.method === "POST"),
      ).toBe(true),
    );
    const posted = calls.find((c) => c.url.includes("/check-ins") && c.method === "POST");
    expect(posted?.body).toMatchObject({
      health: "on_track",
      progress_note: "Procedimento revisado",
      sprint_id: SPRINT_ID,
    });
  });

  it("offers a searchable action selector instead of an identifier field", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-dependency-form")).toBeInTheDocument(),
    );

    const select = screen.getByLabelText(/Ação predecessora/i);
    const labels = optionLabels(select);
    expect(labels.join(" ")).toContain("Revisar procedimento de calibração");
    expect(labels.join(" ")).toContain("Bruno Costa");
    expect(labels.join(" ")).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}/i);
    // The card being viewed must not offer itself as its own predecessor.
    expect(labels.join(" ")).not.toContain("Ação de teste para check-in");
    expectNoVisibleUuid();
  });

  it("narrows predecessor candidates by free-text search", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-dependency-form")).toBeInTheDocument(),
    );

    const search = screen.getByLabelText(/Buscar por descrição/i);
    await user.type(search, "Bruno");
    expect(optionLabels(screen.getByLabelText(/Ação predecessora/i)).join(" ")).toContain(
      "Revisar procedimento de calibração",
    );

    await user.clear(search);
    await user.type(search, "assunto inexistente");
    expect(
      screen.getByText(/Nenhuma ação disponível para vincular com esse filtro/i),
    ).toBeInTheDocument();
  });

  it("creates a dependency from the selected action description", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-dependency-form")).toBeInTheDocument(),
    );

    const select = screen.getByLabelText(/Ação predecessora/i);
    await user.selectOptions(select, [
      within(select).getByRole("option", {
        name: /Revisar procedimento de calibração/i,
      }),
    ]);
    await user.click(screen.getByRole("button", { name: "Vincular" }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/dependencies") && c.method === "POST"),
      ).toBe(true),
    );
    const posted = calls.find(
      (c) => c.url.includes("/dependencies") && c.method === "POST",
    );
    expect(posted?.body).toMatchObject({
      predecessor_action_item_id: PREDECESSOR_ID,
      dependent_action_item_id: ACTION_ID,
      dependency_type: "blocks",
    });
  });

  it("lists dependencies by description and soft-deletes on request", async () => {
    installFetch(undefined, {
      dependencies: [
        {
          id: DEPENDENCY_ID,
          organization_id: ORG_ID,
          predecessor_action_item_id: PREDECESSOR_ID,
          dependent_action_item_id: ACTION_ID,
          dependency_type: "blocks",
          status: "active",
          created_by: OWNER_ID,
          created_at: new Date().toISOString(),
        },
      ],
    });
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    const list = await waitFor(() => screen.getByTestId("execution-dependency-list"));
    expect(list).toHaveTextContent("Revisar procedimento de calibração");
    expect(list).toHaveTextContent("Bloqueia esta ação");
    expect(list.textContent ?? "").not.toContain(PREDECESSOR_ID);

    await user.click(within(list).getByRole("button", { name: "Remover" }));
    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/dependencies/") && c.method === "DELETE"),
      ).toBe(true),
    );
  });

  it("requests only active dependencies by default", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-dependency-list")).toBeInTheDocument(),
    );
    const listCall = calls.find(
      (c) => c.url.includes("/dependencies") && c.method === "GET",
    );
    expect(listCall?.url).toContain("include_removed=false");
  });

  it("hides every mutation surface for reader-only profiles", async () => {
    installFetch((input) => {
      if (urlOf(input).includes("/organizations/me/memberships")) {
        return membershipResponse(["reader"]);
      }
      return undefined;
    });
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText("Ação de teste para check-in")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("execution-check-in-form")).toBeNull();
    expect(screen.queryByTestId("execution-dependency-form")).toBeNull();
    expect(screen.queryByRole("button", { name: "Vincular" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Registrar" })).toBeNull();
    expect(
      screen.getAllByText(/Seu perfil é somente leitura/i).length,
    ).toBeGreaterThan(0);
  });

  it("surfaces stale QMind analysis with a link back to the analysis", async () => {
    const caseId = "11111111-1111-4111-8111-111111111111";
    installFetch(undefined, {
      board: boardPayload(
        {
          in_progress: [
            boardCard({
              action_item_id: ACTION_ID,
              description: "Ação de teste para check-in",
              source_analysis_is_stale: true,
              source_analysis_run_id: "22222222-2222-4222-8222-222222222222",
              source_finding_code: "F-12",
              improvement_case_id: caseId,
            }),
          ],
        },
        { active_sprint_id: SPRINT_ID },
      ),
    });
    const user = userEvent.setup();
    renderExecution(<CardDetailPage />, {
      path: ROUTE,
      initial: `/execution/cards/${ACTION_ID}`,
    });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-detail-stale-analysis")).toHaveTextContent(
        "Análise QMind desatualizada",
      ),
    );
    expect(
      screen.getByRole("link", { name: /Rever análise \(achado F-12\)/i }),
    ).toHaveAttribute("href", `/improvement-cases/${caseId}#ic-finding-anchor-F-12`);
    expectNoVisibleUuid();
  });
});

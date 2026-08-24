import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BoardPage } from "@/execution/BoardPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";
import {
  ACTION_ID,
  boardCard,
  boardPayload,
  executionQueryKeys,
  expectNoVisibleUuid,
  jsonResponse,
  membershipResponse,
  methodOf,
  ORG_ID,
  OWNER_ID,
  renderExecution,
  stubMatchMedia,
  urlOf,
} from "@/test/executionHarness";

const CASE_ID = "11111111-1111-4111-8111-111111111111";
const RUN_ID = "22222222-2222-4222-8222-222222222222";
const STALE_ACTION_ID = "33333333-3333-4333-8333-333333333333";

type Router = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Response | Promise<Response> | undefined;

const calls: { url: string; method: string }[] = [];

function installFetch(router?: Router, board = boardPayload()) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      calls.push({ url, method: methodOf(input, init) });

      const custom = await router?.(input, init);
      if (custom) return custom;

      if (url.includes("/organizations/me/memberships")) return membershipResponse();
      if (url.includes("/agile/board/move")) {
        return jsonResponse({
          action_item_id: ACTION_ID,
          from_column: "in_progress",
          to_column: "implemented",
          item_status: "implemented",
        });
      }
      if (url.includes("/agile/board")) return jsonResponse(board);
      if (url.includes("/agile/squads")) return jsonResponse([]);
      if (url.includes("/agile/sprints")) return jsonResponse([]);
      return jsonResponse({}, 404);
    }),
  );
}

describe("BoardPage", () => {
  beforeEach(() => {
    calls.length = 0;
    resetConfigCache();
    resetQmindClient();
    vi.stubGlobal("matchMedia", vi.fn(stubMatchMedia(true)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders empty board state with column headers after load", async () => {
    installFetch();
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText(/Nenhuma ação no board ainda/i)).toBeInTheDocument(),
    );
  });

  it("renders populated board with owner display name, not raw UUID", async () => {
    installFetch(undefined, boardPayload({ in_progress: [boardCard()] }));
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText("Implementar controle de documentos")).toBeInTheDocument(),
    );
    expect(screen.getByRole("region", { name: /Board de execução ágil/i })).toBeInTheDocument();
    expect(screen.getByTestId(`execution-card-${ACTION_ID}`)).toHaveTextContent("Ana Silva");
    expect(screen.queryByText(OWNER_ID)).toBeNull();
    expectNoVisibleUuid();
  });

  it("reads check-in and impediment state from the board payload without per-card queries", async () => {
    installFetch(
      undefined,
      boardPayload({
        in_progress: [
          boardCard({
            latest_check_in_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
            latest_check_in_health: "attention",
            has_open_impediment: true,
            open_impediment_count: 2,
            has_blocking_dependency: true,
            blocking_dependency_count: 3,
          }),
        ],
      }),
    );
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    const card = await waitFor(() => screen.getByTestId(`execution-card-${ACTION_ID}`));
    expect(card).toHaveTextContent(/Há 5 dias/);
    expect(card).toHaveTextContent(/Precisa de atenção/);
    expect(card).toHaveTextContent("Bloqueada (2)");
    expect(card).toHaveTextContent("Dependência (3)");
    expect(card).toHaveTextContent("Sem check-in recente");

    expect(calls.filter((c) => c.url.includes("/check-ins"))).toHaveLength(0);
    expect(calls.filter((c) => c.url.includes("/impediments"))).toHaveLength(0);
    expect(calls.filter((c) => c.url.includes("/agile/board"))).toHaveLength(1);
  });

  it("badges stale QMind analysis and links to the originating improvement case", async () => {
    installFetch(
      undefined,
      boardPayload({
        in_progress: [
          boardCard({
            source_analysis_is_stale: true,
            source_analysis_run_id: RUN_ID,
            source_finding_code: "F-07",
            improvement_case_id: CASE_ID,
          }),
        ],
      }),
    );
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId(`execution-stale-analysis-${ACTION_ID}`)).toHaveTextContent(
        "Análise QMind desatualizada",
      ),
    );
    const link = screen.getByRole("link", { name: /Rever análise \(achado F-07\)/i });
    expect(link).toHaveAttribute("href", `/improvement-cases/${CASE_ID}#ic-finding-anchor-F-07`);
    expectNoVisibleUuid();
  });

  it("filters stale check-in and stale intelligence independently", async () => {
    installFetch(
      undefined,
      boardPayload({
        in_progress: [
          boardCard({
            action_item_id: ACTION_ID,
            description: "Card com check-in antigo",
            latest_check_in_at: new Date(Date.now() - 10 * 86_400_000).toISOString(),
            source_analysis_is_stale: false,
          }),
          boardCard({
            action_item_id: STALE_ACTION_ID,
            description: "Card com análise vencida",
            latest_check_in_at: new Date().toISOString(),
            source_analysis_is_stale: true,
            source_analysis_run_id: RUN_ID,
            improvement_case_id: CASE_ID,
          }),
        ],
      }),
    );
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText("Card com check-in antigo")).toBeInTheDocument(),
    );

    const staleCheckIn = screen.getByRole("checkbox", { name: /Sem check-in recente/i });
    const staleAnalysis = screen.getByRole("checkbox", { name: /Inteligência desatualizada/i });
    expect(staleCheckIn).not.toBe(staleAnalysis);

    await user.click(staleCheckIn);
    expect(screen.getByText("Card com check-in antigo")).toBeInTheDocument();
    expect(screen.queryByText("Card com análise vencida")).toBeNull();

    await user.click(staleCheckIn);
    await user.click(staleAnalysis);
    expect(screen.getByText("Card com análise vencida")).toBeInTheDocument();
    expect(screen.queryByText("Card com check-in antigo")).toBeNull();
  });

  it("badges evidence and measurement posture straight from the board payload", async () => {
    installFetch(
      undefined,
      boardPayload({
        in_progress: [
          boardCard({
            evidence_count_total: 2,
            evidence_count_approved: 1,
            indicator_count: 1,
            measurement_posture: "overdue",
            target_posture: "not_met",
          }),
        ],
      }),
    );
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    const badges = await waitFor(() =>
      screen.getByTestId(`execution-result-badges-${ACTION_ID}`),
    );
    expect(badges).toHaveTextContent("2 evidências · 1 aprovada");
    expect(badges).toHaveTextContent("Medição atrasada");
    expect(badges).toHaveTextContent("Meta não atingida");

    expect(calls.filter((c) => c.url.includes("evidence-links"))).toHaveLength(0);
    expect(calls.filter((c) => c.url.includes("measurement"))).toHaveLength(0);
    expect(calls.filter((c) => c.url.includes("/agile/board"))).toHaveLength(1);
    expectNoVisibleUuid();
  });

  it("says so when a card carries no evidence at all", async () => {
    installFetch(undefined, boardPayload({ in_progress: [boardCard()] }));
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    const badges = await waitFor(() =>
      screen.getByTestId(`execution-result-badges-${ACTION_ID}`),
    );
    expect(badges).toHaveTextContent("Sem evidência");
    expect(badges).toHaveTextContent("Sem medição planejada");
  });

  it("filters overdue measurement and unmet target independently", async () => {
    installFetch(
      undefined,
      boardPayload({
        in_progress: [
          boardCard({
            action_item_id: ACTION_ID,
            description: "Card com medição atrasada",
            measurement_posture: "overdue",
            target_posture: "unknown",
          }),
          boardCard({
            action_item_id: STALE_ACTION_ID,
            description: "Card com meta não atingida",
            measurement_posture: "on_time",
            target_posture: "not_met",
          }),
        ],
      }),
    );
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText("Card com medição atrasada")).toBeInTheDocument(),
    );

    const overdueFilter = screen.getByRole("checkbox", { name: /Medição atrasada/i });
    const targetFilter = screen.getByRole("checkbox", { name: /Meta não atingida/i });

    await user.click(overdueFilter);
    expect(screen.getByText("Card com medição atrasada")).toBeInTheDocument();
    expect(screen.queryByText("Card com meta não atingida")).toBeNull();

    await user.click(overdueFilter);
    await user.click(targetFilter);
    expect(screen.getByText("Card com meta não atingida")).toBeInTheDocument();
    expect(screen.queryByText("Card com medição atrasada")).toBeNull();
  });

  it("shows keyboard move controls on compact layout without drag", async () => {
    installFetch(undefined, boardPayload({ in_progress: [boardCard()] }));
    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-keyboard-move")).toBeInTheDocument(),
    );

    await user.selectOptions(screen.getByLabelText(/Mover card/i), "implemented");
    await user.click(screen.getByRole("button", { name: "Mover" }));

    await waitFor(() =>
      expect(calls.some((c) => c.url.includes("/agile/board/move"))).toBe(true),
    );
  });

  it("rolls the card back to its column when the move is rejected", async () => {
    let moveAttempts = 0;
    installFetch((input) => {
      if (urlOf(input).includes("/agile/board/move")) {
        moveAttempts += 1;
        return jsonResponse(
          {
            code: "impediment_open",
            message: "Card bloqueado por impedimento aberto",
            correlation_id: "11111111-2222-4333-8444-555555555555",
          },
          409,
        );
      }
      return undefined;
    }, boardPayload({ in_progress: [boardCard()] }));

    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-keyboard-move")).toBeInTheDocument(),
    );

    await user.selectOptions(screen.getByLabelText(/Mover card/i), "implemented");
    await user.click(screen.getByRole("button", { name: "Mover" }));

    await waitFor(() => expect(moveAttempts).toBe(1));
    await waitFor(() =>
      expect(screen.getByText(/Não foi possível mover o card/i)).toBeInTheDocument(),
    );

    const inProgress = screen.getByRole("region", { name: /Coluna Em execução/i });
    expect(
      within(inProgress).getByText("Implementar controle de documentos"),
    ).toBeInTheDocument();
  });

  it("hides move controls for reader-only profiles", async () => {
    installFetch((input) => {
      if (urlOf(input).includes("/organizations/me/memberships")) {
        return membershipResponse(["reader"]);
      }
      return undefined;
    }, boardPayload({ in_progress: [boardCard()] }));

    const user = userEvent.setup();
    renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText("Implementar controle de documentos")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("execution-keyboard-move")).toBeNull();
    expect(screen.queryByRole("button", { name: "Mover" })).toBeNull();
  });

  it("scopes board cache keys to the active organization", async () => {
    installFetch(undefined, boardPayload({ in_progress: [boardCard()] }));
    const user = userEvent.setup();
    const { queryClient } = renderExecution(<BoardPage />);
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText("Implementar controle de documentos")).toBeInTheDocument(),
    );

    const keys = executionQueryKeys(queryClient);
    expect(keys.length).toBeGreaterThan(0);
    for (const key of keys) {
      expect(key[1]).toBe(ORG_ID);
    }
    expect(keys.some((key) => key[3] === "board")).toBe(true);
  });
});

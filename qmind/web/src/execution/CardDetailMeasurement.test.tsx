import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
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
  executionQueryKeys,
  expectNoVisibleUuid,
  indicatorPayload,
  jsonResponse,
  measurementRecordPayload,
  measurementSummaryPayload,
  membershipResponse,
  methodOf,
  orgMemberPayload,
  ORG_ID,
  OWNER_ID,
  PLAN_ID,
  renderExecution,
  SPRINT_ID,
  stubMatchMedia,
  targetEvaluationPayload,
  urlOf,
} from "@/test/executionHarness";

const ROUTE = "/execution/cards/:actionItemId";

type Call = { url: string; method: string; body: unknown };
const calls: Call[] = [];

function actionItemPayload() {
  return {
    id: ACTION_ID,
    organization_id: ORG_ID,
    action_plan_id: PLAN_ID,
    finding_id: null,
    source_evolution_suggestion_id: null,
    source_analysis_run_id: null,
    source_finding_code: null,
    action_kind: "improvement",
    description: "Padronizar o registro de ocorrências",
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
  };
}

type Router = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Response | undefined;

function installFetch(
  options: {
    router?: Router;
    summary?: unknown;
    indicators?: unknown[];
    records?: unknown[];
  } = {},
) {
  const summary = options.summary ?? measurementSummaryPayload({ plan: null });
  const indicators = options.indicators ?? [];
  const records = options.records ?? [];

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      const method = methodOf(input, init);
      calls.push({ url, method, body: await bodyOf(input, init) });

      const custom = options.router?.(input, init);
      if (custom) return custom;

      if (url.includes("/organizations/me/memberships")) return membershipResponse();
      if (url.includes("/organizations/current/members")) {
        return jsonResponse([orgMemberPayload()]);
      }
      if (url.includes("/organizations/current/evidence-links")) return jsonResponse([]);
      if (url.includes("/measurement-summary")) return jsonResponse(summary);
      if (url.includes("/indicators")) return jsonResponse(indicators);
      if (url.includes("/measurements")) {
        return method === "POST"
          ? jsonResponse(measurementRecordPayload(), 201)
          : jsonResponse(records);
      }
      if (url.includes("/measurement-plans")) {
        return method === "POST"
          ? jsonResponse({ id: "plan-created" }, 201)
          : jsonResponse([]);
      }
      if (url.includes("/action-items/")) return jsonResponse(actionItemPayload());
      if (url.includes("/agile/board")) {
        return jsonResponse(
          boardPayload(
            {
              in_progress: [
                boardCard({
                  action_item_id: ACTION_ID,
                  description: "Padronizar o registro de ocorrências",
                  sprint_id: SPRINT_ID,
                }),
              ],
            },
            { active_sprint_id: SPRINT_ID },
          ),
        );
      }
      if (url.includes("/check-ins")) return jsonResponse([]);
      if (url.includes("/impediments")) return jsonResponse([]);
      if (url.includes("/dependencies")) return jsonResponse([]);
      return jsonResponse({}, 404);
    }),
  );
}

function renderCard() {
  return renderExecution(<CardDetailPage />, {
    path: ROUTE,
    initial: `/execution/cards/${ACTION_ID}`,
  });
}

describe("CardDetailPage — medição do resultado", () => {
  beforeEach(() => {
    calls.length = 0;
    resetConfigCache();
    resetQmindClient();
    vi.stubGlobal("matchMedia", vi.fn(stubMatchMedia(false)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("offers to create the measurement plan when the action has none", async () => {
    installFetch({
      summary: measurementSummaryPayload({
        plan: null,
        measurement_posture: "not_planned",
        target_posture: "unknown",
        substantiation: "none",
        indicator_count: 0,
        evaluations: [],
        headline: "Esta ação ainda não tem como provar que funcionou.",
        what_to_do_next: "Defina o que será medido.",
      }),
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("measurement-plan-form")).toBeInTheDocument(),
    );
    await user.type(
      screen.getByLabelText(/O que esta ação precisa provar/i),
      "Reduzir o retrabalho na linha 2",
    );
    await user.click(screen.getByRole("button", { name: /Criar plano de medição/i }));

    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url.includes("/measurement-plans") && c.method === "POST",
        ),
      ).toBe(true),
    );
    const posted = calls.find(
      (c) => c.url.includes("/measurement-plans") && c.method === "POST",
    );
    expect(posted?.body).toMatchObject({
      action_plan_id: PLAN_ID,
      objective: "Reduzir o retrabalho na linha 2",
    });
  });

  it("warns that a met target is not confirmed efficacy", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [measurementRecordPayload()],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const section = await waitFor(() =>
      screen.getByTestId("execution-measurement-section"),
    );
    await waitFor(() => expect(section).toHaveTextContent("Medição em dia"));
    expect(screen.getByTestId("measurement-efficacy-warning")).toHaveTextContent(
      "Meta atingida não equivale, por si só, à eficácia confirmada.",
    );
    expect(section).toHaveTextContent("Meta atingida");
  });

  it("shows the indicator in words, keeping decimal values exactly as recorded", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [measurementRecordPayload()],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const card = await waitFor(() =>
      screen.getByTestId(`measurement-indicator-${indicatorPayload().id}`),
    );
    expect(card).toHaveTextContent("Retrabalho na linha 2");
    expect(card).toHaveTextContent("peças/semana");
    expect(card).toHaveTextContent("18.50");
    expect(card).toHaveTextContent("9.25");
    expect(card).toHaveTextContent("9.10");
    expect(card).toHaveTextContent("Quanto menor, melhor");
    expect(card).toHaveTextContent("Ana Silva");
    expectNoVisibleUuid();
  });

  it("shows a single reading as a value and a table, not as a trend", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [measurementRecordPayload()],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const history = await waitFor(() =>
      screen.getByTestId(`measurement-history-${indicatorPayload().id}`),
    );
    expect(history).toHaveTextContent(/Uma única medição/i);
    expect(history.querySelector("svg")).toBeNull();
    expect(history.querySelector("table")).not.toBeNull();
  });

  it("draws a trend once two comparable readings of the same indicator exist", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [
        measurementRecordPayload({ value: "14.00" }),
        measurementRecordPayload({
          id: "19191919-1919-4919-8919-191919191919",
          value: "9.10",
          measured_at: new Date(Date.now() + 86_400_000).toISOString(),
        }),
      ],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const history = await waitFor(() =>
      screen.getByTestId(`measurement-history-${indicatorPayload().id}`),
    );
    await waitFor(() => expect(history.querySelector("svg")).not.toBeNull());
    expect(history).toHaveTextContent("14.00");
    expect(history).toHaveTextContent("9.10");
  });

  it("says who answers for the plan and for each indicator", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [measurementRecordPayload()],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const planOwner = await waitFor(() =>
      screen.getByTestId("measurement-plan-owner"),
    );
    expect(planOwner).toHaveTextContent("Ana Silva");
    const indicatorOwner = await waitFor(() =>
      screen.getByTestId(`measurement-indicator-owner-${indicatorPayload().id}`),
    );
    expect(indicatorOwner).toHaveTextContent("Ana Silva");
    expectNoVisibleUuid();
  });

  it("records the starting point as a baseline reading, not as a definition edit", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [
        indicatorPayload({
          baseline_status: "missing",
          baseline_value: null,
          baseline_at: null,
          baseline_measurement_id: null,
        }),
      ],
      records: [],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    await waitFor(() =>
      expect(
        screen.getByTestId(`measurement-baseline-form-${indicatorPayload().id}`),
      ).toBeInTheDocument(),
    );
    await user.type(screen.getByLabelText(/Valor de partida/i), "18.50");
    await user.click(
      screen.getByRole("button", { name: /Registrar ponto de partida/i }),
    );

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/measurements") && c.method === "POST"),
      ).toBe(true),
    );
    const posted = calls.find(
      (c) => c.url.includes("/measurements") && c.method === "POST",
    );
    expect(posted?.body).toMatchObject({
      indicator_definition_id: indicatorPayload().id,
      value: "18.50",
      measurement_kind: "baseline",
    });
  });

  it("keeps a value too large for a float readable and charted", async () => {
    const huge = "123456789012345678901234567890.55";
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [
        measurementRecordPayload({ value: huge }),
        measurementRecordPayload({
          id: "19191919-1919-4919-8919-191919191919",
          value: "123456789012345678901234567890.56",
          measured_at: new Date(Date.now() + 86_400_000).toISOString(),
        }),
      ],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const history = await waitFor(() =>
      screen.getByTestId(`measurement-history-${indicatorPayload().id}`),
    );
    expect(history).toHaveTextContent(huge);
    const path = history.querySelector("path")?.getAttribute("d") ?? "";
    expect(path).not.toContain("NaN");
    expect(path).not.toContain("Infinity");
  });

  it("records a measurement with the value exactly as typed", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    await waitFor(() =>
      expect(
        screen.getByTestId(`measurement-record-form-${indicatorPayload().id}`),
      ).toBeInTheDocument(),
    );
    await user.type(screen.getByLabelText(/Valor medido/i), "9.10");
    await user.click(screen.getByRole("button", { name: /Registrar medição/i }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/measurements") && c.method === "POST"),
      ).toBe(true),
    );
    const posted = calls.find(
      (c) => c.url.includes("/measurements") && c.method === "POST",
    );
    expect(posted?.body).toMatchObject({
      indicator_definition_id: indicatorPayload().id,
      value: "9.10",
    });
  });

  it("asks for a reason before correcting a measurement", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [measurementRecordPayload()],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const form = await waitFor(() =>
      screen.getByTestId(`measurement-correction-form-${indicatorPayload().id}`),
    );
    expect(form).toHaveTextContent(/não apaga a anterior/i);
    expect(screen.getByLabelText(/Motivo da correção/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Corrigir medição/i }),
    ).toBeDisabled();
  });

  it("flags an overdue measurement on the indicator", async () => {
    installFetch({
      summary: measurementSummaryPayload({
        measurement_posture: "overdue",
        target_posture: "not_met",
        evaluations: [
          targetEvaluationPayload({
            state: "target_not_met",
            is_measurement_overdue: true,
            headline: "Retrabalho na linha 2: meta não atingida no prazo (14.00 peças/semana).",
          }),
        ],
      }),
      indicators: [indicatorPayload()],
      records: [measurementRecordPayload()],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const state = await waitFor(() =>
      screen.getByTestId(`measurement-state-${indicatorPayload().id}`),
    );
    expect(state).toHaveTextContent("Meta não atingida no prazo");
    expect(state).toHaveTextContent("Medição atrasada");
  });

  it("hides every measurement form for reader-only profiles", async () => {
    installFetch({
      router: (input) =>
        urlOf(input).includes("/organizations/me/memberships")
          ? membershipResponse(["reader"])
          : undefined,
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [measurementRecordPayload()],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    await waitFor(() =>
      expect(
        screen.getByTestId(`measurement-indicator-${indicatorPayload().id}`),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("measurement-plan-form")).toBeNull();
    expect(screen.queryByTestId("measurement-add-indicator")).toBeNull();
    expect(
      screen.queryByTestId(`measurement-record-form-${indicatorPayload().id}`),
    ).toBeNull();
    expect(
      screen.queryByTestId(`measurement-correction-form-${indicatorPayload().id}`),
    ).toBeNull();
  });

  it("scopes measurement cache keys to the active organization", async () => {
    installFetch({
      summary: measurementSummaryPayload(),
      indicators: [indicatorPayload()],
      records: [measurementRecordPayload()],
    });
    const user = userEvent.setup();
    const { queryClient } = renderCard();
    await enterApp(user);

    await waitFor(() =>
      expect(
        screen.getByTestId(`measurement-indicator-${indicatorPayload().id}`),
      ).toBeInTheDocument(),
    );

    const keys = executionQueryKeys(queryClient);
    expect(keys.length).toBeGreaterThan(0);
    for (const key of keys) expect(key[1]).toBe(ORG_ID);
    expect(keys.some((key) => key[3] === "measurement")).toBe(true);
    expect(keys.some((key) => key[3] === "evidence")).toBe(true);
  });
});

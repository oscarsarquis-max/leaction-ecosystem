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
  evidenceLinkPayload,
  evidencePayload,
  expectNoVisibleUuid,
  jsonResponse,
  membershipResponse,
  methodOf,
  ORG_ID,
  OWNER_ID,
  PLAN_ID,
  renderExecution,
  SPRINT_ID,
  stubMatchMedia,
  urlOf,
} from "@/test/executionHarness";

const ROUTE = "/execution/cards/:actionItemId";
const OTHER_EVIDENCE_ID = "17171717-1717-4717-8717-171717171717";

const calls: { url: string; method: string }[] = [];

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
  options: { router?: Router; links?: unknown[]; evidences?: unknown[] } = {},
) {
  const links = options.links ?? [];
  const evidences = options.evidences ?? [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      const method = methodOf(input, init);
      calls.push({ url, method });

      const custom = options.router?.(input, init);
      if (custom) return custom;

      if (url.includes("/organizations/me/memberships")) return membershipResponse();
      if (url.includes("/organizations/current/members")) return jsonResponse([]);
      if (url.includes("/organizations/current/evidence-links")) {
        // The server resolves each link into an attachment, so the browser
        // never has to read the evidences one by one.
        return jsonResponse(
          (links as { evidence_id: string }[]).map((link) => ({
            link,
            evidence:
              (evidences as { id: string }[]).find(
                (e) => e.id === link.evidence_id,
              ) ?? null,
          })),
        );
      }
      if (url.includes("/measurement-summary")) return jsonResponse({}, 404);
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

describe("CardDetailPage — evidências", () => {
  beforeEach(() => {
    calls.length = 0;
    resetConfigCache();
    resetQmindClient();
    vi.stubGlobal("matchMedia", vi.fn(stubMatchMedia(false)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("explains what to do when no evidence is attached yet", async () => {
    installFetch();
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const list = await waitFor(() => screen.getByTestId("execution-evidence-list"));
    expect(list).toHaveTextContent(/Nenhuma evidência anexada a esta ação ainda/i);
    expect(screen.getByTestId("execution-evidence-upload")).toBeInTheDocument();
  });

  it("describes attached evidence by type, situation and date — never by identifier", async () => {
    installFetch({
      links: [
        evidenceLinkPayload(),
        evidenceLinkPayload({
          id: "18181818-1818-4818-8818-181818181818",
          evidence_id: OTHER_EVIDENCE_ID,
        }),
      ],
      evidences: [
        evidencePayload(),
        evidencePayload({
          id: OTHER_EVIDENCE_ID,
          content_type: "image/png",
          status: "quarantined",
          byte_size: 4096,
        }),
      ],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const list = await waitFor(() => screen.getByTestId("execution-evidence-list"));
    await waitFor(() => expect(list).toHaveTextContent("Documento PDF"));
    expect(list).toHaveTextContent("Aprovada");
    expect(list).toHaveTextContent("Imagem");
    expect(list).toHaveTextContent(/Recebida, aguardando verificação/i);
    expect(list.textContent ?? "").not.toContain("secret-object-key");
    expectNoVisibleUuid();
  });

  it("requests only the links of this action, without removed history", async () => {
    installFetch();
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("execution-evidence-list")).toBeInTheDocument(),
    );
    const linkCall = calls.find((c) =>
      c.url.includes("/organizations/current/evidence-links"),
    );
    expect(linkCall?.url).toContain("target_type=action_item");
    expect(linkCall?.url).toContain(`target_id=${ACTION_ID}`);
    expect(linkCall?.url).toContain("include_removed=false");
  });

  it("reads the attachments in a single request", async () => {
    installFetch({
      links: [
        evidenceLinkPayload(),
        evidenceLinkPayload({
          id: "18181818-1818-4818-8818-181818181818",
          evidence_id: OTHER_EVIDENCE_ID,
        }),
      ],
      evidences: [evidencePayload(), evidencePayload({ id: OTHER_EVIDENCE_ID })],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const list = await waitFor(() => screen.getByTestId("execution-evidence-list"));
    await waitFor(() => expect(list).toHaveTextContent("Documento PDF"));
    // One call for the attachments, and no follow-up read per evidence.
    expect(
      calls.filter((c) => c.url.includes("/organizations/current/evidence-links")),
    ).toHaveLength(1);
    expect(calls.filter((c) => /\/evidences\/[0-9a-f-]+$/.test(c.url))).toHaveLength(
      0,
    );
  });

  it("hides the upload control for reader-only profiles", async () => {
    installFetch({
      router: (input) =>
        urlOf(input).includes("/organizations/me/memberships")
          ? membershipResponse(["reader"])
          : undefined,
      links: [evidenceLinkPayload()],
      evidences: [evidencePayload()],
    });
    const user = userEvent.setup();
    renderCard();
    await enterApp(user);

    const list = await waitFor(() => screen.getByTestId("execution-evidence-list"));
    await waitFor(() => expect(list).toHaveTextContent("Documento PDF"));
    expect(screen.queryByTestId("execution-evidence-upload")).toBeNull();
    expect(
      screen.getByText(/somente leitura — peça a alguém com permissão de execução para anexar/i),
    ).toBeInTheDocument();
  });
});

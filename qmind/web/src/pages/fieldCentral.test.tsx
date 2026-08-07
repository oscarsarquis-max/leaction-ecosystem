import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AssessmentWorkPage } from "@/pages/AssessmentWorkPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext } from "@/api/tenantContext";
import { enterApp } from "@/test/enterApp";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const AID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const MEMBERSHIP = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function urlOf(input: RequestInfo | URL) {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

function membership(roles: string[]) {
  return [
    {
      id: MEMBERSHIP,
      organization_id: ORG,
      organization_name: "Org Campo",
      roles,
      status: "active",
    },
  ];
}

function assessment(status: string) {
  return {
    id: AID,
    organization_id: ORG,
    assessment_model_id: "11111111-1111-4111-8111-111111111111",
    standard_version_id: "22222222-2222-4222-8222-222222222222",
    type: "diagnosis",
    status,
    lead_membership_id: MEMBERSHIP,
    started_at: status === "in_progress" ? "2026-07-01T12:00:00.000Z" : null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

function mockApi(opts: {
  status: string;
  roles?: string[];
  interviews?: unknown[];
  scheduleItems?: unknown[];
}) {
  const roles = opts.roles ?? ["org_admin"];
  const interviews = opts.interviews ?? [];
  const scheduleItems = opts.scheduleItems ?? [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = urlOf(input);
      if (url.includes("/memberships") || url.includes("/me/memberships")) {
        return json(membership(roles));
      }
      if (url.includes(`/assessments/${AID}/scopes`)) return json([]);
      if (url.includes(`/assessments/${AID}/team`)) return json([]);
      if (url.includes(`/assessments/${AID}/interviews`)) return json(interviews);
      if (url.includes(`/assessments/${AID}/evidences`)) return json([]);
      if (url.includes(`/assessments/${AID}/questions`)) return json([]);
      if (url.includes(`/assessments/${AID}/audit-plan/schedule`)) {
        return json({
          assessment_id: AID,
          timezone: "America/Sao_Paulo",
          field_period_start: null,
          field_period_end: null,
          has_opening_meeting: true,
          has_closing_meeting: false,
          items: scheduleItems,
        });
      }
      if (url.includes(`/assessments/${AID}/audit-plan`)) {
        return json({
          plan_status: "ready",
          modality: "diagnosis",
          scope_text: "Escopo",
          readiness: { ready: true, percent: 100, items: [], blockers: [] },
          processes: [],
        });
      }
      if (url.includes(`/assessments/${AID}`) && !url.includes("/audit-plan")) {
        return json(assessment(opts.status));
      }
      return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
    }),
  );
}

function renderWork() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <OrganizationProvider>
          <MemoryRouter initialEntries={[`/assessments/${AID}/work`]}>
            <Routes>
              <Route element={<AppShell />}>
                <Route
                  path="assessments/:assessmentId/work"
                  element={<AssessmentWorkPage />}
                />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("Central de Campo (/work)", () => {
  beforeEach(() => {
    resetQmindClient();
    resetTenantContext();
    resetConfigCache();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("draft orienta ao Plano", async () => {
    const user = userEvent.setup();
    mockApi({ status: "draft" });
    renderWork();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("field-draft-redirect")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("field-cta-audit-plan")).toBeInTheDocument();
    expect(screen.queryByTestId("field-today-agenda")).toBeNull();
  });

  it("planned mostra handoff sem agenda de execução", async () => {
    const user = userEvent.setup();
    mockApi({
      status: "planned",
      scheduleItems: [
        {
          id: "open-1",
          kind: "meeting",
          plan_activity_kind: "opening_meeting",
          title: "Abertura",
          status: "scheduled",
          starts_at: new Date().toISOString(),
          interview_id: null,
        },
      ],
    });
    renderWork();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("field-planned-handoff")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("field-next-action")).toHaveTextContent(/abertura|plano|iniciar/i);
    expect(screen.queryByTestId("field-central")).toBeNull();
    expect(screen.queryByTestId("field-execution")).toBeNull();
  });

  it("in_progress abre central com próxima ação e agenda", async () => {
    const user = userEvent.setup();
    const today = new Date().toISOString();
    mockApi({
      status: "in_progress",
      interviews: [
        {
          id: "iv-1",
          title: "Entrevista TI",
          status: "confirmed",
          process_name: "TI",
          scheduled_at: today,
          mode: "onsite",
        },
      ],
      scheduleItems: [
        {
          id: "sch-1",
          kind: "interview",
          plan_activity_kind: "interview",
          title: "Entrevista TI",
          status: "confirmed",
          starts_at: today,
          interview_id: "iv-1",
          process_name: "TI",
          preparation: "Levar organograma",
        },
      ],
    });
    renderWork();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("field-central")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("field-next-action")).toBeInTheDocument();
    expect(screen.getByTestId("field-today-agenda")).toBeInTheDocument();
    expect(screen.getByTestId("field-progress")).toBeInTheDocument();
    expect(screen.getByTestId("field-evidence")).toBeInTheDocument();
    expect(screen.getByTestId("field-assistant-context")).toBeInTheDocument();
    // UUID pode existir em href/contexto oculto; não nos rótulos visíveis.
    expect(screen.getByTestId("page-header")).toHaveTextContent(/Central de Campo/);
    expect(screen.getByTestId("page-header")).not.toHaveTextContent(AID);
    expect(screen.getByTestId("field-next-action")).not.toHaveTextContent(AID);
    expect(screen.getByTestId("field-today-agenda")).not.toHaveTextContent(AID);
  });

  it("analysis mostra resumo somente leitura", async () => {
    const user = userEvent.setup();
    mockApi({
      status: "analysis",
      interviews: [
        {
          id: "iv-1",
          title: "Feita",
          status: "completed",
          process_name: "TI",
        },
      ],
    });
    renderWork();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("field-readonly")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("field-next-action")).toBeInTheDocument();
    expect(screen.queryByTestId("field-unplanned")).toBeNull();
  });

  it("reader não vê mutações de atividade não planejada", async () => {
    const user = userEvent.setup();
    mockApi({ status: "in_progress", roles: ["reader"] });
    renderWork();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("field-central")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("field-unplanned")).toBeNull();
  });
});

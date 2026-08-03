import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AssessmentDetailPage } from "@/pages/AssessmentDetailPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext } from "@/api/tenantContext";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const AID = "44444444-4444-4444-8444-444444444444";
const MEMBERSHIP = "55555555-5555-4555-8555-555555555555";
const OTHER = "66666666-6666-4666-8666-666666666666";
const PLAN = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const ITEM = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const FID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function urlOf(input: RequestInfo | URL) {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

function methodOf(input: RequestInfo | URL, init?: RequestInit) {
  return (init?.method || (input instanceof Request ? input.method : "GET")).toUpperCase();
}

function assessmentJson(status = "actions") {
  return {
    id: AID,
    organization_id: ORG,
    assessment_model_id: "11111111-1111-4111-8111-111111111111",
    standard_version_id: "22222222-2222-4222-8222-222222222222",
    maturity_model_id: "a1000000-0000-4000-8000-000000000001",
    type: "diagnosis",
    status,
    lead_membership_id: MEMBERSHIP,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function basePlan(overrides: Record<string, unknown> = {}) {
  return {
    id: PLAN,
    organization_id: ORG,
    assessment_id: AID,
    status: "draft",
    empty_plan_rationale: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function baseItem(overrides: Record<string, unknown> = {}) {
  return {
    id: ITEM,
    organization_id: ORG,
    action_plan_id: PLAN,
    finding_id: FID,
    action_kind: "corrective_action",
    description: "Corrigir NC de calibração",
    owner_membership_id: MEMBERSHIP,
    due_at: "2020-01-01T12:00:00Z",
    status: "implemented",
    is_overdue: false,
    efficacy_required: true,
    source_finding_withdrawn: true,
    validated_by: null,
    efficacy_confirmed_by: null,
    cancel_reason: null,
    reject_reason: null,
    efficacy_fail_reason: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <OrganizationProvider>
          <MemoryRouter initialEntries={[`/assessments/${AID}`]}>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="assessments/:assessmentId" element={<AssessmentDetailPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("action plan UI", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    resetTenantContext();
    vi.stubEnv("VITE_ENVIRONMENT", "local");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    vi.stubEnv("VITE_API_BASE_URL", "");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("shows overdue + withdrawn, blocks owner validate (SoD), and gates double activate", async () => {
    const user = userEvent.setup();
    let plan = basePlan({ status: "active" });
    let item = baseItem();
    let validateCalls = 0;
    let activateCalls = 0;
    let assessmentStatus = "actions";

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = urlOf(input);
        const method = methodOf(input, init);
        if (url.includes("/memberships")) {
          return json([
            {
              id: MEMBERSHIP,
              organization_id: ORG,
              organization_name: "Org A",
              roles: ["org_admin"],
              status: "active",
            },
          ]);
        }
        if (
          url.includes("/scopes") ||
          url.includes("/questions") ||
          url.includes("/interviews") ||
          url.includes("/evidences") ||
          url.includes("/maturity-assessments")
        ) {
          return json([]);
        }
        if (url.includes("/team")) {
          return json([{ membership_id: MEMBERSHIP, role: "lead" }]);
        }
        if (url.includes("/api/v1/findings") && method === "GET") {
          return json([
            {
              id: FID,
              status: "withdrawn",
              finding_type: "nonconformity",
              title: "NC calibração",
              body: "x",
              author_membership_id: MEMBERSHIP,
            },
          ]);
        }
        if (url.includes("/action-plans") && method === "GET" && !url.includes("/items")) {
          return json([plan]);
        }
        if (url.includes(`/action-plans/${PLAN}/items`) && method === "GET") {
          return json([item]);
        }
        if (url.includes(`/action-plans/${PLAN}/transitions/activate`) && method === "POST") {
          activateCalls += 1;
          await new Promise((r) => setTimeout(r, 40));
          plan = { ...plan, status: "active" };
          return json({
            plan,
            from_status: "draft",
            to_status: "active",
            event: "activate",
          });
        }
        if (url.includes(`/action-items/${ITEM}/transitions/validate`) && method === "POST") {
          validateCalls += 1;
          return json(
            {
              code: "sod_violation",
              message: "Validator must differ from action owner",
              correlation_id: "corr-sod-act",
            },
            403,
          );
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json(assessmentJson(assessmentStatus));
        }
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );

    renderPage();

    await waitFor(() => expect(screen.getByTestId("action-plan")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByTestId("action-plan-workspace")).toBeInTheDocument());

    await user.click(screen.getByTestId(`action-item-select-${ITEM}`));
    expect(screen.getByTestId("action-withdrawn-banner")).toBeInTheDocument();
    expect(screen.getByTestId("action-item-overdue-badge")).toBeInTheDocument();
    expect(screen.getByTestId("action-sod-banner")).toBeInTheDocument();

    const validateBtn = screen.getByTestId("action-item-validate");
    expect(validateBtn).toBeDisabled();
    await user.click(validateBtn);
    expect(validateCalls).toBe(0);
  });

  it("creates plan + item, activates once on double click, conflict reloads", async () => {
    const user = userEvent.setup();
    let plans: ReturnType<typeof basePlan>[] = [];
    let items: ReturnType<typeof baseItem>[] = [];
    let activateCalls = 0;
    let listPlanCalls = 0;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = urlOf(input);
        const method = methodOf(input, init);
        if (url.includes("/memberships")) {
          return json([
            {
              id: MEMBERSHIP,
              organization_id: ORG,
              organization_name: "Org A",
              roles: ["quality_manager"],
              status: "active",
            },
          ]);
        }
        if (
          url.includes("/scopes") ||
          url.includes("/questions") ||
          url.includes("/interviews") ||
          url.includes("/evidences") ||
          url.includes("/maturity-assessments")
        ) {
          return json([]);
        }
        if (url.includes("/team")) {
          return json([
            { membership_id: MEMBERSHIP, role: "lead" },
            { membership_id: OTHER, role: "member" },
          ]);
        }
        if (url.includes("/api/v1/findings") && method === "GET") {
          return json([
            {
              id: FID,
              status: "approved",
              finding_type: "nonconformity",
              title: "NC processo",
              body: "y",
              author_membership_id: OTHER,
            },
          ]);
        }
        if (
          url.endsWith("/action-plans") &&
          method === "POST" &&
          !url.includes("/items") &&
          !url.includes("/transitions")
        ) {
          const created = basePlan();
          plans = [created];
          return json(created, 201);
        }
        if (
          url.includes("/action-plans") &&
          method === "GET" &&
          !url.includes("/items") &&
          !url.includes("/transitions")
        ) {
          listPlanCalls += 1;
          return json(plans);
        }
        if (url.includes(`/action-plans/${PLAN}/items`) && method === "POST") {
          const body =
            typeof init?.body === "string"
              ? JSON.parse(init.body)
              : input instanceof Request
                ? await input.clone().json()
                : {};
          const created = baseItem({
            status: "open",
            source_finding_withdrawn: false,
            due_at: body.due_at,
            description: body.description,
            owner_membership_id: body.owner_membership_id,
            finding_id: body.finding_id,
            is_overdue: false,
          });
          items = [created];
          return json(created, 201);
        }
        if (url.includes(`/action-plans/${PLAN}/items`) && method === "GET") {
          return json(items);
        }
        if (url.includes(`/action-plans/${PLAN}/transitions/activate`) && method === "POST") {
          activateCalls += 1;
          await new Promise((r) => setTimeout(r, 50));
          if (activateCalls === 1) {
            plans = [{ ...plans[0]!, status: "active" }];
            return json({
              plan: plans[0],
              from_status: "draft",
              to_status: "active",
              event: "activate",
            });
          }
          return json(
            {
              code: "invalid_transition",
              message: "activate requires draft",
              correlation_id: "corr-act-dup",
            },
            409,
          );
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json(assessmentJson("actions"));
        }
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );

    renderPage();
    await waitFor(() => expect(screen.getByTestId("action-create-plan")).toBeInTheDocument());
    await user.click(screen.getByTestId("action-create-plan"));
    await waitFor(() => expect(screen.getByTestId("action-create-item-form")).toBeInTheDocument());

    await user.selectOptions(screen.getByTestId("action-item-finding"), FID);
    await user.clear(screen.getByTestId("action-item-description"));
    await user.type(screen.getByTestId("action-item-description"), "Ação de contenção");
    await user.selectOptions(screen.getByTestId("action-item-owner"), OTHER);
    await user.type(screen.getByTestId("action-item-due"), "2030-06-15T10:00");
    await user.click(screen.getByTestId("action-create-item"));

    await waitFor(() => expect(screen.getByTestId(`action-item-select-${ITEM}`)).toBeInTheDocument());

    const activate = screen.getByTestId("action-activate");
    await Promise.all([user.click(activate), user.click(activate)]);
    await waitFor(() =>
      expect(screen.getByTestId("action-plan-status")).toHaveTextContent("ativo"),
    );
    expect(activateCalls).toBe(1);
    expect(listPlanCalls).toBeGreaterThan(1);
  });

  it("non-owner validator can confirm efficacy; open_actions from analysis", async () => {
    const user = userEvent.setup();
    let assessmentStatus = "analysis";
    let plan = basePlan({ status: "active" });
    let item = baseItem({
      owner_membership_id: OTHER,
      status: "validated",
      source_finding_withdrawn: false,
      due_at: "2030-01-01T12:00:00Z",
    });
    let openCalls = 0;
    let efficacyCalls = 0;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = urlOf(input);
        const method = methodOf(input, init);
        if (url.includes("/memberships")) {
          return json([
            {
              id: MEMBERSHIP,
              organization_id: ORG,
              organization_name: "Org A",
              roles: ["org_admin"],
              status: "active",
            },
          ]);
        }
        if (
          url.includes("/scopes") ||
          url.includes("/team") ||
          url.includes("/questions") ||
          url.includes("/interviews") ||
          url.includes("/evidences") ||
          url.includes("/maturity-assessments") ||
          url.includes("/findings")
        ) {
          return json([]);
        }
        if (url.includes("/transitions/open_actions") && method === "POST") {
          openCalls += 1;
          assessmentStatus = "actions";
          return json({
            ...assessmentJson("actions"),
            from_status: "analysis",
            to_status: "actions",
            event: "open_actions",
          });
        }
        if (url.includes("/action-plans") && method === "GET" && !url.includes("/items")) {
          return json([plan]);
        }
        if (url.includes(`/action-plans/${PLAN}/items`) && method === "GET") {
          return json([item]);
        }
        if (
          url.includes(`/action-items/${ITEM}/transitions/confirm_efficacy`) &&
          method === "POST"
        ) {
          efficacyCalls += 1;
          await new Promise((r) => setTimeout(r, 40));
          item = { ...item, status: "done" };
          return json({
            item,
            from_status: "validated",
            to_status: "done",
            event: "confirm_efficacy",
          });
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json(assessmentJson(assessmentStatus));
        }
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );

    renderPage();
    await waitFor(() => expect(screen.getByTestId("action-open-actions")).toBeInTheDocument());
    await user.click(screen.getByTestId("action-open-actions"));
    await waitFor(() => expect(openCalls).toBe(1));

    await waitFor(() => expect(screen.getByTestId(`action-item-select-${ITEM}`)).toBeInTheDocument());
    await user.click(screen.getByTestId(`action-item-select-${ITEM}`));
    expect(screen.queryByTestId("action-sod-banner")).toBeNull();

    const confirm = screen.getByTestId("action-item-confirm-efficacy");
    expect(confirm).not.toBeDisabled();
    await Promise.all([user.click(confirm), user.click(confirm)]);
    await waitFor(() =>
      expect(screen.getByTestId("action-item-status")).toHaveTextContent("concluída"),
    );
    expect(efficacyCalls).toBe(1);
  });
});

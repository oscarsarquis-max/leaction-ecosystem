/**
 * Shared scaffolding for the Agile Action Execution Workspace suites.
 * Keeps the fetch routing table and board fixtures in one place so each
 * suite only declares what it actually asserts on.
 */
import { createElement, type ReactNode } from "react";
import { expect } from "vitest";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import type { BoardCard, BoardOut, SprintMetrics } from "@/execution/api";

export const ORG_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
export const OTHER_ORG_ID = "aaaaaaaa-aaaa-4aaa-8aaa-bbbbbbbbbbbb";
export const OWNER_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
export const ACTION_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
export const PLAN_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
export const SQUAD_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
export const SPRINT_ID = "ffffffff-ffff-4fff-8fff-ffffffffffff";
export const MEASUREMENT_PLAN_ID = "12121212-1212-4212-8212-121212121212";
export const INDICATOR_ID = "13131313-1313-4313-8313-131313131313";
export const MEASUREMENT_ID = "14141414-1414-4414-8414-141414141414";
export const EVIDENCE_ID = "15151515-1515-4515-8515-151515151515";
export const EVIDENCE_LINK_ID = "16161616-1616-4616-8616-161616161616";

/** Canonical UUID shape — used by the "no operational id on screen" guards. */
export const UUID_RE =
  /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/;

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function noContentResponse(): Response {
  return new Response(null, { status: 204 });
}

export function membershipResponse(
  roles: string[] = ["org_admin"],
  organizationId = ORG_ID,
): Response {
  return jsonResponse([
    {
      id: "mem-1",
      organization_id: organizationId,
      organization_name: "Org Teste",
      roles,
      status: "active",
    },
  ]);
}

export function urlOf(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

export function methodOf(input: RequestInfo | URL, init?: RequestInit): string {
  const fromInit = init?.method;
  if (fromInit) return fromInit.toUpperCase();
  if (input instanceof Request) return input.method.toUpperCase();
  return "GET";
}

export async function bodyOf(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<unknown> {
  const raw =
    (init?.body as string | undefined) ??
    (input instanceof Request ? await input.clone().text() : undefined);
  if (!raw) return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

const COLUMN_KEYS = [
  "backlog",
  "selected",
  "in_progress",
  "implemented",
  "validated",
  "ineffective",
  "done",
] as const;

export function boardCard(overrides: Partial<BoardCard> = {}): BoardCard {
  return {
    action_item_id: ACTION_ID,
    action_plan_id: PLAN_ID,
    description: "Implementar controle de documentos",
    action_kind: "improvement",
    status: "in_progress",
    owner_membership_id: OWNER_ID,
    owner_display_name: "Ana Silva",
    owner_email: "ana@example.com",
    due_at: new Date(Date.now() + 86_400_000).toISOString(),
    is_overdue: false,
    priority: "high",
    estimate_points: 3,
    sprint_id: null,
    sprint_name: "Sprint 1",
    squad_id: null,
    squad_name: "Qualidade",
    has_open_impediment: false,
    has_blocking_dependency: false,
    open_impediment_count: 0,
    blocking_dependency_count: 0,
    latest_check_in_at: new Date().toISOString(),
    latest_check_in_health: "on_track",
    source_analysis_run_id: null,
    source_finding_code: null,
    source_analysis_is_stale: null,
    assessment_id: null,
    improvement_case_id: null,
    finding_id: null,
    card_id: null,
    position: 0,
    evidence_count_total: 0,
    evidence_count_approved: 0,
    indicator_count: 0,
    measurement_posture: "not_planned",
    target_posture: "unknown",
    ...overrides,
  };
}

export function boardPayload(
  cardsByColumn: Partial<Record<(typeof COLUMN_KEYS)[number], BoardCard[]>> = {},
  overrides: Partial<Omit<BoardOut, "columns">> = {},
): BoardOut {
  return {
    squad_id: null,
    sprint_id: null,
    active_sprint_id: null,
    wip_limit_in_progress: null,
    wip_signal: false,
    in_progress_count: 0,
    ...overrides,
    columns: COLUMN_KEYS.map((key) => ({
      key,
      label: key,
      cards: cardsByColumn[key] ?? [],
    })),
  };
}

export function sprintPayload(overrides: Record<string, unknown> = {}) {
  const now = Date.now();
  return {
    id: SPRINT_ID,
    organization_id: ORG_ID,
    squad_id: SQUAD_ID,
    name: "Sprint 1",
    goal: "Fechar achados críticos",
    starts_at: new Date(now - 2 * 86_400_000).toISOString(),
    ends_at: new Date(now + 5 * 86_400_000).toISOString(),
    timezone: "America/Sao_Paulo",
    status: "planned",
    capacity_points: null,
    wip_limit_in_progress: null,
    activation_skip_cards_rationale: null,
    created_by: OWNER_ID,
    activated_by: null,
    closed_by: null,
    created_at: new Date(now).toISOString(),
    activated_at: null,
    closed_at: null,
    updated_at: new Date(now).toISOString(),
    ...overrides,
  };
}

export function squadPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: SQUAD_ID,
    organization_id: ORG_ID,
    name: "Squad Qualidade",
    purpose: "Melhorias do SGQ",
    status: "active",
    default_sprint_length_days: 14,
    created_by: OWNER_ID,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

export function sprintMetricsPayload(
  overrides: Partial<SprintMetrics> = {},
): SprintMetrics {
  return {
    sprint_id: SPRINT_ID,
    squad_id: SQUAD_ID,
    planned_cards: 6,
    completed_cards: 4,
    carry_over_cards: 2,
    in_progress_count: 3,
    open_impediments: 1,
    overdue_actions: 1,
    throughput: 4,
    goal: "Fechar achados críticos",
    status: "active",
    average_cycle_time_hours: 18,
    median_cycle_time_hours: 30,
    oldest_in_progress_age_hours: 120,
    blocked_time_hours: 12,
    cards_without_recent_check_in: 2,
    check_in_stale_window_hours: 72,
    review_outcome: "Meta parcialmente atingida",
    ...overrides,
  };
}

export function measurementPlanPayload(overrides: Record<string, unknown> = {}) {
  const now = new Date().toISOString();
  return {
    id: MEASUREMENT_PLAN_ID,
    organization_id: ORG_ID,
    action_plan_id: PLAN_ID,
    assessment_id: null,
    improvement_case_id: null,
    objective: "Provar que o retrabalho caiu",
    owner_membership_id: OWNER_ID,
    owner_display_name: "Ana Silva",
    owner_email: "ana@example.com",
    review_cadence_days: null,
    next_review_at: null,
    status: "active",
    activated_by: OWNER_ID,
    activated_at: now,
    closed_by: null,
    closed_at: null,
    closure_reason: null,
    created_by: OWNER_ID,
    created_at: now,
    updated_at: now,
    indicator_count: 1,
    active_indicator_count: 1,
    ...overrides,
  };
}

export function indicatorPayload(overrides: Record<string, unknown> = {}) {
  const now = new Date().toISOString();
  return {
    id: INDICATOR_ID,
    organization_id: ORG_ID,
    measurement_plan_id: MEASUREMENT_PLAN_ID,
    code: "RETRABALHO-LINHA-2",
    name: "Retrabalho na linha 2",
    question: "Quantas peças voltam por semana?",
    owner_membership_id: OWNER_ID,
    owner_display_name: "Ana Silva",
    owner_email: "ana@example.com",
    value_type: "decimal",
    unit_kind: "custom",
    custom_unit_label: "peças/semana",
    currency_code: null,
    decimal_places: 2,
    unit_label: "peças/semana",
    direction: "lower_is_better",
    baseline_status: "recorded",
    baseline_value: "18.50",
    baseline_at: now,
    baseline_measurement_id: MEASUREMENT_ID,
    baseline_unavailable_reason: null,
    target_value: "9.25",
    target_min: null,
    target_max: null,
    target_due_at: null,
    measurement_frequency_days: 7,
    data_source: "",
    collection_method: "",
    status: "active",
    version: 1,
    lineage_id: INDICATOR_ID,
    supersedes_indicator_id: null,
    revision_reason: null,
    retired_reason: null,
    created_by: OWNER_ID,
    created_at: now,
    updated_at: now,
    measurement_count: 1,
    latest_value: "9.10",
    latest_measured_at: now,
    ...overrides,
  };
}

export function measurementRecordPayload(overrides: Record<string, unknown> = {}) {
  const now = new Date().toISOString();
  return {
    id: MEASUREMENT_ID,
    organization_id: ORG_ID,
    measurement_plan_id: MEASUREMENT_PLAN_ID,
    indicator_definition_id: INDICATOR_ID,
    measurement_kind: "observation",
    value: "9.10",
    measured_at: now,
    window_start: null,
    window_end: null,
    note: "Contagem semanal",
    collection_method: "",
    status: "active",
    supersedes_measurement_id: null,
    superseded_by_measurement_id: null,
    correction_reason: null,
    evidence_link_count: 0,
    verified_evidence_count: 0,
    substantiation: "none",
    recorded_by: OWNER_ID,
    recorded_at: now,
    ...overrides,
  };
}

export function targetEvaluationPayload(overrides: Record<string, unknown> = {}) {
  return {
    indicator_definition_id: INDICATOR_ID,
    indicator_code: "RETRABALHO-LINHA-2",
    indicator_name: "Retrabalho na linha 2",
    unit_kind: "custom",
    unit_label: "peças/semana",
    decimal_places: 2,
    direction: "lower_is_better",
    state: "target_met",
    baseline_status: "recorded",
    substantiation: "verified",
    baseline_value: "18.50",
    baseline_at: new Date().toISOString(),
    target_value: "9.25",
    target_min: null,
    target_max: null,
    target_due_at: null,
    latest_value: "9.10",
    latest_measured_at: new Date().toISOString(),
    latest_measurement_id: MEASUREMENT_ID,
    measurement_count: 1,
    evidence_link_count: 1,
    verified_evidence_count: 1,
    next_measurement_due_at: null,
    is_measurement_overdue: false,
    owner_membership_id: OWNER_ID,
    owner_display_name: "Ana Silva",
    headline: "Retrabalho na linha 2: meta atingida (9.10 peças/semana).",
    what_to_do_next:
      "Leve este resultado para a decisão de eficácia — a meta atingida é uma evidência, não a conclusão.",
    ...overrides,
  };
}

export function measurementSummaryPayload(overrides: Record<string, unknown> = {}) {
  return {
    action_plan_id: PLAN_ID,
    plan: measurementPlanPayload(),
    measurement_posture: "on_time",
    target_posture: "met",
    substantiation: "verified",
    baseline_status: "recorded",
    indicator_count: 1,
    overdue_indicator_count: 0,
    evaluations: [targetEvaluationPayload()],
    headline: "A ação tem medição que sustenta o resultado.",
    what_to_do_next: "Leve o resultado para a decisão de eficácia.",
    ...overrides,
  };
}

export function evidenceLinkPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: EVIDENCE_LINK_ID,
    organization_id: ORG_ID,
    evidence_id: EVIDENCE_ID,
    target_type: "action_item",
    target_id: ACTION_ID,
    created_at: new Date().toISOString(),
    removed_at: null,
    removed_by: null,
    removal_reason: null,
    ...overrides,
  };
}

export function evidencePayload(overrides: Record<string, unknown> = {}) {
  const now = new Date().toISOString();
  return {
    id: EVIDENCE_ID,
    organization_id: ORG_ID,
    assessment_id: null,
    improvement_case_id: null,
    status: "approved",
    classification: "confidential",
    content_type: "application/pdf",
    byte_size: 20480,
    content_hash: null,
    storage_key: "org/aaaa/evidence/secret-object-key.pdf",
    version_no: 1,
    legal_hold: false,
    upload_expires_at: null,
    collected_phase: null,
    collected_at: null,
    collected_by: null,
    collection_origin: null,
    created_at: now,
    updated_at: now,
    ...overrides,
  };
}

export function orgMemberPayload(overrides: Record<string, unknown> = {}) {
  return {
    membership_id: OWNER_ID,
    email: "ana@example.com",
    display_name: "Ana Silva",
    roles: ["quality_manager"],
    status: "active",
    ...overrides,
  };
}

/** Wide-viewport matchMedia so board tests get the drag layout by default. */
export function stubMatchMedia(compact = false) {
  return (query: string) => ({
    matches: compact && query.includes("max-width: 768px"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  });
}

export function renderExecution(
  ui: ReactNode,
  options: { path?: string; initial?: string } = {},
) {
  const path = options.path ?? "/execution";
  const initial = options.initial ?? path;
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const result = render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(
        AuthProvider,
        null,
        createElement(
          OrganizationProvider,
          null,
          createElement(
            MemoryRouter,
            { initialEntries: [initial] },
            createElement(
              Routes,
              null,
              createElement(
                Route,
                { element: createElement(AppShell) },
                createElement(Route, { path, element: ui }),
              ),
            ),
          ),
        ),
      ),
    ),
  );
  return { ...result, queryClient };
}

/** Query keys currently cached for the execution workspace. */
export function executionQueryKeys(queryClient: QueryClient): unknown[][] {
  return queryClient
    .getQueryCache()
    .getAll()
    .map((q) => q.queryKey as unknown[])
    .filter((key) => key[0] === "org" && key[2] === "execution");
}

/**
 * Visible text must never expose an operational identifier.
 * Attributes (route hrefs, option values, test ids) are out of scope.
 */
export function expectNoVisibleUuid(): void {
  expect(document.body.textContent ?? "").not.toMatch(UUID_RE);
}

/** Option labels of a select — used to prove pickers show names, not ids. */
export function optionLabels(select: HTMLElement): string[] {
  return [...(select as HTMLSelectElement).options].map((o) => o.textContent ?? "");
}

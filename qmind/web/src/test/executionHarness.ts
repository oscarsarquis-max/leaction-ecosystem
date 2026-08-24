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

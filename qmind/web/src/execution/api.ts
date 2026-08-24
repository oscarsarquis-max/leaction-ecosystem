/**
 * Agile Action Execution Workspace — thin wrappers over the generated SDK.
 *
 * Types come from `@qmind/api-client` (generated from backend/openapi/openapi.json).
 * Only board shapes are narrowed locally, so pages can rely on `columns[].cards`
 * always being an array instead of guarding the optional generated field.
 */
import type {
  ActionItemOut,
  ActionItemStatus,
  ActionKind,
  AgendaEventCreate,
  AgendaEventOut,
  BoardCardOut,
  BoardColumnOut,
  BoardMoveIn,
  BoardMoveOut,
  BoardOut as GeneratedBoardOut,
  CarryDecisionIn,
  CeremonyRecordCreate,
  CeremonyRecordOut,
  CheckInCreate,
  CheckInOut,
  DependencyCreate,
  DependencyOut,
  ImpedimentCreate,
  ImpedimentOut,
  ImpedimentUpdate,
  SprintCreate,
  SprintMetricsOut,
  SprintOut,
  SquadCreate,
  SquadMembershipCreate,
  SquadMembershipOut,
  SquadMembershipUpdate,
  SquadOut,
} from "@qmind/api-client";
import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";

export type {
  ActionItemStatus,
  ActionKind,
  AgendaEventOut,
  BoardCardOut,
  BoardMoveOut,
  CarryDecisionIn,
  CeremonyRecordCreate,
  CheckInCreate,
  DependencyCreate,
  ImpedimentCreate,
  ImpedimentUpdate,
  SprintCreate,
  SquadCreate,
  SquadMembershipCreate,
  SquadMembershipUpdate,
};

export type BoardColumnKey = BoardColumnOut["key"];
export type CardPriority = NonNullable<BoardCardOut["priority"]>;
export type SquadStatus = SquadOut["status"];
export type AgileRole = SquadMembershipOut["agile_role"];
export type SprintStatus = SprintOut["status"];
export type CheckInHealth = CheckInOut["health"];
export type ImpedimentSeverity = ImpedimentOut["severity"];
export type ImpedimentStatus = ImpedimentOut["status"];
export type DependencyType = DependencyOut["dependency_type"];
export type DependencyStatus = NonNullable<DependencyOut["status"]>;
export type CeremonyType = CeremonyRecordOut["ceremony_type"];
export type AgendaEventType = AgendaEventCreate["event_type"];

export type BoardCard = BoardCardOut;
export type BoardColumn = Omit<BoardColumnOut, "cards"> & { cards: BoardCard[] };
export type BoardOut = Omit<GeneratedBoardOut, "columns"> & {
  columns: BoardColumn[];
};

export type Squad = SquadOut;
export type SquadMembership = SquadMembershipOut;
export type Sprint = SprintOut;
export type SprintMetrics = SprintMetricsOut;
export type CheckIn = CheckInOut;
export type Impediment = ImpedimentOut;
export type Dependency = DependencyOut;
export type CeremonyRecord = CeremonyRecordOut;
export type ActionItemDetail = ActionItemOut;
export type BoardMovePayload = BoardMoveIn;

/** Ceremony types are also agenda event types — no separate mapping needed. */
export const CEREMONY_EVENT_TYPES: readonly CeremonyType[] = [
  "sprint_planning",
  "daily_check_in",
  "sprint_review",
  "retrospective",
];

export function isCeremonyEvent(
  event: Pick<AgendaEventOut, "event_type">,
): boolean {
  return (CEREMONY_EVENT_TYPES as readonly string[]).includes(event.event_type);
}

function normalizeBoard(board: GeneratedBoardOut | undefined): BoardOut {
  return {
    squad_id: board?.squad_id ?? null,
    sprint_id: board?.sprint_id ?? null,
    active_sprint_id: board?.active_sprint_id ?? null,
    wip_limit_in_progress: board?.wip_limit_in_progress ?? null,
    wip_signal: board?.wip_signal ?? false,
    in_progress_count: board?.in_progress_count ?? 0,
    columns: (board?.columns ?? []).map((column) => ({
      ...column,
      cards: column.cards ?? [],
    })),
  };
}

export function emptyBoard(): BoardOut {
  return normalizeBoard(undefined);
}

export async function fetchBoard(filters?: {
  squad_id?: string;
  sprint_id?: string;
}): Promise<BoardOut> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.getAgileBoard({
      query: {
        squad_id: filters?.squad_id ?? null,
        sprint_id: filters?.sprint_id ?? null,
      },
    });
    return normalizeBoard(res.data);
  });
}

export async function moveBoardCard(body: BoardMovePayload) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.moveAgileBoardCard({ body });
    return res.data as BoardMoveOut;
  });
}

export async function listSquads(status?: SquadStatus) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listAgileSquads({
      query: { status: status ?? null },
    });
    return res.data ?? [];
  });
}

export async function createSquad(body: SquadCreate) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createAgileSquad({ body });
    return res.data as Squad;
  });
}

export async function listSquadMemberships(squadId: string) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listAgileSquadMemberships({
      path: { squad_id: squadId },
    });
    return res.data ?? [];
  });
}

export async function addSquadMembership(
  squadId: string,
  body: SquadMembershipCreate,
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.addAgileSquadMembership({
      path: { squad_id: squadId },
      body,
    });
    return res.data as SquadMembership;
  });
}

export async function patchSquadMembership(
  squadId: string,
  membershipId: string,
  body: SquadMembershipUpdate,
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.patchAgileSquadMembership({
      path: { squad_id: squadId, membership_id: membershipId },
      body,
    });
    return res.data as SquadMembership;
  });
}

export async function listSprints(filters?: {
  squad_id?: string;
  status?: SprintStatus;
}) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listAgileSprints({
      query: {
        squad_id: filters?.squad_id ?? null,
        status: filters?.status ?? null,
      },
    });
    return res.data ?? [];
  });
}

export async function createSprint(body: SprintCreate) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createAgileSprint({ body });
    return res.data as Sprint;
  });
}

export async function activateSprint(
  sprintId: string,
  body?: { activation_skip_cards_rationale?: string | null },
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.activateAgileSprint({
      path: { sprint_id: sprintId },
      body: {
        activation_skip_cards_rationale:
          body?.activation_skip_cards_rationale ?? null,
      },
    });
    return res.data as Sprint;
  });
}

export async function completeSprint(
  sprintId: string,
  body: { carry_decisions: CarryDecisionIn[] },
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.completeAgileSprint({
      path: { sprint_id: sprintId },
      body,
    });
    return res.data as Sprint;
  });
}

export async function fetchSprintMetrics(sprintId: string) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.getAgileSprintMetrics({
      path: { sprint_id: sprintId },
    });
    return res.data as SprintMetrics;
  });
}

export async function listCeremonyRecords(
  sprintId: string,
  ceremonyType?: CeremonyType,
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listAgileCeremonyRecords({
      path: { sprint_id: sprintId },
      query: { ceremony_type: ceremonyType ?? null },
    });
    return res.data ?? [];
  });
}

export async function createCeremonyRecord(
  sprintId: string,
  body: CeremonyRecordCreate,
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createAgileCeremonyRecord({
      path: { sprint_id: sprintId },
      body,
    });
    return res.data as CeremonyRecord;
  });
}

export async function fetchActionItem(actionItemId: string) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.getActionItem({
      path: { item_id: actionItemId },
    });
    return res.data as ActionItemDetail;
  });
}

export async function listCheckIns(actionItemId: string) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listActionExecutionCheckIns({
      path: { action_item_id: actionItemId },
    });
    return res.data ?? [];
  });
}

export async function createCheckIn(actionItemId: string, body: CheckInCreate) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createActionExecutionCheckIn({
      path: { action_item_id: actionItemId },
      body,
    });
    return res.data as CheckIn;
  });
}

export async function listImpediments(actionItemId: string) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listActionImpediments({
      path: { action_item_id: actionItemId },
    });
    return res.data ?? [];
  });
}

export async function createImpediment(
  actionItemId: string,
  body: ImpedimentCreate,
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createActionImpediment({
      path: { action_item_id: actionItemId },
      body,
    });
    return res.data as Impediment;
  });
}

export async function patchImpediment(
  actionItemId: string,
  impedimentId: string,
  body: ImpedimentUpdate,
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.patchActionImpediment({
      path: { action_item_id: actionItemId, impediment_id: impedimentId },
      body,
    });
    return res.data as Impediment;
  });
}

/** Active dependencies only — removed rows stay out unless history is requested. */
export async function listDependencies(
  actionItemId: string,
  options?: { includeRemoved?: boolean },
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listActionDependencies({
      path: { action_item_id: actionItemId },
      query: { include_removed: options?.includeRemoved ?? false },
    });
    return res.data ?? [];
  });
}

export async function createDependency(
  actionItemId: string,
  body: DependencyCreate,
) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createActionDependency({
      path: { action_item_id: actionItemId },
      body,
    });
    return res.data as Dependency;
  });
}

/** Soft delete — backend flips status to `removed` and keeps history. */
export async function deleteDependency(
  actionItemId: string,
  dependencyId: string,
): Promise<void> {
  const client = getQmindClient();
  await withTenantGeneration(() =>
    client.api.deleteActionDependency({
      path: { action_item_id: actionItemId, dependency_id: dependencyId },
    }),
  );
}

/** Agenda events for a single day — used to build the sprint ceremony picker. */
export async function listAgendaEventsForDay(day: string) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listAgendaEvents({ query: { day } });
    return res.data ?? [];
  });
}

export async function createCeremonyAgendaEvent(body: {
  title: string;
  ceremony_type: CeremonyType;
  sprint_id: string;
  starts_at: string;
  description?: string;
}) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createAgendaEvent({
      body: {
        title: body.title,
        event_type: body.ceremony_type,
        sprint_id: body.sprint_id,
        starts_at: body.starts_at,
        description: body.description ?? "",
      },
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
    return res.data as AgendaEventOut;
  });
}

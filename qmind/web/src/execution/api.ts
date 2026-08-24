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
  EvidenceLinkOut,
  EvidenceLinkTargetType,
  EvidenceOut,
  ImpedimentCreate,
  ImpedimentOut,
  ImpedimentUpdate,
  IndicatorCreate,
  IndicatorOut,
  IndicatorReviseIn,
  MeasurementCorrectionIn,
  MeasurementPlanCreate,
  MeasurementPlanOut,
  MeasurementRecordCreate,
  MeasurementRecordOut,
  MeasurementSummaryOut,
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
  EvidenceLinkOut,
  EvidenceLinkTargetType,
  EvidenceOut,
  ImpedimentCreate,
  ImpedimentUpdate,
  IndicatorCreate,
  IndicatorOut,
  IndicatorReviseIn,
  MeasurementCorrectionIn,
  MeasurementPlanCreate,
  MeasurementPlanOut,
  MeasurementRecordCreate,
  MeasurementRecordOut,
  MeasurementSummaryOut,
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

export type MeasurementPosture = NonNullable<BoardCardOut["measurement_posture"]>;
export type TargetPosture = NonNullable<BoardCardOut["target_posture"]>;
export type MeasurementSummary = MeasurementSummaryOut;
export type MeasurementPlan = MeasurementPlanOut;
export type Indicator = IndicatorOut;
export type MeasurementRecord = MeasurementRecordOut;
export type TargetEvaluation = NonNullable<
  MeasurementSummaryOut["evaluations"]
>[number];
export type TargetEvaluationState = TargetEvaluation["state"];
export type SubstantiationLevel = TargetEvaluation["substantiation"];
export type IndicatorDirection = TargetEvaluation["direction"];
export type IndicatorUnitKind = TargetEvaluation["unit_kind"];
export type BaselineStatus = TargetEvaluation["baseline_status"];
export type MeasurementKind = MeasurementRecordOut["measurement_kind"];
export type EvidenceStatus = EvidenceOut["status"];

/**
 * An evidence link plus the evidence it points to. The link alone only knows
 * identifiers, and a person needs to read type, situation and date — so the
 * two reads are joined here instead of leaking ids into the UI.
 */
export type EvidenceAttachment = {
  link: EvidenceLinkOut;
  evidence: EvidenceOut | null;
};

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

/** Agenda events for a single day. */
export async function listAgendaEventsForDay(day: string) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listAgendaEvents({ query: { day } });
    return res.data ?? [];
  });
}

/**
 * Every agenda event of one sprint, in one request. Asking the sprint instead
 * of asking each day removes the timezone guesswork the day-by-day version
 * needed to avoid missing an event scheduled just past midnight.
 */
export async function listSprintAgendaEvents(sprintId: string) {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listAgileSprintAgendaEvents({
      path: { sprint_id: sprintId },
    });
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

/* --- Evidence attached to execution objects (ISOI-008) --- */

/**
 * Attachments of one object: link plus the document it points at, resolved by
 * the server in a single query. The browser no longer walks the links to read
 * each evidence, so a card with attachments costs exactly one round trip.
 */
export async function listEvidenceAttachments(
  targetType: EvidenceLinkTargetType,
  targetId: string,
): Promise<EvidenceAttachment[]> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listEvidenceLinksForTarget({
      query: { target_type: targetType, target_id: targetId, include_removed: false },
    });
    return (res.data ?? []).map((attachment) => ({
      link: attachment.link,
      evidence: attachment.evidence ?? null,
    }));
  });
}

/* --- Measurement of the result (ISOI-008) --- */

export async function fetchMeasurementSummary(
  actionPlanId: string,
): Promise<MeasurementSummaryOut> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.getActionPlanMeasurementSummary({
      path: { action_plan_id: actionPlanId },
    });
    return res.data as MeasurementSummaryOut;
  });
}

export async function createMeasurementPlan(
  body: MeasurementPlanCreate,
): Promise<MeasurementPlanOut> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createMeasurementPlan({
      body: { ...body, objective: body.objective ?? "" },
    });
    return res.data as MeasurementPlanOut;
  });
}

export async function activateMeasurementPlan(
  planId: string,
): Promise<MeasurementPlanOut> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.activateMeasurementPlan({
      path: { plan_id: planId },
    });
    return res.data as MeasurementPlanOut;
  });
}

export async function listIndicators(planId: string): Promise<IndicatorOut[]> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listIndicatorDefinitions({
      path: { plan_id: planId },
      query: { include_superseded: false },
    });
    return res.data ?? [];
  });
}

export async function createIndicator(
  planId: string,
  body: IndicatorCreate,
): Promise<IndicatorOut> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createIndicatorDefinition({
      path: { plan_id: planId },
      body,
    });
    return res.data as IndicatorOut;
  });
}

/** Registering a baseline after the fact is a revision — the reason is kept. */
export async function reviseIndicator(
  indicatorId: string,
  body: IndicatorReviseIn,
): Promise<IndicatorOut> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.reviseIndicatorDefinition({
      path: { indicator_id: indicatorId },
      body,
    });
    return res.data as IndicatorOut;
  });
}

export async function listMeasurementRecords(
  planId: string,
  options?: { indicatorId?: string },
): Promise<MeasurementRecordOut[]> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.listMeasurementRecords({
      path: { plan_id: planId },
      query: {
        indicator_definition_id: options?.indicatorId ?? null,
        include_superseded: false,
      },
    });
    return res.data ?? [];
  });
}

/**
 * Values travel as strings: a measurement is audit evidence and must reach the
 * server exactly as the person typed it, without a float rounding it first.
 */
export async function createMeasurementRecord(
  planId: string,
  body: MeasurementRecordCreate,
): Promise<MeasurementRecordOut> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.createMeasurementRecord({
      path: { plan_id: planId },
      body,
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
    return res.data as MeasurementRecordOut;
  });
}

/** A correction never rewrites history — it supersedes the previous reading. */
export async function correctMeasurementRecord(
  recordId: string,
  body: MeasurementCorrectionIn,
): Promise<MeasurementRecordOut> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.api.correctMeasurementRecord({
      path: { record_id: recordId },
      body,
    });
    return res.data as MeasurementRecordOut;
  });
}

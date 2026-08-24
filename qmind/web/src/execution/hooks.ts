import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { queryKeys } from "@/api/queryKeys";
import { withTenantGeneration, StaleTenantResponseError } from "@/api/qmindApi";
import {
  activateSprint,
  addSquadMembership,
  completeSprint,
  createCeremonyAgendaEvent,
  createCeremonyRecord,
  createCheckIn,
  createImpediment,
  createSquad,
  createSprint,
  createDependency,
  deleteDependency,
  emptyBoard,
  fetchActionItem,
  fetchBoard,
  fetchSprintMetrics,
  isCeremonyEvent,
  listAgendaEventsForDay,
  listCeremonyRecords,
  listCheckIns,
  listDependencies,
  listImpediments,
  listSquadMemberships,
  listSprints,
  listSquads,
  moveBoardCard,
  patchImpediment,
  patchSquadMembership,
  type AgendaEventOut,
  type AgileRole,
  type BoardMovePayload,
  type BoardOut,
  type SquadCreate,
  type SquadMembershipUpdate,
} from "@/execution/api";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

function orgKey(orgId: string | null, requestGeneration: number) {
  return requestGeneration;
}

export function useExecutionBoard(filters: { squadId?: string; sprintId?: string }) {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey: currentOrganizationId
      ? [
          ...queryKeys.executionBoard(currentOrganizationId, filters),
          orgKey(currentOrganizationId, requestGeneration),
        ]
      : ["org", "none", "execution-board"],
    enabled: !!currentOrganizationId,
    queryFn: async (): Promise<BoardOut> => {
      if (!currentOrganizationId) return emptyBoard();
      try {
        return await guardTenant(() =>
          fetchBoard({
            squad_id: filters.squadId,
            sprint_id: filters.sprintId,
          }),
        );
      } catch (e) {
        if (e instanceof StaleTenantResponseError) return emptyBoard();
        throw e;
      }
    },
  });
}

export function useMoveBoardCard() {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: (payload: BoardMovePayload) => guardTenant(() => moveBoardCard(payload)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        predicate: (q) =>
          q.queryKey[0] === "org" &&
          q.queryKey[1] === currentOrganizationId &&
          q.queryKey[2] === "execution",
      });
    },
  });
}

export function useSquads() {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey: currentOrganizationId
      ? [...queryKeys.executionSquads(currentOrganizationId), requestGeneration]
      : ["org", "none", "squads"],
    enabled: !!currentOrganizationId,
    queryFn: () => guardTenant(() => listSquads()),
  });
}

export function useCreateSquad() {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (body: SquadCreate) => guardTenant(() => createSquad(body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionSquads(currentOrganizationId),
      });
    },
  });
}

export function useSquadMemberships(squadId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && squadId
        ? [
            ...queryKeys.executionSquadMemberships(currentOrganizationId, squadId),
            requestGeneration,
          ]
        : ["org", "none", "squad-memberships"],
    enabled: !!currentOrganizationId && !!squadId,
    queryFn: () => guardTenant(() => listSquadMemberships(squadId!)),
  });
}

export function useAddSquadMembership(squadId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (body: { membership_id: string; agile_role: AgileRole }) =>
      guardTenant(() => addSquadMembership(squadId, body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionSquadMemberships(currentOrganizationId, squadId),
      });
    },
  });
}

export function usePatchSquadMembership(squadId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (args: { membershipId: string; body: SquadMembershipUpdate }) =>
      guardTenant(() => patchSquadMembership(squadId, args.membershipId, args.body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionSquadMemberships(currentOrganizationId, squadId),
      });
    },
  });
}

export function useSprints(squadId?: string) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey: currentOrganizationId
      ? [...queryKeys.executionSprints(currentOrganizationId, squadId), requestGeneration]
      : ["org", "none", "sprints"],
    enabled: !!currentOrganizationId,
    queryFn: () => guardTenant(() => listSprints(squadId ? { squad_id: squadId } : undefined)),
  });
}

export function useCreateSprint() {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (body: Parameters<typeof createSprint>[0]) =>
      guardTenant(() => createSprint(body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        predicate: (q) =>
          q.queryKey[0] === "org" &&
          q.queryKey[1] === currentOrganizationId &&
          q.queryKey[2] === "execution" &&
          q.queryKey[3] === "sprints",
      });
    },
  });
}

export function useActivateSprint() {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (args: { sprintId: string; rationale?: string }) =>
      guardTenant(() =>
        activateSprint(args.sprintId, {
          activation_skip_cards_rationale: args.rationale,
        }),
      ),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        predicate: (q) =>
          q.queryKey[0] === "org" &&
          q.queryKey[1] === currentOrganizationId &&
          q.queryKey[2] === "execution",
      });
    },
  });
}

export function useCompleteSprint() {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (args: {
      sprintId: string;
      carry_decisions: { action_item_id: string; decision: string }[];
    }) => guardTenant(() => completeSprint(args.sprintId, args)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        predicate: (q) =>
          q.queryKey[0] === "org" &&
          q.queryKey[1] === currentOrganizationId &&
          q.queryKey[2] === "execution",
      });
    },
  });
}

export function useSprintMetrics(sprintId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && sprintId
        ? [...queryKeys.executionSprintMetrics(currentOrganizationId, sprintId), requestGeneration]
        : ["org", "none", "sprint-metrics"],
    enabled: !!currentOrganizationId && !!sprintId,
    queryFn: () => guardTenant(() => fetchSprintMetrics(sprintId!)),
  });
}

export function useCeremonyRecords(sprintId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && sprintId
        ? [...queryKeys.executionCeremonies(currentOrganizationId, sprintId), requestGeneration]
        : ["org", "none", "ceremonies"],
    enabled: !!currentOrganizationId && !!sprintId,
    queryFn: () => guardTenant(() => listCeremonyRecords(sprintId!)),
  });
}

/** Inclusive UTC day range, defensive one day on each side for timezone drift. */
function sprintDayRange(startsAt: string, endsAt: string, maxDays = 45): string[] {
  const start = Date.parse(startsAt);
  const end = Date.parse(endsAt);
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return [];
  const DAY = 24 * 60 * 60 * 1000;
  const days: string[] = [];
  for (let t = start - DAY; t <= end + DAY && days.length < maxDays; t += DAY) {
    days.push(new Date(t).toISOString().slice(0, 10));
  }
  return days;
}

/**
 * Ceremony events already scheduled for a sprint, so the UI can offer a
 * pick-from-list instead of asking for an agenda event identifier.
 */
export function useSprintCeremonyEvents(
  sprint: { id: string; starts_at: string; ends_at: string } | undefined,
) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && sprint
        ? [
            ...queryKeys.executionCeremonyEvents(currentOrganizationId, sprint.id),
            requestGeneration,
          ]
        : ["org", "none", "ceremony-events"],
    enabled: !!currentOrganizationId && !!sprint,
    queryFn: async (): Promise<AgendaEventOut[]> => {
      if (!sprint) return [];
      const days = sprintDayRange(sprint.starts_at, sprint.ends_at);
      return guardTenant(async () => {
        const batches = await Promise.all(
          days.map((day) => listAgendaEventsForDay(day)),
        );
        const byId = new Map<string, AgendaEventOut>();
        for (const event of batches.flat()) {
          if (event.sprint_id === sprint.id && isCeremonyEvent(event)) {
            byId.set(event.id, event);
          }
        }
        return [...byId.values()].sort((a, b) =>
          a.starts_at.localeCompare(b.starts_at),
        );
      });
    },
  });
}

export function useCreateCeremonyAgendaEvent(sprintId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (body: Omit<Parameters<typeof createCeremonyAgendaEvent>[0], "sprint_id">) =>
      guardTenant(() => createCeremonyAgendaEvent({ ...body, sprint_id: sprintId })),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionCeremonyEvents(currentOrganizationId, sprintId),
      });
    },
  });
}

export function useCreateCeremonyRecord(sprintId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (body: Parameters<typeof createCeremonyRecord>[1]) =>
      guardTenant(() => createCeremonyRecord(sprintId, body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionCeremonies(currentOrganizationId, sprintId),
      });
    },
  });
}

export function useActionItemDetail(actionItemId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && actionItemId
        ? [...queryKeys.executionActionItem(currentOrganizationId, actionItemId), requestGeneration]
        : ["org", "none", "action-item"],
    enabled: !!currentOrganizationId && !!actionItemId,
    queryFn: () => guardTenant(() => fetchActionItem(actionItemId!)),
  });
}

export function useCheckIns(actionItemId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && actionItemId
        ? [...queryKeys.executionCheckIns(currentOrganizationId, actionItemId), requestGeneration]
        : ["org", "none", "check-ins"],
    enabled: !!currentOrganizationId && !!actionItemId,
    queryFn: () => guardTenant(() => listCheckIns(actionItemId!)),
  });
}

export function useCreateCheckIn(actionItemId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (body: Parameters<typeof createCheckIn>[1]) =>
      guardTenant(() => createCheckIn(actionItemId, body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionCheckIns(currentOrganizationId, actionItemId),
      });
      await qc.invalidateQueries({
        predicate: (q) =>
          q.queryKey[0] === "org" &&
          q.queryKey[1] === currentOrganizationId &&
          q.queryKey[2] === "execution" &&
          q.queryKey[3] === "board",
      });
    },
  });
}

export function useImpediments(actionItemId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && actionItemId
        ? [...queryKeys.executionImpediments(currentOrganizationId, actionItemId), requestGeneration]
        : ["org", "none", "impediments"],
    enabled: !!currentOrganizationId && !!actionItemId,
    queryFn: () => guardTenant(() => listImpediments(actionItemId!)),
  });
}

export function useCreateImpediment(actionItemId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (body: Parameters<typeof createImpediment>[1]) =>
      guardTenant(() => createImpediment(actionItemId, body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionImpediments(currentOrganizationId, actionItemId),
      });
      await qc.invalidateQueries({
        predicate: (q) =>
          q.queryKey[0] === "org" &&
          q.queryKey[1] === currentOrganizationId &&
          q.queryKey[2] === "execution" &&
          q.queryKey[3] === "board",
      });
    },
  });
}

export function usePatchImpediment(actionItemId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (args: {
      impedimentId: string;
      body: Parameters<typeof patchImpediment>[2];
    }) => guardTenant(() => patchImpediment(actionItemId, args.impedimentId, args.body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionImpediments(currentOrganizationId, actionItemId),
      });
    },
  });
}

export function useDependencies(actionItemId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && actionItemId
        ? [...queryKeys.executionDependencies(currentOrganizationId, actionItemId), requestGeneration]
        : ["org", "none", "dependencies"],
    enabled: !!currentOrganizationId && !!actionItemId,
    queryFn: () => guardTenant(() => listDependencies(actionItemId!)),
  });
}

export function useCreateDependency(actionItemId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (body: Parameters<typeof createDependency>[1]) =>
      guardTenant(() => createDependency(actionItemId, body)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionDependencies(currentOrganizationId, actionItemId),
      });
    },
  });
}

export function useDeleteDependency(actionItemId: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();
  return useMutation({
    mutationFn: (dependencyId: string) =>
      guardTenant(() => deleteDependency(actionItemId, dependencyId)),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.executionDependencies(currentOrganizationId, actionItemId),
      });
    },
  });
}

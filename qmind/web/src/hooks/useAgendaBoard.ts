import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { queryKeys } from "@/api/queryKeys";
import {
  createAgendaEvent,
  fetchAgendaBoard,
  updateAgendaEvent,
  type AgendaEventCreate,
  type AgendaEventStatus,
} from "@/api/agendaApi";
import { StaleTenantResponseError } from "@/api/qmindApi";

export function useAgendaBoard(selectedDate: string) {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey: currentOrganizationId
      ? [
          ...queryKeys.agendaBoard(currentOrganizationId, selectedDate),
          requestGeneration,
        ]
      : ["org", "none", "agenda"],
    enabled: !!currentOrganizationId && !!selectedDate,
    queryFn: async () => {
      try {
        const board = await fetchAgendaBoard(selectedDate);
        if (
          currentOrganizationId &&
          board.next_up &&
          board.next_up.organization_id !== currentOrganizationId
        ) {
          return {
            ...board,
            next_up: null,
            today: [],
            selected_day: [],
            overdue: [],
            in_progress_assessments: [],
            month_markers: [],
          };
        }
        return board;
      } catch (e) {
        if (e instanceof StaleTenantResponseError) {
          return null;
        }
        throw e;
      }
    },
  });
}

export function useAgendaMutations(selectedDate: string) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  const invalidate = () => {
    if (!currentOrganizationId) return;
    void qc.invalidateQueries({
      queryKey: ["org", currentOrganizationId, "agenda"],
    });
  };

  const create = useMutation({
    mutationFn: (payload: AgendaEventCreate) => createAgendaEvent(payload),
    onSuccess: invalidate,
  });

  const setStatus = useMutation({
    mutationFn: ({
      eventId,
      status,
    }: {
      eventId: string;
      status: AgendaEventStatus;
    }) => updateAgendaEvent(eventId, { status }),
    onSuccess: invalidate,
  });

  return { create, setStatus, selectedDate };
}

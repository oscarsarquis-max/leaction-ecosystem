import { useMemo, useState } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import { useOrgMembers } from "@/hooks/useAssessmentDetail";
import {
  useCreateActionFromFinding,
  useImprovementCaseActions,
} from "@/hooks/useImprovementCaseActions";
import { canCreateFindingActions } from "@/lib/permissions";
import { QmindApiError } from "@/api/qmindApi";
import type { ActionItemOut, ImprovementCaseAnalysisRunOut } from "@qmind/api-client";

type Finding = NonNullable<
  NonNullable<ImprovementCaseAnalysisRunOut["analysis"]>["findings"]
>[number];

function formatDue(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(
      new Date(iso),
    );
  } catch {
    return iso;
  }
}

function formatRunDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

const STATUS_LABEL: Record<string, string> = {
  open: "Aberta",
  in_progress: "Em andamento",
  implemented: "Implementada",
  validated: "Validada",
  efficacy_pending: "Eficácia pendente",
  closed_effective: "Encerrada (eficaz)",
  closed_ineffective: "Encerrada (ineficaz)",
  cancelled: "Cancelada",
};

export function FindingActionControls({
  caseId,
  run,
  finding,
  onFocusFinding,
}: {
  caseId: string;
  run: ImprovementCaseAnalysisRunOut;
  finding: Finding;
  onFocusFinding?: () => void;
}) {
  const org = useOrganization();
  const canCreate = canCreateFindingActions(org.currentOrganization?.roles);
  const actionsQuery = useImprovementCaseActions(caseId);
  const create = useCreateActionFromFinding(caseId);
  const members = useOrgMembers();

  const [open, setOpen] = useState(false);
  const [owner, setOwner] = useState(org.currentOrganization?.id ?? "");
  const [dueLocal, setDueLocal] = useState("");
  const [error, setError] = useState<string | null>(null);

  const existing = useMemo(() => {
    const items = actionsQuery.data?.items ?? [];
    return items.find(
      (i) =>
        i.source_analysis_run_id === run.id &&
        i.source_finding_code === finding.code,
    );
  }, [actionsQuery.data?.items, run.id, finding.code]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!owner || !dueLocal) {
      setError("Informe responsável e prazo.");
      return;
    }
    try {
      await create.mutateAsync({
        runId: run.id,
        findingCode: finding.code,
        body: {
          owner_membership_id: owner,
          due_at: new Date(dueLocal).toISOString(),
        },
      });
      setOpen(false);
    } catch (err) {
      const msg =
        err instanceof QmindApiError
          ? err.message
          : "Não foi possível criar a ação.";
      setError(msg);
    }
  }

  if (existing) {
    return (
      <div
        className="mt-2 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
        data-testid={`ic-finding-action-created-${finding.code}`}
      >
        <p className="font-medium text-slate-800">Ação criada</p>
        <p className="text-slate-600">
          Status: {STATUS_LABEL[existing.status] ?? existing.status} · prazo{" "}
          {formatDue(existing.due_at)}
        </p>
        <button
          type="button"
          className="mt-1 text-sm underline"
          onClick={() => {
            document
              .getElementById(`ic-action-item-${existing.id}`)
              ?.scrollIntoView({ behavior: "smooth" });
            onFocusFinding?.();
          }}
        >
          Ver na seção Ações
        </button>
      </div>
    );
  }

  if (!canCreate) return null;

  return (
    <div className="mt-2" data-testid={`ic-finding-action-${finding.code}`}>
      {!open ? (
        <button
          type="button"
          className="qm-btn-secondary"
          data-testid={`ic-create-action-${finding.code}`}
          onClick={() => {
            setOpen(true);
            setError(null);
            setOwner(org.currentOrganization?.id ?? "");
          }}
        >
          Criar ação
        </button>
      ) : (
        <form
          className="space-y-3 rounded border border-slate-200 p-3"
          onSubmit={(e) => void submit(e)}
          data-testid={`ic-create-action-form-${finding.code}`}
        >
          <div className="text-sm text-slate-700">
            <p className="font-medium">Achado (somente leitura)</p>
            <p>{finding.title}</p>
            <p className="mt-1 font-medium">Recomendação</p>
            <p>{finding.recommended_next_step}</p>
          </div>
          <label className="block text-sm">
            <span className="font-medium">Responsável</span>
            <select
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
              required
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              data-testid="ic-action-owner"
            >
              <option value="">Selecione…</option>
              {(members.data ?? []).map((m) => (
                  <option key={m.membership_id} value={m.membership_id}>
                    {m.display_name || m.email || m.membership_id}
                  </option>
                ))}
              {org.currentOrganization?.id &&
              !(members.data ?? []).some(
                (m) => m.membership_id === org.currentOrganization?.id,
              ) ? (
                <option value={org.currentOrganization.id}>Você</option>
              ) : null}
            </select>
          </label>
          <label className="block text-sm">
            <span className="font-medium">Prazo</span>
            <input
              type="datetime-local"
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
              required
              value={dueLocal}
              onChange={(e) => setDueLocal(e.target.value)}
              data-testid="ic-action-due"
            />
          </label>
          {error ? (
            <p className="text-sm text-red-700" role="alert">
              {error}
            </p>
          ) : null}
          <div className="flex gap-2">
            <button
              type="submit"
              className="qm-btn-primary"
              disabled={create.isPending}
              data-testid="ic-action-confirm"
            >
              {create.isPending ? "Criando…" : "Confirmar"}
            </button>
            <button
              type="button"
              className="qm-btn-secondary"
              onClick={() => setOpen(false)}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export function ImprovementCaseActionsSection({
  caseId,
  runs,
  onOpenRunFinding,
}: {
  caseId: string;
  runs: ImprovementCaseAnalysisRunOut[];
  onOpenRunFinding: (runId: string, findingCode: string) => void;
}) {
  const query = useImprovementCaseActions(caseId);
  const items = query.data?.items ?? [];

  if (query.isLoading) {
    return (
      <div className="qm-panel" data-testid="ic-section-actions">
        <h2 className="text-base font-semibold text-slate-900">Ações</h2>
        <p className="mt-2 text-sm text-slate-600">Carregando ações…</p>
      </div>
    );
  }

  return (
    <div className="qm-panel space-y-3" data-testid="ic-section-actions">
      <h2 className="text-base font-semibold text-slate-900">Ações</h2>
      {items.length === 0 ? (
        <p className="text-sm text-slate-600" data-testid="ic-actions-empty">
          Nenhuma ação foi criada para este problema.
        </p>
      ) : (
        <ul className="space-y-3" data-testid="ic-actions-list">
          {items.map((item: ActionItemOut) => {
            const run = runs.find((r) => r.id === item.source_analysis_run_id);
            return (
              <li
                key={item.id}
                id={`ic-action-item-${item.id}`}
                className="rounded border border-slate-200 p-3 text-sm"
                data-testid={`ic-action-item-${item.id}`}
              >
                <p className="font-medium text-slate-900">
                  {item.description.split("\n\n")[0]}
                </p>
                <p className="mt-1 text-slate-600 line-clamp-2">
                  {item.description}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Status: {STATUS_LABEL[item.status] ?? item.status} · prazo{" "}
                  {formatDue(item.due_at)} · responsável{" "}
                  {item.owner_membership_id.slice(0, 8)}…
                </p>
                {run && item.source_finding_code ? (
                  <button
                    type="button"
                    className="mt-2 text-sm underline"
                    data-testid={`ic-action-origin-${item.id}`}
                    onClick={() =>
                      onOpenRunFinding(run.id, item.source_finding_code!)
                    }
                  >
                    Origem: Análise de {formatRunDate(run.generated_at)} ·{" "}
                    {item.source_finding_code}
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

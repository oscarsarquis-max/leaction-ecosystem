import { useState } from "react";
import { Link } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  useCreateImprovementCase,
  useImprovementCases,
} from "@/hooks/useImprovementCases";
import { canManageImprovementCases } from "@/lib/permissions";
import { labelImprovementCaseStatus } from "@/lib/improvementCaseLabels";
import { LoadingPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { QmindApiError } from "@/api/qmindApi";

function truncate(text: string, max = 120): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function formatUpdatedAt(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function OrgImprovementCasesPanel() {
  const org = useOrganization();
  const roles = org.currentOrganization?.roles;
  const canWrite = canManageImprovementCases(roles);
  const query = useImprovementCases();
  const create = useCreateImprovementCase();

  const [openForm, setOpenForm] = useState(false);
  const [problem, setProblem] = useState("");
  const [impact, setImpact] = useState("");
  const [processName, setProcessName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  if (!org.currentOrganizationId) return null;

  if (query.isLoading) {
    return <LoadingPanel title="Carregando problemas em acompanhamento…" />;
  }

  if (query.isError) {
    return (
      <ApiErrorBanner
        title="Não foi possível carregar os problemas"
        error={query.error}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const items = query.data ?? [];

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setCreatedId(null);
    try {
      const created = await create.mutateAsync({
        problem_statement: problem,
        impact_statement: impact,
        related_process: processName,
      });
      setProblem("");
      setImpact("");
      setProcessName("");
      setOpenForm(false);
      setCreatedId(created.id);
    } catch (err) {
      const msg =
        err instanceof QmindApiError
          ? err.message
          : "Não foi possível registrar o problema.";
      setFormError(msg);
    }
  }

  return (
    <section
      className="qm-panel space-y-4"
      data-testid="improvement-cases-panel"
      aria-labelledby="improvement-cases-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2
            id="improvement-cases-heading"
            className="text-lg font-semibold text-slate-900"
          >
            Problemas em acompanhamento
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Registre dores operacionais da organização. A interpretação pelo
            QMind chega nas próximas etapas — aqui ficam os fatos declarados.
          </p>
        </div>
        {canWrite ? (
          <button
            type="button"
            className="qm-btn-primary shrink-0"
            data-testid="register-improvement-case"
            onClick={() => {
              setOpenForm((v) => !v);
              setFormError(null);
            }}
          >
            Registrar problema
          </button>
        ) : null}
      </div>

      {createdId ? (
        <p
          className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
          data-testid="improvement-case-created"
        >
          Problema registrado.{" "}
          <Link
            className="font-medium underline"
            to={`/improvement-cases/${createdId}`}
          >
            Abrir detalhe
          </Link>
        </p>
      ) : null}

      {openForm && canWrite ? (
        <form
          className="qm-panel qm-panel--soft space-y-3"
          onSubmit={(e) => void onSubmit(e)}
          data-testid="improvement-case-form"
        >
          <label className="block text-sm">
            <span className="font-medium text-slate-800">
              Qual problema está acontecendo?
            </span>
            <textarea
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              rows={3}
              required
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              data-testid="ic-problem"
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-800">
              Qual é o impacto observado?
            </span>
            <textarea
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              rows={2}
              required
              value={impact}
              onChange={(e) => setImpact(e.target.value)}
              data-testid="ic-impact"
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-800">
              Em qual processo ele acontece?
            </span>
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              required
              value={processName}
              onChange={(e) => setProcessName(e.target.value)}
              data-testid="ic-process"
            />
          </label>
          {formError ? (
            <p className="text-sm text-red-700" role="alert">
              {formError}
            </p>
          ) : null}
          <div className="flex gap-2">
            <button
              type="submit"
              className="qm-btn-primary"
              disabled={create.isPending}
              data-testid="ic-submit"
            >
              {create.isPending ? "Salvando…" : "Salvar problema"}
            </button>
            <button
              type="button"
              className="qm-btn-secondary"
              onClick={() => setOpenForm(false)}
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : null}

      {items.length === 0 ? (
        <p
          className="text-sm text-slate-600"
          data-testid="improvement-cases-empty"
        >
          Nenhum problema está sendo acompanhado.
        </p>
      ) : (
        <ul className="audit-list" data-testid="improvement-cases-list">
          {items.map((c) => (
            <li key={c.id}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-slate-900">
                    {truncate(c.problem_statement, 160)}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    Impacto: {truncate(c.impact_statement, 100)}
                  </p>
                  <p className="text-sm text-slate-600">
                    Processo: {truncate(c.related_process, 80)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {labelImprovementCaseStatus(c.status)} · atualizado{" "}
                    {formatUpdatedAt(c.updated_at)}
                  </p>
                </div>
                <Link
                  className="qm-btn-secondary shrink-0"
                  to={`/improvement-cases/${c.id}`}
                  data-testid={`open-improvement-case-${c.id}`}
                >
                  Abrir
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

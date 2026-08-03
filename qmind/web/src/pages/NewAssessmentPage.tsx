import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  useCreateAssessment,
  validateCreateAssessmentInput,
  type CreateAssessmentInput,
} from "@/hooks/useAssessmentDetail";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import { EmptyPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { isUuid } from "@/lib/validation";
import { StaleTenantResponseError } from "@/api/qmindApi";

type AssessmentType = CreateAssessmentInput["type"];
const TYPES: AssessmentType[] = ["diagnosis", "internal_audit", "other"];

function envDefault(name: string): string {
  const v = import.meta.env[name];
  return typeof v === "string" ? v.trim() : "";
}

export function NewAssessmentPage() {
  const org = useOrganization();
  const perms = useAssessmentPermissions();
  const navigate = useNavigate();
  const create = useCreateAssessment();
  const submittingRef = useRef(false);

  const [assessmentModelId, setAssessmentModelId] = useState(
    envDefault("VITE_DEFAULT_ASSESSMENT_MODEL_ID"),
  );
  const [standardVersionId, setStandardVersionId] = useState(
    envDefault("VITE_DEFAULT_STANDARD_VERSION_ID"),
  );
  const [type, setType] = useState<AssessmentType>("diagnosis");
  const [scopeKind, setScopeKind] = useState<"requirement" | "process" | "none">(
    envDefault("VITE_DEFAULT_REQUIREMENT_ID") ? "requirement" : "none",
  );
  const [requirementId, setRequirementId] = useState(
    envDefault("VITE_DEFAULT_REQUIREMENT_ID"),
  );
  const [orgProcessId, setOrgProcessId] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);

  if (!org.currentOrganizationId) {
    return (
      <EmptyPanel
        title="Selecione uma organização"
        message="É necessário um tenant ativo para criar avaliação."
      />
    );
  }

  if (!perms.canMutate) {
    return <Navigate to="/assessments" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (submittingRef.current || create.isPending) return;
    submittingRef.current = true;
    setClientError(null);

    const payload: CreateAssessmentInput = {
      assessment_model_id: assessmentModelId.trim(),
      standard_version_id: standardVersionId.trim(),
      type,
      requirement_id:
        scopeKind === "requirement" ? requirementId.trim() || undefined : undefined,
      org_process_id:
        scopeKind === "process" ? orgProcessId.trim() || undefined : undefined,
    };

    const invalid = validateCreateAssessmentInput(payload);
    if (invalid) {
      setClientError(invalid);
      submittingRef.current = false;
      return;
    }

    try {
      const created = await create.mutateAsync(payload);
      navigate(`/assessments/${created.id}`);
    } catch (err) {
      if (err instanceof StaleTenantResponseError) {
        setClientError("Contexto de organização mudou — tente novamente.");
      }
      // API errors surface via create.error
    } finally {
      submittingRef.current = false;
    }
  }

  const busy = create.isPending || submittingRef.current;

  return (
    <section className="max-w-xl">
      <header className="mb-6">
        <p className="text-sm text-teal-950/60">
          <Link to="/assessments" className="hover:underline">
            Avaliações
          </Link>
          {" / "}
          Nova
        </p>
        <h1 className="mt-1 font-display text-3xl tracking-tight text-teal-950">
          Nova avaliação
        </h1>
        <p className="mt-1 text-sm text-teal-950/70">
          Cria rascunho (`draft`) na organização ativa. O criador entra como lead.
        </p>
      </header>

      {clientError ? (
        <div className="mb-4">
          <ApiErrorBanner
            title="Validação"
            error={new Error(clientError)}
          />
        </div>
      ) : null}
      {create.error ? (
        <div className="mb-4">
          <ApiErrorBanner title="Não foi possível criar" error={create.error} />
        </div>
      ) : null}

      <form onSubmit={(e) => void onSubmit(e)} className="space-y-4" noValidate>
        <Field label="Assessment model id">
          <input
            required
            className="field"
            value={assessmentModelId}
            onChange={(e) => setAssessmentModelId(e.target.value)}
            placeholder="UUID"
            pattern={undefined}
            aria-invalid={assessmentModelId.length > 0 && !isUuid(assessmentModelId)}
          />
        </Field>
        <Field label="Standard version id">
          <input
            required
            className="field"
            value={standardVersionId}
            onChange={(e) => setStandardVersionId(e.target.value)}
            placeholder="UUID"
            aria-invalid={
              standardVersionId.length > 0 && !isUuid(standardVersionId)
            }
          />
        </Field>
        <Field label="Tipo">
          <select
            className="field"
            value={type}
            onChange={(e) => setType(e.target.value as AssessmentType)}
          >
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>

        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold text-teal-950">
            Escopo inicial (opcional)
          </legend>
          <div className="flex flex-wrap gap-3 text-sm">
            {(
              [
                ["none", "Depois"],
                ["requirement", "Requirement"],
                ["process", "Org process"],
              ] as const
            ).map(([value, label]) => (
              <label key={value} className="flex items-center gap-1.5">
                <input
                  type="radio"
                  name="scopeKind"
                  checked={scopeKind === value}
                  onChange={() => setScopeKind(value)}
                />
                {label}
              </label>
            ))}
          </div>
          {scopeKind === "requirement" ? (
            <input
              required
              className="field"
              value={requirementId}
              onChange={(e) => setRequirementId(e.target.value)}
              placeholder="requirement_id (UUID)"
            />
          ) : null}
          {scopeKind === "process" ? (
            <input
              required
              className="field"
              value={orgProcessId}
              onChange={(e) => setOrgProcessId(e.target.value)}
              placeholder="org_process_id (UUID)"
            />
          ) : null}
        </fieldset>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-teal-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {busy ? "Criando…" : "Criar rascunho"}
          </button>
          <Link
            to="/assessments"
            className="rounded-md border border-teal-900/20 bg-white px-4 py-2 text-sm font-semibold text-teal-950"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-semibold text-teal-950">{label}</span>
      {children}
    </label>
  );
}

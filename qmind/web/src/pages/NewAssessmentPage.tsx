import { useRef, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  useCreateAssessment,
  validateCreateAssessmentInput,
  type CreateAssessmentInput,
} from "@/hooks/useAssessmentDetail";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  ContextualHelp,
  GuidedEmptyState,
  PageHeader,
} from "@/components/qm";
import { ASSESSMENT_TYPE_OPTIONS } from "@/lib/labels";
import { isUuid } from "@/lib/validation";
import { StaleTenantResponseError } from "@/api/qmindApi";

type AssessmentType = CreateAssessmentInput["type"];

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

  const defaultModel = envDefault("VITE_DEFAULT_ASSESSMENT_MODEL_ID");
  const defaultStandard = envDefault("VITE_DEFAULT_STANDARD_VERSION_ID");
  const defaultsReady = isUuid(defaultModel) && isUuid(defaultStandard);

  const [assessmentModelId, setAssessmentModelId] = useState(defaultModel);
  const [standardVersionId, setStandardVersionId] = useState(defaultStandard);
  const [type, setType] = useState<AssessmentType>("diagnosis");
  const [showAdvanced, setShowAdvanced] = useState(!defaultsReady);
  const [clientError, setClientError] = useState<string | null>(null);

  if (!org.currentOrganizationId) {
    return (
      <GuidedEmptyState
        title="Escolha uma organização para começar"
        why="A avaliação fica vinculada à organização ativa."
        example="Selecione a empresa no topo e depois escolha a modalidade."
        howToStart="Use o seletor “Organização” no cabeçalho."
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
    };

    const invalid = validateCreateAssessmentInput(payload);
    if (invalid) {
      setClientError(
        defaultsReady
          ? "Não foi possível iniciar com a configuração padrão. Peça apoio a quem administra o QMind."
          : "A configuração técnica está incompleta. Peça os dados a quem administra o QMind.",
      );
      setShowAdvanced(true);
      submittingRef.current = false;
      return;
    }

    try {
      const created = await create.mutateAsync(payload);
      navigate(`/assessments/${created.id}`);
      // Mantém o latch após sucesso — evita segundo POST em double-click
      // antes da navegação desmontar o formulário.
    } catch (err) {
      submittingRef.current = false;
      if (err instanceof StaleTenantResponseError) {
        setClientError(
          "A organização mudou enquanto você criava. Confirme o seletor no topo e tente de novo.",
        );
      }
    }
  }

  const busy = create.isPending || submittingRef.current;
  const selected = ASSESSMENT_TYPE_OPTIONS.find((t) => t.value === type);

  return (
    <section className="mx-auto max-w-2xl space-y-6">
      <p className="text-sm text-[var(--qm-muted)]">
        <Link to="/assessments" className="hover:underline">
          Minhas avaliações
        </Link>
        {" / "}
        Nova
      </p>

      <PageHeader
        title="Iniciar uma avaliação"
        explanation="Escolha a modalidade. Em seguida o QMind abre o mapa do percurso e explica a preparação — você poderá interromper e retomar a qualquer momento."
        expectedResult="Uma avaliação criada na organização atual, pronta para a fase Preparação."
        nextStep="Escolher a modalidade e confirmar"
      />

      <ContextualHelp
        title="Não precisa decidir tudo agora"
        example="Se ainda não sabe se será certificação, comece por Diagnóstico inicial."
      >
        A modalidade ajuda a contextualizar o trabalho. O mapa das fases é o mesmo:
        preparação → campo → análise → plano de ação → relatório → conclusão.
      </ContextualHelp>

      {clientError ? (
        <ApiErrorBanner title="Não foi possível criar" error={new Error(clientError)} />
      ) : null}
      {create.error ? (
        <ApiErrorBanner title="Não foi possível criar" error={create.error} />
      ) : null}

      <form onSubmit={(e) => void onSubmit(e)} className="space-y-5" noValidate>
        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-[var(--qm-ink)]">
            Qual é a modalidade desta avaliação?
          </legend>
          <div className="grid gap-2">
            {ASSESSMENT_TYPE_OPTIONS.filter((t) => t.value !== "other").map((t) => (
              <button
                key={t.value}
                type="button"
                className={`type-card${type === t.value ? " type-card--selected" : ""}`}
                onClick={() => setType(t.value)}
                aria-pressed={type === t.value}
              >
                <p className="type-card__title">{t.label}</p>
                <p className="type-card__desc">{t.description}</p>
              </button>
            ))}
          </div>
          {selected ? (
            <p className="text-sm text-[var(--qm-muted)]">
              Selecionado:{" "}
              <strong className="text-[var(--qm-ink)]">{selected.label}</strong>
            </p>
          ) : null}
        </fieldset>

        {showAdvanced ? (
          <div className="space-y-3 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] p-4">
            <p className="text-sm font-semibold text-[var(--qm-ink)]">
              Configuração técnica (só se o administrador pedir)
            </p>
            <p className="text-sm text-[var(--qm-muted)]">
              Na maioria dos casos estes valores já vêm prontos. Não são algo que você
              inventa na hora.
            </p>
            <label className="block text-sm">
              <span className="mb-1 block font-semibold text-[var(--qm-ink)]">
                Modelo de avaliação
              </span>
              <input
                className="qm-field"
                value={assessmentModelId}
                onChange={(e) => setAssessmentModelId(e.target.value)}
                autoComplete="off"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-semibold text-[var(--qm-ink)]">
                Versão da norma
              </span>
              <input
                className="qm-field"
                value={standardVersionId}
                onChange={(e) => setStandardVersionId(e.target.value)}
                autoComplete="off"
              />
            </label>
          </div>
        ) : (
          <button
            type="button"
            className="text-sm font-semibold text-[var(--qm-muted)] underline-offset-2 hover:text-[var(--qm-ink)] hover:underline"
            onClick={() => setShowAdvanced(true)}
          >
            Preciso ajustar a configuração técnica
          </button>
        )}

        <div className="flex flex-wrap gap-3 pt-1">
          <button type="submit" disabled={busy} className="qm-btn-primary">
            {busy ? "Criando…" : "Criar e ver o mapa"}
          </button>
          <Link to="/assessments" className="qm-btn-secondary">
            Voltar
          </Link>
        </div>
      </form>
    </section>
  );
}

import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useOrganization } from "@/org/OrganizationProvider";
import { useAssessments } from "@/hooks/useAssessments";
import { selectFocusAssessment } from "@/lib/selectFocusAssessment";
import {
  GUIDED_TOUR_STEPS,
  clearGuidedTour,
  readGuidedTourStepIndex,
  setGuidedTourStepIndex,
  writeGuidedTourActive,
} from "@/lib/guidedTour";
import { LoadingPanel, ErrorPanel } from "@/components/StatePanels";

/**
 * Apresentação guiada autenticada — somente orientação; sem mutações.
 */
export function GuidedTourPage() {
  const org = useOrganization();
  const assessments = useAssessments();
  const navigate = useNavigate();
  const [stepIndex, setStepIndex] = useState(() => readGuidedTourStepIndex());
  const [pickedId, setPickedId] = useState<string>("");

  const focus = useMemo(() => {
    const items = assessments.data ?? [];
    if (pickedId) {
      return items.find((a) => a.id === pickedId) ?? selectFocusAssessment(items);
    }
    return selectFocusAssessment(items);
  }, [assessments.data, pickedId]);

  const assessmentId = focus?.id ?? null;
  const step = GUIDED_TOUR_STEPS[stepIndex] ?? GUIDED_TOUR_STEPS[0]!;
  const total = GUIDED_TOUR_STEPS.length;
  const href = step.resolveHref(assessmentId);
  const needsPick = step.needsAssessment && !assessmentId;

  if (org.loading && !org.currentOrganizationId) {
    return <LoadingPanel title="Carregando organizações…" />;
  }

  if (!org.currentOrganizationId) {
    return (
      <ErrorPanel
        title="Organização necessária"
        message="Selecione uma organização ativa para iniciar a apresentação guiada."
        action={{
          label: "Ir para avaliações",
          onClick: () => void navigate("/assessments"),
        }}
      />
    );
  }

  const activateAndOpen = () => {
    if (!href) return;
    writeGuidedTourActive(org.currentOrganizationId!, stepIndex);
    void navigate(href);
  };

  const goStep = (next: number) => {
    const clamped = Math.max(0, Math.min(next, total - 1));
    setStepIndex(clamped);
    setGuidedTourStepIndex(clamped);
    writeGuidedTourActive(org.currentOrganizationId!, clamped);
  };

  return (
    <div className="space-y-6" data-testid="guided-tour-page">
      <header className="qm-page-header space-y-2">
        <p className="qm-page-header__eyebrow">Apresentação guiada</p>
        <h1 className="qm-page-header__title">{step.title}</h1>
        <p className="qm-page-header__explain">
          Etapa {stepIndex + 1} de {total} · organização{" "}
          {org.currentOrganization?.organizationName ?? "ativa"}
        </p>
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-[var(--qm-surface-soft)]"
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={total}
          aria-valuenow={stepIndex + 1}
          aria-label="Progresso da apresentação guiada"
        >
          <div
            className="h-full rounded-full bg-[var(--qm-accent)] transition-[width] duration-300"
            style={{ width: `${((stepIndex + 1) / total) * 100}%` }}
          />
        </div>
      </header>

      <section className="qm-panel space-y-4 p-5">
        <div>
          <h2 className="text-base font-semibold text-[var(--qm-ink)]">
            O que demonstrar
          </h2>
          <p className="mt-1 text-[var(--qm-muted)]">{step.demonstrate}</p>
        </div>
        <div>
          <h2 className="text-base font-semibold text-[var(--qm-ink)]">
            Mensagem principal
          </h2>
          <p className="mt-1 text-[var(--qm-muted)]">{step.message}</p>
        </div>
        <div>
          <h2 className="text-base font-semibold text-[var(--qm-ink)]">
            Benefício
          </h2>
          <p className="mt-1 text-[var(--qm-muted)]">{step.benefit}</p>
        </div>

        {needsPick ? (
          <div className="rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] p-4">
            <p className="text-sm text-[var(--qm-ink)]">
              Esta etapa precisa de uma avaliação demonstrativa. Escolha uma
              avaliação existente — nenhuma rota será aberta sem destino válido.
            </p>
            {assessments.isLoading ? (
              <p className="mt-2 text-sm text-[var(--qm-muted)]">
                Carregando avaliações…
              </p>
            ) : (assessments.data ?? []).length === 0 ? (
              <p className="mt-2 text-sm text-[var(--qm-muted)]">
                Nenhuma avaliação disponível. Crie uma avaliação na home da
                organização e retorne à apresentação.
              </p>
            ) : (
              <label className="mt-3 block text-sm">
                <span className="font-medium text-[var(--qm-ink)]">
                  Avaliação demonstrativa
                </span>
                <select
                  className="qm-field mt-1 w-full"
                  value={pickedId || assessmentId || ""}
                  onChange={(e) => setPickedId(e.target.value)}
                  data-testid="guided-tour-assessment-select"
                >
                  <option value="">Selecione…</option>
                  {(assessments.data ?? []).map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.type} · {a.status} · {a.updated_at.slice(0, 10)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <Link
              to="/assessments"
              className="mt-3 inline-block text-sm font-medium text-[var(--qm-accent)] underline-offset-2 hover:underline"
            >
              Abrir lista de avaliações
            </Link>
          </div>
        ) : null}

        {focus && !needsPick ? (
          <p className="text-sm text-[var(--qm-muted)]">
            Avaliação em foco:{" "}
            <strong className="text-[var(--qm-ink)]">
              {focus.type} · {focus.status} · {focus.updated_at.slice(0, 10)}
            </strong>
          </p>
        ) : null}
      </section>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="qm-btn-primary"
          disabled={!href}
          onClick={activateAndOpen}
          data-testid="guided-tour-open-product"
        >
          Abrir no produto
        </button>
        <button
          type="button"
          className="qm-btn-secondary"
          disabled={stepIndex >= total - 1}
          onClick={() => goStep(stepIndex + 1)}
          data-testid="guided-tour-next"
        >
          Próxima etapa
        </button>
        <button
          type="button"
          className="qm-btn-secondary"
          disabled={stepIndex <= 0}
          onClick={() => goStep(stepIndex - 1)}
        >
          Etapa anterior
        </button>
        <Link to="/" className="qm-btn-secondary">
          Voltar à apresentação
        </Link>
        <button
          type="button"
          className="qm-btn-secondary"
          onClick={() => {
            clearGuidedTour();
            void navigate("/assessments");
          }}
        >
          Encerrar tour
        </button>
      </div>
    </div>
  );
}

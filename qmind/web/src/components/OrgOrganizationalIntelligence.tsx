import {
  useAnalyzeOrganizationalIntelligence,
  useLatestOrganizationalIntelligence,
} from "@/hooks/useOrganizationalIntelligence";
import { LoadingPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { GuidedEmptyState } from "@/components/qm";
import { QmindApiError } from "@/api/qmindApi";
import {
  insightReasonValue,
  type OrganizationalInsight,
} from "@/api/organizationalIntelligenceApi";

function formatDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function analyzeErrorTitle(error: unknown): string {
  if (!(error instanceof QmindApiError)) {
    return "Não foi possível atualizar a análise";
  }
  switch (error.code) {
    case "oi_not_configured":
      return "Inteligência Organizacional não configurada";
    case "oi_timeout":
      return "Tempo esgotado ao consultar a Inteligência Organizacional";
    case "oi_unavailable":
    case "oi_error":
    case "oi_bad_response":
    case "oi_invalid_response":
      return "Inteligência Organizacional indisponível";
    case "oi_organization_mismatch":
      return "Resposta incompatível com a organização corrente";
    default:
      return "Não foi possível atualizar a análise";
  }
}

function InsightCard({ insight }: { insight: OrganizationalInsight }) {
  const clause = insightReasonValue(insight, "clause");
  const priority = insightReasonValue(insight, "priority");
  const missing = insight.explanation?.supporting_facts ?? [];

  return (
    <article
      className="rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] px-4 py-3"
      data-testid="oi-insight"
      data-clause={clause ?? ""}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold text-[var(--qm-ink)]">{insight.title}</h3>
        {clause ? (
          <span
            className="rounded border border-[var(--qm-line)] px-2 py-0.5 text-xs text-[var(--qm-muted)]"
            data-testid="oi-insight-clause"
          >
            Cláusula {clause}
          </span>
        ) : null}
        {priority ? (
          <span
            className="rounded border border-[var(--qm-line)] px-2 py-0.5 text-xs text-[var(--qm-muted)]"
            data-testid="oi-insight-priority"
          >
            Prioridade: {priority}
          </span>
        ) : null}
      </div>
      <p
        className="mt-2 whitespace-pre-wrap text-sm text-[var(--qm-muted)]"
        data-testid="oi-insight-summary"
      >
        {insight.summary}
      </p>
      {missing.length > 0 ? (
        <div className="mt-3" data-testid="oi-insight-missing">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--qm-ink)]">
            Informações ausentes
          </p>
          <ul className="mt-1 list-inside list-disc text-sm text-[var(--qm-muted)]">
            {missing.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}

export function OrgOrganizationalIntelligence() {
  const latest = useLatestOrganizationalIntelligence();
  const analyze = useAnalyzeOrganizationalIntelligence();

  const onAnalyze = () => {
    analyze.reset();
    analyze.mutate();
  };

  if (latest.isLoading) {
    return <LoadingPanel title="Carregando Inteligência Organizacional…" />;
  }

  if (latest.isError) {
    return (
      <ApiErrorBanner
        title="Não foi possível carregar a Inteligência Organizacional"
        error={latest.error}
        onRetry={() => void latest.refetch()}
      />
    );
  }

  const run = latest.data;
  const insights = run?.insights.insights ?? [];

  return (
    <section
      className="space-y-4 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] p-4"
      data-testid="org-organizational-intelligence"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-lg text-[var(--qm-ink)]">
            Inteligência Organizacional
          </h2>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            Prontidão do contexto em relação à ISO 9001 — não é conformidade,
            certificação, auditoria concluída nem não conformidade.
          </p>
          {run ? (
            <p className="mt-2 text-sm text-[var(--qm-ink)]" data-testid="oi-last-analyzed">
              Última análise:{" "}
              <time dateTime={run.generated_at}>
                {formatDateTime(run.generated_at)}
              </time>
            </p>
          ) : null}
        </div>
        <button
          type="button"
          className="qm-btn-secondary shrink-0"
          data-testid="oi-analyze-button"
          disabled={analyze.isPending}
          onClick={onAnalyze}
        >
          {analyze.isPending
            ? "Atualizando…"
            : run
              ? "Atualizar análise"
              : "Gerar análise"}
        </button>
      </div>

      {analyze.isError ? (
        <ApiErrorBanner
          title={analyzeErrorTitle(analyze.error)}
          error={analyze.error}
          onRetry={onAnalyze}
        />
      ) : null}

      {!run ? (
        <GuidedEmptyState
          title="A organização ainda não possui uma análise de Inteligência Organizacional."
          why="A análise usa o perfil da organização para indicar a prontidão do contexto (cláusulas 4 e 7)."
          example="Após gerar, você verá insights com título, descrição, cláusula e informações ausentes — quando houver."
          howToStart='Toque em “Gerar análise”.'
          action={{
            label: analyze.isPending ? "Gerando…" : "Gerar análise",
            onClick: onAnalyze,
          }}
        />
      ) : (
        <ul className="space-y-3" data-testid="oi-insights-list">
          {insights.map((insight) => (
            <li key={insight.insight_id}>
              <InsightCard insight={insight} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

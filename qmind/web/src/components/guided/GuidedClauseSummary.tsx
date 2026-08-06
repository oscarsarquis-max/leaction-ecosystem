import type { ClauseNarrative, NarrativeItem } from "@/lib/guidedNarrative";

type Props = {
  narrative: ClauseNarrative;
  onContinue: () => void;
  onReviewPending: () => void;
  onBackToQuestions: () => void;
};

function Bucket({
  title,
  items,
  empty,
  renderExtra,
}: {
  title: string;
  items: NarrativeItem[];
  empty: string;
  renderExtra?: (item: NarrativeItem) => string | null;
}) {
  return (
    <section className="space-y-2">
      <h4 className="text-sm font-semibold text-[var(--qm-ink)]">{title}</h4>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--qm-muted)]">{empty}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.questionId}
              className="rounded-md border border-[var(--qm-line)] bg-[var(--qm-app)]/50 px-3 py-2"
            >
              <p className="text-sm font-medium text-[var(--qm-ink)]">
                {item.theme}
              </p>
              <p className="mt-0.5 text-sm text-[var(--qm-muted)]">{item.question}</p>
              {item.tags.length > 0 ? (
                <p className="mt-1 flex flex-wrap gap-1.5">
                  {item.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded bg-[var(--qm-surface-soft)] px-1.5 py-0.5 text-[11px] font-semibold text-[var(--qm-ink)]"
                    >
                      {t}
                    </span>
                  ))}
                </p>
              ) : null}
              {renderExtra?.(item) ? (
                <p className="mt-1 text-xs text-[var(--qm-muted)]">
                  {renderExtra(item)}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-[var(--qm-line)] bg-[var(--qm-app)]/40 px-3 py-2 text-center">
      <p className="text-lg font-semibold text-[var(--qm-ink)]">{value}</p>
      <p className="text-[11px] text-[var(--qm-muted)]">{label}</p>
    </div>
  );
}

export function GuidedClauseSummary({
  narrative,
  onContinue,
  onReviewPending,
  onBackToQuestions,
}: Props) {
  const continueLabel = narrative.nextClauseMajor
    ? `Continuar para ${narrative.nextClauseMajor} — ${narrative.nextClauseLabel}`
    : "Ir para a revisão final";

  return (
    <div className="space-y-6" data-testid="guided-clause-summary-panel">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--qm-muted)]">
          Fechamento da etapa {narrative.major}
        </p>
        <h3 className="font-display text-2xl text-[var(--qm-ink)]">
          {narrative.businessName}
        </h3>
        <p className="text-sm leading-relaxed text-[var(--qm-muted)]">
          <span className="font-semibold text-[var(--qm-ink)]">Objetivo: </span>
          {narrative.objective}
        </p>
        <p className="text-sm leading-relaxed text-[var(--qm-muted)]">
          {narrative.whatCompanyInformed}
        </p>
        <p className="text-xs text-[var(--qm-muted)]">
          Leitura neutra — não declara conformidade nem não conformidade. Não
          promete melhoria automática.
        </p>
      </header>

      <div
        className="grid grid-cols-2 gap-2 sm:grid-cols-5"
        data-testid="clause-stage-stats"
      >
        <Stat label="Respondidas" value={narrative.stats.answered} />
        <Stat label="Aplicáveis" value={narrative.stats.applicable} />
        <Stat label="Evidências" value={narrative.stats.evidenceCount} />
        <Stat label="Pendências" value={narrative.stats.pending} />
        <Stat label="Para revisão" value={narrative.stats.reviewPoints} />
      </div>

      <Bucket
        title="Práticas identificadas"
        items={narrative.informedPractices}
        empty="Nenhuma prática marcada como já estabelecida nesta etapa."
      />
      <Bucket
        title="Evidências disponíveis"
        items={narrative.linkedOrDescribedEvidence}
        empty="Nenhuma evidência vinculada ou descrita ainda."
        renderExtra={(i) =>
          i.evidenceCount > 0
            ? `${i.evidenceCount} evidência(s) vinculada(s)`
            : i.evidenceNote || null
        }
      />
      <Bucket
        title="Evidências prometidas"
        items={narrative.promisedEvidence}
        empty="Nenhuma evidência marcada para depois."
      />
      <Bucket
        title="Respostas parciais"
        items={narrative.partialAnswers}
        empty="Nenhuma resposta parcial."
        renderExtra={(i) => i.description || null}
      />
      <Bucket
        title="Respostas negativas"
        items={narrative.negativeAnswers}
        empty="Nenhuma resposta negativa."
        renderExtra={(i) => i.description || null}
      />
      <Bucket
        title="Pontos desconhecidos"
        items={narrative.unknownAnswers}
        empty="Nenhum ponto marcado como desconhecido."
      />
      <Bucket
        title="Itens não aplicáveis"
        items={narrative.notApplicable}
        empty="Nenhum item não aplicável."
        renderExtra={(i) =>
          i.naJustification
            ? `Justificativa: ${i.naJustification}`
            : "Sem justificativa registrada"
        }
      />
      <Bucket
        title="Assuntos que precisam de esclarecimento"
        items={narrative.clarificationPoints}
        empty="Nenhum assunto sinalizado para esclarecimento nesta etapa."
      />

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-[var(--qm-ink)]">
          Oportunidades aparentes de fortalecimento
        </h4>
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
          {narrative.strengtheningOpportunities.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-[var(--qm-ink)]">
          Possíveis impactos empresariais
        </h4>
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
          {narrative.possibleBusinessImpacts.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      {narrative.nextClauseMajor ? (
        <p className="text-sm text-[var(--qm-muted)]" data-testid="next-clause-hint">
          Próxima cláusula:{" "}
          <span className="font-semibold text-[var(--qm-ink)]">
            {narrative.nextClauseMajor} — {narrative.nextClauseLabel}
          </span>
        </p>
      ) : (
        <p className="text-sm text-[var(--qm-muted)]" data-testid="next-clause-hint">
          Próximo passo: revisão final do roteiro.
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="qm-btn-secondary"
          data-testid="clause-summary-back"
          onClick={onBackToQuestions}
        >
          Voltar às perguntas
        </button>
        {narrative.pending > 0 ? (
          <button
            type="button"
            className="qm-btn-secondary"
            data-testid="clause-review-pending"
            onClick={onReviewPending}
          >
            Revisar pendências
          </button>
        ) : null}
        <button
          type="button"
          className="qm-btn-primary"
          data-testid="clause-summary-continue"
          onClick={onContinue}
        >
          {continueLabel}
        </button>
      </div>
    </div>
  );
}

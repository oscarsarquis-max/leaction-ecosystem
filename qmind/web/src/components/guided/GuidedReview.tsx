import { Link } from "react-router-dom";
import type { GuidedAnswer, GuidedClauseGroup, GuidedQuestion, GuidedSession } from "@/api/guidedTypes";
import { GuidedEvidencePanel } from "@/components/guided/GuidedEvidencePanel";
import {
  buildFinalReview,
  type NarrativeItem,
} from "@/lib/guidedNarrative";

type Props = {
  session: GuidedSession;
  questions: GuidedQuestion[];
  clauseGroups?: GuidedClauseGroup[];
  assessmentId: string;
  readOnly?: boolean;
  onGoToClause: (major: string) => void;
  onGoToQuestion: (questionId: string) => void;
  onReviewPending: () => void;
  onRefresh: () => Promise<void>;
  onProvideLater: (questionId: string) => Promise<void>;
  onDescribe: (questionId: string, note: string) => Promise<void>;
  onLinkEvidence: (questionId: string, evidenceId: string) => Promise<void>;
  onUnlinkEvidence: (questionId: string, evidenceId: string) => Promise<void>;
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <p className="text-sm text-[var(--qm-muted)]">
      <span className="font-semibold text-[var(--qm-ink)]">{label}: </span>
      {value?.trim() ? value : "—"}
    </p>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <h4 className="text-sm font-semibold text-[var(--qm-ink)]">{title}</h4>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-[var(--qm-muted)]">Nenhum item informado.</p>
      ) : (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
          {items.map((item, i) => (
            <li key={`${item}-${i}`}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ThemeList({ title, items }: { title: string; items: NarrativeItem[] }) {
  return (
    <section>
      <h4 className="text-sm font-semibold text-[var(--qm-ink)]">{title}</h4>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-[var(--qm-muted)]">Nenhum item nesta categoria.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {items.slice(0, 12).map((item) => (
            <li
              key={item.questionId}
              className="rounded-md border border-[var(--qm-line)] px-3 py-2 text-sm"
            >
              <p className="font-medium text-[var(--qm-ink)]">{item.theme}</p>
              <p className="text-[var(--qm-muted)]">{item.question}</p>
              {item.tags.length > 0 ? (
                <p className="mt-1 flex flex-wrap gap-1">
                  {item.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded bg-[var(--qm-surface-soft)] px-1.5 py-0.5 text-[11px] font-semibold"
                    >
                      {t}
                    </span>
                  ))}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function GuidedReview({
  session,
  questions,
  clauseGroups,
  assessmentId,
  readOnly,
  onGoToClause,
  onGoToQuestion,
  onReviewPending,
  onRefresh,
  onProvideLater,
  onDescribe,
  onLinkEvidence,
  onUnlinkEvidence,
}: Props) {
  const model = buildFinalReview(session, questions, clauseGroups);
  const answerById = new Map(session.answers.map((a) => [a.question_id, a]));

  return (
    <div className="space-y-8" data-testid="guided-review">
      <p className="text-base text-[var(--qm-muted)]">
        Revisão final em linguagem de negócio: o que foi informado, o que falta
        esclarecer e o próximo passo. Nada aqui gera automaticamente conformidade
        ou não conformidade.
      </p>

      <section className="space-y-3">
        <h3 className="font-display text-xl text-[var(--qm-ink)]">
          Perfil da organização
        </h3>
        {model.profileLines.map((r) => (
          <Row key={r.label} label={r.label} value={r.value} />
        ))}
      </section>

      <section className="space-y-3">
        <h3 className="font-display text-xl text-[var(--qm-ink)]">Escopo</h3>
        {model.scopeLines.map((r) => (
          <Row key={r.label} label={r.label} value={r.value} />
        ))}
      </section>

      <ListBlock title="Produtos e serviços" items={model.products} />
      <ListBlock title="Unidades" items={model.sites} />
      <ListBlock title="Processos" items={model.processes} />
      <ListBlock title="Partes interessadas" items={model.stakeholders} />

      <section className="space-y-3" data-testid="guided-business-journey">
        <h3 className="font-display text-xl text-[var(--qm-ink)]">
          Percurso pelas cláusulas 4–10
        </h3>
        <ol className="space-y-2">
          {model.businessJourney.map((step) => (
            <li
              key={step.major}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--qm-line)] px-3 py-2 text-sm"
            >
              <span className="font-medium text-[var(--qm-ink)]">
                {step.order}. {step.title}
                <span className="ml-2 text-[var(--qm-muted)]">
                  (etapa {step.major})
                </span>
              </span>
              <span className="text-[var(--qm-muted)]">
                {step.answered}/{step.applicable} respondidas
              </span>
              <button
                type="button"
                className="text-xs font-semibold text-[var(--qm-accent)] hover:underline"
                onClick={() => onGoToClause(step.major)}
                data-testid={`review-go-clause-${step.major}`}
              >
                Voltar à cláusula
              </button>
            </li>
          ))}
        </ol>
      </section>

      <section
        className="grid grid-cols-2 gap-2 sm:grid-cols-3"
        data-testid="guided-final-stats"
      >
        {[
          ["Respondidas", model.answeredCount],
          ["Aplicáveis", model.applicableCount],
          ["Evidências relacionadas", model.evidenceRelatedCount],
          ["Aguardando envio", model.evidenceAwaitingUploadCount],
          ["Em processamento", model.evidenceProcessingCount],
          ["Aprovadas", model.evidenceApprovedCount],
          ["Rejeitadas", model.evidenceRejectedCount],
          ["Prometidas para depois", model.evidencePromisedLaterCount],
          ["Pontos desconhecidos", model.unknownCount],
          ["Temas para aprofundar", model.deepeningThemes.length],
        ].map(([label, value]) => (
          <div
            key={String(label)}
            className="rounded-md border border-[var(--qm-line)] bg-[var(--qm-app)]/40 px-3 py-2"
          >
            <p className="text-lg font-semibold text-[var(--qm-ink)]">{value}</p>
            <p className="text-[11px] text-[var(--qm-muted)]">{label}</p>
          </div>
        ))}
      </section>

      <section
        className="space-y-4"
        data-testid="guided-pending-evidences"
      >
        <div>
          <h3 className="font-display text-xl text-[var(--qm-ink)]">
            Evidências pendentes
          </h3>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            Anexar ou vincular aqui atualiza o resumo da pergunta, da cláusula e
            desta revisão. Ter arquivo não significa conformidade automática.
          </p>
        </div>
        {model.pendingEvidenceItems.length === 0 ? (
          <p className="text-sm text-[var(--qm-muted)]">
            Nenhuma evidência pendente neste momento.
          </p>
        ) : (
          <ul className="space-y-6">
            {model.pendingEvidenceItems.map((item) => {
              const answer: GuidedAnswer | undefined = answerById.get(
                item.questionId,
              );
              return (
                <li
                  key={item.questionId}
                  className="rounded-md border border-[var(--qm-line)] px-3 py-3"
                  data-testid={`pending-evidence-${item.questionId}`}
                >
                  <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-[var(--qm-ink)]">{item.theme}</p>
                      <p className="text-sm text-[var(--qm-muted)]">{item.question}</p>
                    </div>
                    <button
                      type="button"
                      className="text-xs font-semibold text-[var(--qm-accent)] hover:underline"
                      onClick={() => onGoToQuestion(item.questionId)}
                    >
                      Abrir pergunta
                    </button>
                  </div>
                  <GuidedEvidencePanel
                    assessmentId={assessmentId}
                    questionId={item.questionId}
                    answer={answer}
                    readOnly={readOnly}
                    onRefresh={onRefresh}
                    onProvideLater={() => onProvideLater(item.questionId)}
                    onDescribe={(note) => onDescribe(item.questionId, note)}
                    onLinkExisting={(eid) => onLinkEvidence(item.questionId, eid)}
                    onUnlink={(eid) => onUnlinkEvidence(item.questionId, eid)}
                  />
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <ThemeList
        title="Temas que precisam de aprofundamento"
        items={model.deepeningThemes}
      />

      <section className="space-y-2">
        <h3 className="font-display text-xl text-[var(--qm-ink)]">
          Próximos passos recomendados
        </h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
          {model.nextSteps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </section>

      <section className="space-y-3" data-testid="guided-review-actions">
        <h3 className="font-display text-lg text-[var(--qm-ink)]">Ações</h3>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            className="qm-btn-secondary"
            data-testid="review-pending"
            onClick={onReviewPending}
          >
            Revisar pendências
          </button>
          <Link
            to={`/assessments/${assessmentId}`}
            className="qm-btn-secondary"
            data-testid="review-continue-later"
          >
            Continuar depois
          </Link>
          <Link
            to={`/assessments/${assessmentId}/work`}
            className="qm-btn-primary"
            data-testid="guided-done"
          >
            Concluir preparação e seguir para execução em campo
          </Link>
        </div>
      </section>
    </div>
  );
}

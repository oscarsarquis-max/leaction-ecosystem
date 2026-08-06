import type { GuidedAnswer, GuidedClauseGroup, GuidedQuestion } from "@/api/guidedTypes";
import {
  CLAUSE_NAV_ORDER,
  CLAUSE_PLAIN,
  clauseMajor,
  clauseProgressList,
} from "@/lib/guidedShowWhen";

type Props = {
  questions: GuidedQuestion[];
  answers: GuidedAnswer[] | undefined;
  currentQuestionId: string | undefined;
  clauseGroups?: GuidedClauseGroup[];
  onSelectQuestion: (index: number) => void;
  onSelectClause?: (major: string) => void;
};

export function GuidedClauseNav({
  questions,
  answers,
  currentQuestionId,
  clauseGroups,
  onSelectQuestion,
  onSelectClause,
}: Props) {
  const progress = clauseProgressList(questions, answers);
  const overallApplicable = progress.reduce((n, p) => n + p.applicable, 0);
  const overallAnswered = progress.reduce((n, p) => n + p.answered, 0);
  const overallPct =
    overallApplicable === 0
      ? 0
      : Math.round((overallAnswered / overallApplicable) * 100);

  const currentMajor = currentQuestionId
    ? clauseMajor(
        questions.find((q) => q.id === currentQuestionId)?.clause_ref ?? "",
      )
    : progress.find((p) => p.applicable > 0)?.major ?? "4";

  const current = progress.find((p) => p.major === currentMajor) ?? progress[0];
  const groupLabel =
    clauseGroups?.find((g) => g.id === currentMajor)?.label ??
    CLAUSE_PLAIN[currentMajor]?.shortLabel ??
    currentMajor;

  return (
    <div className="space-y-4" data-testid="guided-clause-nav">
      <nav className="flex flex-wrap gap-2" aria-label="Navegação por cláusula">
        {CLAUSE_NAV_ORDER.map((major) => {
          const p = progress.find((x) => x.major === major)!;
          const firstIdx = questions.findIndex(
            (q) => clauseMajor(q.clause_ref) === major,
          );
          const label =
            clauseGroups?.find((g) => g.id === major)?.label ??
            CLAUSE_PLAIN[major]?.shortLabel ??
            major;
          const active = major === currentMajor;
          const disabled = p.applicable === 0;
          return (
            <button
              key={major}
              type="button"
              disabled={disabled}
              className={
                active
                  ? "rounded-qmind-sm bg-qmind-semantic-current px-2.5 py-1.5 text-xs font-semibold text-white"
                  : disabled
                    ? "cursor-not-allowed rounded-qmind-sm bg-qmind-app px-2.5 py-1.5 text-xs font-semibold text-qmind-muted/50"
                    : "rounded-qmind-sm bg-qmind-app px-2.5 py-1.5 text-xs font-semibold text-qmind-muted hover:text-qmind-main"
              }
              onClick={() => {
                if (disabled) return;
                onSelectClause?.(major);
                if (firstIdx >= 0) onSelectQuestion(firstIdx);
              }}
              title={`${major} — ${label}: ${p.answered}/${p.applicable}`}
              data-testid={`guided-clause-${major}`}
            >
              {major} — {label}
              <span className="ml-1 opacity-80">
                {p.answered}/{p.applicable}
              </span>
            </button>
          );
        })}
      </nav>

      {current ? (
        <div
          className="rounded-qmind-sm border border-qmind-semantic-future bg-qmind-app/60 px-4 py-3"
          data-testid="guided-clause-summary"
        >
          <p className="text-sm font-semibold text-qmind-main">
            {current.major} — {groupLabel}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-qmind-muted">
            {current.explanation}
          </p>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-qmind-muted">Aplicáveis</dt>
              <dd className="font-semibold text-qmind-main" data-testid="clause-applicable">
                {current.applicable}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-qmind-muted">Respondidas</dt>
              <dd className="font-semibold text-qmind-main" data-testid="clause-answered">
                {current.answered}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-qmind-muted">Pendências</dt>
              <dd className="font-semibold text-qmind-main" data-testid="clause-pending">
                {current.pending}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-qmind-muted">Progresso da cláusula</dt>
              <dd className="font-semibold text-qmind-main" data-testid="clause-pct">
                {current.pct}%
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-xs text-qmind-muted" data-testid="guided-overall-progress">
            Progresso geral do roteiro: {overallAnswered} de {overallApplicable}{" "}
            aplicáveis ({overallPct}%)
          </p>
        </div>
      ) : null}
    </div>
  );
}

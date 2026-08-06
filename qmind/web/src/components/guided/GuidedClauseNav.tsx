import type { GuidedClauseGroup, GuidedQuestion } from "@/api/guidedTypes";
import { clauseMajor } from "@/lib/guidedShowWhen";

type Props = {
  questions: GuidedQuestion[];
  currentQuestionId: string | undefined;
  clauseGroups?: GuidedClauseGroup[];
  onSelectQuestion: (index: number) => void;
};

export function GuidedClauseNav({
  questions,
  currentQuestionId,
  clauseGroups,
  onSelectQuestion,
}: Props) {
  const majors = [...new Set(questions.map((q) => clauseMajor(q.clause_ref)))].sort(
    (a, b) => Number(a) - Number(b),
  );
  const currentMajor = currentQuestionId
    ? clauseMajor(
        questions.find((q) => q.id === currentQuestionId)?.clause_ref ?? "",
      )
    : majors[0];

  return (
    <nav
      className="flex flex-wrap gap-2"
      aria-label="Navegação por cláusula"
      data-testid="guided-clause-nav"
    >
      {majors.map((major) => {
        const firstIdx = questions.findIndex(
          (q) => clauseMajor(q.clause_ref) === major,
        );
        const label =
          clauseGroups?.find((g) => g.id === major)?.label ?? `Cláusula ${major}`;
        const active = major === currentMajor;
        return (
          <button
            key={major}
            type="button"
            className={
              active
                ? "rounded-qmind-sm bg-qmind-semantic-current px-2.5 py-1.5 text-xs font-semibold text-white"
                : "rounded-qmind-sm bg-qmind-app px-2.5 py-1.5 text-xs font-semibold text-qmind-muted hover:text-qmind-main"
            }
            onClick={() => {
              if (firstIdx >= 0) onSelectQuestion(firstIdx);
            }}
            title={label}
          >
            {major} · {label}
          </button>
        );
      })}
    </nav>
  );
}

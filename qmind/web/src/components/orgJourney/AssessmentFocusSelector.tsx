import type { AssessmentOut } from "@qmind/api-client";
import { labelAssessmentStatus, labelAssessmentType } from "@/lib/labels";

type Props = {
  assessments: AssessmentOut[];
  focusId: string;
  onChange: (id: string) => void;
};

export function AssessmentFocusSelector({
  assessments,
  focusId,
  onChange,
}: Props) {
  if (assessments.length <= 1) return null;

  return (
    <label className="org-journey__focus">
      <span className="org-journey__focus-label">Avaliação em foco</span>
      <select
        className="qm-field"
        value={focusId}
        onChange={(e) => onChange(e.target.value)}
        data-testid="journey-focus-select"
        aria-label="Selecionar avaliação em foco"
      >
        {assessments.map((a) => (
          <option key={a.id} value={a.id}>
            {labelAssessmentType(a.type)} — {labelAssessmentStatus(a.status)}
          </option>
        ))}
      </select>
    </label>
  );
}

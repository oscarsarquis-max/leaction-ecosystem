type Tone = "neutral" | "progress" | "attention" | "risk" | "info" | "done" | "future" | "unavailable";

type Props = {
  label: string;
  tone?: Tone;
};

const toneClass: Record<Tone, string> = {
  neutral: "qm-badge qm-badge--neutral",
  progress: "qm-badge qm-badge--progress",
  attention: "qm-badge qm-badge--attention",
  risk: "qm-badge qm-badge--risk",
  info: "qm-badge qm-badge--info",
  done: "qm-badge qm-badge--done",
  future: "qm-badge qm-badge--future",
  unavailable: "qm-badge qm-badge--unavailable",
};

export function StatusBadge({ label, tone = "neutral" }: Props) {
  return <span className={toneClass[tone]}>{label}</span>;
}

export function toneForAssessmentStatus(status: string | undefined | null): Tone {
  switch (status) {
    case "closed":
      return "done";
    case "draft":
    case "planned":
      return "info";
    case "in_progress":
    case "analysis":
    case "actions":
    case "report":
      return "progress";
    case "cancelled":
      return "unavailable";
    default:
      return "neutral";
  }
}

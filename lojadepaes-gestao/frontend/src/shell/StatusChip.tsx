const TONE: Record<string, string> = {
  open: "c-open",
  accepted: "c-acc",
  confirmed: "c-acc",
  paid: "c-paid",
  in_production: "c-prod",
  ready: "c-prod",
  ok: "c-prod",
  delivered: "c-del",
  completed: "c-none",
  cancelled: "c-can",
  attention: "c-warn",
  warning: "c-warn",
};

type Props = {
  stage: string;
  label: string;
};

export function StatusChip({ stage, label }: Props) {
  const tone = TONE[stage] ?? "c-none";
  return (
    <span className={`gestao-chip ${tone}`}>
      <span className="dot" aria-hidden="true" />
      {label}
    </span>
  );
}

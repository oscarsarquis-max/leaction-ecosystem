const TONE: Record<string, string> = {
  open: "c-open",
  submitted: "c-open",
  accepted: "c-acc",
  confirmed: "c-acc",
  paid: "c-paid",
  in_production: "c-prod",
  "in-production": "c-prod",
  ready: "c-prod",
  delivered: "c-del",
  completed: "c-none",
  cancelled: "c-can",
  canceled: "c-can",
  rejected: "c-can",
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
    <span className={`admin-chip ${tone}`}>
      <span className="dot" aria-hidden="true" />
      {label}
    </span>
  );
}

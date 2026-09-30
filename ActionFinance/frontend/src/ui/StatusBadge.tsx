import type { Title } from "../api";
import { formatSettlementStatus } from "../money";

export function StatusBadge({ title }: { title: Title }) {
  const financial = formatSettlementStatus(title.settlementStatus ?? "NOT_APPLICABLE", title.direction);
  const label =
    title.status === "DRAFT"
      ? "Rascunho"
      : title.status === "CANCELLED"
        ? "Cancelado"
        : title.overdue
          ? `⚠ Vencido · ${financial}`
          : financial;
  const kind =
    title.status === "DRAFT"
      ? "draft"
      : title.status === "CANCELLED"
        ? "cancelled"
        : title.overdue
          ? "overdue"
          : title.settlementStatus === "SETTLED"
            ? "settled"
            : "open";
  return <span className={`status status--${kind}`}>{label}</span>;
}

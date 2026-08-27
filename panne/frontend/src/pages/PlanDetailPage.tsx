import { Link, useParams } from "react-router-dom";
import type { PlanDetail } from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import {
  formatDate,
  formatProcessingOrder,
  formatTargetQuantity,
  PROCESSING_ORDER_HELP,
  shiftLabel,
  statusLabel,
} from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { useOrganization } from "../session/OrganizationContext";

function targetModeLabel(mode: string): string {
  if (mode === "mass") return "Massa";
  if (mode === "units") return "Unidades";
  return mode;
}

function productLabel(item: PlanDetail["items"][number], _index: number): string {
  const name = item.product?.display_name?.trim();
  if (name) return name;
  return "Produto ausente";
}

export function PlanDetailPage() {
  const { planId = "" } = useParams();
  const { api, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const { state, reload } = useAsyncResource(
    async () => (await api.getPlan(planId)).data,
    [api, planId, orgId],
    Boolean(planId && orgId),
  );

  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={reload} />;
  if (state.kind !== "ok") return <LoadingState>Carregando plano…</LoadingState>;

  const plan = state.data;

  return (
    <article>
      <p>
        <Link to="/planejamento">← Planos</Link>
      </p>
      <h1>{plan.public_code}</h1>
      <p>
        <StatusBadge tone="neutro" label={statusLabel(plan.status)} /> {formatDate(plan.operational_date)} ·{" "}
        {shiftLabel(plan.shift)}
      </p>
      <section className="section">
        <h2>Itens planejados</h2>
        <table>
          <thead>
            <tr>
              <th>Produto</th>
              <th>Código</th>
              <th>Modo</th>
              <th>Quantidade</th>
              <th title={PROCESSING_ORDER_HELP}>Ordem de processamento</th>
            </tr>
          </thead>
          <tbody>
            {plan.items.map((item, index) => (
              <tr key={item.id}>
                <td>{productLabel(item, index)}</td>
                <td>{item.product?.code?.trim() || "—"}</td>
                <td>{targetModeLabel(item.target_mode)}</td>
                <td>{formatTargetQuantity(item.target_quantity, item.target_mode)}</td>
                <td title={PROCESSING_ORDER_HELP}>{formatProcessingOrder(item.priority)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="meta">{PROCESSING_ORDER_HELP}</p>
        <TechnicalAuditDetails
          title="Identificadores dos itens"
          purpose="IDs internos dos produtos técnicos deste plano."
          rows={plan.items.map((item, index) => ({
            label: productLabel(item, index),
            value: item.technical_product_id,
            copyable: true,
          }))}
        />
      </section>
    </article>
  );
}

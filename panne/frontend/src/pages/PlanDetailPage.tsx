import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { PlanDetail } from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { formatDate, formatDecimal, shiftLabel, statusLabel } from "../format";
import { useOrganization } from "../session/OrganizationContext";

export function PlanDetailPage() {
  const { planId = "" } = useParams();
  const { api } = useOrganization();
  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api
      .getPlan(planId)
      .then((response) => setPlan(response.data))
      .catch(setError);
  }, [api, planId]);

  if (error) return <ErrorState error={error} />;
  if (!plan) return <LoadingState>Carregando plano…</LoadingState>;

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
              <th>Produto técnico</th>
              <th>Modo</th>
              <th>Quantidade</th>
              <th>Prioridade</th>
            </tr>
          </thead>
          <tbody>
            {plan.items.map((item) => (
              <tr key={item.id}>
                <td>{item.technical_product_id}</td>
                <td>{item.target_mode}</td>
                <td>{formatDecimal(item.target_quantity)}</td>
                <td>{item.priority}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </article>
  );
}

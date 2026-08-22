import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { Plan } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { formatDate, shiftLabel, statusLabel } from "../format";
import { useOrganization } from "../session/OrganizationContext";

export function PlansPage() {
  const { api } = useOrganization();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [items, setItems] = useState<Plan[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [state, setState] = useState<"carregando" | "ok" | "erro">("carregando");
  const [error, setError] = useState<unknown>(null);
  const status = params.get("status") ?? "";

  async function load(next?: string | null, append = false) {
    setState("carregando");
    try {
      const page = await api.listPlans({ status: status || undefined, cursor: next ?? undefined });
      setItems((current) => (append ? [...current, ...page.items] : page.items));
      setCursor(page.next_cursor);
      setState("ok");
    } catch (err) {
      setError(err);
      setState("erro");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, status]);

  return (
    <section>
      <div className="page-head">
        <h1>Planos</h1>
      </div>
      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <label>
          Estado
          <select
            value={status}
            onChange={(event) => {
              const next = new URLSearchParams(params);
              if (event.target.value) next.set("status", event.target.value);
              else next.delete("status");
              setParams(next, { replace: true });
            }}
          >
            <option value="">Todos</option>
            <option value="draft">Rascunho</option>
            <option value="scheduled">Programado</option>
          </select>
        </label>
      </form>
      {state === "carregando" && items.length === 0 ? <LoadingState /> : null}
      {state === "erro" ? <ErrorState error={error} onRetry={() => void load()} /> : null}
      {state === "ok" && items.length === 0 ? <EmptyState>Nenhum plano nesta organização.</EmptyState> : null}
      {items.length > 0 ? (
        <div className="table-wrap">
          <table>
            <caption className="visually-hidden">Lista de planos</caption>
            <thead>
              <tr>
                <th>Código</th>
                <th>Data</th>
                <th>Turno</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {items.map((plan) => (
                <tr key={plan.id} tabIndex={0} onClick={() => navigate(`/planejamento/${plan.id}`)}>
                  <td>{plan.public_code}</td>
                  <td>{formatDate(plan.operational_date)}</td>
                  <td>{shiftLabel(plan.shift)}</td>
                  <td>
                    <StatusBadge tone="neutro" label={statusLabel(plan.status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {cursor ? (
        <button type="button" className="ghost" onClick={() => void load(cursor, true)}>
          Carregar mais
        </button>
      ) : null}
    </section>
  );
}

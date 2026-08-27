import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import type { Plan } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { formatDate, shiftLabel, statusLabel } from "../format";
import { useOrganization } from "../session/OrganizationContext";

function planSummary(plan: Plan): string {
  const summary = plan.items_summary?.trim();
  if (summary) return summary;
  const count = plan.item_count;
  if (count == null) return "—";
  if (count === 0) return "Nenhum item planejado";
  if (count === 1) return "1 item planejado";
  return `${count} itens planejados`;
}

export function PlansPage() {
  const { api, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [items, setItems] = useState<Plan[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [state, setState] = useState<"carregando" | "ok" | "erro">("carregando");
  const [error, setError] = useState<unknown>(null);
  const status = params.get("status") ?? "";

  async function load(next?: string | null, append = false) {
    setState("carregando");
    if (!append) {
      setItems([]);
      setCursor(null);
      setError(null);
    }
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
  }, [api, status, orgId]);

  return (
    <section>
      <ListLive
        kind={state}
        empty={state === "ok" && items.length === 0}
        entityLabel={items[0]?.public_code || "plano"}
        status={state === "ok" ? `${items.length} itens` : undefined}
      />
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
                <th>Conteúdo</th>
                <th>Código</th>
                <th>Data</th>
                <th>Turno</th>
                <th>Estado</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((plan) => {
                const detailTo = `/planejamento/${plan.id}`;
                const codeLabel = `Abrir detalhe do plano ${plan.public_code}`;
                const detailActionLabel = `Detalhe do plano ${plan.public_code}`;
                return (
                  <tr
                    key={plan.id}
                    onClick={(event) => {
                      const target = event.target as HTMLElement;
                      if (target.closest("a")) return;
                      navigate(detailTo);
                    }}
                  >
                    <td>{planSummary(plan)}</td>
                    <td>
                      <Link to={detailTo} aria-label={codeLabel}>
                        {plan.public_code}
                      </Link>
                    </td>
                    <td>{formatDate(plan.operational_date)}</td>
                    <td>{shiftLabel(plan.shift)}</td>
                    <td>
                      <StatusBadge tone="neutro" label={statusLabel(plan.status)} />
                    </td>
                    <td>
                      <Link to={detailTo} aria-label={detailActionLabel}>
                        Detalhe
                      </Link>
                    </td>
                  </tr>
                );
              })}
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

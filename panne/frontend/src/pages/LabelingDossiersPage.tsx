import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { LabelingDossier } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { useOrganization } from "../session/OrganizationContext";

function tone(status: string) {
  if (status === "reviewed") return "info" as const;
  if (status === "invalidated") return "erro" as const;
  if (status === "evaluated") return "atencao" as const;
  return "neutro" as const;
}

export function LabelingDossiersPage() {
  const { api, hasPermission, active } = useOrganization();
  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; items: LabelingDossier[]; total: number }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });

  useEffect(() => {
    if (!active) return;
    let alive = true;
    setState({ kind: "carregando" });
    api
      .listLabelingDossiers()
      .then((page) => {
        if (alive) setState({ kind: "ok", items: page.items, total: page.total });
      })
      .catch((error) => {
        if (alive) setState({ kind: "erro", error });
      });
    return () => {
      alive = false;
    };
  }, [api, active]);

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && state.items.length === 0}
        entityLabel="dossiê"
        status={state.kind === "ok" ? `${state.items.length} itens` : undefined}
      />
      <div>
        <h1>Dossiês de rotulagem</h1>
        <p className="lede">
          {hasPermission("labeling.dossier.create") ? (
            <Link className="primary" to="/conformidade/dossies/novo">
              Novo dossiê
            </Link>
          ) : (
            "criação oculta neste papel"
          )}
        </p>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} /> : null}
        {state.kind === "ok" && state.items.length === 0 ? (
          <EmptyState>Não há dossiês nesta organização.</EmptyState>
        ) : null}
        {state.kind === "ok" ? (
          <ul className="list">
            {state.items.map((item) => (
              <li key={item.id}>
                <Link to={`/conformidade/dossies/${item.id}`}>
                  Dossiê {item.id.slice(0, 8)}
                </Link>
                <StatusBadge tone={tone(item.status)} label={item.status} />
                <p className="meta">{item.disclaimer}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

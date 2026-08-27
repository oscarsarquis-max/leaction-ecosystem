import { Link } from "react-router-dom";
import type { LabelingDossier } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { formatDateTime } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { dossierStatusLabel } from "../language/labeling";
import { useOrganization } from "../session/OrganizationContext";

function tone(status: string) {
  if (status === "reviewed") return "info" as const;
  if (status === "invalidated") return "erro" as const;
  if (status === "evaluated") return "atencao" as const;
  return "neutro" as const;
}

function dossierTitle(item: LabelingDossier): string {
  const name = item.formulation?.display_name?.trim();
  if (name) return name;
  const code = item.formulation?.code?.trim();
  if (code) return `Receita ${code}`;
  return "Dossiê sem nome de receita";
}

function nextAction(status: string): string {
  if (status === "draft") return "Preencher perfil e avaliar";
  if (status === "evaluated") return "Revisão humana";
  if (status === "reviewed") return "Conferir e arquivar";
  if (status === "invalidated") return "Abrir nova versão se necessário";
  return "Abrir dossiê";
}

export function LabelingDossiersPage() {
  const { api, hasPermission, active } = useOrganization();
  const { state } = useAsyncResource(
    async () => {
      const page = await api.listLabelingDossiers();
      return { items: page.items, total: page.total };
    },
    [api, active?.organization_id],
    Boolean(active),
  );

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && state.data.items.length === 0}
        entityLabel="dossiê"
        status={state.kind === "ok" ? `${state.data.items.length} itens` : undefined}
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
        {state.kind === "ok" && state.data.items.length === 0 ? (
          <EmptyState>Não há dossiês nesta organização.</EmptyState>
        ) : null}
        {state.kind === "ok" ? (
          <ul className="list">
            {state.data.items.map((item) => (
              <li key={item.id}>
                <Link to={`/conformidade/dossies/${item.id}`}>{dossierTitle(item)}</Link>
                <StatusBadge tone={tone(item.status)} label={dossierStatusLabel(item.status)} />
                <p className="meta">
                  {item.formulation?.code ? `Código ${item.formulation.code} · ` : ""}
                  {item.formulation_version?.version_number != null
                    ? `versão ${item.formulation_version.version_number} · `
                    : ""}
                  {item.created_at ? `${formatDateTime(item.created_at)} · ` : ""}
                  {nextAction(item.status)}
                </p>
                <p className="meta">{item.disclaimer}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

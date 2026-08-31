import { useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import type { FiscalDocumentCard, FiscalDocumentPage } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { formatDate } from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  FISCAL_STATUS_FILTERS,
  fiscalDocumentTitle,
  fiscalFilterLabel,
  fiscalOriginLabel,
  fiscalProgressSentence,
  fiscalStatusFromSlug,
  fiscalStatusLabel,
  fiscalStatusTone,
  fiscalSupplierLabel,
} from "../language/fiscal";
import { canCaptureFiscalDocument } from "../session/fiscalAccess";
import { useOrganization } from "../session/OrganizationContext";

export function FiscalInboxPage() {
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const situacao = params.get("situacao") ?? "";

  const query = useMemo(
    () => ({
      status: fiscalStatusFromSlug(situacao),
      limit: params.get("limit") || "20",
      offset: params.get("offset") || "0",
    }),
    [params, situacao],
  );

  const { state } = useAsyncResource<FiscalDocumentPage>(
    () => api.listFiscalDocuments(query),
    [api, query, orgId],
    Boolean(orgId),
  );

  const offset = Number(query.offset ?? 0);
  const limit = Number(query.limit ?? 20);
  const total = state.kind === "ok" ? state.data.total : 0;
  const items = state.kind === "ok" ? state.data.items : [];
  const canCreate = canCaptureFiscalDocument(hasPermission);

  function applyFilters(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setParams({ situacao: String(data.get("situacao") ?? ""), offset: "0" });
  }

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && items.length === 0}
        entityLabel="entrada fiscal"
        status={state.kind === "ok" ? `${total} entradas` : undefined}
        next="Registrar entrada ou abrir um documento para conferir."
      />
      <div>
        <div className="page-head">
          <div>
            <h1>Entradas fiscais</h1>
          </div>
        </div>
        <p className="lede">
          Toda mercadoria que chega passa por aqui: o documento do fornecedor, a correspondência com
          o cadastro da Panne, a conferência do que realmente chegou e, só então, o estoque.
        </p>
        <p>
          {canCreate ? (
            <Link className="primary" to="/gestao/compras/entradas/nova">
              Registrar entrada
            </Link>
          ) : (
            "Registro de entrada oculto neste papel."
          )}{" "}
          <Link className="ghost" to="/gestao/compras/recebimentos">
            Recebimentos por pedido
          </Link>
        </p>
        <form className="filters" onSubmit={applyFilters}>
          <label>
            Situação
            <select name="situacao" defaultValue={situacao}>
              {FISCAL_STATUS_FILTERS.map((option) => (
                <option key={option.slug || "todas"} value={option.slug}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" className="primary">
            Filtrar
          </button>
        </form>
        {situacao ? (
          <p className="meta" role="status">
            Recorte atual: <strong>{fiscalFilterLabel(situacao)}</strong>
          </p>
        ) : null}
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} /> : null}
        {state.kind === "ok" && items.length === 0 ? (
          <EmptyState>
            Nenhuma entrada neste recorte. Registre uma entrada ou limpe o filtro de situação.
          </EmptyState>
        ) : null}
        {items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <caption>Entradas por documento fiscal</caption>
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Fornecedor</th>
                  <th>Emissão</th>
                  <th>Origem do registro</th>
                  <th>Andamento</th>
                  <th>Situação</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <FiscalRow key={item.id} item={item} onRowNavigate={(to) => navigate(to)} />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {state.kind === "ok" && total > limit ? (
          <p>
            <button
              type="button"
              disabled={offset <= 0}
              onClick={() =>
                setParams({ ...Object.fromEntries(params), offset: String(Math.max(0, offset - limit)) })
              }
            >
              Anterior
            </button>{" "}
            <button
              type="button"
              disabled={offset + limit >= total}
              onClick={() => setParams({ ...Object.fromEntries(params), offset: String(offset + limit) })}
            >
              Seguinte
            </button>
          </p>
        ) : null}
      </div>
      <aside className="panel">
        <h2>Como ler esta lista</h2>
        <p>
          <StatusBadge tone="atencao" label="Aguardando correspondência" /> o documento chegou, mas
          os itens do fornecedor ainda não foram ligados ao cadastro da Panne.
        </p>
        <p>
          <StatusBadge tone="atencao" label="Aguardando conferência" /> falta registrar o que
          realmente chegou na doca.
        </p>
        <p>
          <StatusBadge tone="erro" label="Com divergência" /> a conferência apontou diferença entre o
          documento e a mercadoria.
        </p>
        <p>
          <StatusBadge tone="sucesso" label="Entrada confirmada" /> o estoque já foi atualizado por
          esta entrada.
        </p>
        <p className="meta">
          Registrar o documento não movimenta estoque. O saldo só muda na confirmação da entrada.
        </p>
      </aside>
    </div>
  );
}

function FiscalRow({
  item,
  onRowNavigate,
}: {
  item: FiscalDocumentCard;
  onRowNavigate: (to: string) => void;
}) {
  const detailTo = `/gestao/compras/entradas/${item.id}`;
  const title = fiscalDocumentTitle(item);
  const supplier = fiscalSupplierLabel(item.supplier);

  return (
    <tr
      onClick={(event) => {
        const target = event.target as HTMLElement;
        if (target.closest("a")) return;
        onRowNavigate(detailTo);
      }}
    >
      <td>
        <Link to={detailTo} aria-label={`Abrir ${title}`}>
          {title}
        </Link>
      </td>
      <td>{supplier}</td>
      <td>{formatDate(item.issued_on)}</td>
      <td>{fiscalOriginLabel(item.origin)}</td>
      <td>{fiscalProgressSentence(item)}</td>
      <td>
        <StatusBadge
          tone={fiscalStatusTone(item.status)}
          label={item.status_label?.trim() || fiscalStatusLabel(item.status)}
        />
      </td>
      <td>
        <Link to={detailTo} aria-label={`Conferir ${title} de ${supplier}`}>
          Conferir
        </Link>
      </td>
    </tr>
  );
}

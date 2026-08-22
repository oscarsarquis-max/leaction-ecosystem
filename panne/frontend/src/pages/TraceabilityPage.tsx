import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { Traceability } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { formatDecimal, formatDateTime, statusLabel } from "../format";
import { useOrganization } from "../session/OrganizationContext";

export function TraceabilityHubPage() {
  const { orderId } = useParams();
  const [code, setCode] = useState(orderId ?? "");

  return (
    <section className="feedback">
      <h1>Rastreabilidade</h1>
      <p>Informe o identificador da ordem. Sem permissão, o acesso é negado — não uma tela vazia.</p>
      <label>
        Identificador da ordem
        <input value={code} onChange={(event) => setCode(event.target.value)} />
      </label>
      {code ? <p><Link to={`/rastreabilidade/${code}`}>Abrir rastreio</Link></p> : null}
    </section>
  );
}

export function TraceabilityPage() {
  const { orderId = "" } = useParams();
  const { api, hasPermission } = useOrganization();
  const [data, setData] = useState<Traceability | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!hasPermission("production.traceability.read")) {
      setError(new ApiError("nao_autorizado", "Você não tem permissão para este recurso.", 403));
      return;
    }
    api
      .getTraceability(orderId)
      .then((response) => setData(response.data))
      .catch(setError);
  }, [api, hasPermission, orderId]);

  if (error) return <ErrorState error={error} />;
  if (!data) return <LoadingState>Carregando rastreabilidade…</LoadingState>;

  return (
    <article>
      <h1>Rastreabilidade {data.order.public_code}</h1>
      <section className="section">
        <h2>Formulação e escala</h2>
        <p>Formulação {data.order.formulation_version_id ?? "não informada no rastreio"}</p>
        <p>Escala {data.order.scale_calculation_id ?? "não informada no rastreio"}</p>
        <p className="hashes">
          {data.order.snapshot_hash} · {data.order.materials_hash} · {data.order.steps_hash}
        </p>
      </section>
      <section className="section planned">
        <h2>Materiais planejados</h2>
        {data.planned_materials.map((item) => (
          <p key={item.id}>
            {item.name}: {formatDecimal(item.gross)} {item.unit}
          </p>
        ))}
      </section>
      <section className="section actual">
        <h2>Pesagens, lotes e consumos</h2>
        {data.weighings.map((item) => (
          <p key={item.id}>
            lote {item.lot_code ?? "—"} · {formatDecimal(item.entered_quantity)} {item.entered_unit} →{" "}
            {formatDecimal(item.canonical_quantity)} {item.canonical_unit} · operador {item.operator_user_id}
          </p>
        ))}
        {data.consumptions.map((item) => (
          <p key={item.id}>
            {item.type}: {formatDecimal(item.canonical_quantity)} {item.canonical_unit}
          </p>
        ))}
      </section>
      <section className="section">
        <h2>Etapas, rendimentos e ocorrências</h2>
        {data.step_runs.map((item) => (
          <p key={item.id}>
            {statusLabel(item.status)} · operador {item.operator_user_id ?? "—"}
          </p>
        ))}
        {data.yields.map((item) => (
          <p key={item.id}>
            {item.type}: {formatDecimal(item.quantity)}
          </p>
        ))}
        {data.occurrences.map((item) => (
          <p key={item.id}>
            {item.category} · {statusLabel(item.status)}
          </p>
        ))}
      </section>
      <section className="section">
        <h2>Dependências, overrides, emissões e eventos</h2>
        {data.dependencies.map((item) => (
          <p key={item.id}>
            {item.type} → {item.predecessor_order_id}
          </p>
        ))}
        {data.overrides.map((item) => (
          <p key={item.id}>{item.reason}</p>
        ))}
        {data.sheet_issues.map((item) => (
          <p key={item.id}>
            <Link to={`/ordens/${orderId}/fichas/${item.id}`}>Emissão {item.issue_number}</Link>
          </p>
        ))}
        {data.events.map((item) => (
          <p key={item.id}>
            {formatDateTime(item.occurred_at)} · {item.type}
          </p>
        ))}
      </section>
    </article>
  );
}

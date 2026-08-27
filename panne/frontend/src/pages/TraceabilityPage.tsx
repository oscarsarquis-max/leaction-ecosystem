import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { ApiError } from "../api/errors";
import type { Traceability } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import {
  CONSUMPTION_LABEL,
  catalogLabel,
  formatDateTime,
  OCCURRENCE_LABEL,
  statusLabel,
  YIELD_LABEL,
} from "../format";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { dependencyTypeLabel, eventLabel } from "../language/events";
import { formatOperationalQuantity, integrityStatus } from "../language/quantities";
import { useOrganization } from "../session/OrganizationContext";

export function TraceabilityHubPage() {
  const { orderId } = useParams();
  const [code, setCode] = useState(orderId ?? "");

  return (
    <section className="feedback">
      <h1>Rastreabilidade</h1>
      <p>
        Informe o código público da ordem (ex.: ORD-20260824-0004) ou o link recebido. Sem permissão, o
        acesso é negado.
      </p>
      <label>
        Código da ordem
        <input value={code} onChange={(event) => setCode(event.target.value)} placeholder="ORD-…" />
      </label>
      {code ? (
        <p>
          <Link to={`/rastreabilidade/${code}`}>Abrir rastreio</Link>
        </p>
      ) : null}
    </section>
  );
}

export function TraceabilityPage() {
  const { orderId = "" } = useParams();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const allowed = hasPermission("production.traceability.read");

  const { state, reload } = useAsyncResource(
    async () => {
      if (!allowed) {
        throw new ApiError("nao_autorizado", "Você não tem permissão para este recurso.", 403);
      }
      return (await api.getTraceability(orderId)).data;
    },
    [api, allowed, orderId, orgId],
    Boolean(orderId && orgId),
  );

  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={reload} />;
  if (state.kind !== "ok") return <LoadingState>Carregando rastreabilidade…</LoadingState>;

  const data: Traceability = state.data;
  const operatorIds = [
    ...new Set(
      [
        ...data.weighings.map((item) => item.operator_user_id),
        ...data.step_runs.map((item) => item.operator_user_id).filter(Boolean),
        ...data.verifications.map((item) => item.verifier_user_id),
      ].filter((value): value is string => Boolean(value)),
    ),
  ];

  return (
    <article>
      <h1>Rastreabilidade {data.order.public_code}</h1>
      <section className="section integrity-summary">
        <h2>Integridade da ficha</h2>
        <ul>
          <li>Materiais: {integrityStatus(data.order.materials_hash)}</li>
          <li>Etapas: {integrityStatus(data.order.steps_hash)}</li>
          <li>Registro da ordem: {data.order.snapshot_hash ? "preservado" : "ainda sem registro"}</li>
          <li>
            Formulação e escala:{" "}
            {data.order.formulation_version_id || data.order.scale_calculation_id
              ? "registradas (ver detalhes técnicos)"
              : "não informadas neste rastreio"}
          </li>
        </ul>
      </section>
      <TechnicalAuditDetails
        rows={[
          {
            label: "Hash dos materiais",
            value: data.order.materials_hash ?? "—",
            copyable: Boolean(data.order.materials_hash),
          },
          {
            label: "Hash das etapas",
            value: data.order.steps_hash ?? "—",
            copyable: Boolean(data.order.steps_hash),
          },
          {
            label: "Hash do registro",
            value: data.order.snapshot_hash ?? "—",
            copyable: Boolean(data.order.snapshot_hash),
          },
          {
            label: "Identificador da ordem",
            value: data.order.id,
            copyable: true,
          },
        ]}
      />

      <section className="section planned">
        <h2>Materiais planejados</h2>
        {data.planned_materials.map((item) => (
          <p key={item.id}>
            {item.name}: {formatOperationalQuantity(item.gross, item.unit)}
          </p>
        ))}
      </section>

      <section className="section actual">
        <h2>Pesagens, lotes e consumos</h2>
        {data.weighings.map((item) => (
          <p key={item.id}>
            lote {item.lot_code ?? "—"} ·{" "}
            {formatOperationalQuantity(item.entered_quantity, item.entered_unit)} →{" "}
            {formatOperationalQuantity(item.canonical_quantity, item.canonical_unit)}
          </p>
        ))}
        {data.consumptions.map((item) => (
          <p key={item.id}>
            {catalogLabel(CONSUMPTION_LABEL, item.type)}:{" "}
            {formatOperationalQuantity(item.canonical_quantity, item.canonical_unit)}
          </p>
        ))}
      </section>

      <section className="section">
        <h2>Etapas, rendimentos e ocorrências</h2>
        {data.step_runs.map((item) => (
          <p key={item.id}>{statusLabel(item.status)}</p>
        ))}
        {data.yields.map((item) => (
          <p key={item.id}>
            {catalogLabel(YIELD_LABEL, item.type)}: {formatOperationalQuantity(item.quantity)}
          </p>
        ))}
        {data.occurrences.map((item) => (
          <p key={item.id}>
            {catalogLabel(OCCURRENCE_LABEL, item.category)} · {statusLabel(item.status)}
          </p>
        ))}
      </section>

      <section className="section">
        <h2>Dependências, emissões e eventos</h2>
        {data.dependencies.map((item) => (
          <p key={item.id}>{dependencyTypeLabel(item.type)} de outra ordem</p>
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
            {eventLabel(item.type)} · {formatDateTime(item.occurred_at)}
          </p>
        ))}
        <TechnicalAuditDetails
          title="Códigos técnicos dos eventos"
          purpose="Códigos internos para suporte e auditoria."
          rows={data.events.map((item) => ({
            label: eventLabel(item.type),
            value: item.type,
            copyable: true,
          }))}
        />
        {data.dependencies.length > 0 ? (
          <TechnicalAuditDetails
            title="Dependências técnicas"
            purpose="Identificadores das ordens predecessoras."
            rows={data.dependencies.map((item, index) => ({
              label: `Predecessora ${index + 1}`,
              value: item.predecessor_order_id,
              copyable: true,
            }))}
          />
        ) : null}
        {operatorIds.length > 0 ? (
          <TechnicalAuditDetails
            title="Operadores (auditoria)"
            purpose="Identificadores internos de operadores neste rastreio."
            rows={operatorIds.map((id, index) => ({
              label: `Operador ${index + 1}`,
              value: id,
              copyable: true,
            }))}
          />
        ) : null}
      </section>
    </article>
  );
}

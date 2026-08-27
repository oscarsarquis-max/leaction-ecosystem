import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import type {
  Consumption,
  Dependency,
  EventRow,
  MaterialsView,
  Occurrence,
  Order,
  SheetSummary,
  StepsView,
  WeighingsView,
  YieldRow,
} from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { isCancelledError } from "../api/errors";
import {
  CONSUMPTION_LABEL,
  catalogLabel,
  formatDateTime,
  formatTargetQuantity,
  OCCURRENCE_LABEL,
  statusLabel,
  YIELD_LABEL,
} from "../format";
import { dependencyTypeLabel, eventLabel } from "../language/events";
import { formatExactQuantity, formatOperationalQuantity, integrityStatus } from "../language/quantities";
import { canOfferFloorExecution } from "../orderListActions";
import { useOrganization } from "../session/OrganizationContext";

type Detail = {
  order: Order;
  materials: MaterialsView;
  steps: StepsView;
  weighings: WeighingsView;
  consumptions: Consumption[];
  yields: YieldRow[];
  occurrences: Occurrence[];
  dependencies: Dependency[];
  events: EventRow[];
  sheets: SheetSummary[];
};

export function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [partial, setPartial] = useState(false);
  const fromStatus = searchParams.get("from_status");
  const backToOrders = fromStatus ? `/ordens?status=${encodeURIComponent(fromStatus)}` : "/ordens";
  const canExecute = (status: string) => canOfferFloorExecution(status, hasPermission);

  useEffect(() => {
    let ativo = true;
    setDetail(null);
    setError(null);
    setPartial(false);
    async function load() {
      try {
        const order = (await api.getOrder(orderId)).data;
        const extras = await Promise.allSettled([
          api.getMaterials(orderId),
          api.getSteps(orderId),
          api.getWeighings(orderId),
          api.getConsumptions(orderId),
          api.getYields(orderId),
          api.getOccurrences(orderId),
          api.getDependencies(orderId),
          api.getEvents(orderId),
          api.getSheets(orderId),
        ]);
        if (!ativo) return;
        const value = <T,>(index: number, fallback: T): T => {
          const item = extras[index];
          if (item.status !== "fulfilled") return fallback;
          return "data" in item.value ? (item.value.data as T) : (item.value as T);
        };
        const eventsResult = extras[7];
        const events =
          eventsResult.status === "fulfilled" && "items" in eventsResult.value
            ? eventsResult.value.items
            : [];
        setPartial(extras.some((item) => item.status === "rejected"));
        setDetail({
          order,
          materials: value(0, { planned: [], actual: [] }),
          steps: value(1, { planned: [], actual: [] }),
          weighings: value(2, { entries: [], verifications: [] }),
          consumptions: value(3, []),
          yields: value(4, []),
          occurrences: value(5, []),
          dependencies: value(6, []),
          events,
          sheets: value(8, []),
        });
      } catch (err) {
        if (ativo && !isCancelledError(err)) setError(err);
      }
    }
    if (orderId && orgId) void load();
    return () => {
      ativo = false;
    };
  }, [api, orderId, orgId]);

  if (error) return <ErrorState error={error} />;
  if (!detail) return <LoadingState>Carregando ordem…</LoadingState>;

  const events = Array.isArray(detail.events) ? detail.events : [];
  const order = detail.order;

  return (
    <article>
      <p>
        <Link to={backToOrders}>← Ordens</Link>
        {canExecute(order.status) ? (
          <>
            {" · "}
            <Link to={`/producao/ordens/${orderId}/executar`}>Executar</Link>
          </>
        ) : null}
      </p>
      <h1>{order.public_code}</h1>
      <p>
        {order.product?.display_name?.trim() || "Produto ausente"}
        {" · "}
        <StatusBadge tone="neutro" label={statusLabel(order.status)} /> alvo{" "}
        {formatTargetQuantity(order.target_quantity, order.target_mode)} · prioridade {order.priority}
      </p>
      {order.plan?.public_code || order.plan_id ? (
        <p>
          Plano:{" "}
          {order.plan?.id ? (
            <Link to={`/planejamento/${order.plan.id}`}>
              {order.plan.public_code || "Plano sem código legível"}
            </Link>
          ) : order.plan_id ? (
            <Link to={`/planejamento/${order.plan_id}`}>Plano sem código legível</Link>
          ) : null}
        </p>
      ) : null}
      {partial ? (
        <p role="status">Alguns blocos chegaram incompletos. Os registros visíveis não foram alterados.</p>
      ) : null}

      <section className="section integrity-summary">
        <h2>Integridade da ficha</h2>
        <ul>
          <li>Materiais: {integrityStatus(order.materials_hash)}</li>
          <li>Etapas: {integrityStatus(order.steps_hash)}</li>
          <li>Registro da ordem: {order.snapshot_hash ? "preservado" : "ainda sem registro"}</li>
        </ul>
      </section>

      <TechnicalAuditDetails
        rows={[
          { label: "Hash dos materiais", value: order.materials_hash ?? "—", copyable: Boolean(order.materials_hash) },
          { label: "Hash das etapas", value: order.steps_hash ?? "—", copyable: Boolean(order.steps_hash) },
          { label: "Hash do registro", value: order.snapshot_hash ?? "—", copyable: Boolean(order.snapshot_hash) },
          { label: "Identificador interno da ordem", value: order.id, copyable: true },
          ...(order.plan_id
            ? [{ label: "Identificador interno do plano", value: order.plan_id, copyable: true }]
            : []),
        ]}
      />

      <div className="grid-2">
        <section className="section planned">
          <h2>Materiais planejados</h2>
          <ul>
            {detail.materials.planned.map((item) => (
              <li key={item.id}>
                {item.name}: {formatOperationalQuantity(item.gross, item.unit)}
              </li>
            ))}
          </ul>
        </section>
        <section className="section actual">
          <h2>Materiais realizados</h2>
          <ul>
            {detail.materials.actual.map((item) => (
              <li key={item.id}>
                pesado {formatOperationalQuantity(item.weighed_canonical, "g")} · consumo{" "}
                {formatOperationalQuantity(item.consumption.use, "g")}
              </li>
            ))}
          </ul>
        </section>
      </div>
      <div className="grid-2">
        <section className="section planned">
          <h2>Etapas planejadas</h2>
          <ol>
            {detail.steps.planned.map((item) => (
              <li key={item.id}>{item.title}</li>
            ))}
          </ol>
        </section>
        <section className="section actual">
          <h2>Etapas realizadas</h2>
          <ul>
            {detail.steps.actual.map((item) => (
              <li key={item.id}>{statusLabel(item.status)}</li>
            ))}
          </ul>
        </section>
      </div>
      <section className="section">
        <h2>Pesagens e conferências</h2>
        {detail.weighings.entries.map((entry) => (
          <p key={entry.id}>
            informado {formatOperationalQuantity(entry.entered_quantity, entry.entered_unit)} → canônico{" "}
            {formatOperationalQuantity(entry.canonical_quantity, entry.canonical_unit)}
          </p>
        ))}
        {detail.weighings.verifications.map((item) => (
          <p key={item.id}>Conferência {statusLabel(item.decision)}</p>
        ))}
      </section>
      <section className="section">
        <h2>Consumos e rendimento</h2>
        {detail.consumptions.map((item) => (
          <p key={item.id}>
            {catalogLabel(CONSUMPTION_LABEL, item.type)}:{" "}
            {formatOperationalQuantity(item.entered_quantity, item.entered_unit)}
          </p>
        ))}
        {detail.yields.map((item) => (
          <p key={item.id}>
            {catalogLabel(YIELD_LABEL, item.type)}: {formatOperationalQuantity(item.quantity, "g")}
          </p>
        ))}
      </section>
      <section className="section">
        <h2>Ocorrências e dependências</h2>
        {detail.occurrences.map((item) => (
          <p key={item.id} className={item.status === "open" ? "blocked" : undefined}>
            {catalogLabel(OCCURRENCE_LABEL, item.category)} · {statusLabel(item.status)}
          </p>
        ))}
        {detail.dependencies.map((item) => (
          <p key={item.id}>
            {dependencyTypeLabel(item.dependency_type)} · ordem relacionada (ver detalhes técnicos)
          </p>
        ))}
        {detail.dependencies.length > 0 ? (
          <TechnicalAuditDetails
            title="Dependências — identificadores"
            purpose="Códigos internos das ordens predecessoras, para suporte."
            rows={detail.dependencies.map((item, index) => ({
              label: `Predecessora ${index + 1}`,
              value: item.predecessor_order_id,
              copyable: true,
            }))}
          />
        ) : null}
      </section>
      <section className="section">
        <h2>Histórico e emissões</h2>
        {events.map((item) => (
          <p key={item.id}>
            {formatDateTime(item.occurred_at)} · {eventLabel(item.type)}
          </p>
        ))}
        {events.length > 0 ? (
          <TechnicalAuditDetails
            title="Códigos técnicos dos eventos"
            purpose="Nome interno do evento, para auditoria e suporte."
            rows={events.map((item, index) => ({
              label: `Evento ${index + 1} (${formatDateTime(item.occurred_at)})`,
              value: item.type,
              copyable: true,
            }))}
          />
        ) : null}
        {detail.sheets.map((item) => (
          <p key={item.id}>
            <Link to={`/ordens/${orderId}/fichas/${item.id}`}>Ficha {item.issue_number}</Link>
          </p>
        ))}
        <p>
          <Link to={`/rastreabilidade/${orderId}`}>Abrir rastreabilidade</Link>
        </p>
      </section>

      {detail.materials.planned.some((item) => (item.gross ?? "").includes(".")) ||
      detail.materials.actual.length > 0 ? (
        <TechnicalAuditDetails
          title="Quantidades com precisão integral"
          purpose="Valores exatamente como registrados. A lista acima usa arredondamento só visual."
          rows={[
            ...detail.materials.planned.map((item) => ({
              label: `${item.name} (planejado)`,
              value: formatExactQuantity(item.gross, item.unit),
            })),
            ...detail.materials.actual.map((item, index) => ({
              label: `Realizado ${index + 1}`,
              value: `${formatExactQuantity(item.weighed_canonical, "g")} · consumo ${formatExactQuantity(item.consumption.use, "g")}`,
            })),
          ]}
        />
      ) : null}
    </article>
  );
}

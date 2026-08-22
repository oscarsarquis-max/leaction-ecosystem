import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
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
import { formatDecimal, formatDateTime, statusLabel } from "../format";
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
  const { api } = useOrganization();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [partial, setPartial] = useState(false);

  useEffect(() => {
    let ativo = true;
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
        if (ativo) setError(err);
      }
    }
    void load();
    return () => {
      ativo = false;
    };
  }, [api, orderId]);

  if (error) return <ErrorState error={error} />;
  if (!detail) return <LoadingState>Carregando ordem…</LoadingState>;

  const events = Array.isArray(detail.events) ? detail.events : [];

  return (
    <article>
      <p>
        <Link to="/ordens">← Ordens</Link>
      </p>
      <h1>{detail.order.public_code}</h1>
      <p>
        <StatusBadge tone="neutro" label={statusLabel(detail.order.status)} /> alvo{" "}
        {formatDecimal(detail.order.target_quantity)} · prioridade {detail.order.priority}
      </p>
      {detail.order.plan_id ? (
        <p>
          Plano: <Link to={`/planejamento/${detail.order.plan_id}`}>{detail.order.plan_id}</Link>
        </p>
      ) : null}
      {partial ? (
        <p role="status">Alguns blocos chegaram incompletos. Os snapshots visíveis não foram editados.</p>
      ) : null}
      <section className="section hashes">
        <h2>Área técnica</h2>
        <p>Materiais {detail.order.materials_hash ?? "—"}</p>
        <p>Etapas {detail.order.steps_hash ?? "—"}</p>
        <p>Snapshot {detail.order.snapshot_hash ?? "—"}</p>
      </section>
      <div className="grid-2">
        <section className="section planned">
          <h2>Materiais planejados</h2>
          <ul>
            {detail.materials.planned.map((item) => (
              <li key={item.id}>
                {item.name}: {formatDecimal(item.gross)} {item.unit}
              </li>
            ))}
          </ul>
        </section>
        <section className="section actual">
          <h2>Materiais realizados</h2>
          <ul>
            {detail.materials.actual.map((item) => (
              <li key={item.id}>
                pesado {formatDecimal(item.weighed_canonical)} g · consumo {formatDecimal(item.consumption.use)}
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
            informado {formatDecimal(entry.entered_quantity)} {entry.entered_unit} → canônico{" "}
            {formatDecimal(entry.canonical_quantity)} {entry.canonical_unit}
          </p>
        ))}
        {detail.weighings.verifications.map((item) => (
          <p key={item.id}>
            Conferência {statusLabel(item.decision)}
          </p>
        ))}
      </section>
      <section className="section">
        <h2>Consumos e rendimento</h2>
        {detail.consumptions.map((item) => (
          <p key={item.id}>
            {item.type}: {formatDecimal(item.entered_quantity)} {item.entered_unit}
          </p>
        ))}
        {detail.yields.map((item) => (
          <p key={item.id}>
            {item.type}: {formatDecimal(item.quantity)}
          </p>
        ))}
      </section>
      <section className="section">
        <h2>Ocorrências e dependências</h2>
        {detail.occurrences.map((item) => (
          <p key={item.id} className={item.status === "open" ? "blocked" : undefined}>
            {item.category} · {statusLabel(item.status)}
          </p>
        ))}
        {detail.dependencies.map((item) => (
          <p key={item.id}>
            depende de {item.predecessor_order_id} ({item.dependency_type})
          </p>
        ))}
      </section>
      <section className="section">
        <h2>Histórico e emissões</h2>
        {events.map((item) => (
          <p key={item.id}>
            {formatDateTime(item.occurred_at)} · {item.type}
          </p>
        ))}
        {detail.sheets.map((item) => (
          <p key={item.id}>
            <Link to={`/ordens/${orderId}/fichas/${item.id}`}>Ficha {item.issue_number}</Link>
          </p>
        ))}
        <p>
          <Link to={`/rastreabilidade/${orderId}`}>Abrir rastreabilidade</Link>
        </p>
      </section>
    </article>
  );
}

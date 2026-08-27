import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ApiError, isCancelledError } from "../api/errors";
import type { ReportIndicator, ReportPayload, ReportSnapshot, SavedReportView } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { ReportingMentor } from "../components/ReportingMentor";
import { TechnicalAuditDetails } from "../components/TechnicalAuditDetails";
import { useOrganization } from "../session/OrganizationContext";

const REPORTS: Array<{ code: string; path: string; title: string; permission: string }> = [
  { code: "executive", path: "/gestao/relatorios/executivo", title: "Visão executiva", permission: "reporting.dashboard.read" },
  { code: "production", path: "/gestao/relatorios/producao", title: "Produção", permission: "reporting.production.read" },
  { code: "consumption", path: "/gestao/relatorios/componentes", title: "Componentes e perdas", permission: "reporting.production.read" },
  { code: "costing", path: "/gestao/relatorios/custos", title: "Custos e preços", permission: "reporting.costing.read" },
  { code: "compliance", path: "/gestao/relatorios/conformidade", title: "Conformidade", permission: "reporting.compliance.read" },
  { code: "traceability", path: "/gestao/relatorios/rastreabilidade", title: "Rastreabilidade", permission: "reporting.traceability.read" },
  { code: "inventory", path: "/gestao/relatorios/estoque", title: "Estoque e compras", permission: "reporting.inventory.read" },
  { code: "data_quality", path: "/gestao/relatorios/qualidade", title: "Qualidade dos dados", permission: "reporting.data_quality.read" },
];

function tone(status: string): "sucesso" | "atencao" | "erro" | "info" {
  if (status === "available") return "sucesso";
  if (status === "known_zero") return "info";
  if (status === "unavailable") return "atencao";
  return "erro";
}

const GROUP_LABELS: Record<string, string> = {
  planned: "Planejadas",
  released: "Liberadas",
  in_execution: "Em execução",
  completed: "Concluídas",
  short_closed: "Encerradas parcialmente",
  cancelled: "Canceladas",
};

function CompositionChart({ item }: { item: ReportIndicator }) {
  const groups = item.by_group;
  if (!groups) return null;
  const entries = Object.entries(groups);
  const max = Math.max(1, ...entries.map(([, value]) => value));
  return (
    <figure className="chart-block">
      <figcaption>Composição por estado — alternativa tabular abaixo. Cor não é o único indicador.</figcaption>
      <ul className="bar-chart" aria-hidden="true">
        {entries.map(([key, value]) => (
          <li key={key}>
            <span>{GROUP_LABELS[key] ?? key}</span>
            <span className="bar-track">
              <span className="bar-fill" style={{ width: `${(value / max) * 100}%` }} />
            </span>
            <span>{value}</span>
          </li>
        ))}
      </ul>
      <table>
        <caption>Tabela equivalente da composição</caption>
        <thead>
          <tr>
            <th scope="col">Estado</th>
            <th scope="col">Quantidade</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([key, value]) => (
            <tr key={key}>
              <td>{GROUP_LABELS[key] ?? key}</td>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

function IndicatorCard({ item, onDrill }: { item: ReportIndicator; onDrill: () => void }) {
  return (
    <article className="card">
      <h2>{item.name}</h2>
      <p>
        <StatusBadge tone={tone(item.status)} label={item.status === "available" ? "disponível" : item.status === "known_zero" ? "zero conhecido" : "indisponível"} />
      </p>
      <p className="lede">{item.value ?? "—"} {item.unit && item.value ? item.unit : ""}</p>
      {item.coverage ? (
        <p className="meta">
          Cobertura {item.coverage.valid_count ?? 0}/{item.coverage.universe ?? 0}. Ausentes: {item.coverage.missing_count ?? 0}.
        </p>
      ) : null}
      {item.reason ? <p className="meta">{item.reason.replaceAll("_", " ")}</p> : null}
      <button type="button" className="ghost" onClick={onDrill}>
        Abrir detalhes
      </button>
      <CompositionChart item={item} />
    </article>
  );
}

export function ReportingOverviewPage() {
  const { hasPermission } = useOrganization();
  return (
    <div className="stage">
      <div>
        <div className="page-head">
          <div>
            <h1>Relatórios e painéis</h1>
            <p className="lede">
              Projeções sobre fatos canônicos. Não é tempo real. Ausência não é zero. Margem estimada não é faturamento.
            </p>
          </div>
        </div>
        <div className="cards">
          {REPORTS.filter((item) => hasPermission(item.permission)).map((item) => (
            <article className="card" key={item.code}>
              <h2>{item.title}</h2>
              <Link className="primary" to={item.path}>
                Abrir {item.title.toLowerCase()}
              </Link>
            </article>
          ))}
          {hasPermission("reporting.saved_view.manage") ? (
            <article className="card">
              <h2>Relatórios salvos</h2>
              <Link className="primary" to="/gestao/relatorios/salvos">
                Abrir visões
              </Link>
            </article>
          ) : null}
        </div>
      </div>
      <ReportingMentor step={0} notes={["escolha um relatório"]} />
    </div>
  );
}

export function ReportingReportPage({
  code,
  title,
  extraCodes = [],
}: {
  code: string;
  title: string;
  extraCodes?: string[];
}) {
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [params, setParams] = useSearchParams();
  const periodStart = params.get("inicio") ?? "";
  const periodEnd = params.get("fim") ?? "";
  const compare = params.get("comparar") === "1";
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; data: ReportPayload; reference?: ReportPayload } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const [details, setDetails] = useState<Array<Record<string, unknown>> | null>(null);
  const query = useMemo(
    () => ({
      period_start: periodStart || undefined,
      period_end: periodEnd || undefined,
    }),
    [periodStart, periodEnd],
  );
  const allowedExtra = extraCodes.filter((item) => {
    if (item === "pricing") return hasPermission("reporting.pricing.read");
    if (item === "yield_losses") return hasPermission("reporting.production.read");
    return true;
  });

  function load() {
    setState({ kind: "carregando" });
    setDetails(null);
    Promise.all([
      api.reportingReport(code, query),
      ...allowedExtra.map((item) => api.reportingReport(item, query)),
      compare
        ? api.reportingReport(code, {
            period_start: periodStart ? undefined : new Date(Date.now() - 14 * 86400000).toISOString(),
            period_end: periodStart || new Date(Date.now() - 7 * 86400000).toISOString(),
          })
        : Promise.resolve(null),
    ])
      .then(([primary, ...rest]) => {
        const extras = rest.filter((item): item is { data: ReportPayload } => item !== null && "data" in item);
        const reference = compare ? extras.at(-1) : undefined;
        const merged = extras.slice(0, compare ? -1 : extras.length);
        const indicators = [...primary.data.indicators];
        for (const extra of merged) {
          for (const card of extra.data.indicators) {
            if (!indicators.some((item) => item.code === card.code)) indicators.push(card);
          }
        }
        setState({
          kind: "ok",
          data: { ...primary.data, indicators },
          reference: reference?.data,
        });
      })
      .catch((error) => {
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, periodStart, periodEnd, compare, orgId, api]);

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  const data = state.data;
  const hideCost = !hasPermission("reporting.costing.read") && !hasPermission("reporting.pricing.read");
  const indicators = data.indicators.filter((item) => {
    if (!hideCost) return true;
    return !["cost_variance", "cost_per_sellable_unit", "markup_percent", "gross_margin", "contribution_margin"].includes(item.code);
  });

  return (
    <div className="stage">
      <div>
        <h1>{title}</h1>
        <p className="lede">
          Dados até {new Date(data.data_cutoff_at).toLocaleString("pt-BR")}. Recorte registrado. Não é tempo real.
        </p>
        <TechnicalAuditDetails
          rows={[
            {
              label: "Hash do conteúdo",
              value: data.content_hash,
              copyable: true,
            },
          ]}
        />
        <form
          className="filters"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const next = new URLSearchParams(params);
            next.set("inicio", String(form.get("inicio") || ""));
            next.set("fim", String(form.get("fim") || ""));
            setParams(next);
          }}
        >
          <label>
            Início
            <input name="inicio" type="datetime-local" defaultValue={periodStart} />
          </label>
          <label>
            Fim
            <input name="fim" type="datetime-local" defaultValue={periodEnd} />
          </label>
          <label>
            <input
              type="checkbox"
              checked={compare}
              onChange={(event) => {
                const next = new URLSearchParams(params);
                if (event.target.checked) next.set("comparar", "1");
                else next.delete("comparar");
                setParams(next);
              }}
            />{" "}
            Comparar com o período anterior
          </label>
          <button type="submit">Aplicar filtros</button>
          <button type="button" className="ghost" onClick={load}>
            Atualizar agora
          </button>
        </form>
        {indicators.length === 0 ? <EmptyState>Não há indicadores autorizados neste recorte.</EmptyState> : null}
        <div className="cards">
          {indicators.map((item) => (
            <IndicatorCard
              key={item.code}
              item={item}
              onDrill={() => {
                api.reportingDrillDown(code, item.code, query).then((body) => setDetails(body.data.rows));
              }}
            />
          ))}
        </div>
        {state.reference ? (
          <section className="compare-grid" aria-label="Comparação de períodos">
            <h2>Comparação escolhida</h2>
            <p className="meta">Variação não é causa. Cada coluna usa o mesmo dicionário de métricas.</p>
            <table>
              <caption>Período atual versus referência</caption>
              <thead>
                <tr>
                  <th scope="col">Indicador</th>
                  <th scope="col">Atual</th>
                  <th scope="col">Referência</th>
                </tr>
              </thead>
              <tbody>
                {indicators.map((item) => {
                  const other = state.reference?.indicators.find((row) => row.code === item.code);
                  return (
                    <tr key={item.code}>
                      <th scope="row">{item.name}</th>
                      <td>{item.value ?? "indisponível"}</td>
                      <td>{other?.value ?? "indisponível"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ) : null}
        {details ? (
          <table>
            <caption>Detalhe reconciliável</caption>
            <thead>
              <tr>
                <th scope="col">Entidade</th>
                <th scope="col">Estado ou inclusão</th>
              </tr>
            </thead>
            <tbody>
              {details.map((row, index) => (
                <tr key={String(row.id ?? index)}>
                  <td>{String(row.public_code ?? row.id ?? row.note ?? "—")}</td>
                  <td>{String(row.status ?? row.include ?? "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        <p className="meta">Impossível neste ciclo: {data.impossible.join(", ").replaceAll("_", " ")}.</p>
        {hasPermission("reporting.snapshot.create") ? (
          <button
            type="button"
            onClick={() => {
              api.catalogCommand("/reporting/snapshots?report_code=" + code, {
                body: query,
                idempotencyKey: crypto.randomUUID(),
              });
            }}
          >
            Criar snapshot
          </button>
        ) : null}
      </div>
      <ReportingMentor step={4} notes={["cobertura explícita", "correlação não é causa"]} />
    </div>
  );
}

export function ReportingSavedPage() {
  const { api, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [items, setItems] = useState<SavedReportView[]>([]);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    setItems([]);
    setError(null);
    api
      .reportingSavedViews()
      .then((body) => setItems(body.items))
      .catch((err) => {
        if (isCancelledError(err)) return;
        setError(err);
      });
  }, [api, orgId]);
  if (error) return <ErrorState error={error} />;
  return (
    <div className="stage">
      <div>
        <h1>Relatórios salvos</h1>
        {items.length === 0 ? <EmptyState>Não há visões salvas.</EmptyState> : (
          <ul>
            {items.map((item) => (
              <li key={item.id}>
                {item.display_name} · {item.report_code}
              </li>
            ))}
          </ul>
        )}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            api.catalogCommand("/reporting/saved-views", {
              body: {
                code: String(form.get("code")),
                display_name: String(form.get("name")),
                report_code: "production",
                filters: {},
              },
              idempotencyKey: crypto.randomUUID(),
            });
          }}
        >
          <label>
            Código
            <input name="code" required />
          </label>
          <label>
            Nome
            <input name="name" required />
          </label>
          <button type="submit">Salvar visão</button>
        </form>
      </div>
      <ReportingMentor step={7} notes={["visão não altera o fato"]} />
    </div>
  );
}

export function ReportingSnapshotPage() {
  const { snapshotId } = useParams();
  const { api, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [item, setItem] = useState<ReportSnapshot | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    setItem(null);
    setError(null);
    api
      .reportingSnapshots()
      .then((body) => setItem(body.items.find((row) => row.id === snapshotId) ?? body.items[0] ?? null))
      .catch((err) => {
        if (isCancelledError(err)) return;
        setError(err);
      });
  }, [api, snapshotId, orgId]);
  if (error) return <ErrorState error={error instanceof ApiError ? error : error} />;
  if (!item) return <LoadingState />;
  return (
    <div className="print-report">
      <h1>Relatório congelado</h1>
      <p>Emitido em {new Date(item.created_at).toLocaleString("pt-BR")}. Não recalcula.</p>
      <TechnicalAuditDetails
        rows={[
          {
            label: "Hash do conteúdo",
            value: item.content_hash,
            copyable: true,
          },
          {
            label: "Identificador do registro",
            value: item.id,
            copyable: true,
          },
        ]}
      />
      <table>
        <caption>Indicadores congelados</caption>
        <tbody>
          {item.payload.indicators.map((row) => (
            <tr key={row.code}>
              <th scope="row">{row.name}</th>
              <td>{row.value ?? "indisponível"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Dashboard econômico — entrada canônica `/gestao/custos`.
 * Agrega client-side produtos, cálculos e preços (sem endpoint de agregados).
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { isCancelledError } from "../api/errors";
import type { CostingCalculation, PracticedPrice, ProductCard } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { ChartTable, GroupedCompare, HorizontalBars } from "../costing/charts";
import {
  channelLabel,
  costingCompleteness,
  supplyModeSurfaceLabel,
  varianceSignal,
} from "../language/costing";
import { formatMoneyAmount } from "../language/ingredients";
import { useOrganization } from "../session/OrganizationContext";

type AttentionKind =
  | "preco_ausente"
  | "custo_parcial"
  | "unidade_ausente"
  | "rendimento_ausente"
  | "realizado_acima"
  | "base_comercial_ausente"
  | "markup_sem_politica";

type AttentionItem = {
  id: string;
  kind: AttentionKind;
  title: string;
  detail: string;
  to: string;
  action: string;
};

type FilterKey = "todos" | "completo" | "parcial" | "sem_preco" | "sem_base" | "divergencia";

function productKey(item: CostingCalculation) {
  return item.technical_product_id || nameOf(item);
}

function nameOf(item: CostingCalculation) {
  return item.subject?.product_display_name || item.subject?.formulation_display_name || "Produto";
}

function pickLatest(items: CostingCalculation[]) {
  return [...items].sort((a, b) => {
    const byCreated = String(b.created_at ?? "").localeCompare(String(a.created_at ?? ""));
    if (byCreated !== 0) return byCreated;
    return String(b.valuation_at ?? "").localeCompare(String(a.valuation_at ?? ""));
  })[0];
}

export function EconomicDashboardPage() {
  const { api, active, hasPermission } = useOrganization();
  const orgId = active?.organization_id ?? "";
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [state, setState] = useState<
    | { kind: "carregando" }
    | {
        kind: "ok";
        products: ProductCard[];
        calcs: CostingCalculation[];
        prices: PracticedPrice[];
      }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });

  const q = (params.get("q") || "").trim().toLowerCase();
  const familia = params.get("familia") || "";
  const modalidade = params.get("modalidade") || "";
  const filtro = (params.get("filtro") as FilterKey) || "todos";

  function load() {
    setState({ kind: "carregando" });
    Promise.all([
      api.listProducts({ limit: "100", offset: "0" }).catch(() => ({ items: [] as ProductCard[], total: 0, limit: 100, offset: 0 })),
      api.listCostingCalculations().catch(() => ({ items: [] as CostingCalculation[] })),
      hasPermission("costing.read")
        ? api.listPracticedPrices().catch(() => ({ items: [] as PracticedPrice[] }))
        : Promise.resolve({ items: [] as PracticedPrice[] }),
    ])
      .then(([products, calcs, prices]) => {
        setState({
          kind: "ok",
          products: products.items ?? [],
          calcs: calcs.items ?? [],
          prices: prices.items ?? [],
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
  }, [api, orgId]);

  const model = useMemo(() => {
    if (state.kind !== "ok") return null;
    const { products, calcs, prices } = state;
    const priceByProduct = new Map<string, PracticedPrice[]>();
    for (const price of prices) {
      const pid = price.technical_product_id;
      if (!pid) continue;
      const list = priceByProduct.get(pid) ?? [];
      list.push(price);
      priceByProduct.set(pid, list);
    }

    const calcsByProduct = new Map<string, CostingCalculation[]>();
    for (const calc of calcs) {
      const key = productKey(calc);
      const list = calcsByProduct.get(key) ?? [];
      list.push(calc);
      calcsByProduct.set(key, list);
    }

    type Row = {
      id: string;
      code: string;
      name: string;
      family: string;
      modality: string;
      planned: CostingCalculation | null;
      actual: CostingCalculation | null;
      unitCost: string | null;
      completeness: string;
      hasPrice: boolean;
      priceAmount: string | null;
      missingSaleBasis: boolean;
      currency: string;
      gaps: string[];
      varianceBad: boolean;
    };

    const rows: Row[] = [];
    const seen = new Set<string>();

    for (const product of products) {
      seen.add(product.id);
      const related = calcsByProduct.get(product.id) ?? [];
      const planned = pickLatest(related.filter((c) => c.kind === "planned")) ?? null;
      const actual = pickLatest(related.filter((c) => c.kind === "actual")) ?? null;
      const primary = planned ?? actual;
      const productPrices = priceByProduct.get(product.id) ?? [];
      const activePrice =
        productPrices.find((p) => p.status === "active" || p.status === "published") ?? null;
      const unitCost = primary?.sellable_unit_amount ?? primary?.cost_base?.amount ?? primary?.total_amount ?? null;
      const completeness = primary?.completeness ?? "absent";
      const signal =
        planned && actual
          ? varianceSignal("cost", planned.sellable_unit_amount ?? planned.total_amount, actual.sellable_unit_amount ?? actual.total_amount)
          : { delta: null, label: null };
      // KPI “Preço sem base comercial”: apenas preço vigente do produto (active/published).
      // Históricos legados sem base não entram neste indicador.
      const missingSaleBasis = Boolean(
        activePrice &&
          !(
            activePrice.sale_basis?.informed === true ||
            activePrice.comparison?.allowed === true
          ),
      );
      const gaps: string[] = [];
      if (!product.sale_unit) gaps.push("unidade vendável ausente");
      if (primary?.completeness === "partial" || primary?.completeness === "incomplete") gaps.push("custo parcial");
      if (!activePrice) gaps.push("preço vigente ausente");
      if (missingSaleBasis) gaps.push("base comercial do preço ausente");
      if (primary?.subject?.commercial_presentation && !primary.subject.commercial_presentation.defined) {
        gaps.push("rendimento / apresentação ausente");
      }
      rows.push({
        id: product.id,
        code: product.code,
        name: product.display_name,
        family: product.family?.display_name ?? "Sem família",
        modality: supplyModeSurfaceLabel(product.supply_mode),
        planned,
        actual,
        unitCost,
        completeness,
        hasPrice: Boolean(activePrice),
        priceAmount: activePrice?.amount ?? null,
        missingSaleBasis,
        currency: activePrice?.currency ?? primary?.currency ?? "BRL",
        gaps,
        varianceBad: signal.label === "desfavorável",
      });
    }

    // Cálculos órfãos (sem produto na lista)
    for (const [key, list] of calcsByProduct) {
      if (seen.has(key)) continue;
      const planned = pickLatest(list.filter((c) => c.kind === "planned")) ?? null;
      const actual = pickLatest(list.filter((c) => c.kind === "actual")) ?? null;
      const primary = planned ?? actual;
      if (!primary) continue;
      rows.push({
        id: key,
        code: "—",
        name: nameOf(primary),
        family: "—",
        modality: supplyModeSurfaceLabel(primary.subject?.supply_mode),
        planned,
        actual,
        unitCost: primary.sellable_unit_amount ?? primary.cost_base?.amount ?? primary.total_amount,
        completeness: primary.completeness,
        hasPrice: false,
        priceAmount: null,
        missingSaleBasis: false,
        currency: primary.currency,
        gaps: ["produto sem ficha comercial vinculada na lista"],
        varianceBad: false,
      });
    }

    const filtered = rows.filter((row) => {
      if (q && !`${row.name} ${row.code}`.toLowerCase().includes(q)) return false;
      if (familia && row.family !== familia) return false;
      if (modalidade && row.modality !== modalidade) return false;
      if (filtro === "completo" && row.completeness !== "complete") return false;
      if (filtro === "parcial" && row.completeness !== "partial" && row.completeness !== "incomplete") return false;
      if (filtro === "sem_preco" && row.hasPrice) return false;
      if (filtro === "sem_base" && !row.missingSaleBasis) return false;
      if (filtro === "divergencia" && !row.varianceBad) return false;
      return true;
    });

    const analyzed = rows.filter((r) => r.planned || r.actual).length;
    const complete = rows.filter((r) => r.completeness === "complete").length;
    const partial = rows.filter((r) => r.completeness === "partial" || r.completeness === "incomplete").length;
    const noPrice = rows.filter((r) => !r.hasPrice && (r.planned || r.actual)).length;
    const noSaleBasis = rows.filter((r) => r.missingSaleBasis).length;
    const varianceBad = rows.filter((r) => r.varianceBad).length;

    const unitBars = filtered
      .filter((r) => r.unitCost != null)
      .slice(0, 12)
      .map((r) => ({
        id: r.id,
        label: r.name,
        amount: r.unitCost,
        state: costingCompleteness(r.completeness).label,
      }));

    const compareSeries = filtered
      .filter((r) => r.planned || r.actual)
      .slice(0, 8)
      .map((r) => ({
        label: r.name,
        planned: r.planned?.sellable_unit_amount ?? r.planned?.total_amount ?? null,
        actual: r.actual?.sellable_unit_amount ?? r.actual?.total_amount ?? null,
        metric: "cost" as const,
      }));

    const attention: AttentionItem[] = [];
    for (const row of rows) {
      if (!row.hasPrice && (row.planned || row.actual)) {
        attention.push({
          id: `price-${row.id}`,
          kind: "preco_ausente",
          title: `${row.name}: preço vigente ausente`,
          detail: "Não há preço praticado publicado para este produto.",
          to: `/gestao/custos/precos?produto=${encodeURIComponent(row.id)}`,
          action: "Abrir preços e histórico",
        });
      }
      if (row.missingSaleBasis) {
        attention.push({
          id: `basis-${row.id}`,
          kind: "base_comercial_ausente",
          title: `${row.name}: base comercial do preço não informada`,
          detail:
            "Há preço histórico, mas sem quantidade-base e unidade comerciais persistidas. Markup e margem ficam bloqueados até a próxima decisão com base.",
          to: `/gestao/custos/precos?produto=${encodeURIComponent(row.id)}`,
          action: "Abrir preços e histórico",
        });
      }
      if (row.completeness === "partial" || row.completeness === "incomplete") {
        const calcId = row.planned?.id ?? row.actual?.id;
        attention.push({
          id: `partial-${row.id}`,
          kind: "custo_parcial",
          title: `${row.name}: custo parcial`,
          detail: "Há lacunas de preço ou premissa. Ausência não entra como zero.",
          to: calcId ? `/gestao/custos/formacao?calculo=${calcId}` : "/gestao/custos/formacao",
          action: "Abrir formação do custo",
        });
      }
      if (row.gaps.includes("unidade vendável ausente")) {
        attention.push({
          id: `unit-${row.id}`,
          kind: "unidade_ausente",
          title: `${row.name}: unidade vendável ausente`,
          detail: "Sem unidade vendável a margem comercial fica sem base clara.",
          to: `/produtos/${row.id}`,
          action: "Abrir produto",
        });
      }
      if (row.varianceBad && row.planned && row.actual) {
        attention.push({
          id: `var-${row.id}`,
          kind: "realizado_acima",
          title: `${row.name}: realizado acima do previsto`,
          detail: "Aumento de custo na mesma base é desfavorável.",
          to: `/gestao/custos/variacao?produto=${encodeURIComponent(row.id)}`,
          action: "Comparar previsto vs realizado",
        });
      }
    }
    attention.push({
      id: "markup-policy",
      kind: "markup_sem_politica",
      title: "Políticas de markup/margem",
      detail:
        "Precedência produto → família → organização está ativa na API. Canal/estabelecimento ainda não entram neste ciclo.",
      to: "/gestao/custos/politicas",
      action: "Ver políticas e premissas",
    });

    const families = [...new Set(rows.map((r) => r.family).filter(Boolean))].sort();
    const modalities = [...new Set(rows.map((r) => r.modality).filter(Boolean))].sort();

    return {
      rows: filtered,
      allRows: rows,
      indicators: {
        analyzed,
        complete,
        partial,
        noPrice,
        noSaleBasis,
        varianceBad,
      },
      unitBars,
      compareSeries,
      attention: attention.slice(0, 12),
      families,
      modalities,
    };
  }, [state, q, familia, modalidade, filtro]);

  function setFilter(next: FilterKey) {
    const copy = new URLSearchParams(params);
    if (next === "todos") copy.delete("filtro");
    else copy.set("filtro", next);
    setParams(copy);
  }

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  if (!model) return null;

  const { indicators } = model;

  return (
    <div className="econ-dashboard">
      <header className="econ-dashboard__head">
        <div>
          <h1>Custos, preços e margem</h1>
          <p className="lede">
            Quanto custa, se o custo está completo, qual preço está vigente e onde agir. Simulação não grava preço.
          </p>
          <p className="meta">
            Indicadores: <strong>Analisados</strong> = produtos com cálculo; <strong>Completos</strong> /
            <strong>Parciais</strong> = completude do custo vigente; <strong>Sem preço</strong> = sem preço
            active/published; <strong>Sem base comercial</strong> = preço vigente sem base (não conta legado
            histórico); <strong>Divergência</strong> = realizado desfavorável vs previsto.
          </p>
        </div>
        <form
          className="econ-filters"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const copy = new URLSearchParams(params);
            const query = String(form.get("q") || "").trim();
            if (query) copy.set("q", query);
            else copy.delete("q");
            const fam = String(form.get("familia") || "");
            if (fam) copy.set("familia", fam);
            else copy.delete("familia");
            const mod = String(form.get("modalidade") || "");
            if (mod) copy.set("modalidade", mod);
            else copy.delete("modalidade");
            setParams(copy);
          }}
        >
          <label>
            Buscar produto
            <input name="q" defaultValue={params.get("q") ?? ""} placeholder="Nome ou código" />
          </label>
          <label>
            Família
            <select name="familia" defaultValue={familia}>
              <option value="">Todas</option>
              {model.families.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Modalidade
            <select name="modalidade" defaultValue={modalidade}>
              <option value="">Todas</option>
              {model.modalities.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" className="primary">
            Aplicar
          </button>
        </form>
      </header>

      <section className="econ-kpis" aria-label="Indicadores econômicos">
        {(
          [
            { key: "todos" as FilterKey, label: "Produtos analisados", value: indicators.analyzed },
            { key: "completo" as FilterKey, label: "Custo aplicável completo", value: indicators.complete },
            { key: "parcial" as FilterKey, label: "Custo parcial", value: indicators.partial },
            { key: "sem_preco" as FilterKey, label: "Sem preço vigente", value: indicators.noPrice },
            { key: "sem_base" as FilterKey, label: "Preço sem base comercial", value: indicators.noSaleBasis },
            { key: "divergencia" as FilterKey, label: "Previsto vs realizado desfavorável", value: indicators.varianceBad },
          ] as const
        ).map((kpi) => (
          <button
            key={kpi.key}
            type="button"
            className={filtro === kpi.key || (kpi.key === "todos" && filtro === "todos") ? "econ-kpi is-active" : "econ-kpi"}
            onClick={() => setFilter(kpi.key)}
          >
            <span className="econ-kpi__value">{kpi.value}</span>
            <span className="econ-kpi__label">{kpi.label}</span>
          </button>
        ))}
      </section>

      <div className="econ-dashboard__grid">
        <section className="econ-panel">
          {model.unitBars.length === 0 ? (
            <EmptyState>Não há custo unitário conhecido no recorte. Ausência não gera gráfico zero.</EmptyState>
          ) : (
            <>
              <HorizontalBars
                title="Quanto custa cada produto (unitário)?"
                caption="Unidade: R$ por unidade vendável ou custo-base conhecido. Sem valor = sem barra."
                bars={model.unitBars}
                onSelect={(bar) => {
                  if (bar.id) navigate(`/gestao/custos/formacao?produto=${bar.id}`);
                }}
              />
              <ChartTable
                caption="Tabela equivalente — custo unitário"
                headers={["Produto", "Custo", "Situação"]}
                rows={model.unitBars.map((bar) => [
                  bar.label,
                  formatMoneyAmount(bar.amount, "BRL"),
                  bar.state || "—",
                ])}
              />
            </>
          )}
        </section>

        <section className="econ-panel">
          {model.compareSeries.every((s) => s.planned == null && s.actual == null) ? (
            <EmptyState>Não há pares previsto/realizado suficientes para comparar.</EmptyState>
          ) : (
            <GroupedCompare
              title="O realizado ficou acima ou abaixo do previsto?"
              series={model.compareSeries}
            />
          )}
        </section>
      </div>

      <section className="econ-attention" aria-label="Painel de atenção">
        <h2>Onde agir agora</h2>
        {model.attention.length === 0 ? (
          <EmptyState>Nenhum achado automático no recorte atual.</EmptyState>
        ) : (
          <ul>
            {model.attention.map((item) => (
              <li key={item.id}>
                <div>
                  <strong>{item.title}</strong>
                  <p className="meta">{item.detail}</p>
                </div>
                <Link className="ghost" to={item.to}>
                  {item.action}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="econ-product-table" aria-label="Produtos do recorte">
        <h2>Produtos no recorte</h2>
        {model.rows.length === 0 ? (
          <EmptyState>Nenhum produto corresponde aos filtros.</EmptyState>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Produto</th>
                  <th>Código</th>
                  <th>Modalidade</th>
                  <th>Custo unitário</th>
                  <th>Completude</th>
                  <th>Preço vigente</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {model.rows.map((row) => {
                  const badge = costingCompleteness(row.completeness);
                  const calcId = row.planned?.id ?? row.actual?.id;
                  return (
                    <tr key={row.id}>
                      <td>{row.name}</td>
                      <td>{row.code}</td>
                      <td>{row.modality}</td>
                      <td>{formatMoneyAmount(row.unitCost, row.currency)}</td>
                      <td>
                        <StatusBadge tone={badge.tone} label={badge.label} />
                      </td>
                      <td>
                        {row.hasPrice
                          ? formatMoneyAmount(row.priceAmount, row.currency)
                          : "Sem preço vigente"}
                      </td>
                      <td>
                        <Link
                          to={
                            calcId
                              ? `/gestao/custos/formacao?calculo=${calcId}`
                              : `/gestao/custos/formacao?produto=${row.id}`
                          }
                        >
                          Analisar
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="meta">
          Markup e margem só aparecem com base comercial e custo comparáveis persistidos pela API. Política de
          markup e margem hierárquicos usam política persistida (produto → família → organização). Canal e
          estabelecimento ficam para evolução posterior — não inventamos referência falsa na superfície.
          {hasPermission("pricing.review") ? (
            <>
              {" "}
              Canal de exemplo na lista de preços: {channelLabel("own_counter")}.
            </>
          ) : null}
        </p>
      </section>
    </div>
  );
}

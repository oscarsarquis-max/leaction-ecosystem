/**
 * Previsto × realizado — comparação na mesma base, com avaliação semântica.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { isCancelledError } from "../api/errors";
import type { CostingCalculation } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { ChartTable, GroupedCompare } from "../costing/charts";
import {
  costingCompleteness,
  costingKindLabel,
  formatPercentDisplay,
  varianceSignal,
} from "../language/costing";
import { formatMoneyAmount } from "../language/ingredients";
import { formatDateTime } from "../format";
import { useOrganization } from "../session/OrganizationContext";

function nameOf(item: CostingCalculation) {
  return item.subject?.product_display_name || item.subject?.formulation_display_name || costingKindLabel(item.kind);
}

function parseAmt(v: string | null | undefined): number | null {
  if (v == null || v === "") return null;
  const n = Number(String(v).replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function pickLatest(items: CostingCalculation[]) {
  return [...items].sort((a, b) => String(b.created_at ?? "").localeCompare(String(a.created_at ?? "")))[0] ?? null;
}

export function CostingVariancePage() {
  const { api, active } = useOrganization();
  const [params] = useSearchParams();
  const productFilter = params.get("produto") || "";
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; items: CostingCalculation[] } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });

  function load() {
    setState({ kind: "carregando" });
    api
      .listCostingCalculations()
      .then((body) => setState({ kind: "ok", items: body.items }))
      .catch((error) => {
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, active?.organization_id]);

  const pairs = useMemo(() => {
    if (state.kind !== "ok") return [];
    const byProduct = new Map<string, CostingCalculation[]>();
    for (const item of state.items) {
      const key = item.technical_product_id || nameOf(item);
      const list = byProduct.get(key) ?? [];
      list.push(item);
      byProduct.set(key, list);
    }
    const rows = [];
    for (const [key, list] of byProduct) {
      if (productFilter && key !== productFilter && !list.some((i) => i.technical_product_id === productFilter)) {
        continue;
      }
      const planned = pickLatest(list.filter((i) => i.kind === "planned"));
      const actual = pickLatest(list.filter((i) => i.kind === "actual"));
      if (!planned && !actual) continue;
      const pUnit = planned?.sellable_unit_amount ?? planned?.total_amount ?? null;
      const aUnit = actual?.sellable_unit_amount ?? actual?.total_amount ?? null;
      const costSignal = varianceSignal("cost", pUnit, aUnit);
      const pYield = planned?.sellable_quantity ?? null;
      const aYield = actual?.sellable_quantity ?? null;
      const yieldSignal = varianceSignal("yield", pYield, aYield);
      const pNum = parseAmt(pUnit);
      const aNum = parseAmt(aUnit);
      let pct: string | null = null;
      if (pNum != null && aNum != null && pNum !== 0) {
        pct = (((aNum - pNum) / pNum) * 100).toFixed(2);
      }
      rows.push({
        key,
        name: nameOf(planned ?? actual!),
        planned,
        actual,
        pUnit,
        aUnit,
        costSignal,
        yieldSignal,
        pct,
        currency: planned?.currency ?? actual?.currency ?? "BRL",
      });
    }
    return rows;
  }, [state, productFilter]);

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;

  return (
    <div className="econ-page">
      <header>
        <h1>Previsto vs realizado</h1>
        <p className="lede">
          Comparação na mesma base. Aumento de custo é desfavorável; queda de rendimento é desfavorável; totais iguais
          são neutros. Valor negativo sozinho não define favorabilidade.
        </p>
      </header>

      {pairs.length === 0 ? (
        <EmptyState>Não há cálculos previstos ou realizados para comparar neste recorte.</EmptyState>
      ) : (
        <>
          <GroupedCompare
            title="Custo unitário previsto e realizado por produto"
            series={pairs.map((row) => ({
              label: row.name,
              planned: row.pUnit,
              actual: row.aUnit,
              metric: "cost" as const,
              delta: row.costSignal.delta == null ? null : String(row.costSignal.delta),
            }))}
          />
          <ChartTable
            caption="Tabela equivalente — variação de custo"
            headers={[
              "Produto",
              "Previsto",
              "Realizado",
              "Diferença R$",
              "Diferença %",
              "Avaliação",
              "Ação",
            ]}
            rows={pairs.map((row) => [
              row.name,
              formatMoneyAmount(row.pUnit, row.currency),
              formatMoneyAmount(row.aUnit, row.currency),
              row.costSignal.delta == null
                ? "—"
                : formatMoneyAmount(String(row.costSignal.delta), row.currency),
              row.pct == null ? "—" : formatPercentDisplay(row.pct),
              row.costSignal.label ?? "Sem informação",
              <Link
                key={row.key}
                to={`/gestao/custos/formacao?calculo=${row.actual?.id ?? row.planned?.id}`}
              >
                Analisar
              </Link>,
            ])}
          />

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Produto</th>
                  <th>Recorte</th>
                  <th>Data</th>
                  <th>Rendimento</th>
                  <th>Custo total</th>
                  <th>Custo unitário</th>
                  <th>Completude</th>
                  <th>Escopo</th>
                </tr>
              </thead>
              <tbody>
                {pairs.flatMap((row) =>
                  [row.planned, row.actual].filter(Boolean).map((item) => {
                    const calc = item as CostingCalculation;
                    const badge = costingCompleteness(calc.completeness);
                    return (
                      <tr key={calc.id}>
                        <td>{row.name}</td>
                        <td>{costingKindLabel(calc.kind)}</td>
                        <td>{formatDateTime(calc.valuation_at || calc.created_at)}</td>
                        <td>
                          {calc.sellable_quantity != null
                            ? `${calc.sellable_quantity}`
                            : "Sem informação"}
                          {row.yieldSignal.label && calc.kind === "actual"
                            ? ` · rendimento ${row.yieldSignal.label}`
                            : ""}
                        </td>
                        <td>{formatMoneyAmount(calc.total_amount, calc.currency)}</td>
                        <td>{formatMoneyAmount(calc.sellable_unit_amount, calc.currency)}</td>
                        <td>
                          <StatusBadge tone={badge.tone} label={badge.label} />
                        </td>
                        <td>{calc.cost_scope?.scope_label ?? "—"}</td>
                      </tr>
                    );
                  }),
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      <p className="meta">
        Listas legadas:{" "}
        <Link to="/gestao/custos/previstos">somente previstos</Link>
        {" · "}
        <Link to="/gestao/custos/realizados">somente realizados</Link>
      </p>
    </div>
  );
}

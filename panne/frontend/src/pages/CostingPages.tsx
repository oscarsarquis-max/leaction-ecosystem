import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { CostingCalculation, CostingPolicy, PracticedPrice, PricingSimulation } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { CostingMentor } from "../components/CostingMentor";
import { useOrganization } from "../session/OrganizationContext";

const CHANNELS: Record<string, string> = {
  own_counter: "balcão próprio",
  made_to_order: "encomenda",
  wholesale: "atacado",
  own_delivery: "entrega própria",
  marketplace: "praça eletrônica",
  other: "outro",
};

const COMPLETENESS: Record<string, { label: string; tone: "sucesso" | "atencao" | "erro" | "info" }> = {
  complete: { label: "completo", tone: "sucesso" },
  partial: { label: "parcial", tone: "atencao" },
  insufficient_data: { label: "dados insuficientes", tone: "erro" },
  invalidated: { label: "invalidado", tone: "erro" },
};

function completenessBadge(code: string) {
  const item = COMPLETENESS[code] ?? { label: code, tone: "info" as const };
  return <StatusBadge tone={item.tone} label={item.label} />;
}

function useList<T>(loader: () => Promise<{ items: T[] }>, key: string) {
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; items: T[] } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  function load() {
    setState({ kind: "carregando" });
    loader()
      .then((body) => setState({ kind: "ok", items: body.items }))
      .catch((error) => setState({ kind: "erro", error }));
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return { state, load };
}

export function CostingPoliciesPage() {
  const { api, hasPermission } = useOrganization();
  const { state, load } = useList(() => api.listCostingPolicies(), "policies");
  const [code, setCode] = useState("POL-PADRAO");
  const [justification, setJustification] = useState("política inicial da organização");
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>Políticas de custeio</h1>
        <p className="lede">
          Política publicada é imutável. Alteração cria nova versão. Cálculos apontam para a versão usada.
        </p>
        {state.items.length === 0 ? <EmptyState>Não há políticas nesta organização.</EmptyState> : null}
        <ul>
          {state.items.map((item: CostingPolicy) => (
            <li key={item.id}>
              <strong>{item.display_name}</strong> <StatusBadge tone="info" label={item.status} />
              <span className="meta">
                {" "}
                {item.version?.currency} · {item.version?.price_criterion}
              </span>
            </li>
          ))}
        </ul>
        {hasPermission("costing.policy.manage") ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              api
                .catalogCommand("/costing/policies", {
                  body: {
                    code,
                    effective_from: new Date().toISOString(),
                    justification,
                    price_criterion: "latest_observed",
                    enabled_categories: ["ingredient", "packaging", "waste", "rework", "other"],
                  },
                  idempotencyKey: crypto.randomUUID(),
                })
                .then(load);
            }}
          >
            <h2>Nova política</h2>
            <label>
              Código
              <input value={code} onChange={(event) => setCode(event.target.value)} required />
            </label>
            <label>
              Justificativa
              <input
                value={justification}
                onChange={(event) => setJustification(event.target.value)}
                required
              />
            </label>
            <p className="meta">Critério inicial: último preço observado vigente. Sem escolha automática do menor preço.</p>
            <button type="submit" className="primary">
              Criar política
            </button>
          </form>
        ) : null}
      </div>
      <CostingMentor step={2} pending={[]} />
    </div>
  );
}

export function CostingListPage({ kind, title }: { kind: "planned" | "actual"; title: string }) {
  const { api } = useOrganization();
  const { state, load } = useList(() => api.listCostingCalculations(kind), kind);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>{title}</h1>
        <p className="lede">
          {kind === "actual"
            ? "Somente fatos persistidos. Pesado não é consumido. Retorno não é desperdício."
            : "Projeção anterior à execução, com política e preços vigentes na data."}
        </p>
        {state.items.length === 0 ? <EmptyState>Não há cálculos neste recorte.</EmptyState> : null}
        <ul>
          {state.items.map((item: CostingCalculation) => (
            <li key={item.id}>
              <Link to={`/gestao/custos/calculos/${item.id}`}>
                {item.kind === "actual" ? "realizado" : item.kind === "standard" ? "padrão" : "previsto"}
              </Link>{" "}
              {completenessBadge(item.completeness)}
              <span className="meta"> total {item.total_amount ?? "ausente"}</span>
            </li>
          ))}
        </ul>
      </div>
      <CostingMentor step={kind === "actual" ? 5 : 3} pending={[]} />
    </div>
  );
}

export function CostingCalculationPage() {
  const { calcId = "" } = useParams();
  const { api, hasPermission } = useOrganization();
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; data: CostingCalculation } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const [compare, setCompare] = useState<string | null>(null);
  function load() {
    setState({ kind: "carregando" });
    api
      .getCostingCalculation(calcId)
      .then((body) => setState({ kind: "ok", data: body.data }))
      .catch((error) => setState({ kind: "erro", error }));
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, calcId]);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  const data = state.data;
  return (
    <div className="stage">
      <div>
        <h1>Cálculo de custo</h1>
        <p>{completenessBadge(data.completeness)}</p>
        <p>Total: {data.total_amount ?? "ausente"}</p>
        <p>Unidade vendável: {data.sellable_unit_amount ?? "ausente"}</p>
        <p className="meta">Ausência não é zero. Valor faltante permanece vazio.</p>
        <h2>Composição</h2>
        <ul>
          {(data.components ?? []).map((item) => (
            <li key={`${item.category}-${item.quality}`}>
              {item.category}: {item.amount ?? "sem valor"} ({item.quality}
              {item.share_percent ? ` · ${item.share_percent}%` : ""})
            </li>
          ))}
        </ul>
        <h2>Lacunas</h2>
        {(data.gaps ?? []).length === 0 ? <p>Nenhuma lacuna listada.</p> : null}
        <ul>
          {(data.gaps ?? []).map((item) => (
            <li key={item.code}>{item.message}</li>
          ))}
        </ul>
        <h2>Previsto versus realizado</h2>
        <button
          type="button"
          onClick={() =>
            api.compareCostingCalculations(data.id, data.id).then((body) => {
              const delta = body.data.total_delta;
              setCompare(typeof delta === "string" ? delta : "sem delta");
            })
          }
        >
          Comparar com o mesmo recorte
        </button>
        {compare ? <p role="status">Variação de total: {compare}</p> : null}
        {hasPermission("pricing.simulation.manage") ? (
          <button
            type="button"
            onClick={() =>
              api.catalogCommand(`/costing/calculations/${data.id}/simulations`, {
                body: { kind: "markup_factor", factor: "2", channel: "own_counter" },
                idempotencyKey: crypto.randomUUID(),
              })
            }
          >
            Simular markup 2x
          </button>
        ) : null}
      </div>
      <CostingMentor step={7} pending={(data.gaps ?? []).map((item) => item.code)} />
    </div>
  );
}

export function CostingSimulationsPage() {
  const { api, hasPermission } = useOrganization();
  const { state, load } = useList(() => api.listPricingSimulations(), "simulations");
  const [kind, setKind] = useState("markup_factor");
  const [channel, setChannel] = useState("own_counter");
  const [calcId, setCalcId] = useState("");
  useEffect(() => {
    api.listCostingCalculations().then((body) => setCalcId(body.items[0]?.id ?? ""));
  }, [api]);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>Simulações</h1>
        <p className="lede">
          Markup incide sobre o custo. Margem bruta incide sobre o preço. Margem de contribuição desconta
          custos e despesas variáveis. Não são sinônimos.
        </p>
        {state.items.length === 0 ? <EmptyState>Não há simulações nesta organização.</EmptyState> : null}
        <ul>
          {state.items.map((item: PricingSimulation) => (
            <li key={item.id}>
              {item.kind} · {CHANNELS[item.channel] ?? item.channel} · sugerido {item.suggested_price ?? "—"}
              {item.warning ? <p role="status">{item.warning}</p> : null}
              <p className="meta">{item.disclaimer}</p>
            </li>
          ))}
        </ul>
        {hasPermission("pricing.simulation.manage") ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const body =
                kind === "gross_margin"
                  ? { kind, target_rate: "0.20", channel }
                  : kind === "contribution_margin"
                    ? { kind, target_rate: "0.20", variable_expense_rate: "0.10", channel }
                    : kind === "reverse"
                      ? { kind, price: "25", variable_product: "12.5", variable_selling: "2", channel }
                      : { kind: "markup_factor", factor: "2", channel };
              if (!calcId) return;
              api
                .catalogCommand(`/costing/calculations/${calcId}/simulations`, {
                  body,
                  idempotencyKey: crypto.randomUUID(),
                })
                .then(load);
            }}
          >
            <h2>Simulador</h2>
            <label>
              Fórmula
              <select value={kind} onChange={(event) => setKind(event.target.value)}>
                <option value="markup_factor">Markup por fator</option>
                <option value="gross_margin">Margem bruta alvo</option>
                <option value="contribution_margin">Margem de contribuição alvo</option>
                <option value="reverse">Reversa a partir do preço</option>
              </select>
            </label>
            <label>
              Canal
              <select value={channel} onChange={(event) => setChannel(event.target.value)}>
                {Object.entries(CHANNELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <p className="meta">
              Premissa comercial manual. A Panne não apura nem valida obrigação fiscal.
            </p>
            <button type="submit" className="primary">
              Calcular simulação
            </button>
          </form>
        ) : null}
      </div>
      <CostingMentor step={8} pending={[]} />
    </div>
  );
}

export function CostingPricesPage() {
  const { api, hasPermission } = useOrganization();
  const { state, load } = useList(() => api.listPracticedPrices(), "prices");
  const [row, setRow] = useState(1);
  const [notes, setNotes] = useState("revisão humana");
  const [reinforced, setReinforced] = useState(false);
  const [conflict, setConflict] = useState(false);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="stage">
      <div>
        <h1>Preços praticados</h1>
        <p className="lede">Publicação é decisão humana. Não há envio a praça eletrônica neste ciclo.</p>
        {conflict ? (
          <div className="feedback" role="alert">
            <h2>Conflito de estado</h2>
            <p>A versão mudou. Recarregue antes de publicar.</p>
            <button type="button" className="primary" onClick={() => { setConflict(false); load(); }}>
              Recarregar
            </button>
          </div>
        ) : null}
        {state.items.length === 0 ? <EmptyState>Não há preços praticados.</EmptyState> : null}
        <ul>
          {state.items.map((item: PracticedPrice) => (
            <li key={item.id}>
              {CHANNELS[item.channel] ?? item.channel} · {item.amount} · {item.status}
              {hasPermission("pricing.publish") && item.status === "draft" ? (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    api
                      .catalogCommand(`/pricing/practiced/${item.id}/decide`, {
                        body: {
                          decision: "publish",
                          notes,
                          reinforced_confirmation: reinforced,
                        },
                        idempotencyKey: crypto.randomUUID(),
                        ifMatch: row,
                      })
                      .then(() => setRow((value) => value + 1))
                      .catch((error) => {
                        if (error instanceof ApiError && error.code === "conflito") {
                          setConflict(true);
                          load();
                        }
                      });
                  }}
                >
                  <label>
                    Justificativa da publicação
                    <input value={notes} onChange={(event) => setNotes(event.target.value)} required />
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={reinforced}
                      onChange={(event) => setReinforced(event.target.checked)}
                    />
                    Confirmação reforçada para cálculo parcial
                  </label>
                  <button type="submit">Confirmar publicação</button>
                </form>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
      <CostingMentor step={9} pending={["confirmação humana"]} />
    </div>
  );
}

import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ApiError, isCancelledError } from "../api/errors";
import type { CostingCalculation, PracticedPrice, ProductCard } from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import {
  ChartTable,
  GroupedCompare,
  HorizontalBars,
  ScenarioImpact,
  WaterfallBars,
  type ChartBar,
} from "../costing/charts";
import {
  applyDesiredPrice,
  applyMarkupFactor,
  emptyCalculator,
  humanInputMarkup,
  humanInputPrice,
  initFromCostBase,
  type CalculatorSnapshot,
} from "../costing/priceCalculator";
import { formatDateTime } from "../format";
import {
  channelLabel,
  costingCompleteness,
  costingKindLabel,
  formatMarkupFactor,
  formatPercentDisplay,
  isPurchasedCalc,
  practicedStatusLabel,
  productComparisonScope,
  qualityLabel,
  varianceSignal,
} from "../language/costing";
import { formatMoneyAmount } from "../language/ingredients";
import { formatOperationalQuantity } from "../language/quantities";
import { SURFACE_PHRASES } from "../language/surface";
import { useOrganization } from "../session/OrganizationContext";

function money(amount: string | null | undefined, currency = "BRL") {
  return formatMoneyAmount(amount, currency);
}

function nameOf(item: CostingCalculation) {
  return (
    item.subject?.product_display_name ||
    item.subject?.formulation_display_name ||
    costingKindLabel(item.kind)
  );
}

function pickLatest(items: CostingCalculation[], pred: (item: CostingCalculation) => boolean) {
  return (
    items
      .filter(pred)
      .sort((a, b) => {
        const byCreated = String(b.created_at ?? "").localeCompare(String(a.created_at ?? ""));
        if (byCreated !== 0) return byCreated;
        return String(b.valuation_at ?? "").localeCompare(String(a.valuation_at ?? ""));
      })[0] ?? null
  );
}

type ScenarioKey = "A" | "B" | "C" | "D";

const SCENARIO_META: Record<ScenarioKey, { title: string; hint: string }> = {
  A: { title: "A · Pão francês", hint: "Ingredientes por unidade · calculadora" },
  B: { title: "B · Pão integral", hint: "Custo parcial · lacuna intencional" },
  C: { title: "C · Manteiga comprada", hint: "Mercadoria comprada · OP não se aplica" },
  D: { title: "D · Focaccia", hint: "Previsto × realizado" },
};

function resolveScenarios(items: CostingCalculation[]) {
  const match = (re: RegExp) => items.filter((item) => re.test(nameOf(item)));
  const a = pickLatest(match(/p[aã]o franc/i), (item) => item.kind === "planned" && item.sellable_unit_amount != null);
  const b = pickLatest(match(/integral/i), (item) => item.kind === "planned");
  const c = pickLatest(match(/manteiga|comprado/i), (item) => item.kind === "planned");
  const dPlan = pickLatest(match(/focaccia/i), (item) => item.kind === "planned" && item.sellable_quantity != null);
  const dAct = pickLatest(match(/focaccia/i), (item) => item.kind === "actual" && item.sellable_quantity != null);
  return { A: a, B: b, C: c, D: dAct ?? dPlan, D_planned: dPlan, D_actual: dAct };
}

function CalculatorPanel({
  calc,
  snapshot,
  onMarkup,
  onPrice,
  onReset,
  onLoadPolicy,
  canSimulate,
  canApply,
  onRequestApply,
  ingredientsComplete,
  productionComplete,
  priceDefinitiveAllowed,
  marginLabel,
  scopeHint,
  purchased,
  vigentePrice,
  suggestedPrice,
  policySummary,
  policyKindLabel,
  simulating,
}: {
  calc: CostingCalculation;
  snapshot: CalculatorSnapshot;
  onMarkup: (value: string) => void;
  onPrice: (value: string) => void;
  onReset: () => void;
  onLoadPolicy: () => void;
  canSimulate: boolean;
  canApply: boolean;
  onRequestApply: () => void;
  ingredientsComplete: boolean;
  productionComplete: boolean;
  priceDefinitiveAllowed: boolean;
  marginLabel: string;
  scopeHint: string;
  purchased: boolean;
  vigentePrice: string | null;
  suggestedPrice: string | null;
  policySummary: string | null;
  policyKindLabel: string | null;
  simulating: boolean;
}) {
  const currency = calc.currency || "BRL";
  const unit = calc.cost_base?.unit_label || "R$ / unidade";
  const [markupDraft, setMarkupDraft] = useState<string | null>(null);
  const [priceDraft, setPriceDraft] = useState<string | null>(null);
  const uid = useMemo(() => Math.random().toString(36).slice(2, 9), []);
  const markupId = `cost-markup-${uid}`;
  const priceId = `cost-price-${uid}`;
  return (
    <div className="costing-calculator">
      <header className="costing-calculator__head">
        <h2>Calculadora de preço</h2>
        <p className="meta">
          {purchased
            ? priceDefinitiveAllowed
              ? "Base de aquisição completa."
              : "Simulação sobre custo de aquisição."
            : productionComplete
              ? "Base de produção completa."
              : ingredientsComplete
                ? "Simulação sobre custo de ingredientes (outras categorias fora)."
                : "Simulação exploratória sobre custo parcial."}
        </p>
      </header>

      <dl className="costing-calculator__facts costing-calculator__prices-triad">
        <div className="costing-price-slot costing-price-slot--vigente">
          <dt>Preço vigente</dt>
          <dd>{vigentePrice ? money(vigentePrice, currency) : "Sem preço vigente"}</dd>
        </div>
        <div className="costing-price-slot costing-price-slot--sugerido">
          <dt>Preço sugerido pela política</dt>
          <dd>
            {suggestedPrice ? money(suggestedPrice, currency) : "Sem política efetiva"}
            {policyKindLabel ? <span className="meta"> · {policyKindLabel}</span> : null}
          </dd>
        </div>
        <div className={`costing-price-slot costing-price-slot--sim ${simulating ? "is-active" : ""}`}>
          <dt>Simulação atual</dt>
          <dd>
            {money(snapshot.price, currency)}{" "}
            <span className="meta">não grava</span>
          </dd>
        </div>
      </dl>

      {policySummary ? (
        <p className="costing-banner costing-banner--info" role="status">
          {policySummary}
        </p>
      ) : null}

      <dl className="costing-calculator__facts">
        <div>
          <dt>Custo-base</dt>
          <dd>
            {money(snapshot.costBase, currency)} <span className="meta">{unit}</span>
          </dd>
        </div>
        <div>
          <dt>Origem</dt>
          <dd>{snapshot.costOriginLabel}</dd>
        </div>
      </dl>

      {!priceDefinitiveAllowed ? (
        <p className="costing-banner costing-banner--warn" role="status">
          {scopeHint}{" "}
          {purchased
            ? "Preço definitivo bloqueado enquanto o custo de aquisição não estiver completo."
            : "Preço definitivo bloqueado enquanto o custo total de produção não estiver completo."}
          {!purchased && !ingredientsComplete
            ? ` Parcelas sem preço: ${(calc.analytics?.missing_names ?? []).join(", ") || "componentes"}.`
            : null}
        </p>
      ) : null}

      <div className="costing-calculator__field">
        <label htmlFor={markupId}>Markup (fator) — simulação</label>
        <input
          id={markupId}
          type="text"
          inputMode="decimal"
          value={markupDraft ?? humanInputMarkup(snapshot.markupFactor)}
          onFocus={() => setMarkupDraft(humanInputMarkup(snapshot.markupFactor))}
          onBlur={() => setMarkupDraft(null)}
          onChange={(event) => {
            setMarkupDraft(event.target.value);
            onMarkup(event.target.value);
          }}
          disabled={!canSimulate || !snapshot.costBase}
          aria-describedby={`${markupId}-help`}
        />
        <p id={`${markupId}-help`} className="meta">
          Preço = custo × markup · mesma unidade do custo-base. Alterar aqui só simula.
        </p>
      </div>

      <div className="costing-calculator__field">
        <label htmlFor={priceId}>Preço desejado (R$ / un.) — simulação</label>
        <input
          id={priceId}
          type="text"
          inputMode="decimal"
          value={priceDraft ?? humanInputPrice(snapshot.price)}
          onFocus={() => setPriceDraft(humanInputPrice(snapshot.price))}
          onBlur={() => setPriceDraft(null)}
          onChange={(event) => {
            setPriceDraft(event.target.value);
            onPrice(event.target.value);
          }}
          disabled={!canSimulate || !snapshot.costBase}
        />
      </div>

      <dl className="costing-calculator__results">
        <div>
          <dt>{priceDefinitiveAllowed ? "Preço simulado" : "Preço exploratório"}</dt>
          <dd>
            {money(snapshot.price, currency)} <span className="meta">/ un.</span>
          </dd>
        </div>
        <div>
          <dt>Markup</dt>
          <dd>{formatMarkupFactor(snapshot.markupFactor)}</dd>
        </div>
        <div>
          <dt>{marginLabel}</dt>
          <dd>{formatPercentDisplay(snapshot.marginPercent)}</dd>
        </div>
        <div>
          <dt>Margem R$ / un.</dt>
          <dd>{money(snapshot.marginMoney, currency)}</dd>
        </div>
      </dl>

      {snapshot.error ? (
        <p className="costing-banner costing-banner--error" role="alert">
          {snapshot.error}
        </p>
      ) : null}

      <div className="costing-calculator__actions no-print">
        <button type="button" className="ghost" onClick={onLoadPolicy} disabled={!canSimulate || !suggestedPrice}>
          Carregar política efetiva
        </button>
        <button type="button" className="ghost" onClick={onReset} disabled={!canSimulate}>
          Restaurar política / cenário
        </button>
        {canApply ? (
          <button type="button" className="primary" onClick={onRequestApply} disabled={!snapshot.price}>
            Aplicar novo preço…
          </button>
        ) : priceDefinitiveAllowed ? null : (
          <p className="meta">Aplicação de preço derivada do custo bloqueada por completude.</p>
        )}
      </div>
      <p className="meta no-print">
        {SURFACE_PHRASES.priceRecordHint}
      </p>
    </div>
  );
}

export function CostingDecisionPage() {
  const { calcId: routeCalcId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const canSimulate =
    hasPermission("pricing.simulation.manage") ||
    hasPermission("pricing.review") ||
    hasPermission("costing.read");
  const canPublish = hasPermission("pricing.publish");

  const [listState, setListState] = useState<
    { kind: "carregando" } | { kind: "ok"; items: CostingCalculation[] } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const [detailState, setDetailState] = useState<
    { kind: "idle" } | { kind: "carregando" } | { kind: "ok"; data: CostingCalculation } | { kind: "erro"; error: unknown }
  >({ kind: "idle" });
  const [prices, setPrices] = useState<PracticedPrice[]>([]);
  const [productCard, setProductCard] = useState<ProductCard | null>(null);
  const [policyResolution, setPolicyResolution] = useState<Record<string, unknown> | null>(null);
  const [suggestedPrice, setSuggestedPrice] = useState<string | null>(null);
  const [policyBaseline, setPolicyBaseline] = useState<CalculatorSnapshot | null>(null);
  const [calculator, setCalculator] = useState<CalculatorSnapshot>(emptyCalculator());
  const [initialCalculator, setInitialCalculator] = useState<CalculatorSnapshot>(emptyCalculator());
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"grafico" | "tabela">("grafico");
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const [scenario, setScenario] = useState<ScenarioKey | null>(null);
  const [auditOpen, setAuditOpen] = useState(false);
  const [confirmApply, setConfirmApply] = useState(false);
  const [applyBusy, setApplyBusy] = useState(false);
  const [applyConflict, setApplyConflict] = useState<string | null>(null);
  const [applyDone, setApplyDone] = useState<string | null>(null);
  const applyKeyRef = useRef<string | null>(null);
  const decideKeyRef = useRef<string | null>(null);
  const calcTriggerRef = useRef<HTMLButtonElement | null>(null);
  const drawerPanelRef = useRef<HTMLElement | null>(null);

  const selectedId = routeCalcId || searchParams.get("calculo") || "";

  function loadList() {
    setListState({ kind: "carregando" });
    api
      .listCostingCalculations()
      .then((body) => setListState({ kind: "ok", items: body.items }))
      .catch((error) => {
        if (isCancelledError(error)) return;
        setListState({ kind: "erro", error });
      });
  }

  function loadDetail(id: string, opts?: { keepApplyFeedback?: boolean }) {
    if (!id) {
      setDetailState({ kind: "idle" });
      return;
    }
    setDetailState({ kind: "carregando" });
    if (!opts?.keepApplyFeedback) {
      setApplyDone(null);
      setApplyConflict(null);
    }
    Promise.all([
      api.getCostingCalculation(id),
      api.listPracticedPrices().catch(() => ({ items: [] as PracticedPrice[] })),
    ])
      .then(async ([body, priceBody]) => {
        const data = body.data;
        setPrices(priceBody.items ?? []);
        setDetailState({ kind: "ok", data });
        const base = data.cost_base;
        let product: ProductCard | null = null;
        let resolution: Record<string, unknown> | null = null;
        let suggested: string | null = null;
        if (data.technical_product_id) {
          try {
            const prodBody = await api.getProduct(data.technical_product_id);
            product = (prodBody.data ?? prodBody) as ProductCard;
          } catch {
            product = null;
          }
          try {
            const pol = await api.resolveMarkupPolicy(data.technical_product_id);
            resolution = pol.data ?? null;
          } catch {
            resolution = null;
          }
        }
        setProductCard(product);
        setPolicyResolution(resolution);
        const costNum = Number(String(base?.amount ?? "").replace(",", "."));
        const effective = resolution?.effective as Record<string, unknown> | undefined;
        if (effective && Number.isFinite(costNum) && costNum > 0) {
          const kind = String(effective.kind);
          const value = Number(String(effective.value ?? "").replace(",", "."));
          if (kind === "markup_factor" && Number.isFinite(value)) {
            suggested = (costNum * value).toFixed(2);
          } else if (kind === "margin_rate" && Number.isFinite(value) && value < 1) {
            suggested = (costNum / (1 - value)).toFixed(2);
          }
        }
        setSuggestedPrice(suggested);
        const snap = initFromCostBase({
          amount: base?.amount ?? null,
          origin: base?.origin ?? "absent",
          originLabel: base?.origin_label ?? "Custo-base ausente",
          incomplete: base?.incomplete ?? !data.cost_scope?.price_definitive_allowed,
          initialMarkup: suggested && costNum > 0 ? String(Number(suggested) / costNum) : "2",
        });
        if (suggested) {
          const withPrice = applyDesiredPrice(snap, suggested);
          setCalculator(withPrice);
          setInitialCalculator(withPrice);
          setPolicyBaseline(withPrice);
        } else {
          setCalculator(snap);
          setInitialCalculator(snap);
          setPolicyBaseline(null);
        }
      })
      .catch((error) => {
        if (isCancelledError(error)) return;
        setDetailState({ kind: "erro", error });
      });
  }

  useEffect(() => {
    loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, orgId]);

  useEffect(() => {
    loadDetail(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, orgId, selectedId]);

  const scenarios = useMemo(
    () => (listState.kind === "ok" ? resolveScenarios(listState.items) : null),
    [listState],
  );

  useEffect(() => {
    if (!scenarios || selectedId) return;
    if (scenarios.A) {
      setScenario("A");
      setSearchParams({ calculo: scenarios.A.id });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarios]);

  useEffect(() => {
    if (!scenarios || !selectedId) return;
    const entries: Array<[ScenarioKey, CostingCalculation | null]> = [
      ["A", scenarios.A],
      ["B", scenarios.B],
      ["C", scenarios.C],
      ["D", scenarios.D],
    ];
    const match = entries.find(([, item]) => item?.id === selectedId);
    if (match) setScenario(match[0]);
    else if (scenarios.D_planned?.id === selectedId || scenarios.D_actual?.id === selectedId) {
      setScenario("D");
    }
  }, [scenarios, selectedId]);

  function selectCalculation(id: string, key?: ScenarioKey) {
    if (key) setScenario(key);
    if (routeCalcId) {
      navigate(`/gestao/custos/calculos/${id}`);
      return;
    }
    setSearchParams(id ? { calculo: id } : {});
  }

  function openScenario(key: ScenarioKey) {
    const target = scenarios?.[key];
    if (!target) return;
    selectCalculation(target.id, key);
  }

  useEffect(() => {
    if (!drawerOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const panel = drawerPanelRef.current;
    const focusable = panel?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    focusable?.[0]?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setDrawerOpen(false);
        calcTriggerRef.current?.focus();
        return;
      }
      if (event.key !== "Tab" || !panel || !focusable?.length) return;
      const list = Array.from(focusable);
      const first = list[0];
      const last = list[list.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", onKey);
    };
  }, [drawerOpen]);

  if (listState.kind === "carregando" && detailState.kind === "idle") return <LoadingState />;
  if (listState.kind === "erro") return <ErrorState error={listState.error} onRetry={loadList} />;

  const data = detailState.kind === "ok" ? detailState.data : null;
  const scope = data?.cost_scope;
  const purchased = Boolean(data && isPurchasedCalc(data));
  const ingredientsComplete = Boolean(scope?.ingredients_complete);
  const productionComplete = Boolean(scope?.production_complete);
  const acquisitionComplete = Boolean(scope?.acquisition_complete);
  const priceDefinitiveAllowed = Boolean(
    scope?.price_definitive_allowed ?? (purchased ? acquisitionComplete : productionComplete),
  );
  const completenessLabel = scope?.completeness_label || costingCompleteness(data?.completeness ?? "partial").label;
  const marginLabel =
    scope?.margin_label ||
    (purchased ? "Margem sobre o custo de aquisição" : "Margem sobre o custo conhecido");
  const currency = data?.currency || "BRL";
  const title = data ? nameOf(data) : "Custos e calculadora";
  const productPrices = prices
    .filter((p) => !data?.technical_product_id || p.technical_product_id === data.technical_product_id)
    .sort((a, b) => String(b.valid_from ?? "").localeCompare(String(a.valid_from ?? "")));
  const practiced =
    productPrices.find((p) => p.status === "active" || p.status === "published") ?? null;
  const analytics = data?.analytics;
  const componentBars: ChartBar[] = (analytics?.component_bars ?? []).map((row) => ({
    id: row.id ?? row.label,
    label: row.label,
    amount: row.amount,
    sharePercent: row.share_of_known_percent,
    state: row.state,
  }));

  const dPlan = scenarios?.D_planned ?? null;
  const dAct = scenarios?.D_actual ?? null;
  const compareSeries =
    scenario === "D" || (data && /focaccia/i.test(title))
      ? [
          {
            label: "Custo do recorte (R$)",
            planned: dPlan?.total_amount ?? null,
            actual: dAct?.total_amount ?? null,
            metric: "cost" as const,
          },
          {
            label: "Custo unitário vendável (R$ / un.)",
            planned: dPlan?.sellable_unit_amount ?? null,
            actual: dAct?.sellable_unit_amount ?? null,
            metric: "cost" as const,
          },
          {
            label: "Rendimento (un.)",
            planned: dPlan?.sellable_quantity ?? null,
            actual: dAct?.sellable_quantity ?? null,
            metric: "yield" as const,
          },
        ]
      : [
          {
            label: "Total do recorte (R$)",
            planned: data?.kind === "planned" ? data.total_amount : null,
            actual: data?.kind === "actual" ? data.total_amount : null,
          },
        ];

  const productCompare = [scenarios?.A, scenarios?.C, scenarios?.D_planned].filter(Boolean) as CostingCalculation[];
  const scenarioCompare = [scenarios?.A, scenarios?.B].filter(Boolean) as CostingCalculation[];

  const unitCost = data?.sellable_unit_amount;
  const yieldUnits = data?.subject?.commercial_presentation?.yield_units ?? data?.sellable_quantity;
  const policyEffective = (policyResolution?.effective as Record<string, unknown> | undefined) ?? null;
  const policyKindLabel = policyEffective
    ? policyEffective.kind === "margin_rate"
      ? "política de margem"
      : "política de markup"
    : null;
  const policySummary =
    (policyResolution?.human_summary as string | undefined) ||
    (policyResolution?.reason_label as string | undefined) ||
    null;
  const saleUnitId = productCard?.sale_unit?.id ?? null;
  const canApplyPrice =
    Boolean(canPublish && priceDefinitiveAllowed && data?.technical_product_id && saleUnitId && calculator.price);
  const simulatingAwayFromPolicy =
    Boolean(suggestedPrice) &&
    Number(String(calculator.price ?? "").replace(",", ".")) !==
      Number(String(suggestedPrice ?? "").replace(",", "."));

  async function confirmAndApplyPrice() {
    if (!data?.technical_product_id || !saleUnitId || !calculator.price || applyBusy) return;
    setApplyBusy(true);
    setApplyConflict(null);
    const createKey = applyKeyRef.current ?? crypto.randomUUID();
    applyKeyRef.current = createKey;
    const decideKey = decideKeyRef.current ?? crypto.randomUUID();
    decideKeyRef.current = decideKey;
    try {
      const created = await api.catalogCommand<{ data: PracticedPrice; row_version: number }>(
        "/pricing/practiced",
        {
          body: {
            technical_product_id: data.technical_product_id,
            channel: "own_counter",
            amount: String(calculator.price),
            currency: currency,
            valid_from: new Date().toISOString(),
            justification: "GATE4-VALIDACAO — aplicação pela calculadora (não produção)",
            sale_basis_quantity: "1",
            sale_basis_unit_id: saleUnitId,
          },
          idempotencyKey: createKey,
        },
      );
      const draft = created.data;
      await api.catalogCommand(`/pricing/practiced/${draft.id}/decide`, {
        body: {
          decision: "publish",
          notes: "GATE4-VALIDACAO — confirmação humana",
          reinforced_confirmation: true,
          expected_active_price_id: practiced?.id ?? null,
          expected_active_row_version: practiced?.row_version ?? null,
        },
        idempotencyKey: decideKey,
        ifMatch: draft.row_version ?? created.row_version,
      });
      setApplyDone(String(calculator.price));
      setConfirmApply(false);
      applyKeyRef.current = null;
      decideKeyRef.current = null;
      loadDetail(data.id);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 409 || err.status === 422)) {
        setApplyConflict(
          "Conflito ou regra de domínio impediu a aplicação. O contexto será recarregado; a operação não foi repetida silenciosamente.",
        );
        applyKeyRef.current = null;
        decideKeyRef.current = null;
        loadDetail(data.id, { keepApplyFeedback: true });
      } else if (!isCancelledError(err)) {
        setApplyConflict(err instanceof Error ? err.message : "Falha ao aplicar preço.");
      }
    } finally {
      setApplyBusy(false);
    }
  }

  const calculatorProps = data
    ? {
        calc: data,
        snapshot: calculator,
        canSimulate,
        canApply: canApplyPrice,
        ingredientsComplete,
        productionComplete,
        priceDefinitiveAllowed,
        purchased,
        marginLabel,
        scopeHint: scope?.hint || "",
        vigentePrice: practiced?.amount ?? null,
        suggestedPrice,
        policySummary,
        policyKindLabel,
        simulating: simulatingAwayFromPolicy,
        onMarkup: (value: string) => setCalculator((prev) => applyMarkupFactor(prev, value)),
        onPrice: (value: string) => setCalculator((prev) => applyDesiredPrice(prev, value)),
        onReset: () => setCalculator(policyBaseline ?? initialCalculator),
        onLoadPolicy: () => {
          if (policyBaseline) setCalculator(policyBaseline);
          else if (suggestedPrice) setCalculator((prev) => applyDesiredPrice(prev, suggestedPrice));
        },
        onRequestApply: () => {
          applyKeyRef.current = null;
          decideKeyRef.current = null;
          setConfirmApply(true);
        },
      }
    : null;

  return (
    <div className={`costing-decision ${drawerOpen ? "costing-decision--drawer-open" : ""}`}>
      <div className="costing-decision__main">
        <div className="page-head costing-decision__head">
          <div>
            <h1>{title}</h1>
            <p className="lede">
              Analise a formação do custo, compare cenários e simule preços na mesma unidade.
            </p>
          </div>
          <div className="costing-decision__head-actions no-print">
            <button type="button" className="ghost" onClick={() => window.print()}>
              Imprimir visão gerencial
            </button>
            <button
              type="button"
              className="primary costing-decision__calc-trigger"
              ref={calcTriggerRef}
              onClick={() => setDrawerOpen(true)}
              disabled={!data}
            >
              Simular preço
            </button>
          </div>
        </div>

        <section className="costing-scenarios no-print" aria-label="Cenários canônicos A–D">
          {(Object.keys(SCENARIO_META) as ScenarioKey[]).map((key) => {
            const available = Boolean(scenarios?.[key]);
            return (
              <button
                key={key}
                type="button"
                className={scenario === key ? "primary" : "ghost"}
                disabled={!available}
                onClick={() => openScenario(key)}
              >
                <strong>{SCENARIO_META[key].title}</strong>
                <span className="meta">{SCENARIO_META[key].hint}</span>
              </button>
            );
          })}
        </section>

        {detailState.kind === "carregando" ? <LoadingState /> : null}
        {detailState.kind === "erro" ? (
          <ErrorState error={detailState.error} onRetry={() => loadDetail(selectedId)} />
        ) : null}
        {detailState.kind === "idle" && !selectedId ? (
          <EmptyState>Escolha um cenário A–D para abrir a análise.</EmptyState>
        ) : null}

        {data ? (
          <>
            <section className="costing-kpis" aria-label="Indicadores de síntese">
              <article>
                <h2>{purchased ? "Custo de aquisição" : "Custo do recorte"}</h2>
                <p className="costing-figure">{money(data.total_amount, currency)}</p>
                <p className="meta">
                  {scope?.scope_label || "Custo conhecido"} ·{" "}
                  {purchased ? "R$ / unidade de compra" : "R$ / recorte"} ·{" "}
                  {formatDateTime(data.valuation_at)}
                </p>
              </article>
              <article>
                <h2>Custo / unidade</h2>
                <p className="costing-figure">{money(unitCost, currency)}</p>
                <p className="meta">
                  {purchased
                    ? "Custo de aquisição por unidade"
                    : yieldUnits != null
                      ? `${yieldUnits} un. de rendimento`
                      : "Sem rendimento"}{" "}
                  · R$ / un.
                </p>
              </article>
              <article>
                <h2>Preço atual / un.</h2>
                <p className="costing-figure">{practiced ? money(practiced.amount, currency) : "—"}</p>
                <p className="meta">{practiced ? "Praticado · mesma unidade" : "Sem preço vigente"}</p>
              </article>
              <article>
                <h2>{marginLabel}</h2>
                <p className="costing-figure">{formatPercentDisplay(calculator.marginPercent)}</p>
                <p className="meta">Simulação sobre a mesma unidade do custo-base</p>
              </article>
              <article>
                <h2>Markup / un.</h2>
                <p className="costing-figure">{formatMarkupFactor(calculator.markupFactor)}</p>
                <p className="meta">Fator preço ÷ custo (mesma unidade)</p>
              </article>
              <article>
                <h2>Escopo</h2>
                <p>
                  <StatusBadge
                    tone={
                      priceDefinitiveAllowed
                        ? "sucesso"
                        : purchased || ingredientsComplete
                          ? "atencao"
                          : "erro"
                    }
                    label={completenessLabel}
                  />
                </p>
                <p className="meta">{scope?.hint}</p>
              </article>
            </section>

            <section aria-label="Categorias do escopo">
              <h2>Categorias incluídas e excluídas</h2>
              <ChartTable
                caption="Escopo da política de custeio"
                headers={["Categoria", "Estado", "Valor"]}
                rows={(scope?.categories ?? []).map((row) => [
                  row.label,
                  row.state_label,
                  row.amount == null ? "—" : money(row.amount, currency),
                ])}
              />
            </section>

            <div className="costing-view-toggle no-print" role="group" aria-label="Modo de visualização">
              <button
                type="button"
                className={viewMode === "grafico" ? "primary" : "ghost"}
                onClick={() => setViewMode("grafico")}
              >
                Gráfico
              </button>
              <button
                type="button"
                className={viewMode === "tabela" ? "primary" : "ghost"}
                onClick={() => setViewMode("tabela")}
              >
                Tabela
              </button>
            </div>

            <section className="costing-analysis" aria-label="Análise visual">
              {viewMode === "grafico" ? (
                <>
                  <HorizontalBars
                    title={analytics?.composition_title || "Formação do custo"}
                    caption={analytics?.share_basis_label}
                    bars={componentBars}
                    currency={currency}
                    selectedId={selectedComponent}
                    onSelect={(bar) => setSelectedComponent(bar.id || bar.label)}
                  />
                  {analytics?.use_waterfall ? (
                    <WaterfallBars
                      title={analytics.formation_title || "Cascata do custo"}
                      steps={analytics.waterfall ?? []}
                      currency={currency}
                    />
                  ) : (
                    <HorizontalBars
                      title="Formação do custo por categoria"
                      bars={(analytics?.category_bars ?? []).map((row) => ({
                        id: row.category,
                        label: row.category_label,
                        amount: row.amount,
                        sharePercent: row.share_of_known_percent,
                        state: row.state,
                      }))}
                      currency={currency}
                    />
                  )}
                  <GroupedCompare
                    title={
                      scenario === "D" || /focaccia/i.test(title)
                        ? "Previsto × realizado (FOCACCIA)"
                        : "Previsto × realizado"
                    }
                    series={compareSeries}
                    currency={currency}
                  />
                  <ScenarioImpact
                    title="Impacto da simulação (mesma unidade)"
                    cost={calculator.costBase}
                    currentPrice={practiced?.amount ?? null}
                    simulatedPrice={calculator.price}
                    currentMarginPct={
                      practiced && calculator.costBase
                        ? String(
                            ((Number(practiced.amount) - Number(calculator.costBase)) /
                              Number(practiced.amount)) *
                              100,
                          )
                        : null
                    }
                    simulatedMarginPct={calculator.marginPercent}
                    currency={currency}
                  />
                </>
              ) : (
                <ChartTable
                  caption="Tabela equivalente à composição"
                  headers={["Componente", "Quantidade", "Custo", "Estado", "Participação"]}
                  rows={(data.components ?? []).map((item) => [
                    item.display_name || item.category_label || "—",
                    formatOperationalQuantity(item.quantity, item.unit_code),
                    item.amount == null ? "Sem informação" : money(item.amount, currency),
                    item.price_missing ? "Sem preço vigente" : item.quality_label || qualityLabel(item.quality),
                    item.share_percent ? formatPercentDisplay(item.share_percent) : "—",
                  ])}
                />
              )}
            </section>

            {scenario === "D" && dPlan && dAct ? (
              <section aria-label="Desvio FOCACCIA">
                <h2>Desvio previsto × realizado</h2>
                <ChartTable
                  caption="FOCACCIA — mesma base de recorte"
                  headers={["Métrica", "Previsto", "Realizado", "Desvio", "Avaliação"]}
                  rows={[
                    (() => {
                      const sig = varianceSignal("yield", dPlan.sellable_quantity, dAct.sellable_quantity);
                      return [
                        "Rendimento (un.)",
                        String(dPlan.sellable_quantity ?? "—"),
                        String(dAct.sellable_quantity ?? "—"),
                        sig.delta == null ? "—" : String(sig.delta),
                        sig.label ?? "—",
                      ];
                    })(),
                    (() => {
                      const sig = varianceSignal(
                        "cost",
                        dPlan.sellable_unit_amount,
                        dAct.sellable_unit_amount,
                      );
                      return [
                        "Custo unitário (R$ / un.)",
                        money(dPlan.sellable_unit_amount, currency),
                        money(dAct.sellable_unit_amount, currency),
                        sig.delta == null ? "—" : money(String(sig.delta), currency),
                        sig.label ?? "—",
                      ];
                    })(),
                    (() => {
                      const sig = varianceSignal("cost", dPlan.total_amount, dAct.total_amount);
                      return [
                        "Custo do recorte (R$)",
                        money(dPlan.total_amount, currency),
                        money(dAct.total_amount, currency),
                        sig.delta == null ? "—" : money(String(sig.delta), currency),
                        sig.label ?? "—",
                      ];
                    })(),
                  ]}
                />
              </section>
            ) : null}

            <section aria-label="Comparação entre produtos">
              <h2>Comparação entre produtos</h2>
              {productCompare.length < 2 ? (
                <p className="meta">Aguardando cenários A, C e D com base unitária comparável.</p>
              ) : (
                <ChartTable
                  caption="A · C · D — custo e preço por unidade"
                  headers={["Produto", "Custo / un.", "Preço / un.", "Escopo"]}
                  rows={productCompare.map((item) => {
                    const price = prices
                      .filter((p) => p.technical_product_id === item.technical_product_id && p.status === "active")
                      .slice(-1)[0];
                    return [
                      nameOf(item),
                      item.sellable_unit_amount == null
                        ? "Sem informação"
                        : `${money(item.sellable_unit_amount, item.currency)} / un.`,
                      price ? `${money(price.amount, currency)} / un.` : "Sem preço vigente",
                      productComparisonScope(item),
                    ];
                  })}
                />
              )}
            </section>

            <section aria-label="Comparação entre cenários">
              <h2>Comparação entre cenários</h2>
              {scenarioCompare.length < 2 ? (
                <p className="meta">Cenários A (completo de ingredientes) e B (parcial) indisponíveis.</p>
              ) : (
                <ChartTable
                  caption="Mesmo tipo de produto · completo vs parcial de ingredientes"
                  headers={["Cenário", "Produto", "Total conhecido", "Custo / un."]}
                  rows={scenarioCompare.map((item, index) => [
                    index === 0 ? "A · ingredientes completos" : "B · parcial",
                    nameOf(item),
                    item.total_amount == null ? "Sem informação" : money(item.total_amount, item.currency),
                    item.sellable_unit_amount == null
                      ? "Sem informação"
                      : `${money(item.sellable_unit_amount, item.currency)} / un.`,
                  ])}
                />
              )}
            </section>

            <section aria-label="Histórico">
              <h2>Evolução histórica</h2>
              {productPrices.length >= 3 ? (
                <ChartTable
                  caption="Preço de venda no tempo (mesma unidade)"
                  headers={["Vigência", "Preço / un.", "Canal", "Estado"]}
                  rows={productPrices.map((row) => [
                    row.valid_from ? formatDateTime(row.valid_from) : "—",
                    money(row.amount, currency),
                    channelLabel(row.channel),
                    practicedStatusLabel(row.status),
                  ])}
                />
              ) : (
                <p className="meta">Histórico de preço deste produto ainda com menos de 3 pontos.</p>
              )}
            </section>

            <section className="no-print" aria-label="Detalhes técnicos de auditoria">
              <button
                type="button"
                className="ghost costing-memory-toggle"
                aria-expanded={auditOpen}
                onClick={() => setAuditOpen((value) => !value)}
              >
                {auditOpen
                  ? "Ocultar detalhes técnicos de auditoria"
                  : "Detalhes técnicos de auditoria"}
              </button>
              {auditOpen && data.price_basis?.flour_audit ? (
                <div className="costing-memory">
                  <h2>Detalhes técnicos de auditoria</h2>
                  <p className="meta">
                    Farinha {data.price_basis.flour_audit.sku}: {data.price_basis.flour_audit.finding}
                  </p>
                  <p className="meta">
                    {data.price_basis.label}. {data.price_basis.note}
                  </p>
                </div>
              ) : null}
            </section>

            <section aria-label="Memória de cálculo">
              <button
                type="button"
                className="ghost costing-memory-toggle"
                aria-expanded={memoryOpen}
                onClick={() => setMemoryOpen((value) => !value)}
              >
                {memoryOpen ? "Ocultar memória de cálculo" : "Abrir memória de cálculo"}
              </button>
              {memoryOpen ? (
                <div className="costing-memory">
                  <h2>Memória de cálculo</h2>
                  <dl>
                    <div>
                      <dt>Fundamento do preço</dt>
                      <dd>
                        {data.price_basis?.label}: {data.price_basis?.formula}. {data.price_basis?.note}
                      </dd>
                    </div>
                    <div>
                      <dt>Escopo</dt>
                      <dd>
                        {scope?.scope_label}. {scope?.hint}
                      </dd>
                    </div>
                    <div>
                      <dt>Resultado simulado</dt>
                      <dd>
                        preço {money(calculator.price, currency)} / un.; markup{" "}
                        {formatMarkupFactor(calculator.markupFactor)}; {marginLabel}{" "}
                        {formatPercentDisplay(calculator.marginPercent)}; margem monetária{" "}
                        {money(calculator.marginMoney, currency)} / un.
                      </dd>
                    </div>
                  </dl>
                  {(data.components ?? []).map((item) => (
                    <div
                      key={item.id || item.display_name}
                      className={
                        selectedComponent &&
                        (item.id === selectedComponent || item.display_name === selectedComponent)
                          ? "costing-memory__block is-selected"
                          : "costing-memory__block"
                      }
                    >
                      <h3>{item.display_name}</h3>
                      <ul>
                        {(item.memory ?? []).map((line) => (
                          <li key={line.code}>
                            <strong>{line.label}:</strong> {line.value}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : null}
            </section>

            <p className="meta no-print">
              <Link className="ghost" to="/gestao/custos">
                Voltar ao painel de custos
              </Link>
            </p>
          </>
        ) : null}
      </div>

      <aside className="costing-decision__side no-print" aria-label="Calculadora de preço">
        {calculatorProps ? (
          <CalculatorPanel {...calculatorProps} />
        ) : (
          <div className="costing-calculator">
            <h2>Calculadora de preço</h2>
            <p className="meta">Selecione um cenário A–D.</p>
          </div>
        )}
      </aside>

      {drawerOpen && calculatorProps ? (
        <div className="costing-calc-drawer no-print">
          <button
            type="button"
            className="costing-calc-drawer__mask"
            aria-label="Fechar fundo da calculadora"
            onClick={() => {
              setDrawerOpen(false);
              calcTriggerRef.current?.focus();
            }}
          />
          <aside
            ref={drawerPanelRef}
            className="costing-calc-drawer__panel"
            role="dialog"
            aria-modal="true"
            aria-label="Calculadora de preço"
          >
            <header className="costing-calc-drawer__head">
              <h2>Calculadora de preço</h2>
              <button
                type="button"
                className="ghost"
                onClick={() => {
                  setDrawerOpen(false);
                  calcTriggerRef.current?.focus();
                }}
              >
                Fechar
              </button>
            </header>
            <div className="costing-calc-drawer__body">
              <CalculatorPanel {...calculatorProps} />
            </div>
          </aside>
        </div>
      ) : null}

      {confirmApply && data ? (
        <div className="costing-confirm-modal no-print" role="dialog" aria-modal="true" aria-label="Confirmar aplicação de preço">
          <div className="costing-confirm-modal__panel">
            <h2>Confirmar novo preço</h2>
            <p className="meta">{SURFACE_PHRASES.priceRecordConfirm}</p>
            <dl>
              <div>
                <dt>Produto</dt>
                <dd>{title}</dd>
              </div>
              <div>
                <dt>Preço atual</dt>
                <dd>{practiced ? money(practiced.amount, currency) : "Sem preço vigente"}</dd>
              </div>
              <div>
                <dt>Preço proposto</dt>
                <dd>{money(calculator.price, currency)}</dd>
              </div>
              <div>
                <dt>Diferença</dt>
                <dd>
                  {practiced && calculator.price
                    ? money(
                        String(
                          Number(String(calculator.price).replace(",", ".")) -
                            Number(String(practiced.amount).replace(",", ".")),
                        ),
                        currency,
                      )
                    : "—"}
                </dd>
              </div>
              <div>
                <dt>Base comercial</dt>
                <dd>1 {productCard?.sale_unit?.display_name || "unidade"}</dd>
              </div>
              <div>
                <dt>Custo utilizado</dt>
                <dd>{money(calculator.costBase, currency)}</dd>
              </div>
              <div>
                <dt>Completude</dt>
                <dd>{completenessLabel}</dd>
              </div>
              <div>
                <dt>Política</dt>
                <dd>{policySummary || "Sem política efetiva carregada"}</dd>
              </div>
              <div>
                <dt>Arredondamento</dt>
                <dd>Comercial half-up, 2 casas</dd>
              </div>
            </dl>
            {applyConflict ? (
              <p className="costing-banner costing-banner--error" role="alert">
                {applyConflict}
              </p>
            ) : null}
            <div className="costing-calculator__actions">
              <button type="button" className="ghost" disabled={applyBusy} onClick={() => setConfirmApply(false)}>
                Cancelar
              </button>
              <button type="button" className="primary" disabled={applyBusy} onClick={confirmAndApplyPrice}>
                {applyBusy ? "Aplicando…" : "Confirmar e criar decisão"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {applyDone ? (
        <div className="feedback no-print" role="status">
          <p>Novo preço vigente: {money(applyDone, currency)}. Histórico anterior preservado.</p>
        </div>
      ) : null}

      {data ? (
        <div className="print-only costing-print">
          <h1>Visão gerencial — custos e preço</h1>
          <p>
            {title} · {completenessLabel} · {formatDateTime(data.valuation_at)}
          </p>
          <p>
            {purchased ? "Custo de aquisição" : "Recorte"}: {money(data.total_amount, currency)} · / un.:{" "}
            {money(data.sellable_unit_amount, currency)} · simulação: {money(calculator.price, currency)} / un. ·{" "}
            {marginLabel} {formatPercentDisplay(calculator.marginPercent)}
          </p>
          <h2>Escopo</h2>
          <p>
            {scope?.comparison_scope_label || completenessLabel}. {scope?.hint}
          </p>
          <h2>Composição</h2>
          <ul>
            {(data.components ?? []).map((item) => (
              <li key={item.id || item.display_name}>
                {item.display_name}: {money(item.amount, currency)} (
                {item.quality_label || qualityLabel(item.quality)})
              </li>
            ))}
          </ul>
          {scenario === "D" && dPlan && dAct ? (
            <>
              <h2>Previsto × realizado</h2>
              <ul>
                <li>
                  Rendimento: {String(dPlan.sellable_quantity)} → {String(dAct.sellable_quantity)} ·{" "}
                  {varianceSignal("yield", dPlan.sellable_quantity, dAct.sellable_quantity).label}
                </li>
                <li>
                  Custo unitário: {money(dPlan.sellable_unit_amount, currency)} →{" "}
                  {money(dAct.sellable_unit_amount, currency)} ·{" "}
                  {
                    varianceSignal("cost", dPlan.sellable_unit_amount, dAct.sellable_unit_amount)
                      .label
                  }
                </li>
                <li>
                  Custo do recorte: {money(dPlan.total_amount, currency)} →{" "}
                  {money(dAct.total_amount, currency)} ·{" "}
                  {varianceSignal("cost", dPlan.total_amount, dAct.total_amount).label}
                </li>
              </ul>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

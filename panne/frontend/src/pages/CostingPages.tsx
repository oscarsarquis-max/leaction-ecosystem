/**
 * Páginas econômicas: políticas A/B/C, listas legadas, preços gerenciais, simulador.
 */
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, isCancelledError } from "../api/errors";
import type {
  CostingCalculation,
  CostingPolicy,
  PracticedPrice,
  PricingSimulation,
  ProductCard,
} from "../api/types";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import { statusLabel } from "../format";
import {
  channelLabel,
  costingCompleteness,
  costingKindLabel,
  formatMarkupFactor,
  formatPercentDisplay,
  practicedStatusLabel,
  priceCriterionLabel,
  simulationKindLabel,
  supplyModeSurfaceLabel,
} from "../language/costing";
import { formatMoneyAmount } from "../language/ingredients";
import { SURFACE_PHRASES } from "../language/surface";
import { formatDateTime } from "../format";
import { useOrganization } from "../session/OrganizationContext";
import { CostingDecisionPage } from "./CostingDecisionPage";

function parseAmt(v: string | null | undefined): number | null {
  if (v == null || v === "") return null;
  const n = Number(String(v).replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function useList<T>(loader: () => Promise<{ items: T[] }>, key: string) {
  const [state, setState] = useState<
    { kind: "carregando" } | { kind: "ok"; items: T[] } | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  function load() {
    setState({ kind: "carregando" });
    loader()
      .then((body) => setState({ kind: "ok", items: body.items }))
      .catch((error) => {
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return { state, load };
}

function completenessBadge(code: string) {
  const item = costingCompleteness(code);
  return <StatusBadge tone={item.tone} label={item.label} />;
}

function MarkupPoliciesPanel() {
  const { api, hasPermission, active } = useOrganization();
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [audits, setAudits] = useState<Array<Record<string, unknown>>>([]);
  const [products, setProducts] = useState<ProductCard[]>([]);
  const [families, setFamilies] = useState<Array<{ id: string; display_name: string }>>([]);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showAudit, setShowAudit] = useState(false);
  const [resolveProductId, setResolveProductId] = useState("");
  const [resolveResult, setResolveResult] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState({
    code: "",
    display_name: "",
    kind: "markup_factor",
    value: "2.5",
    scope_level: "organization",
    product_family_id: "",
    technical_product_id: "",
    valid_from: new Date().toISOString().slice(0, 16),
    justification: "",
  });
  const canManage = hasPermission("pricing.policy.manage");
  const canAudit = hasPermission("pricing.audit.read");

  function scopeLabel(level: unknown) {
    if (level === "product") return "Produto";
    if (level === "family") return "Família";
    if (level === "organization") return "Organização";
    return String(level ?? "—");
  }
  function statusLabelLocal(status: unknown) {
    if (status === "active") return "Vigente";
    if (status === "draft") return "Rascunho";
    if (status === "retired") return "Encerrada";
    return String(status ?? "—");
  }
  function valueLabel(row: Record<string, unknown>) {
    const raw = Number(String(row.value ?? "").replace(",", "."));
    if (!Number.isFinite(raw)) return String(row.value ?? "—");
    if (row.kind === "margin_rate") return `${(raw * 100).toFixed(1).replace(".", ",")}%`;
    return `${raw.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}×`;
  }

  function load() {
    setError(null);
    setConflict(null);
    Promise.all([
      api.listMarkupPolicies(),
      canAudit ? api.listEconomicAudit().catch(() => ({ items: [] })) : Promise.resolve({ items: [] }),
      api.listProducts({ limit: "100", offset: "0" }).catch(() => ({ items: [] as ProductCard[] })),
    ])
      .then(([policies, auditBody, productBody]) => {
        setItems(policies.items ?? []);
        setAudits(auditBody.items ?? []);
        const prods = productBody.items ?? [];
        setProducts(prods);
        const famMap = new Map<string, string>();
        for (const p of prods) {
          if (p.family?.id && p.family.display_name) famMap.set(p.family.id, p.family.display_name);
        }
        setFamilies([...famMap.entries()].map(([id, display_name]) => ({ id, display_name })));
      })
      .catch((err) => {
        if (isCancelledError(err)) return;
        setError(err);
      });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, active?.organization_id]);

  async function createPolicy(event: FormEvent) {
    event.preventDefault();
    if (!canManage || busy) return;
    setBusy(true);
    setConflict(null);
    try {
      const body: Record<string, unknown> = {
        code: form.code.trim(),
        display_name: form.display_name.trim() || form.code.trim(),
        kind: form.kind,
        value: form.kind === "margin_rate" && Number(form.value) > 1 ? String(Number(form.value) / 100) : form.value,
        scope_level: form.scope_level,
        valid_from: new Date(form.valid_from).toISOString(),
        justification: form.justification.trim() || null,
      };
      if (form.scope_level === "family") body.product_family_id = form.product_family_id;
      if (form.scope_level === "product") body.technical_product_id = form.technical_product_id;
      await api.catalogCommand("/pricing/markup-policies", {
        body,
        idempotencyKey: crypto.randomUUID(),
      });
      setForm((prev) => ({ ...prev, code: "", display_name: "", justification: "" }));
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflict("Conflito de versão ou vigência. Recarregue e tente de novo.");
      } else {
        setError(err);
      }
    } finally {
      setBusy(false);
    }
  }

  async function activatePolicy(row: Record<string, unknown>) {
    if (!canManage || busy) return;
    setBusy(true);
    setConflict(null);
    try {
      await api.catalogCommand(`/pricing/markup-policies/${row.id}/activate`, {
        body: { notes: "ativação pela tela de políticas" },
        idempotencyKey: crypto.randomUUID(),
        ifMatch: Number(row.row_version) || null,
      });
      load();
    } catch (err) {
      if (err instanceof ApiError && (err.status === 409 || err.status === 422)) {
        setConflict(
          "Não foi possível ativar: vigência conflitante ou versão desatualizada. Recarregue o contexto.",
        );
        load();
      } else {
        setError(err);
      }
    } finally {
      setBusy(false);
    }
  }

  async function retirePolicy(row: Record<string, unknown>) {
    if (!canManage || busy) return;
    setBusy(true);
    setConflict(null);
    try {
      await api.catalogCommand(`/pricing/markup-policies/${row.id}/retire`, {
        body: { notes: "encerramento temporal pela tela de políticas" },
        idempotencyKey: crypto.randomUUID(),
        ifMatch: Number(row.row_version) || null,
      });
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setConflict("Versão desatualizada. O contexto foi recarregado.");
        load();
      } else {
        setError(err);
      }
    } finally {
      setBusy(false);
    }
  }

  async function resolveForProduct() {
    if (!resolveProductId) return;
    setBusy(true);
    try {
      const body = await api.resolveMarkupPolicy(resolveProductId);
      setResolveResult(body.data ?? null);
    } catch (err) {
      if (isCancelledError(err)) return;
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (error) return <ErrorState error={error} onRetry={load} />;

  const vigentes = items.filter((r) => r.status === "active");
  const historico = items.filter((r) => r.status !== "active");
  const visible = showHistory ? items : vigentes;

  return (
    <div className="econ-markup-policies">
      <p className="meta">
        Políticas por canal e estabelecimento serão tratadas em evolução posterior.
      </p>
      {conflict ? (
        <div className="feedback" role="alert">
          <p>{conflict}</p>
          <button type="button" className="ghost" onClick={load}>
            Recarregar
          </button>
        </div>
      ) : null}

      <div className="econ-markup-policies__toolbar no-print">
        <button type="button" className={showHistory ? "primary" : "ghost"} onClick={() => setShowHistory((v) => !v)}>
          {showHistory ? "Só vigentes" : "Ver histórico"}
        </button>
        {canAudit ? (
          <button type="button" className={showAudit ? "primary" : "ghost"} onClick={() => setShowAudit((v) => !v)}>
            {showAudit ? "Ocultar auditoria" : "Abrir auditoria"}
          </button>
        ) : null}
      </div>

      {visible.length === 0 ? (
        <EmptyState>
          {showHistory ? "Nenhuma política no histórico." : "Nenhuma política vigente."}
        </EmptyState>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Tipo</th>
                <th>Valor</th>
                <th>Escopo</th>
                <th>Início</th>
                <th>Situação</th>
                {canManage ? <th>Ações</th> : null}
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={String(row.id)}>
                  <td>{String(row.display_name || row.code)}</td>
                  <td>{row.kind === "margin_rate" ? "Margem" : "Markup"}</td>
                  <td>{valueLabel(row)}</td>
                  <td>{scopeLabel(row.scope_level)}</td>
                  <td>{row.valid_from ? formatDateTime(String(row.valid_from)) : "—"}</td>
                  <td>{statusLabelLocal(row.status)}</td>
                  {canManage ? (
                    <td>
                      {row.status === "draft" ? (
                        <button type="button" className="ghost" disabled={busy} onClick={() => activatePolicy(row)}>
                          Ativar
                        </button>
                      ) : null}
                      {row.status === "active" || row.status === "draft" ? (
                        <button type="button" className="ghost" disabled={busy} onClick={() => retirePolicy(row)}>
                          Encerrar vigência
                        </button>
                      ) : null}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showHistory && historico.length > 0 ? (
        <p className="meta">{historico.length} registro(s) históricos / encerrados.</p>
      ) : null}

      <section className="econ-premises" aria-label="Política efetiva por produto">
        <h3>Qual política vale para um produto</h3>
        <div className="econ-filters">
          <label>
            Produto
            <select value={resolveProductId} onChange={(e) => setResolveProductId(e.target.value)}>
              <option value="">Selecione</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.display_name}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="primary" disabled={!resolveProductId || busy} onClick={resolveForProduct}>
            Resolver
          </button>
        </div>
        {resolveResult ? (
          <div className="econ-policy-resolve" role="status">
            <p>
              {(resolveResult.human_summary as string) ||
                (resolveResult.reason_label as string) ||
                "Sem política efetiva."}
            </p>
            {resolveResult.effective ? (
              <dl>
                <div>
                  <dt>Tipo</dt>
                  <dd>
                    {(resolveResult.effective as Record<string, unknown>).kind === "margin_rate"
                      ? "Margem"
                      : "Markup"}
                  </dd>
                </div>
                <div>
                  <dt>Valor</dt>
                  <dd>{valueLabel(resolveResult.effective as Record<string, unknown>)}</dd>
                </div>
                <div>
                  <dt>Origem</dt>
                  <dd>{scopeLabel(resolveResult.origin_level)}</dd>
                </div>
                <div>
                  <dt>Vigência</dt>
                  <dd>
                    {formatDateTime(String((resolveResult.effective as Record<string, unknown>).valid_from ?? ""))}
                    {(resolveResult.effective as Record<string, unknown>).valid_to
                      ? ` → ${formatDateTime(String((resolveResult.effective as Record<string, unknown>).valid_to))}`
                      : " (aberta)"}
                  </dd>
                </div>
              </dl>
            ) : null}
          </div>
        ) : null}
      </section>

      {canManage ? (
        <section className="econ-premises" aria-label="Criar política">
          <h3>Criar política</h3>
          <p className="meta">
            Para substituir uma vigente no mesmo escopo, encerre a anterior e ative a nova (sucessão temporal).
          </p>
          <form className="econ-filters" onSubmit={createPolicy}>
            <label>
              Código
              <input
                value={form.code}
                onChange={(e) => setForm((p) => ({ ...p, code: e.target.value }))}
                required
              />
            </label>
            <label>
              Nome
              <input
                value={form.display_name}
                onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))}
              />
            </label>
            <label>
              Tipo
              <select
                value={form.kind}
                onChange={(e) => setForm((p) => ({ ...p, kind: e.target.value }))}
              >
                <option value="markup_factor">Markup</option>
                <option value="margin_rate">Margem</option>
              </select>
            </label>
            <label>
              Valor {form.kind === "margin_rate" ? "(taxa 0–1 ou %)" : "(fator)"}
              <input
                value={form.value}
                onChange={(e) => setForm((p) => ({ ...p, value: e.target.value }))}
                required
              />
            </label>
            <label>
              Escopo
              <select
                value={form.scope_level}
                onChange={(e) => setForm((p) => ({ ...p, scope_level: e.target.value }))}
              >
                <option value="organization">Organização</option>
                <option value="family">Família</option>
                <option value="product">Produto</option>
              </select>
            </label>
            {form.scope_level === "family" ? (
              <label>
                Família
                <select
                  value={form.product_family_id}
                  onChange={(e) => setForm((p) => ({ ...p, product_family_id: e.target.value }))}
                  required
                >
                  <option value="">Selecione</option>
                  {families.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.display_name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {form.scope_level === "product" ? (
              <label>
                Produto
                <select
                  value={form.technical_product_id}
                  onChange={(e) => setForm((p) => ({ ...p, technical_product_id: e.target.value }))}
                  required
                >
                  <option value="">Selecione</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <label>
              Início de vigência
              <input
                type="datetime-local"
                value={form.valid_from}
                onChange={(e) => setForm((p) => ({ ...p, valid_from: e.target.value }))}
                required
              />
            </label>
            <label>
              Justificativa (opcional)
              <input
                value={form.justification}
                onChange={(e) => setForm((p) => ({ ...p, justification: e.target.value }))}
              />
            </label>
            <button type="submit" className="primary" disabled={busy}>
              Criar rascunho
            </button>
          </form>
        </section>
      ) : (
        <p className="meta">Consulta e simulação disponíveis. Sem permissão para alterar políticas.</p>
      )}

      {showAudit && canAudit ? (
        <section className="econ-premises" aria-label="Auditoria econômica">
          <h3>Auditoria</h3>
          {audits.length === 0 ? (
            <EmptyState>Nenhum evento de auditoria econômica.</EmptyState>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Quando</th>
                    <th>Operação</th>
                    <th>Justificativa</th>
                  </tr>
                </thead>
                <tbody>
                  {audits.slice(0, 40).map((row) => (
                    <tr key={String(row.id)}>
                      <td>{row.created_at ? formatDateTime(String(row.created_at)) : "—"}</td>
                      <td>{String(row.operation ?? "—")}</td>
                      <td>{String(row.justification ?? "—")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}

export function CostingPoliciesPage() {
  const { api, hasPermission, active } = useOrganization();
  const { state, load } = useList(
    () => api.listCostingPolicies(),
    `policies:${active?.organization_id ?? ""}`,
  );
  const [code, setCode] = useState("POL-PADRAO");
  const [justification, setJustification] = useState("política inicial da organização");
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;

  return (
    <div className="econ-page">
      <header>
        <h1>Políticas e premissas</h1>
        <p className="lede">
          Distinção explícita entre o que já se configura, o que ainda não existe e o que a Panne deriva
          automaticamente.
        </p>
      </header>

      <section className="econ-premises">
        <h2>A · Configurações existentes e editáveis</h2>
        <ul className="econ-premises__list">
          <li>
            <strong>Política de custeio</strong>
            <span>Critério de preço de insumos, categorias habilitadas, moeda. Versão publicada é imutável.</span>
            {state.items.length === 0 ? (
              <em>Nenhuma política nesta organização.</em>
            ) : (
              <ul>
                {state.items.map((item: CostingPolicy) => (
                  <li key={item.id}>
                    <strong>{item.display_name}</strong>
                    {" · "}
                    {statusLabel(item.status)} · {priceCriterionLabel(item.version?.price_criterion)} ·{" "}
                    {item.version?.currency}
                  </li>
                ))}
              </ul>
            )}
          </li>
          {hasPermission("costing.policy.manage") ? (
            <li>
              <strong>Criar política (rascunho)</strong>
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
                <p className="meta">Critério inicial: último preço observado. Publicação de versão ainda sem tela dedicada.</p>
                <button type="submit" className="primary">
                  Criar política
                </button>
              </form>
            </li>
          ) : null}
          <li>
            <strong>Unidade vendável e apresentação comercial</strong>
            <span>
              Editáveis na ficha do produto.{" "}
              <Link to="/produtos">Abrir produtos</Link>
            </span>
          </li>
          <li>
            <strong>Preços de compra de ingredientes</strong>
            <span>
              Em componentes. Ausência de preço não vira zero no custo.{" "}
              <Link to="/componentes/ingredientes">Abrir ingredientes</Link>
            </span>
          </li>
        </ul>
      </section>

      <section className="econ-premises">
        <h2>B · Políticas de markup e margem</h2>
        <ul className="econ-premises__list">
          <li>
            <strong>Hierarquia efetiva</strong>
            <span>
              Precedência persistida: produto → família → organização. Canal e estabelecimento ficam para
              extensão posterior (sem controle nesta tela).
            </span>
            <StatusBadge tone="sucesso" label="Gestão e resolução na tela" />
          </li>
          <li>
            <strong>Markup × margem</strong>
            <span>{SURFACE_PHRASES.markupDerived}</span>
          </li>
          <li>
            <strong>Conflito de vigência</strong>
            <span>Duas políticas ativas sobrepostas no mesmo escopo são recusadas pela API.</span>
          </li>
        </ul>
        <MarkupPoliciesPanel />
      </section>

      <section className="econ-premises">
        <h2>C · Premissas derivadas automaticamente</h2>
        <ul className="econ-premises__list">
          <li>
            <strong>Composição do custo</strong>
            <span>Ingredientes, embalagem, mão de obra, energia e indiretos conforme política e fatos persistidos.</span>
          </li>
          <li>
            <strong>Completude e lacunas</strong>
            <span>Calculadas no motor; ausência ≠ zero.</span>
          </li>
          <li>
            <strong>Custo-base aplicável</strong>
            <span>Escolhido pelo escopo (produzido vs mercadoria comprada).</span>
          </li>
          <li>
            <strong>Markup e margem na calculadora</strong>
            <span>Derivados na hora a partir do custo-base e do preço simulado — não são cadastro.</span>
          </li>
        </ul>
      </section>
    </div>
  );
}

export function CostingListPage({ kind, title }: { kind: "planned" | "actual"; title: string }) {
  const { api, active } = useOrganization();
  const { state, load } = useList(
    () => api.listCostingCalculations(kind),
    `${kind}:${active?.organization_id ?? ""}`,
  );
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;
  return (
    <div className="econ-page">
      <h1>{title}</h1>
      <p className="lede">
        {kind === "actual"
          ? "Somente fatos persistidos. Preferir a visão comparativa Previsto vs realizado."
          : "Projeção anterior à execução. Preferir a visão comparativa Previsto vs realizado."}{" "}
        <Link to="/gestao/custos/variacao">Abrir previsto vs realizado</Link>
      </p>
      {state.items.length === 0 ? <EmptyState>Não há cálculos neste recorte.</EmptyState> : null}
      <ul className="econ-simple-list">
        {state.items.map((item: CostingCalculation) => (
          <li key={item.id}>
            <Link to={`/gestao/custos/calculos/${item.id}`}>
              {item.subject?.product_display_name || costingKindLabel(item.kind)}
            </Link>{" "}
            {completenessBadge(item.completeness)}
            <span className="meta">
              {" "}
              {item.completeness === "complete" ? "total" : "total parcial"}{" "}
              {formatMoneyAmount(item.total_amount, item.currency)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CostingCalculationPage() {
  return <CostingDecisionPage />;
}

export function CostingCalculatorPage() {
  return (
    <div className="econ-page econ-page--calculator">
      <header className="econ-calculator-banner">
        <h1>Calculadora</h1>
        <p className="lede">
          Simule preço, markup e margem a partir do custo aplicável. Esta simulação não altera o preço cadastrado.
          Premissas ausentes: configure em <Link to="/gestao/custos/politicas">Políticas e premissas</Link> ou na
          ficha do produto. Simulações gravadas:{" "}
          <Link to="/gestao/custos/simulacoes">abrir registros</Link>.
        </p>
      </header>
      <CostingDecisionPage />
    </div>
  );
}

export function CostingSimulationsPage() {
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const { state, load } = useList(
    () => api.listPricingSimulations(),
    `simulations:${orgId ?? ""}`,
  );
  const [kind, setKind] = useState("markup_factor");
  const [channel, setChannel] = useState("own_counter");
  const [calcId, setCalcId] = useState("");
  useEffect(() => {
    setCalcId("");
    api.listCostingCalculations().then((body) => setCalcId(body.items[0]?.id ?? ""));
  }, [api, orgId]);
  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;

  return (
    <div className="econ-page">
      <header>
        <h1>Simulações persistidas</h1>
        <p className="lede">
          Markup incide sobre o custo. Margem bruta incide sobre o preço. Registros gravados via API — a
          calculadora da formação do custo não grava sozinha.{" "}
          <Link to="/gestao/custos/calculadora">Abrir calculadora</Link>
        </p>
      </header>
      {state.items.length === 0 ? <EmptyState>Não há simulações nesta organização.</EmptyState> : null}
      <ul className="econ-simple-list">
        {state.items.map((item: PricingSimulation) => (
          <li key={item.id}>
            {simulationKindLabel(item.kind)} · {channelLabel(item.channel)} · sugerido{" "}
            {formatMoneyAmount(item.suggested_price, "BRL")}
            {item.warning ? <p role="status">{item.warning}</p> : null}
            <p className="meta">{item.disclaimer}</p>
          </li>
        ))}
      </ul>
      {hasPermission("pricing.simulation.manage") ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const payload =
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
                body: payload,
                idempotencyKey: crypto.randomUUID(),
              })
              .then(load);
          }}
        >
          <h2>Gravar simulação (API)</h2>
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
              {Object.entries({
                own_counter: "Balcão próprio",
                made_to_order: "Encomenda",
                wholesale: "Atacado",
                own_delivery: "Entrega própria",
                marketplace: "Praça eletrônica",
                other: "Outro",
              }).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <p className="meta">Premissa comercial manual. A Panne não apura obrigação fiscal.</p>
          <button type="submit" className="primary">
            Calcular e gravar simulação
          </button>
        </form>
      ) : null}
    </div>
  );
}

type EnrichedPrice = {
  price: PracticedPrice;
  product: ProductCard | null;
  currency: string;
  /** Markup/margem só quando a API autoriza comparação (nunca derivados no cliente). */
  markup: string | null;
  marginMoney: string | null;
  marginPct: string | null;
  comparisonLabel: string | null;
};

export function CostingPricesPage() {
  const { api, hasPermission, active } = useOrganization();
  const [searchParams, setSearchParams] = useSearchParams();
  const productFilter = searchParams.get("produto") || "";
  const q = (searchParams.get("q") || "").trim().toLowerCase();
  const channelFilter = searchParams.get("canal") || "";
  const statusFilter = searchParams.get("situacao") || "";
  const viewFilter = searchParams.get("visao") || "vigente";
  const historyProduct = searchParams.get("historico") || "";

  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; prices: PracticedPrice[]; products: ProductCard[] }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
  const [row, setRow] = useState(1);
  const [notes, setNotes] = useState("revisão humana");
  const [reinforced, setReinforced] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [sort, setSort] = useState<"produto" | "preco" | "vigencia">("produto");

  function load() {
    setState({ kind: "carregando" });
    Promise.all([
      api.listPracticedPrices(),
      api.listProducts({ limit: "100", offset: "0" }),
    ])
      .then(([prices, products]) => {
        setState({
          kind: "ok",
          prices: prices.items ?? [],
          products: products.items ?? [],
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
  }, [api, active?.organization_id]);

  const enriched = useMemo(() => {
    if (state.kind !== "ok") return [] as EnrichedPrice[];
    const productMap = new Map(state.products.map((p) => [p.id, p]));
    return state.prices.map((price) => {
      const product = price.technical_product_id
        ? productMap.get(price.technical_product_id) ?? null
        : null;
      const cmp = price.comparison;
      const allowed = Boolean(cmp?.allowed);
      const marginRate = cmp?.margin_rate != null ? Number(cmp.margin_rate) : null;
      return {
        price,
        product,
        currency: price.currency || "BRL",
        markup: allowed && cmp?.markup_factor != null ? String(cmp.markup_factor) : null,
        marginMoney: allowed && cmp?.margin_amount != null ? String(cmp.margin_amount) : null,
        marginPct:
          allowed && marginRate != null && Number.isFinite(marginRate)
            ? (marginRate * 100).toFixed(2)
            : null,
        comparisonLabel: allowed
          ? null
          : cmp?.reason_label ||
            price.sale_basis?.status_label ||
            "Comparação bloqueada pela API",
      };
    });
  }, [state]);

  const filtered = useMemo(() => {
    let rows = enriched;
    if (productFilter) {
      rows = rows.filter((r) => r.price.technical_product_id === productFilter);
    }
    if (historyProduct) {
      rows = rows.filter((r) => r.price.technical_product_id === historyProduct);
    }
    if (q) {
      rows = rows.filter((r) => {
        const name = r.product?.display_name ?? "";
        const code = r.product?.code ?? "";
        return `${name} ${code}`.toLowerCase().includes(q);
      });
    }
    if (channelFilter) {
      rows = rows.filter((r) => r.price.channel === channelFilter);
    }
    if (statusFilter) {
      rows = rows.filter((r) => r.price.status === statusFilter);
    } else if (viewFilter === "vigente") {
      rows = rows.filter((r) => r.price.status === "active" || r.price.status === "published");
    } else if (viewFilter === "legado") {
      rows = rows.filter(
        (r) =>
          (r.price.status === "retired" || r.price.status === "superseded" || r.price.status === "cancelled") &&
          !(r.price.sale_basis?.informed || r.price.comparison?.allowed),
      );
    } else if (viewFilter === "historico") {
      rows = rows.filter((r) => r.price.status !== "active" && r.price.status !== "published");
    }
    const sorted = [...rows];
    sorted.sort((a, b) => {
      if (sort === "preco") {
        return (parseAmt(b.price.amount) ?? 0) - (parseAmt(a.price.amount) ?? 0);
      }
      if (sort === "vigencia") {
        return String(b.price.valid_from ?? "").localeCompare(String(a.price.valid_from ?? ""));
      }
      const an = a.product?.display_name ?? a.price.technical_product_id ?? "";
      const bn = b.product?.display_name ?? b.price.technical_product_id ?? "";
      return an.localeCompare(bn, "pt-BR");
    });
    return sorted;
  }, [enriched, productFilter, historyProduct, q, channelFilter, statusFilter, viewFilter, sort]);

  if (state.kind === "carregando") return <LoadingState />;
  if (state.kind === "erro") return <ErrorState error={state.error} onRetry={load} />;

  const orphanCount = enriched.filter((r) => !r.product).length;

  return (
    <div className="econ-page">
      <header>
        <h1>Preços e histórico</h1>
        <p className="lede">
          Preço praticado por produto, canal e vigência. A visão principal prioriza o preço vigente com base;
          históricos legados sem base ficam no filtro dedicado — não misturados como bloqueio atual.
        </p>
      </header>

      {conflict ? (
        <div className="feedback" role="alert">
          <h2>Conflito de estado</h2>
          <p>A versão mudou. Recarregue antes de publicar.</p>
          <button
            type="button"
            className="primary"
            onClick={() => {
              setConflict(false);
              load();
            }}
          >
            Recarregar
          </button>
        </div>
      ) : null}

      <form
        className="econ-filters"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const next = new URLSearchParams();
          const query = String(form.get("q") || "").trim();
          if (query) next.set("q", query);
          const canal = String(form.get("canal") || "");
          if (canal) next.set("canal", canal);
          const situacao = String(form.get("situacao") || "");
          if (situacao) next.set("situacao", situacao);
          const visao = String(form.get("visao") || "vigente");
          if (visao && visao !== "vigente") next.set("visao", visao);
          if (productFilter) next.set("produto", productFilter);
          setSearchParams(next);
        }}
      >
        <label>
          Buscar
          <input name="q" defaultValue={searchParams.get("q") ?? ""} placeholder="Produto ou código" />
        </label>
        <label>
          Visão
          <select name="visao" defaultValue={viewFilter}>
            <option value="vigente">Preços vigentes</option>
            <option value="historico">Histórico / substituídos</option>
            <option value="legado">Legado sem base comercial</option>
            <option value="todos">Todos os registros</option>
          </select>
        </label>
        <label>
          Canal
          <select name="canal" defaultValue={channelFilter}>
            <option value="">Todos</option>
            <option value="own_counter">Balcão próprio</option>
            <option value="wholesale">Atacado</option>
            <option value="made_to_order">Encomenda</option>
            <option value="own_delivery">Entrega própria</option>
            <option value="marketplace">Praça eletrônica</option>
          </select>
        </label>
        <label>
          Situação
          <select name="situacao" defaultValue={statusFilter}>
            <option value="">Conforme visão</option>
            <option value="published">Publicado</option>
            <option value="active">Vigente</option>
            <option value="draft">Rascunho</option>
            <option value="retired">Encerrado / substituído</option>
          </select>
        </label>
        <label>
          Ordenar
          <select value={sort} onChange={(event) => setSort(event.target.value as typeof sort)}>
            <option value="produto">Produto</option>
            <option value="preco">Preço</option>
            <option value="vigencia">Vigência</option>
          </select>
        </label>
        <button type="submit" className="primary">
          Filtrar
        </button>
      </form>

      {historyProduct ? (
        <p className="meta">
          Histórico do produto selecionado.{" "}
          <button type="button" className="ghost" onClick={() => setSearchParams({})}>
            Limpar histórico
          </button>
        </p>
      ) : null}

      {orphanCount > 0 ? (
        <p className="meta" role="status">
          Lacuna de contrato: {orphanCount} preço(s) sem produto resolvido na lista (só identificador técnico).
        </p>
      ) : null}

      {filtered.length === 0 ? (
        <EmptyState>Não há preços praticados neste recorte.</EmptyState>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Produto</th>
                <th>Código</th>
                <th>Modalidade</th>
                <th>Família</th>
                <th>Canal</th>
                <th>Preço</th>
                <th>Base comercial</th>
                <th>Vigência</th>
                <th>Situação</th>
                <th>Markup</th>
                <th>Margem %</th>
                <th>Política efetiva</th>
                <th>Origem</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(({ price, product, currency, markup, marginPct, comparisonLabel }) => (
                <tr key={price.id}>
                  <td>{product?.display_name ?? "Produto não identificado"}</td>
                  <td>{product?.code ?? "—"}</td>
                  <td>{supplyModeSurfaceLabel(product?.supply_mode)}</td>
                  <td>{product?.family?.display_name ?? "—"}</td>
                  <td>{channelLabel(price.channel)}</td>
                  <td>{formatMoneyAmount(price.amount, currency)}</td>
                  <td>
                    {price.sale_basis?.informed
                      ? price.sale_basis.label || "Informada"
                      : price.sale_basis?.status_label || "Base comercial do preço não informada"}
                  </td>
                  <td>
                    {price.valid_from ? formatDateTime(price.valid_from) : "—"}
                    {price.valid_to ? ` → ${formatDateTime(price.valid_to)}` : ""}
                  </td>
                  <td>{practicedStatusLabel(price.status)}</td>
                  <td>
                    {markup != null
                      ? formatMarkupFactor(markup)
                      : comparisonLabel || "—"}
                  </td>
                  <td>
                    {marginPct != null
                      ? formatPercentDisplay(marginPct)
                      : price.comparison?.scope_complete_for_margin === false && price.comparison?.allowed
                        ? "Indicativa (custo parcial)"
                        : "—"}
                  </td>
                  <td>
                    {price.effective_markup_policy
                      ? `${price.effective_markup_policy.code || "política"} (${price.effective_markup_policy_resolution?.origin_level || "—"})`
                      : price.effective_markup_policy_note || "Sem política"}
                  </td>
                  <td>{price.justification?.trim() ? price.justification : "Decisão humana"}</td>
                  <td>
                    <div className="econ-row-actions">
                      <Link
                        to={
                          price.technical_product_id
                            ? `/gestao/custos/formacao?produto=${price.technical_product_id}`
                            : "/gestao/custos/formacao"
                        }
                      >
                        Analisar
                      </Link>
                      {price.technical_product_id ? (
                        <button
                          type="button"
                          className="ghost"
                          onClick={() =>
                            setSearchParams({ historico: price.technical_product_id! })
                          }
                        >
                          Histórico
                        </button>
                      ) : null}
                    </div>
                    {hasPermission("pricing.publish") && price.status === "draft" ? (
                      <form
                        onSubmit={(event) => {
                          event.preventDefault();
                          api
                            .catalogCommand(`/pricing/practiced/${price.id}/decide`, {
                              body: {
                                decision: "publish",
                                notes,
                                reinforced_confirmation: reinforced,
                              },
                              idempotencyKey: crypto.randomUUID(),
                              ifMatch: row,
                            })
                            .then(() => {
                              setRow((value) => value + 1);
                              load();
                            })
                            .catch((error) => {
                              if (error instanceof ApiError && error.code === "conflito") {
                                setConflict(true);
                                load();
                              }
                            });
                        }}
                      >
                        <label>
                          Justificativa
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

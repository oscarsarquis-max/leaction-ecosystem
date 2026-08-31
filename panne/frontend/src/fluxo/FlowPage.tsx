import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { ProductCard } from "../api/types";
import { StatusBadge } from "../components/Feedback";
import { GigioIdentity } from "../assistant/GigioIdentity";
import { config } from "../config";
import { readOperationalContext } from "../session/operationalContext";
import { useAuth } from "../auth/AuthContext";
import { useOrganization } from "../session/OrganizationContext";
import {
  buildCriticalPath,
  productJourneyFromCard,
  type FlowViewMode,
  type ProductJourneyContext,
} from "./criticalPath";
import { FlowMap } from "./FlowMap";
import {
  buildOrientation,
  inferModality,
} from "./orientation";
import {
  focusStepsForRole,
  preferredStepForRole,
  resolveFlowRole,
  roleDisplayLabel,
} from "./profileFocus";
import { neighborSteps } from "./resolve";
import type { FlowStepId } from "./steps";
import { withFlowReturn } from "./steps";
import { useFlowEvidence } from "./useFlowEvidence";

const FISCAL_SUBSTEPS = [
  "Captura ou importação do documento",
  "Correspondência dos itens",
  "Conferência física",
  "Recebimento e geração de lotes",
  "Atualização de estoque e custos",
] as const;

function linkAllowed(
  link: { permission?: string; permissionAnyOf?: string[] },
  hasPermission: (code: string) => boolean,
): boolean {
  if (link.permissionAnyOf?.length) {
    return link.permissionAnyOf.some((code) => hasPermission(code));
  }
  if (link.permission) return hasPermission(link.permission);
  return true;
}

function situationTone(situation: string): "sucesso" | "atencao" | "erro" | "info" | "neutro" {
  switch (situation) {
    case "Você está aqui":
    case "Em andamento":
      return "info";
    case "Requer atenção":
      return "atencao";
    case "Sem acesso":
      return "erro";
    case "Não se aplica":
      return "neutro";
    case "Pronto":
      return "sucesso";
    case "Não iniciado":
      return "neutro";
    default:
      return "neutro";
  }
}

function parseEtapa(raw: string | null, fallback: FlowStepId): FlowStepId {
  const n = Number(raw);
  if (n >= 1 && n <= 8) return n as FlowStepId;
  return fallback;
}

function parseMode(raw: string | null): FlowViewMode {
  return raw === "produto" ? "product" : "org";
}

export function FlowPage() {
  const { session } = useAuth();
  const { hasPermission, active, me, api } = useOrganization();
  const [params, setParams] = useSearchParams();
  const { evidence, loading } = useFlowEvidence();
  const roles = active?.roles?.length ? active.roles : me?.roles;
  const roleHint = resolveFlowRole(roles);
  const preferred = preferredStepForRole(roleHint);
  const focusSet = focusStepsForRole(roleHint);
  const orgId = active?.organization_id ?? null;
  const userHint = session?.displayHint ?? "";

  const mode = parseMode(params.get("modo"));
  const productCode = (params.get("produto") ?? "").trim();
  const mixedOriginParam = params.get("origem");
  const mixedOrigin =
    mixedOriginParam === "comprado"
      ? "purchased"
      : mixedOriginParam === "produzido"
        ? "produced"
        : null;

  const [selected, setSelected] = useState<FlowStepId>(() => parseEtapa(params.get("etapa"), preferred));
  const [productOptions, setProductOptions] = useState<ProductCard[]>([]);
  const [product, setProduct] = useState<ProductJourneyContext | null>(null);
  const [productError, setProductError] = useState<string | null>(null);
  const [productsLoading, setProductsLoading] = useState(false);

  const operational = orgId ? readOperationalContext(orgId, userHint) : null;

  useEffect(() => {
    const fromQuery = params.get("etapa");
    if (fromQuery) setSelected(parseEtapa(fromQuery, preferred));
    else setSelected(preferred);
  }, [params, preferred, orgId]);

  useEffect(() => {
    if (!orgId || !hasPermission("product.read")) {
      setProductOptions([]);
      return;
    }
    let alive = true;
    setProductsLoading(true);
    void Promise.all([
      api.listProducts({ limit: "50", offset: "0", status: "active" }),
      api.listProducts({ limit: "50", offset: "0", status: "inactive" }),
    ])
      .then(([activePage, inactivePage]) => {
        if (!alive) return;
        const byCode = new Map<string, ProductCard>();
        for (const row of [...(activePage.items ?? []), ...(inactivePage.items ?? [])]) {
          byCode.set(row.code, row);
        }
        setProductOptions([...byCode.values()].sort((a, b) => a.code.localeCompare(b.code)));
      })
      .catch(() => {
        if (alive) setProductOptions([]);
      })
      .finally(() => {
        if (alive) setProductsLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [api, orgId, hasPermission]);

  useEffect(() => {
    if (mode !== "product" || !productCode || !orgId) {
      setProduct(null);
      setProductError(null);
      return;
    }
    let alive = true;
    const listed = productOptions.find((row) => row.code === productCode);
    if (listed) {
      // Detalhe para links reais (ordens/receitas) sem N+1 na lista.
      void api
        .getProduct(listed.id)
        .then((body) => {
          if (!alive) return;
          setProduct(productJourneyFromCard(body.data, mixedOrigin));
          setProductError(null);
        })
        .catch(() => {
          if (!alive) return;
          setProduct(productJourneyFromCard(listed, mixedOrigin));
          setProductError(null);
        });
      return () => {
        alive = false;
      };
    }
    if (productsLoading) return;
    setProduct(null);
    setProductError("Produto não encontrado nesta organização (use o código público).");
    return () => {
      alive = false;
    };
  }, [mode, productCode, orgId, productOptions, productsLoading, api, mixedOrigin]);

  const path = useMemo(
    () =>
      buildCriticalPath({
        mode: mode === "product" && product ? "product" : "org",
        evidence,
        hasPermission,
        focusId: selected,
        profileFocus: focusSet,
        product: mode === "product" ? product : null,
      }),
    [mode, product, evidence, hasPermission, selected, focusSet],
  );

  const current = path.steps.find((row) => row.def.id === path.focusId) ?? path.steps[0];
  const currentId = current?.def.id ?? preferred;
  const { prev, next } = neighborSteps(
    path.steps.map((row) => ({
      def: row.def,
      situation: row.situation,
      pending: row.pending,
      nextAction: row.nextAction,
      hasAccess: row.hasAccess,
      visible: true,
      inFocus: row.profileEmphasis,
    })),
    currentId,
  );

  const permissions = useMemo(() => {
    const raw = [...(active?.permissions ?? []), ...(me?.permissions ?? [])];
    return [...new Set(raw)];
  }, [active?.permissions, me?.permissions]);

  const gigio = useMemo(
    () =>
      buildOrientation({
        organizationId: orgId,
        organizationName: active?.display_name ?? null,
        establishmentId: operational?.establishment_id ?? null,
        profile: roleHint,
        stepId: currentId,
        stepTitle: current?.def.title ?? null,
        situation: current?.situation ?? null,
        pending: current?.pending ?? null,
        nextAction: current?.nextAction ?? null,
        permissions,
        productModality: product
          ? (product.supplyMode as ReturnType<typeof inferModality>)
          : inferModality(evidence.products),
        products: evidence.products,
        fiscal: evidence.fiscal,
        recipesTotal: evidence.recipesTotal,
        ordersTotal: evidence.ordersTotal,
        ingredientsTotal: evidence.ingredientsTotal,
        inventoryItemsTotal: evidence.inventoryItemsTotal,
        blocks: [],
        alerts: [],
        mode: path.mode,
        criticalPath: path,
        product,
      }),
    [
      orgId,
      active?.display_name,
      operational?.establishment_id,
      roleHint,
      currentId,
      current,
      permissions,
      product,
      evidence,
      path,
    ],
  );

  function writeParams(next: {
    etapa?: FlowStepId;
    modo?: FlowViewMode;
    produto?: string | null;
    origem?: "purchased" | "produced" | null;
  }) {
    const sp = new URLSearchParams();
    const etapa = next.etapa ?? selected;
    sp.set("etapa", String(etapa));
    const modo = next.modo ?? mode;
    if (modo === "product") {
      sp.set("modo", "produto");
      const code = next.produto === undefined ? productCode : next.produto;
      if (code) sp.set("produto", code);
      const origin = next.origem === undefined ? mixedOrigin : next.origem;
      if (origin === "purchased") sp.set("origem", "comprado");
      if (origin === "produced") sp.set("origem", "produzido");
    }
    setParams(sp, { replace: true });
  }

  function selectStep(id: FlowStepId) {
    setSelected(id);
    writeParams({ etapa: id });
  }

  const recommended = gigio.recommended && gigio.recommended.allowed ? gigio.recommended : null;

  return (
    <div className="flow-page">
      <header className="page-head flow-page__head">
        <div>
          <h1>Fluxo produtivo</h1>
          <p className="lede">Da entrada da mercadoria ao preço e à gestão do produto acabado.</p>
          <p className="meta">
            Organização: <strong>{active?.display_name ?? "—"}</strong>
            {operational?.establishment_name ? (
              <>
                {" "}
                · Estabelecimento: <strong>{operational.establishment_name}</strong>
              </>
            ) : null}
            {" · "}
            Perfil: <strong>{roleDisplayLabel(roleHint)}</strong>
          </p>
          <div className="flow-mode" role="group" aria-label="Modo do fluxo">
            <button
              type="button"
              className={mode === "org" ? "primary" : "ghost"}
              aria-pressed={mode === "org"}
              onClick={() => writeParams({ modo: "org", produto: null, origem: null })}
            >
              Visão geral da organização
            </button>
            <button
              type="button"
              className={mode === "product" ? "primary" : "ghost"}
              aria-pressed={mode === "product"}
              onClick={() => writeParams({ modo: "product" })}
            >
              Jornada de um produto
            </button>
          </div>
          {mode === "product" ? (
            <div className="flow-product-picker">
              <label htmlFor="flow-product-code">
                Produto (nome ou código)
                <select
                  id="flow-product-code"
                  value={productCode}
                  onChange={(event) => {
                    const code = event.target.value;
                    writeParams({ modo: "product", produto: code || null, etapa: selected });
                  }}
                >
                  <option value="">Escolher…</option>
                  {productOptions.map((row) => (
                    <option key={row.code} value={row.code}>
                      {row.code} — {row.display_name}
                    </option>
                  ))}
                </select>
              </label>
              {product?.supplyMode === "mixed" ? (
                <label>
                  Origem do abastecimento
                  <select
                    value={mixedOrigin ?? ""}
                    onChange={(event) => {
                      const v = event.target.value;
                      writeParams({
                        origem: v === "purchased" || v === "produced" ? v : null,
                      });
                    }}
                  >
                    <option value="">Informar…</option>
                    <option value="purchased">Comprado</option>
                    <option value="produced">Produzido</option>
                  </select>
                </label>
              ) : null}
              {productError ? <p role="alert">{productError}</p> : null}
            </div>
          ) : null}
          {config.demoMode ? (
            <p>
              <Link className="ghost" to="/demonstracao">
                Abrir guia da demonstração
              </Link>
            </p>
          ) : null}
        </div>
      </header>

      {path.orgPreparationNote ? (
        <p className="flow-banner" role="status">
          {path.orgPreparationNote}
        </p>
      ) : null}
      {path.modalityNote ? (
        <p className="flow-banner flow-banner--soft" role="status">
          {path.modalityNote}
        </p>
      ) : null}

      <FlowMap steps={path.steps} focusId={currentId} onSelect={selectStep} />

      <section className="flow-orient" aria-labelledby="flow-orient-heading">
        <h2 id="flow-orient-heading">Resumo do caminho</h2>
        <dl className="flow-orient__grid">
          <div>
            <dt>Onde o processo está</dt>
            <dd>
              {loading
                ? "Carregando…"
                : path.criticalPositionId
                  ? path.blockingTitle
                  : "Sem bloqueio urgente no caminho visível"}
            </dd>
          </div>
          <div>
            <dt>O que já está pronto</dt>
            <dd>{loading ? "…" : path.readyTitles.length ? path.readyTitles.join(", ") : "Nada marcado como pronto ainda"}</dd>
          </div>
          <div>
            <dt>O que impede avançar</dt>
            <dd>{loading ? "…" : path.blockingPending ?? "Nada urgente bloqueando agora."}</dd>
          </div>
          <div>
            <dt>Próxima ação</dt>
            <dd>{loading ? "Carregando…" : recommended?.label ?? current?.nextAction ?? "Escolher uma etapa"}</dd>
          </div>
          <div>
            <dt>Não aplicáveis</dt>
            <dd>
              {path.notApplicableTitles.length ? path.notApplicableTitles.join(", ") : "Nenhuma neste recorte"}
            </dd>
          </div>
          <div>
            <dt>Limitações</dt>
            <dd>{path.limitations[0] ?? "—"}</dd>
          </div>
        </dl>
        {recommended ? (
          <p className="flow-orient__cta">
            <Link className="primary" to={withFlowReturn(recommended.to, currentId)}>
              {recommended.label}
            </Link>
          </p>
        ) : null}
      </section>

      <section className="flow-gigio panel" aria-labelledby="flow-gigio-heading">
        <GigioIdentity size="lg" caption="Explica o mapa — não compete com ele" />
        <div className="flow-gigio__body">
          <h2 id="flow-gigio-heading">{gigio.youAreOn}</h2>
          {gigio.pathStoppedAt ? (
            <p>
              <strong>Motivo: </strong>
              {loading ? "Carregando evidências…" : gigio.mainPending}
            </p>
          ) : (
            <p>{gigio.statusLine}</p>
          )}
          {gigio.consequence ? <p>{gigio.consequence}</p> : null}
          <p>
            <strong>Próxima ação: </strong>
            {loading ? "…" : recommended?.label ?? current?.nextAction ?? "—"}
          </p>
          {gigio.modalityNote ? <p className="meta">{gigio.modalityNote}</p> : null}
          <p className="meta">{gigio.purpose}</p>
          <div className="flow-gigio__actions">
            {recommended ? (
              <Link className="primary" to={withFlowReturn(recommended.to, currentId)}>
                {recommended.label}
              </Link>
            ) : null}
            {config.demoMode ? (
              <Link className="ghost" to="/demonstracao">
                Abrir guia da demonstração
              </Link>
            ) : null}
          </div>
        </div>
      </section>

      {current ? (
        <article className="flow-panel" aria-labelledby="flow-step-title">
          <div className="flow-panel__head">
            <h2 id="flow-step-title">
              Detalhe · Etapa {current.def.id} · {current.def.title}
            </h2>
            <StatusBadge tone={situationTone(current.mapLabel)} label={current.mapLabel} />
          </div>
          {current.isFocus && !current.isCriticalPosition ? (
            <p className="meta">Em foco para consulta — a posição real do caminho permanece em outra etapa.</p>
          ) : null}
          <p>{current.def.objective}</p>
          {current.def.id === 1 ? (
            <ol className="flow-panel__substeps">
              {FISCAL_SUBSTEPS.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ol>
          ) : null}
          {current.pending ? (
            <p>
              <strong>Pendência: </strong>
              {current.pending}
            </p>
          ) : null}
          <p>
            <strong>Próxima ação: </strong>
            {current.nextAction}
          </p>
          {current.situation === "Não se aplica" ? (
            <p className="meta">Esta etapa não se aplica ao produto ou perfil atual — o Gigio explica o motivo.</p>
          ) : null}

          <div className="flow-panel__actions">
            {current.def.primary
            && current.hasAccess
            && current.situation !== "Não se aplica"
            && linkAllowed(current.def.primary, hasPermission) ? (
              <Link className="primary" to={withFlowReturn(current.def.primary.to, current.def.id)}>
                {current.def.primary.label}
              </Link>
            ) : null}
            {current.def.secondary
              .filter((link) => linkAllowed(link, hasPermission))
              .map((link) => (
                <Link key={link.to} className="ghost" to={withFlowReturn(link.to, current.def.id)}>
                  {link.label}
                </Link>
              ))}
          </div>

          <div className="flow-panel__nav">
            {prev ? (
              <button type="button" className="ghost" onClick={() => selectStep(prev)}>
                Etapa anterior
              </button>
            ) : (
              <span />
            )}
            <Link className="ghost" to="/fluxo">
              Voltar ao mapa
            </Link>
            {next ? (
              <button type="button" className="ghost" onClick={() => selectStep(next)}>
                Próxima etapa
              </button>
            ) : (
              <span />
            )}
          </div>
        </article>
      ) : (
        <p role="status">Nenhuma etapa disponível para o seu perfil.</p>
      )}
    </div>
  );
}

export { flowHref } from "./steps";

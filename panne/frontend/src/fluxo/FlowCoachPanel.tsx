/**
 * Intervenção compacta e recolhível do Gigio nas telas da jornada.
 * Visível sem abrir o chat completo.
 */
import { useEffect, useId, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { GigioIdentity } from "../assistant/GigioIdentity";
import type { ProductSummary } from "../api/types";
import { useOrganization } from "../session/OrganizationContext";
import { useFlowEvidence } from "./useFlowEvidence";
import {
  buildOrientation,
  inferModality,
  type OrientationResult,
} from "./orientation";
import { matchFlowStep, flowHref, type FlowStepId } from "./steps";
import { resolveStepSituation } from "./resolve";
import { FLOW_STEPS } from "./steps";
import { resolveFlowRole } from "./profileFocus";
import { SURFACE_PHRASES } from "../language/surface";

type Props = {
  /** Força etapa quando a rota ainda não mapeia (ex.: /inicio). */
  forcedStep?: FlowStepId | null;
};

function economicCoachCopy(pathname: string, productsSummary: ProductSummary | null) {
  const purchased = productsSummary?.purchased ?? 0;
  const producedHint =
    productsSummary != null
      ? Math.max(0, productsSummary.total - productsSummary.purchased - productsSummary.intermediate)
      : 0;
  if (pathname.includes("/gestao/custos/precos")) {
    return {
      youAreOn: "Você está em preços e histórico.",
      purpose: "Ler decisões de preço persistidas e o que ainda não permite markup.",
      statusLine:
        "Preços legados sem base comercial permanecem no histórico, mas a API bloqueia markup e margem até uma nova decisão com unidade e quantidade-base.",
      mainPending:
        "Informar base comercial nas próximas publicações; não recalcular silenciosamente a partir da calculadora.",
      nextLabel: "Abrir visão econômica",
      nextTo: "/gestao/custos",
    };
  }
  if (pathname.includes("/gestao/custos/variacao")) {
    return {
      youAreOn: "Você está em previsto vs realizado.",
      purpose: "Comparar custo previsto e realizado na mesma base, sem inventar zero.",
      statusLine:
        "Na focaccia, se o rendimento cai (por exemplo de 8 para 7), o custo unitário realizado sobe mesmo com total estável.",
      mainPending: "Investigar lote ou rendimento quando o unitário piora com total estável.",
      nextLabel: "Abrir formação do custo",
      nextTo: "/gestao/custos/formacao",
    };
  }
  if (pathname.includes("/gestao/custos/formacao") || pathname.includes("/gestao/custos/calculos")) {
    return {
      youAreOn: "Você está na formação do custo.",
      purpose: SURFACE_PHRASES.costingMemoryPurpose,
      statusLine:
        "No pão integral, o custo fica parcial enquanto faltar preço da farinha integral — decisão definitiva baseada nesse custo fica bloqueada.",
      mainPending: "Completar preços de ingredientes antes de tratar o valor como definitivo.",
      nextLabel: "Abrir calculadora",
      nextTo: "/gestao/custos/calculadora",
    };
  }
  if (pathname.includes("/gestao/custos/politicas")) {
    return {
      youAreOn: "Você está em políticas e premissas.",
      purpose: "Consultar, criar e substituir políticas de markup ou margem com vigência.",
      statusLine:
        "A política específica do produto (ex.: manteiga) prevalece sobre família e organização. Canal e estabelecimento ficam para depois.",
      mainPending: "Resolver a política efetiva por produto antes de aplicar preço.",
      nextLabel: "Voltar à visão econômica",
      nextTo: "/gestao/custos",
    };
  }
  if (pathname.includes("/gestao/custos/calculadora")) {
    return {
      youAreOn: "Você está na calculadora.",
      purpose: "Carregar a política efetiva, simular e só então aplicar com confirmação.",
      statusLine:
        "No pão francês, há política de família e custo comparável à unidade. Distinga preço vigente, sugerido pela política e simulação (que não grava).",
      mainPending: "Não confundir simulação com preço vigente; aplicação exige permissão e base comercial.",
      nextLabel: "Abrir preços",
      nextTo: "/gestao/custos/precos",
    };
  }
  return {
    youAreOn: "Você está na área econômica (custos, preços e margem).",
    purpose:
      "Entender quanto custa, se o custo está completo e onde a comparação comercial ainda está bloqueada.",
    statusLine:
      productsSummary
        ? `Catálogo no escopo: cerca de ${producedHint} produzido(s)/outros e ${purchased} comprado(s). Atenção: parcial (pão integral), desvio de rendimento (focaccia) e comprado (manteiga).`
        : "Use o painel de atenção para lacunas reais — políticas e preços vigentes alimentam os indicadores.",
    mainPending:
      "Priorizar custos parciais e preços vigentes sem base antes de tratar markup como decisão publicada.",
    nextLabel: "Abrir formação do custo",
    nextTo: "/gestao/custos/formacao",
  };
}

export function FlowCoachPanel({ forcedStep = null }: Props) {
  const location = useLocation();
  const { active, me, hasPermission } = useOrganization();
  const { evidence } = useFlowEvidence();
  const titleId = useId();
  const [open, setOpen] = useState(true);
  const [cached, setCached] = useState<OrientationResult | null>(null);
  const onCosting = location.pathname.startsWith("/gestao/custos");
  const economic = useMemo(
    () => (onCosting ? economicCoachCopy(location.pathname, evidence.products) : null),
    [onCosting, location.pathname, evidence.products],
  );

  const pathStep = matchFlowStep(location.pathname);
  const stepId = forcedStep ?? pathStep;
  const orgId = active?.organization_id ?? null;

  useEffect(() => {
    // Troca de organização descarta orientação anterior.
    setCached(null);
    // Mobile/tablet ou área econômica: começa recolhido (Gigio não domina a faixa).
    const mq =
      typeof window !== "undefined" && typeof window.matchMedia === "function"
        ? window.matchMedia("(max-width: 720px)")
        : null;
    setOpen(onCosting ? false : !(mq?.matches ?? false));
  }, [orgId, location.pathname, onCosting]);

  useEffect(() => {
    if (!stepId) {
      setCached(null);
      return;
    }
    if (onCosting) {
      // Área econômica: não reutilizar o framing genérico “etapa 8”.
      setCached(null);
      return;
    }
    const def = FLOW_STEPS.find((row) => row.id === stepId);
    if (!def) return;
    const resolved = resolveStepSituation(def, hasPermission, evidence, stepId);
    const permissions = [
      ...(active?.permissions ?? []),
      ...(me?.permissions ?? []),
    ];
    // Dedup
    const uniq = [...new Set(permissions)];
    const modality = inferModality(evidence.products);
    const result = buildOrientation({
      organizationId: orgId,
      organizationName: active?.display_name ?? null,
      establishmentId: null,
      profile: resolveFlowRole(active?.roles?.length ? active.roles : me?.roles),
      stepId,
      stepTitle: def.title,
      situation: resolved.situation,
      pending: resolved.pending,
      nextAction: resolved.nextAction,
      permissions: uniq,
      productModality: modality,
      products: evidence.products,
      fiscal: evidence.fiscal,
      recipesTotal: evidence.recipesTotal,
      ordersTotal: evidence.ordersTotal,
      ingredientsTotal: evidence.ingredientsTotal,
      inventoryItemsTotal: evidence.inventoryItemsTotal,
      blocks: [],
      alerts: [],
    });
    setCached(result);
  }, [
    stepId,
    orgId,
    onCosting,
    active?.display_name,
    active?.permissions,
    active?.roles,
    me?.permissions,
    me?.roles,
    evidence,
    hasPermission,
  ]);

  if (location.pathname === "/fluxo" || location.pathname.startsWith("/fluxo/")) {
    return null;
  }
  if (location.pathname.startsWith("/produtos")) {
    return null;
  }
  if (onCosting && economic) {
    return (
      <aside
        className={`flow-coach${open ? " is-open" : " is-collapsed"}`}
        aria-label="Orientação econômica"
        aria-labelledby={titleId}
      >
        <div className="flow-coach__bar">
          <GigioIdentity size="sm" caption={null} />
          <div className="flow-coach__headline">
            <h2 id={titleId}>Orientação econômica</h2>
            <p className="meta">{economic.youAreOn}</p>
          </div>
          <button
            type="button"
            className="ghost flow-coach__toggle"
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? "Recolher" : "Abrir"}
          </button>
        </div>
        {open ? (
          <div className="flow-coach__body">
            <p>
              <strong>Finalidade: </strong>
              {economic.purpose}
            </p>
            <p>{economic.statusLine}</p>
            <p>
              <strong>Pendência: </strong>
              {economic.mainPending}
            </p>
            <div className="flow-coach__actions">
              <Link className="primary" to={economic.nextTo}>
                {economic.nextLabel}
              </Link>
              <Link className="ghost" to="/fluxo">
                Voltar ao fluxo
              </Link>
            </div>
          </div>
        ) : null}
      </aside>
    );
  }
  if (!stepId || !cached) return null;

  const recommended =
    cached.recommended && cached.recommended.allowed ? cached.recommended : null;

  return (
    <aside
      className={`flow-coach${open ? " is-open" : " is-collapsed"}`}
      aria-label="Orientação do processo"
      aria-labelledby={titleId}
    >
      <div className="flow-coach__bar">
        <GigioIdentity size="sm" caption={null} />
        <div className="flow-coach__headline">
          <h2 id={titleId}>Orientação do processo</h2>
          <p className="meta">{cached.youAreOn}</p>
        </div>
        <button
          type="button"
          className="ghost flow-coach__toggle"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Recolher" : "Abrir"}
        </button>
      </div>
      {open ? (
        <div className="flow-coach__body">
          <p>
            <strong>Finalidade: </strong>
            {cached.purpose}
          </p>
          <p>{cached.statusLine}</p>
          <p>
            <strong>Pendência: </strong>
            {cached.mainPending}
          </p>
          {cached.modalityNote ? <p className="meta">{cached.modalityNote}</p> : null}
          <div className="flow-coach__actions">
            {recommended ? (
              <Link className="primary" to={recommended.to}>
                {recommended.label}
              </Link>
            ) : null}
            <Link className="ghost" to={flowHref(stepId)}>
              Voltar ao fluxo
            </Link>
          </div>
          {cached.calculatorSlot === "reserved" ? (
            <p className="meta">
              Abra Formação do custo ou a Calculadora para ver composição, simular preço e auditar a memória de
              cálculo.
            </p>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}

/**
 * Intervenção compacta e recolhível do Gigio nas telas da jornada.
 * Visível sem abrir o chat completo.
 */
import { useEffect, useId, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { GigioIdentity } from "../assistant/GigioIdentity";
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

type Props = {
  /** Força etapa quando a rota ainda não mapeia (ex.: /inicio). */
  forcedStep?: FlowStepId | null;
};

export function FlowCoachPanel({ forcedStep = null }: Props) {
  const location = useLocation();
  const { active, me, hasPermission } = useOrganization();
  const { evidence } = useFlowEvidence();
  const titleId = useId();
  const [open, setOpen] = useState(true);
  const [cached, setCached] = useState<OrientationResult | null>(null);

  const pathStep = matchFlowStep(location.pathname);
  const stepId = forcedStep ?? pathStep;
  const orgId = active?.organization_id ?? null;

  useEffect(() => {
    // Troca de organização descarta orientação anterior.
    setCached(null);
    // Mobile/tablet: começa recolhido para não ocupar a tela continuamente.
    const mq =
      typeof window !== "undefined" && typeof window.matchMedia === "function"
        ? window.matchMedia("(max-width: 720px)")
        : null;
    setOpen(!(mq?.matches ?? false));
  }, [orgId]);

  useEffect(() => {
    if (!stepId) {
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
              Calculadora lateral reservada para rendimento, conversões e custos — sem números
              simulados nesta fase.
            </p>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}

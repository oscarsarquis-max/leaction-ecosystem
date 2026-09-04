import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { StatusBadge } from "../components/Feedback";
import { GigioIdentity } from "../assistant/GigioIdentity";
import { useOrganization } from "../session/OrganizationContext";
import {
  focusStepsForRole,
  preferredStepForRole,
  resolveFlowRole,
  roleDisplayLabel,
} from "./profileFocus";
import { neighborSteps, resolveVisibleSteps, type FlowEvidence } from "./resolve";
import {
  buildOrientation,
  inferModality,
  type OrientationResult,
} from "./orientation";
import type { FlowStepId } from "./steps";
import { flowHref, withFlowReturn } from "./steps";
import { useFlowEvidence } from "./useFlowEvidence";

const JOURNEY_SEP = " → ";

function journeyLine(visibleTitles: string[]): string {
  return visibleTitles.join(JOURNEY_SEP);
}

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

function buildPageOrientation(
  roleHint: ReturnType<typeof resolveFlowRole>,
  evidence: FlowEvidence,
  currentId: FlowStepId,
  visible: ReturnType<typeof resolveVisibleSteps>,
  orgId: string | null,
  orgName: string | null,
  permissions: string[],
): OrientationResult {
  const current = visible.find((row) => row.def.id === currentId);
  return buildOrientation({
    organizationId: orgId,
    organizationName: orgName,
    establishmentId: null,
    profile: roleHint,
    stepId: currentId,
    stepTitle: current?.def.title ?? null,
    situation: current?.situation ?? null,
    pending: current?.pending ?? null,
    nextAction: current?.nextAction ?? null,
    permissions,
    productModality: inferModality(evidence.products),
    products: evidence.products,
    fiscal: evidence.fiscal,
    recipesTotal: evidence.recipesTotal,
    ordersTotal: evidence.ordersTotal,
    ingredientsTotal: evidence.ingredientsTotal,
    inventoryItemsTotal: evidence.inventoryItemsTotal,
    blocks: [],
    alerts: [],
  });
}

export function FlowPage() {
  const { hasPermission, active, me } = useOrganization();
  const [params, setParams] = useSearchParams();
  const { evidence, loading } = useFlowEvidence();
  const roles = active?.roles?.length ? active.roles : me?.roles;
  const roleHint = resolveFlowRole(roles);
  const preferred = preferredStepForRole(roleHint);
  const focus = focusStepsForRole(roleHint);
  const orgId = active?.organization_id ?? null;

  const [selected, setSelected] = useState<FlowStepId>(() => parseEtapa(params.get("etapa"), preferred));

  useEffect(() => {
    const fromQuery = params.get("etapa");
    if (fromQuery) {
      setSelected(parseEtapa(fromQuery, preferred));
    } else {
      setSelected(preferred);
    }
  }, [params, preferred, orgId]);

  const visible = useMemo(
    () => resolveVisibleSteps(hasPermission, evidence, focus, null),
    [hasPermission, evidence, focus],
  );

  const current = visible.find((row) => row.def.id === selected) ?? visible[0];
  const currentId = current?.def.id ?? preferred;
  const { prev, next } = neighborSteps(visible, currentId);
  // N = id canônico da etapa; M = etapas visíveis ao perfil (8 com custos; 7 sem).
  const stageLabel = `Etapa ${currentId} de ${visible.length}`;
  const journey = journeyLine(visible.map((row) => row.def.title));

  const permissions = useMemo(() => {
    const raw = [...(active?.permissions ?? []), ...(me?.permissions ?? [])];
    return [...new Set(raw)];
  }, [active?.permissions, me?.permissions]);

  const gigio = useMemo(
    () =>
      buildPageOrientation(
        roleHint,
        evidence,
        currentId,
        visible,
        orgId,
        active?.display_name ?? null,
        permissions,
      ),
    [roleHint, evidence, currentId, visible, orgId, active?.display_name, permissions],
  );

  function selectStep(id: FlowStepId) {
    setSelected(id);
    setParams({ etapa: String(id) }, { replace: true });
  }

  const recommended =
    gigio.recommended && gigio.recommended.allowed ? gigio.recommended : null;

  const readyCount = visible.filter((row) => row.situation === "Pronto").length;
  const attentionCount = visible.filter((row) => row.situation === "Requer atenção").length;
  const naCount = visible.filter((row) => row.situation === "Não se aplica").length;

  return (
    <div className="flow-page">
      <header className="page-head">
        <div>
          <h1>Fluxo produtivo</h1>
          <p className="lede">
            {journey}
          </p>
          <p className="meta">
            Perfil: <strong>{roleDisplayLabel(roleHint)}</strong>
            {active?.display_name ? (
              <>
                {" "}
                · Organização <strong>{active.display_name}</strong>
              </>
            ) : null}
            {" · "}
            {stageLabel}
          </p>
        </div>
      </header>

      <section className="flow-gigio panel" aria-labelledby="flow-gigio-heading">
        <GigioIdentity
          size="lg"
          caption="Orientador do processo — dados reais desta organização"
        />
        <div className="flow-gigio__body">
          <h2 id="flow-gigio-heading">{gigio.youAreOn}</h2>
          <p>{gigio.purpose}</p>
          <p>{gigio.statusLine}</p>
          <p>
            <strong>Pendência principal: </strong>
            {loading ? "Carregando evidências…" : gigio.mainPending}
          </p>
          {gigio.modalityNote ? <p className="meta">{gigio.modalityNote}</p> : null}
          <div className="flow-gigio__actions">
            {recommended ? (
              <Link className="primary" to={withFlowReturn(recommended.to, currentId)}>
                {recommended.label}
              </Link>
            ) : null}
            {current?.def.primary
              && current.hasAccess
              && linkAllowed(current.def.primary, hasPermission)
              && (!recommended || recommended.to !== current.def.primary.to) ? (
              <Link className="ghost" to={withFlowReturn(current.def.primary.to, current.def.id)}>
                {current.def.primary.label}
              </Link>
            ) : null}
          </div>
          {gigio.calculatorSlot === "reserved" ? (
            <p className="meta">
              Calculadora lateral reservada (rendimento, conversões, custo e preço) — sem números
              simulados nesta fase.
            </p>
          ) : null}
        </div>
      </section>

      <section className="flow-orient" aria-labelledby="flow-orient-heading">
        <h2 id="flow-orient-heading" className="visually-hidden">
          Painel de condução
        </h2>
        <dl className="flow-orient__grid">
          <div>
            <dt>Onde você está</dt>
            <dd>
              {stageLabel}
              {current ? ` — ${current.def.title}` : ""}
            </dd>
          </div>
          <div>
            <dt>Pronto</dt>
            <dd>{loading ? "…" : `${readyCount} etapa(s)`}</dd>
          </div>
          <div>
            <dt>Requer atenção</dt>
            <dd>{loading ? "…" : `${attentionCount} etapa(s)`}</dd>
          </div>
          <div>
            <dt>Não se aplica</dt>
            <dd>{loading ? "…" : `${naCount} etapa(s)`}</dd>
          </div>
          <div>
            <dt>Próxima ação</dt>
            <dd>{loading ? "Carregando…" : recommended?.label ?? current?.nextAction ?? "Escolher uma etapa"}</dd>
          </div>
          <div>
            <dt>O que impede avançar</dt>
            <dd>
              {loading
                ? "…"
                : attentionCount > 0
                  ? gigio.mainPending
                  : current?.situation === "Sem acesso"
                    ? current.pending
                    : "Nada urgente bloqueando a jornada agora."}
            </dd>
          </div>
        </dl>
      </section>

      <nav className="flow-rail" aria-label="Etapas do fluxo produtivo">
        <p className="flow-rail__mobile-label">
          {stageLabel}
          {current ? `: ${current.def.title}` : ""}
        </p>
        <ol className="flow-rail__list">
          {visible.map((row) => {
            const isCurrent = row.def.id === currentId;
            return (
              <li key={row.def.id} className={row.inFocus ? undefined : "is-context"}>
                <button
                  type="button"
                  className={isCurrent ? "is-current" : undefined}
                  aria-current={isCurrent ? "step" : undefined}
                  disabled={row.situation === "Sem acesso"}
                  onClick={() => selectStep(row.def.id)}
                >
                  <span className="flow-rail__num" aria-hidden="true">
                    {row.def.id}
                  </span>
                  <span className="flow-rail__title">{row.def.title}</span>
                  <StatusBadge tone={situationTone(row.situation)} label={row.situation} />
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      {current ? (
        <article className="flow-panel" aria-labelledby="flow-step-title">
          <div className="flow-panel__head">
            <h2 id="flow-step-title">
              Etapa {current.def.id} · {current.def.title}
            </h2>
            <StatusBadge tone={situationTone(current.situation)} label={current.situation} />
          </div>
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
            <p className="meta">
              Esta etapa não se aplica ao produto ou perfil atual — o Gigio explica o motivo acima.
            </p>
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
              Voltar ao fluxo
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

/** Export auxiliar para testes de deep link. */
export { flowHref };

import { Link, useLocation } from "react-router-dom";
import type { FlowStepId } from "./steps";
import { FLOW_STEPS, flowHref, matchFlowStep } from "./steps";
import { canAccessCosting } from "./resolve";
import { useOrganization } from "../session/OrganizationContext";

type Props = {
  /** Quando na página /fluxo, força a etapa selecionada. */
  selectedStep?: FlowStepId | null;
  /** Modo compacto para páginas internas. */
  compact?: boolean;
  /** Em execução operacional, só “Voltar ao fluxo”. */
  opsLite?: boolean;
};

export function FlowTrail({ selectedStep = null, compact = true, opsLite = false }: Props) {
  const { hasPermission } = useOrganization();
  const location = useLocation();
  const pathStep = matchFlowStep(location.pathname);
  const current = selectedStep ?? pathStep;

  const visible = FLOW_STEPS.filter((step) => {
    if (step.id === 8 && !canAccessCosting(hasPermission)) return false;
    return true;
  });

  if (opsLite) {
    return (
      <nav className="flow-trail flow-trail--ops" aria-label="Retorno ao fluxo produtivo">
        <Link className="ghost" to={current ? flowHref(current) : "/fluxo"}>
          Voltar ao fluxo
        </Link>
      </nav>
    );
  }

  const index = current ? visible.findIndex((step) => step.id === current) : -1;
  const prev = index > 0 ? visible[index - 1] : null;
  const next = index >= 0 && index < visible.length - 1 ? visible[index + 1] : null;

  return (
    <nav className={`flow-trail${compact ? " flow-trail--compact" : ""}`} aria-label="Trilha do fluxo produtivo">
      <div className="flow-trail__meta">
        <Link className="flow-trail__home" to="/fluxo">
          Fluxo produtivo
        </Link>
        {current ? (
          <span className="flow-trail__stage">
            Etapa {current} de {visible.length}
            <span className="visually-hidden">: {visible.find((s) => s.id === current)?.title}</span>
          </span>
        ) : null}
      </div>
      <ol className="flow-trail__steps">
        {visible.map((step) => {
          const isCurrent = step.id === current;
          return (
            <li key={step.id}>
              <Link
                to={flowHref(step.id)}
                className={isCurrent ? "is-current" : undefined}
                aria-current={isCurrent ? "step" : undefined}
                title={step.title}
              >
                <span aria-hidden="true">{step.id}</span>
                <span className="visually-hidden">
                  Etapa {step.id}: {step.title}
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
      <div className="flow-trail__nav">
        {prev ? (
          <Link className="ghost" to={flowHref(prev.id)}>
            Anterior
          </Link>
        ) : (
          <span className="flow-trail__spacer" />
        )}
        <Link className="ghost" to={current ? flowHref(current) : "/fluxo"}>
          Voltar ao fluxo
        </Link>
        {next ? (
          <Link className="ghost" to={flowHref(next.id)}>
            Próxima etapa
          </Link>
        ) : (
          <span className="flow-trail__spacer" />
        )}
      </div>
    </nav>
  );
}

/** Trilha ligada ao pathname atual (uso no Shell). */
export function FlowTrailFromLocation({ pathname }: { pathname: string }) {
  const step = matchFlowStep(pathname);
  const operational = pathname.includes("/executar");
  if (pathname === "/fluxo" || pathname.startsWith("/fluxo?")) return null;
  if (pathname === "/inicio") return null;
  if (!step && !operational) return null;
  return <FlowTrail selectedStep={step} opsLite={operational} />;
}

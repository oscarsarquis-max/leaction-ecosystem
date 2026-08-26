import { useEffect, useId, useRef } from "react";
import { Link } from "react-router-dom";
import { GLOSSARY } from "../guide/glossary";
import { INTENTS } from "../guide/intents";
import { useOrganization } from "../session/OrganizationContext";
import { useAssistant } from "./AssistantContext";

export function GlobalAssistant({ publicMode = false }: { publicMode?: boolean }) {
  const { open, flow, dirty, pendingCommand, live, closeAssistant, minimizeAssistant, dismissAssistant, setFlow } =
    useAssistant();
  const { hasPermission } = useOrganization();
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) closeRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !dirty && !pendingCommand) closeAssistant();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, dirty, pendingCommand, closeAssistant]);

  if (!open) return null;

  const intents = publicMode ? [] : INTENTS.filter((item) => hasPermission(item.permission));
  const terms = GLOSSARY.filter((item) => live.related.includes(item.code)).slice(0, 4);

  return (
    <aside className="drawer-assist panel no-print" role="dialog" aria-labelledby={titleId} aria-modal="false">
      <h2 id={titleId}>{publicMode ? "Ajuda para entrar" : "Assistente"}</h2>
      {publicMode ? (
        <p>O conteúdo ao lado não altera o login. Se as colunas falharem, o acesso continua no centro.</p>
      ) : (
        <>
          <p>
            Você está em <strong>{live.title}</strong>
            {live.entityLabel && live.entityLabel !== live.entity ? ` · ${live.entityLabel}` : ""}. {live.goal}
          </p>
          <p className="meta">
            {live.organization ? `Organização: ${live.organization}. ` : ""}
            Entidade: {live.entity}. Estado: {live.status}.
            {live.operational ? ` Contexto: ${live.operational}.` : ""}
          </p>
          <p className="meta">Próxima ação: {live.next}</p>
          {live.blocked ? <p role="status">Bloqueio: {live.blocked}</p> : null}
          {live.pending ? <p>Falta: {live.pending}</p> : null}
          {!live.guideSpecific ? <p className="meta">Guia mínimo: esta rota ainda não tem texto próprio.</p> : null}
          {dirty || pendingCommand ? (
            <p role="status">Há formulário sujo ou comando pendente. O assistente não executa.</p>
          ) : null}
        </>
      )}
      {flow ? (
        <section>
          <h3>{flow.title}</h3>
          <p>{flow.note}</p>
          <ol>
            {flow.steps.map((step, index) => (
              <li key={step} aria-current={index === flow.step ? "step" : undefined}>
                {step}
              </li>
            ))}
          </ol>
          <button type="button" className="ghost" onClick={() => setFlow(null)}>
            Voltar à orientação
          </button>
        </section>
      ) : null}
      {!publicMode && intents.length ? (
        <section>
          <h3>Ir para</h3>
          <ul className="list">
            {intents.map((item) => (
              <li key={item.code}>
                <Link to={item.to}>{item.label}</Link>
                <div className="meta">{item.precondition}</div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {terms.length ? (
        <section>
          <h3>Glossário</h3>
          {terms.map((item) => (
            <p key={item.code}>
              <strong>{item.title}.</strong> {item.short}
            </p>
          ))}
        </section>
      ) : null}
      <p>
        <button type="button" className="ghost" ref={closeRef} onClick={closeAssistant}>
          Fechar
        </button>{" "}
        <button type="button" className="ghost" onClick={minimizeAssistant}>
          Minimizar
        </button>{" "}
        <button type="button" className="ghost" onClick={dismissAssistant}>
          Dispensar
        </button>
      </p>
    </aside>
  );
}

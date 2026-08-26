import logoCompacto from "../../images/aprovados/compacto-escuro.png";
import { useAssistant } from "./AssistantContext";

export function AssistantAvatar({ publicMode = false }: { publicMode?: boolean }) {
  const { open, openAssistant, live, flow } = useAssistant();
  if (open) return null;
  const pending = Boolean(live.pending || live.blocked || flow);
  const label = publicMode ? "Abrir ajuda para entrar" : "Abrir assistente da Panne";
  const tip = pending ? `${label}. Há pendência ou percurso em andamento.` : label;
  return (
    <button
      type="button"
      className="assistant-avatar no-print"
      aria-label={label}
      title={tip}
      onClick={openAssistant}
    >
      <img src={logoCompacto} alt="" />
      {pending ? (
        <span className="assistant-badge" aria-label="Pendência ou percurso em andamento">
          !
        </span>
      ) : null}
    </button>
  );
}

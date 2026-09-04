import { useEffect, useState } from "react";
import { GIGIO_ALT, GIGIO_AVATAR_SRC, GIGIO_NAME } from "./GigioIdentity";
import { useAssistant } from "./AssistantContext";

/** Esconde o FAB enquanto o teclado virtual reduz a área útil (mobile). */
function useKeyboardOcclusionGuard() {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const sync = () => {
      // Só esconde com evidência clara de teclado (altura útil > 0 e encolheu).
      if (!vv.width || !vv.height) {
        setHidden(false);
        return;
      }
      const shrink = window.innerHeight - vv.height;
      setHidden(shrink > 120);
    };
    sync();
    vv.addEventListener("resize", sync);
    vv.addEventListener("scroll", sync);
    return () => {
      vv.removeEventListener("resize", sync);
      vv.removeEventListener("scroll", sync);
    };
  }, []);
  return hidden;
}

export function AssistantAvatar({ publicMode = false }: { publicMode?: boolean }) {
  const { open, openAssistant, live, flow } = useAssistant();
  const keyboardOpen = useKeyboardOcclusionGuard();
  if (open || keyboardOpen) return null;
  const pending = Boolean(live.pending || live.blocked || flow);
  const label = publicMode
    ? `Abrir ajuda de ${GIGIO_NAME} para entrar`
    : `Abrir ${GIGIO_NAME}, assistente da Panne`;
  const tip = pending ? `${label}. Há pendência ou percurso em andamento.` : label;
  return (
    <button
      type="button"
      className="assistant-avatar no-print"
      aria-label={label}
      title={tip}
      onClick={openAssistant}
    >
      <img src={GIGIO_AVATAR_SRC} alt={GIGIO_ALT} width={48} height={48} decoding="async" />
      {pending ? (
        <span className="assistant-badge" aria-label="Pendência ou percurso em andamento">
          !
        </span>
      ) : null}
    </button>
  );
}

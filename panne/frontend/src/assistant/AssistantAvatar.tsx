import { useEffect, useState } from "react";
import { GIGIO_ALT, GIGIO_AVATAR_SRC } from "./GigioIdentity";
import { useAssistant } from "./AssistantContext";

/** Esconde o FAB enquanto o teclado virtual reduz a área útil (mobile). */
function useKeyboardOcclusionGuard() {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const sync = () => {
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

export function AssistantAvatar() {
  const { open, openAssistant, live } = useAssistant();
  const keyboardOpen = useKeyboardOcclusionGuard();
  if (open || keyboardOpen) return null;
  const pending = Boolean(live.pending || live.blocked);
  return (
    <button
      type="button"
      className="assistant-avatar no-print"
      aria-label="Abrir Gigio"
      title={pending ? "Abrir Gigio. Há uma orientação relevante." : "Abrir Gigio"}
      onClick={openAssistant}
    >
      <img src={GIGIO_AVATAR_SRC} alt={GIGIO_ALT} width={56} height={56} decoding="async" />
      {pending ? (
        <span className="assistant-badge" aria-label="Há uma orientação relevante">
          !
        </span>
      ) : null}
    </button>
  );
}

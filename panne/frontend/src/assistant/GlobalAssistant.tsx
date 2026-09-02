import { useEffect, useId, useRef } from "react";
import { config } from "../config";
import { useAssistant } from "./AssistantContext";
import { GIGIO_NAME, GigioIdentity } from "./GigioIdentity";

function isMobileViewport(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;
}

export function GlobalAssistant({ publicMode = false }: { publicMode?: boolean }) {
  const { open, live, closeAssistant } = useAssistant();
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (open) closeRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeAssistant();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    function onPointer(event: MouseEvent) {
      const el = event.target as HTMLElement | null;
      if (!el) return;
      if (panelRef.current?.contains(el)) return;
      if (el.closest?.(".assistant-avatar")) return;
      /* Não desmontar o alvo no pointerdown de um link/botão — o click precisa completar. */
      if (el.closest?.("a, button, summary, input, label, select, textarea, [role='menuitem'], [role='link']")) {
        return;
      }
      closeAssistant();
    }
    window.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer, true);
    };
  }, [open, closeAssistant]);

  if (!open) return null;

  const situation = publicMode
    ? config.demoMode
      ? "Não há senha nesta demonstração. Escolha um perfil e entre pelo botão do centro."
      : "O conteúdo ao lado não altera o login. Se as colunas falharem, o acesso continua no centro."
    : live.goal;
  const pending = publicMode
    ? "O conteúdo editorial não mistura sessão com autenticação."
    : live.blocked || live.pending || "Nenhuma pendência destacada nesta tela.";
  const next = publicMode
    ? config.demoMode
      ? "Escolher o perfil e entrar na demonstração."
      : "Entrar com a conta da organização."
    : live.next;

  const mobile = isMobileViewport();

  return (
    <>
      {mobile ? <div className="assistant-backdrop no-print" aria-hidden="true" /> : null}
      <aside
        ref={panelRef}
        className={`drawer-assist panel no-print${mobile ? " drawer-assist--sheet" : ""}`}
        role="dialog"
        aria-labelledby={titleId}
        aria-modal="true"
        aria-label={GIGIO_NAME}
      >
        <div className="drawer-assist__bar">
          <GigioIdentity size="sm" caption={null} />
          <h2 id={titleId} className="visually-hidden">
            {GIGIO_NAME}
          </h2>
          <button type="button" className="ghost" ref={closeRef} onClick={closeAssistant}>
            Fechar
          </button>
        </div>
        <p>
          <strong>Situação. </strong>
          {situation}
        </p>
        <p>
          <strong>Principal pendência. </strong>
          {pending}
        </p>
        <p>
          <strong>Próxima ação. </strong>
          {next}
        </p>
      </aside>
    </>
  );
}

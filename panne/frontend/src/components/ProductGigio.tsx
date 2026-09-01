import { useEffect, useId, useRef, useState } from "react";
import { GigioIdentity } from "../assistant/GigioIdentity";

export function ProductGigio({ message }: { message: string }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  function close() {
    setOpen(false);
    queueMicrotask(() => triggerRef.current?.focus());
  }

  return (
    <div className="product-gigio-host">
      {open ? null : (
        <button
          ref={triggerRef}
          type="button"
          className="product-gigio-fab"
          aria-label="Abrir"
          aria-expanded={false}
          aria-controls={panelId}
          onClick={() => setOpen(true)}
        >
          <GigioIdentity size="sm" caption={null} hideName />
          <span>Abrir</span>
        </button>
      )}
      {open ? (
        <aside
          id={panelId}
          className="product-gigio-panel"
          role="dialog"
          aria-modal="true"
          aria-label="Gigio"
        >
          <div className="product-gigio__bar">
            <GigioIdentity size="sm" caption={null} />
            <button ref={closeRef} type="button" className="ghost" onClick={close}>
              Fechar
            </button>
          </div>
          <p>{message}</p>
        </aside>
      ) : null}
    </div>
  );
}

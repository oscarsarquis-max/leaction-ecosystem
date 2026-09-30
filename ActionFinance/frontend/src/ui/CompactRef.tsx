import { useState } from "react";
import { compactReference } from "../money";

export function CompactRef({ value }: { value: string }) {
  const compact = compactReference(value);
  const [copied, setCopied] = useState(false);
  return (
    <span className="ref">
      <span className="ref-text">
        <span aria-hidden="true">{compact.short}</span>
        <span className="sr-only">{compact.full}</span>
      </span>
      <button
        type="button"
        className="link ref-copy"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          void navigator.clipboard?.writeText(compact.full).then(() => {
            setCopied(true);
            window.setTimeout(() => setCopied(false), 2000);
          });
        }}
      >
        Copiar
      </button>
      <span className="live" aria-live="polite">
        {copied ? "Referência copiada" : ""}
      </span>
      {copied ? <span className="copy-feedback">Referência copiada</span> : null}
    </span>
  );
}

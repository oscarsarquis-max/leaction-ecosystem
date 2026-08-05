import { useId, useState } from "react";

type Props = {
  text: string;
};

/**
 * Ajuda discreta para termos técnicos (tooltip / expansível).
 */
export function ContextualHelp({ text }: Props) {
  const [open, setOpen] = useState(false);
  const tipId = useId();

  return (
    <span className="relative inline-flex align-middle">
      <button
        type="button"
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-qmind-semantic-current text-sm font-bold text-qmind-semantic-current transition-[var(--qmind-transition-subtle)] hover:bg-qmind-app"
        aria-label="Ajuda"
        aria-expanded={open}
        aria-controls={tipId}
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        i
      </button>
      {open ? (
        <span
          id={tipId}
          role="tooltip"
          className="absolute left-1/2 top-full z-20 mt-2 w-56 -translate-x-1/2 rounded-qmind-md border border-qmind-semantic-current bg-qmind-surface px-3 py-2 text-left text-sm leading-snug text-qmind-text-main shadow-qmind-card"
        >
          {text}
        </span>
      ) : null}
    </span>
  );
}

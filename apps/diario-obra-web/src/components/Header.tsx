import { exitToChamelleon, getRdoUserName } from '../services/rdoSession';

export default function Header({ subtitle }: { subtitle?: string }) {
  const userName = getRdoUserName();

  return (
    <header className="flex shrink-0 items-center gap-3 bg-gradient-to-r from-emerald-700 to-green-600 px-3 py-3 text-white shadow-md sm:px-4">
      <img
        src="/images/camelleonlogo.png"
        alt="Chamelleon"
        className="h-11 w-11 shrink-0 rounded-lg border border-white/20 bg-white object-cover shadow-sm"
      />
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-100 sm:text-xs">
          Gemba · Campo
        </p>
        <h1 className="truncate text-base font-bold leading-tight sm:text-xl">RDO — Diário de Obra</h1>
        {subtitle && <p className="truncate text-xs text-emerald-50 sm:text-sm">{subtitle}</p>}
      </div>
      <button
        type="button"
        onClick={exitToChamelleon}
        title="Sair do Diário de Obra"
        aria-label="Sair do Diário de Obra"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/25 bg-white/10 text-white transition hover:border-white/40 hover:bg-white/20 active:bg-white/30"
      >
        <svg
          className="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      </button>
      {userName ? (
        <span className="sr-only">Sessão: {userName}</span>
      ) : null}
    </header>
  );
}

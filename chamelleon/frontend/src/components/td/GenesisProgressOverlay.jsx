import { createPortal } from 'react-dom';

export default function GenesisProgressOverlay({
  visible,
  progress = 0,
  statusMessage,
  subtitle,
  currentHint,
  hintIndex = 0,
  hintCount = 1,
}) {
  if (!visible || typeof document === 'undefined') return null;

  const pct = Math.min(100, Math.max(0, Math.round(progress)));

  return createPortal(
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-white/97 p-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="genesis-progress-title"
      aria-busy="true"
    >
      <div className="w-full max-w-xl text-center">
        <p
          id="genesis-progress-title"
          className="text-xs font-semibold uppercase tracking-wide text-violet-600"
        >
          Gênese IA — Motor PanelDX
        </p>

        <h2 className="mt-2 text-xl font-bold text-[#4A2E80]">
          Gerando Plano de Transformação Digital
        </h2>

        <div className="mx-auto mt-6 w-full max-w-lg overflow-hidden rounded-full border border-slate-200 bg-slate-100">
          <div
            className="h-8 rounded-full bg-gradient-to-r from-[#4A2E80] to-violet-500 transition-[width] duration-400 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-2 text-sm font-semibold text-[#4A2E80]">{pct}%</p>

        {statusMessage && (
          <p className="mt-4 text-base font-bold text-[#4A2E80]">{statusMessage}</p>
        )}

        {subtitle && <p className="mt-2 text-sm text-slate-600">{subtitle}</p>}

        <div
          className="mt-8 min-h-[5.5rem] rounded-xl border border-violet-100 bg-violet-50/80 px-5 py-4 text-left transition-opacity duration-500"
          key={hintIndex}
        >
          <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-600">
            Insight do relatório de maturidade
            {hintCount > 1 ? ` · ${(hintIndex % hintCount) + 1}/${hintCount}` : ''}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">{currentHint}</p>
        </div>
      </div>
    </div>,
    document.body,
  );
}

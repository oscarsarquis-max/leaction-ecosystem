import { useMicPermissionBanner } from '../hooks/useMicPermissionBanner';

export default function MicPermissionBanner() {
  const { visible, micState, activating, activateMic, dismiss } = useMicPermissionBanner();

  if (!visible) return null;

  return (
    <div className="mx-4 mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 shadow-sm">
      <p className="font-bold">Microfone para ditado em campo</p>
      <p className="mt-1 text-xs leading-relaxed">
        {micState === 'denied'
          ? 'O microfone está bloqueado. Em Ajustes → Safari/Chrome, permita o microfone para este site e toque em Ativar.'
          : 'Toque em Ativar para liberar o ditado por voz antes de preencher o RDO.'}
      </p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={activateMic}
          disabled={activating}
          className="min-h-10 flex-1 rounded-xl bg-amber-600 px-3 text-xs font-bold text-white disabled:opacity-60"
        >
          {activating ? 'Ativando…' : 'Ativar microfone'}
        </button>
        <button
          type="button"
          onClick={dismiss}
          className="min-h-10 rounded-xl border border-amber-300 px-3 text-xs font-semibold text-amber-900"
        >
          Depois
        </button>
      </div>
    </div>
  );
}

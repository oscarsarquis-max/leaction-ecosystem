/**
 * Ponte visual freemium → ActionHub (checkout real em passo futuro).
 */
export default function UpgradeCreditsModal({ open, onClose }) {
  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-bordo-deep/50 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upgrade-credits-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.()
      }}
    >
      <div className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-6 shadow-soft sm:p-7">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
          Plano gratuito
        </p>
        <h2
          id="upgrade-credits-title"
          className="mt-2 font-display text-2xl font-bold leading-snug text-bordo-deep"
        >
          Você atingiu o seu limite gratuito!
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
          Seus 10 planejamentos gratuitos foram utilizados. Para continuar criando aulas com a
          IA, faça o upgrade para a versão Premium.
        </p>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button type="button" className="btn-ghost !px-4 !py-2.5 text-sm" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary !px-4 !py-2.5 text-sm"
            onClick={() => {
              console.log('TODO: Redirecionar para ActionHub')
            }}
          >
            Fazer Upgrade Agora
          </button>
        </div>
      </div>
    </div>
  )
}

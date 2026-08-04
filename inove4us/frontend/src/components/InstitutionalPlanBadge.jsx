/**
 * Badge de Plano Institucional (Chave Mestra UX).
 * Substitui o contador de créditos / botão de upgrade para professores da escola.
 */
export default function InstitutionalPlanBadge({ institutionalName }) {
  const school =
    (institutionalName && String(institutionalName).trim()) || 'sua escola'
  const tip = `Licença patrocinada por: ${school}`

  return (
    <span
      className="group relative inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800"
      title={tip}
      aria-label={tip}
    >
      <span aria-hidden="true">🏢</span>
      Plano Institucional
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 hidden w-max max-w-[16rem] -translate-x-1/2 rounded-lg bg-slate-900 px-2.5 py-1.5 text-[11px] font-medium text-white shadow-lg group-hover:block"
      >
        {tip}
      </span>
    </span>
  )
}

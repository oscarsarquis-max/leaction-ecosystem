/**
 * Badge de Plano Institucional (Chave Mestra UX).
 * Mostra o saldo de IA incluso na licença da escola (pool do prompt 98).
 */
export default function InstitutionalPlanBadge({ institutionalName, creditosIa }) {
  const school =
    (institutionalName && String(institutionalName).trim()) || 'sua escola'
  const saldo = Number(creditosIa)
  const saldoOk = Number.isFinite(saldo)
  const tip = saldoOk
    ? `A ${school} inclui um pool de créditos de IA na licença. Saldo: ${saldo}. Compra avulsa nesta conta fica bloqueada.`
    : `Licença patrocinada por ${school}: créditos de IA inclusos no plano institucional.`

  return (
    <span
      className="group relative inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800"
      title={tip}
      aria-label={tip}
    >
      Plano Institucional
      {saldoOk ? (
        <span className="font-bold text-blue-950">
          · {saldo} IA
        </span>
      ) : null}
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 hidden w-max max-w-[18rem] -translate-x-1/2 rounded-lg bg-slate-900 px-2.5 py-1.5 text-[11px] font-medium text-white shadow-lg group-hover:block"
      >
        {tip}
      </span>
    </span>
  )
}

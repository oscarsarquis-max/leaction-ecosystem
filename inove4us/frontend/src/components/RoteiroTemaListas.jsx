import { rotuloBnccOption, bnccOptionValue } from '../lib/ementaTopicos'

/**
 * Duas listas lado a lado: BNCC canônico e ementa livre.
 * Sem fusão, sem alerta de conflito — o professor escolhe.
 */
export default function RoteiroTemaListas({
  bnccTemas = [],
  ementaTopicos = [],
  selecionado,
  onEscolher,
}) {
  const temBncc = bnccTemas.length > 0
  const temEmenta = ementaTopicos.length > 0
  if (!temBncc && !temEmenta) return null

  return (
    <div className="space-y-2">
      <span className="field-label">Tema da aula</span>
      <p className="text-[12px] leading-relaxed text-bordo-soft">
        Catálogo BNCC e ementa da escola aparecem juntos. Escolha um item de qualquer lista.
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-brand-100 bg-white/80 p-2">
          <p className="px-1 pb-1 text-[11px] font-semibold uppercase tracking-wide text-bordo-soft">
            BNCC (catálogo)
          </p>
          {temBncc ? (
            <ul className="max-h-56 overflow-y-auto pr-1">
              {bnccTemas.map((b) => {
                const value = bnccOptionValue(b)
                const active = selecionado?.value === value
                return (
                  <li key={b.habilidade_codigo || value}>
                    <button
                      type="button"
                      title={`${b.habilidade_codigo || ''} — ${b.tema || ''}`}
                      onClick={() =>
                        onEscolher({
                          fonte: 'bncc',
                          value,
                          tema: b.tema || '',
                          habilidade_codigo: b.habilidade_codigo || '',
                          texto_oficial: b.texto_oficial || '',
                        })
                      }
                      className={`mb-1 w-full rounded-lg px-2 py-1.5 text-left text-[12px] leading-snug ${
                        active
                          ? 'bg-bordo text-white'
                          : 'text-bordo-deep hover:bg-brand-50'
                      }`}
                    >
                      {rotuloBnccOption(b)}
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="px-1 py-2 text-[12px] text-bordo-soft">Sem temas BNCC aprovados neste recorte.</p>
          )}
        </div>
        <div className="rounded-xl border border-brand-100 bg-white/80 p-2">
          <p className="px-1 pb-1 text-[11px] font-semibold uppercase tracking-wide text-bordo-soft">
            Ementa da escola
          </p>
          {temEmenta ? (
            <ul className="max-h-56 overflow-y-auto pr-1">
              {ementaTopicos.map((t) => {
                const active = selecionado?.value === t
                return (
                  <li key={t}>
                    <button
                      type="button"
                      onClick={() =>
                        onEscolher({
                          fonte: 'ementa',
                          value: t,
                          tema: t,
                          habilidade_codigo: '',
                          texto_oficial: '',
                        })
                      }
                      className={`mb-1 w-full rounded-lg px-2 py-1.5 text-left text-[12px] leading-snug ${
                        active
                          ? 'bg-bordo text-white'
                          : 'text-bordo-deep hover:bg-brand-50'
                      }`}
                    >
                      {t}
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="px-1 py-2 text-[12px] text-bordo-soft">A escola ainda não digitou tópicos nesta ementa.</p>
          )}
        </div>
      </div>
    </div>
  )
}

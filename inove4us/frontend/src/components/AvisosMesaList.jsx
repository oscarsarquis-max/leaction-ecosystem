/**
 * Card de aviso da Mesa — coordenação (School) ou devolutiva da Nina.
 */
export function AvisoMesaItem({ a }) {
  const meta = a.meta && typeof a.meta === 'object' ? a.meta : {}
  const pei = a.tipo === 'resposta_proposta_metodologica'
  const nina = a.tipo === 'resposta_feedback_nina'
  const lilac = pei || nina
  const resultado = String(meta.resultado || '')
  const resultadoLabel =
    resultado === 'aprovada'
      ? 'Aprovada'
      : resultado === 'adaptada'
        ? 'Adaptada'
        : resultado === 'nao_incorporada'
          ? 'Não incorporada agora'
          : ''

  return (
    <li
      className={
        lilac
          ? 'rounded-xl border border-violet-300 bg-violet-50 px-3 py-2 text-sm text-violet-950'
          : 'rounded-xl border border-brand-100 bg-white px-3 py-2 text-sm text-bordo'
      }
    >
      {pei ? (
        <>
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-violet-700">
            [Resposta à Proposta Metodológica]
          </p>
          {resultadoLabel ? (
            <p className="mt-1 text-xs font-semibold">Resultado: {resultadoLabel}</p>
          ) : null}
          {meta.sugestao_resumo ? (
            <p className="mt-1 text-xs text-violet-900/80">Sua proposta: {meta.sugestao_resumo}</p>
          ) : null}
          {meta.retorno_docente ? (
            <p className="mt-1.5 whitespace-pre-wrap text-sm">{meta.retorno_docente}</p>
          ) : (
            <p className="mt-1.5 whitespace-pre-wrap text-sm">{a.texto}</p>
          )}
        </>
      ) : nina ? (
        <>
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-violet-700">
            [Resposta ao seu feedback — Nina]
          </p>
          <p className="mt-1.5 whitespace-pre-wrap text-sm">
            {meta.retorno_texto || a.texto}
          </p>
        </>
      ) : (
        <>
          {a.texto}
          {a.turma_nome || a.disciplina_nome ? (
            <span className="mt-0.5 block text-[11px] text-bordo-soft">
              {[a.disciplina_nome, a.turma_nome].filter(Boolean).join(' · ')}
            </span>
          ) : null}
        </>
      )}
    </li>
  )
}

export default function AvisosMesaList({ avisos, titulo = 'Avisos' }) {
  if (!avisos?.length) return null
  return (
    <div className="mb-4 rounded-2xl border border-brand-200 bg-brand-50/70 p-3 shadow-soft print:hidden sm:p-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
        {titulo}
      </p>
      <ul className="mt-2 space-y-2">
        {avisos.map((a) => (
          <AvisoMesaItem key={a.id} a={a} />
        ))}
      </ul>
    </div>
  )
}

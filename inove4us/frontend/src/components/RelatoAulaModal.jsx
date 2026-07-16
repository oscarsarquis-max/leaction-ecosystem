import { useEffect, useState } from 'react'
import DictationField from './DictationField'

function hojeISO() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : String(n))
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/**
 * Pós-execução da aula: relato, participantes e opcional desdobramento vinculado.
 */
export default function RelatoAulaModal({ aula, missao, onCancel, onSubmit, busy }) {
  const [relato, setRelato] = useState('')
  const [participantes, setParticipantes] = useState('')
  const [criarProximo, setCriarProximo] = useState(false)
  const [dataProximo, setDataProximo] = useState(hojeISO())
  const [tituloProximo, setTituloProximo] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    setRelato('')
    setParticipantes('')
    setCriarProximo(false)
    setDataProximo(hojeISO())
    setTituloProximo(missao ? `Continuidade · ${missao}`.slice(0, 180) : '')
    setError('')
  }, [aula, missao])

  if (!aula) return null

  function handleSubmit(e) {
    e.preventDefault()
    if (!relato.trim()) {
      setError('Registre o que houve na sala.')
      return
    }
    if (!participantes.trim()) {
      setError('Informe quem participou.')
      return
    }
    if (criarProximo && !dataProximo) {
      setError('Informe a data do próximo evento.')
      return
    }
    onSubmit?.({
      relato_sala: relato.trim(),
      participantes: participantes.trim(),
      criar_proximo: criarProximo,
      data_proximo: criarProximo ? dataProximo : undefined,
      titulo_proximo: criarProximo ? (tituloProximo || '').trim() : undefined,
    })
  }

  return (
    <div
      className="fixed inset-0 z-[90] flex items-end justify-center bg-bordo-deep/50 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="relato-aula-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onCancel?.()
      }}
    >
      <form
        onSubmit={handleSubmit}
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-brand-200 bg-white p-5 shadow-soft"
      >
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
          Encerramento da aula
        </p>
        <h2 id="relato-aula-title" className="mt-1 font-display text-xl font-bold text-bordo-deep">
          O que aconteceu na sala?
        </h2>
        <p className="mt-2 text-sm text-bordo-soft">
          Antes de marcar como concluída, registre a realização. Se fizer sentido, gere um novo
          evento vinculado a este.
        </p>

        <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-bordo">
          Relato da sala
        </label>
        <div className="mt-1.5">
          <DictationField
            as="textarea"
            rows={4}
            className="field-input min-h-[110px] resize-y"
            value={relato}
            onChange={setRelato}
            placeholder="Digite ou dite: clima, aprendizagens, obstáculos, decisões…"
          />
        </div>

        <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-bordo">
          Quem participou
        </label>
        <div className="mt-1.5">
          <DictationField
            as="textarea"
            rows={3}
            className="field-input min-h-[80px] resize-y"
            value={participantes}
            onChange={setParticipantes}
            placeholder="Nomes, turmas, papéis (líder, guardião…)…"
          />
        </div>

        <label className="mt-4 flex cursor-pointer items-start gap-2 rounded-xl border border-brand-100 bg-brand-50/50 px-3 py-3">
          <input
            type="checkbox"
            className="mt-1"
            checked={criarProximo}
            onChange={(e) => setCriarProximo(e.target.checked)}
          />
          <span className="text-sm text-bordo">
            <span className="font-bold">Criar novo evento a partir deste</span>
            <span className="mt-0.5 block text-xs text-bordo-soft">
              Fica vinculado no mapa de realizações como desdobramento.
            </span>
          </span>
        </label>

        {criarProximo ? (
          <div className="mt-3 space-y-3 rounded-xl border border-brand-100 bg-white p-3">
            <div>
              <label className="text-xs font-bold uppercase tracking-wide text-bordo">Data</label>
              <input
                type="date"
                className="field-input mt-1"
                value={dataProximo}
                onChange={(e) => setDataProximo(e.target.value)}
                required={criarProximo}
              />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wide text-bordo">
                Título do próximo evento
              </label>
              <input
                className="field-input mt-1"
                value={tituloProximo}
                onChange={(e) => setTituloProximo(e.target.value)}
                placeholder="Ex.: Retomada · validação com a turma"
              />
            </div>
          </div>
        ) : null}

        {error ? <p className="mt-3 text-xs font-semibold text-brand-700">{error}</p> : null}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="btn-ghost !px-4 !py-2 text-sm"
            onClick={onCancel}
            disabled={busy}
          >
            Cancelar
          </button>
          <button type="submit" className="btn-primary !px-4 !py-2 text-sm" disabled={busy}>
            {busy ? 'Salvando…' : 'Concluir realização'}
          </button>
        </div>
      </form>
    </div>
  )
}

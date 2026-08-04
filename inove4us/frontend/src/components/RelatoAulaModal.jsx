import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import DictationField from './DictationField'

function hojeISO() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : String(n))
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/**
 * Pós-execução da aula: relato, participantes e opcional desdobramento vinculado.
 */
export default function RelatoAulaModal({
  aula,
  missao,
  onCancel,
  onSubmit,
  busy,
  temAlunosPei: temAlunosPeiProp,
}) {
  const [relato, setRelato] = useState('')
  const [participantes, setParticipantes] = useState('')
  const [criarProximo, setCriarProximo] = useState(false)
  const [dataProximo, setDataProximo] = useState(hojeISO())
  const [tituloProximo, setTituloProximo] = useState('')
  const [adaptouMetodologia, setAdaptouMetodologia] = useState(false)
  const [adaptacaoTexto, setAdaptacaoTexto] = useState('')
  const [adaptouPei, setAdaptouPei] = useState(false)
  const [peiAdaptacaoTexto, setPeiAdaptacaoTexto] = useState('')
  const [error, setError] = useState('')

  const temAlunosPei = Boolean(
    temAlunosPeiProp ??
      aula?.tem_alunos_pei ??
      aula?.meta_json?.tem_alunos_pei ??
      (Array.isArray(aula?.kanban_pei) && aula.kanban_pei.length > 0),
  )

  useEffect(() => {
    setRelato('')
    setParticipantes('')
    setCriarProximo(false)
    setDataProximo(hojeISO())
    setTituloProximo(missao ? `Continuidade · ${missao}`.slice(0, 180) : '')
    setAdaptouMetodologia(false)
    setAdaptacaoTexto('')
    setAdaptouPei(false)
    setPeiAdaptacaoTexto('')
    setError('')
  }, [aula, missao])

  useEffect(() => {
    if (!aula) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [aula])

  if (!aula || typeof document === 'undefined') return null

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
    if (adaptouMetodologia && !adaptacaoTexto.trim()) {
      setError('Descreva a modificação feita na metodologia.')
      return
    }
    if (adaptouPei && !peiAdaptacaoTexto.trim()) {
      setError('Descreva o que funcionou melhor no PEI nesta metodologia.')
      return
    }
    onSubmit?.({
      relato_sala: relato.trim(),
      participantes: participantes.trim(),
      criar_proximo: criarProximo,
      data_proximo: criarProximo ? dataProximo : undefined,
      titulo_proximo: criarProximo ? (tituloProximo || '').trim() : undefined,
      has_teacher_adaptations: adaptouMetodologia,
      teacher_adaptation_text: adaptouMetodologia ? adaptacaoTexto.trim() : undefined,
      has_pei_adaptations: adaptouPei,
      pei_adaptation_text: adaptouPei ? peiAdaptacaoTexto.trim() : undefined,
    })
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center overflow-y-auto bg-bordo-deep/55 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="relato-aula-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onCancel?.()
      }}
    >
      <form
        onSubmit={handleSubmit}
        className="my-2 w-full max-w-lg rounded-2xl border border-brand-200 bg-white p-5 shadow-soft sm:my-4"
        style={{ maxHeight: 'min(92vh, 920px)', overflowY: 'auto' }}
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
            checked={adaptouMetodologia}
            onChange={(e) => {
              setAdaptouMetodologia(e.target.checked)
              if (!e.target.checked) setAdaptacaoTexto('')
            }}
          />
          <span className="text-sm text-bordo">
            <span className="font-bold">
              Adaptei a metodologia original da escola nesta aula.
            </span>
            <span className="mt-0.5 block text-xs text-bordo-soft">
              Envia a sugestão para a curadoria pedagógica da escola (bottom-up).
            </span>
          </span>
        </label>

        {adaptouMetodologia ? (
          <div className="mt-3">
            <label className="block text-xs font-bold uppercase tracking-wide text-bordo">
              Descreva a modificação
            </label>
            <div className="mt-1.5">
              <DictationField
                as="textarea"
                rows={3}
                className="field-input min-h-[90px] resize-y"
                value={adaptacaoTexto}
                onChange={setAdaptacaoTexto}
                placeholder="Ex.: Mudei o tempo do ciclo PBL, adicionei uma etapa visual…"
              />
            </div>
          </div>
        ) : null}

        {temAlunosPei ? (
          <>
            <label className="mt-4 flex cursor-pointer items-start gap-2 rounded-xl border border-emerald-100 bg-emerald-50/60 px-3 py-3">
              <input
                type="checkbox"
                className="mt-1"
                checked={adaptouPei}
                onChange={(e) => {
                  setAdaptouPei(e.target.checked)
                  if (!e.target.checked) setPeiAdaptacaoTexto('')
                }}
              />
              <span className="text-sm text-bordo">
                <span className="font-bold">
                  Adaptei a execução do PEI para o(s) aluno(s)
                </span>
                <span className="mt-0.5 block text-xs text-bordo-soft">
                  Envia feedback de trincheira para a curadoria do PEI na escola.
                </span>
              </span>
            </label>
            {adaptouPei ? (
              <div className="mt-3">
                <label className="block text-xs font-bold uppercase tracking-wide text-bordo">
                  O que funcionou melhor para o aluno nesta metodologia?
                </label>
                <div className="mt-1.5">
                  <DictationField
                    as="textarea"
                    rows={3}
                    className="field-input min-h-[90px] resize-y"
                    value={peiAdaptacaoTexto}
                    onChange={setPeiAdaptacaoTexto}
                    placeholder="Ex.: Apoio visual curto + tempo extra na estação de entrega…"
                  />
                </div>
              </div>
            ) : null}
          </>
        ) : null}

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
    </div>,
    document.body,
  )
}

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useSpeechDictation } from './DictationField'

const METODOLOGIA = [
  { value: true, label: 'Sim', icon: '👍' },
  { value: false, label: 'Não', icon: '👎' },
]

const ENGAJAMENTO = [
  { value: 'alto', label: 'Alto', icon: '🤩' },
  { value: 'medio', label: 'Médio', icon: '😐' },
  { value: 'baixo', label: 'Baixo', icon: '😞' },
]

const ESTRUTURA = [
  { value: true, label: 'Sim, atendeu', icon: '🏢' },
  { value: false, label: 'Não, faltou algo', icon: '🚧' },
]

function ToggleGroup({ label, options, value, onChange, multiLine = false }) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-bold text-bordo-deep">{label}</legend>
      <div
        className={`grid gap-2 ${
          multiLine || options.length > 2 ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-2'
        }`}
        role="group"
      >
        {options.map((opt) => {
          const selected = value === opt.value
          return (
            <button
              key={String(opt.value)}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(opt.value)}
              className={[
                'flex min-h-[52px] items-center justify-center gap-2 rounded-xl border px-3 py-3 text-sm font-bold transition active:scale-[0.98]',
                selected
                  ? 'border-brand-600 bg-brand-600 text-white shadow-soft'
                  : 'border-brand-200 bg-white text-bordo hover:border-brand-400 hover:bg-brand-50',
              ].join(' ')}
            >
              <span className="text-lg leading-none" aria-hidden>
                {opt.icon}
              </span>
              <span>{opt.label}</span>
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}

/**
 * Feedback Loop pós-aula — preenchimento rápido (toggles + ditado pt-BR).
 */
export default function ClassFeedbackModal({ aula, busy, onCancel, onSubmit, onSkip }) {
  const [metodologiaOk, setMetodologiaOk] = useState(null)
  const [engajamento, setEngajamento] = useState(null)
  const [estruturaOk, setEstruturaOk] = useState(null)
  const [observacoes, setObservacoes] = useState('')
  const [error, setError] = useState('')

  const { listening, supported, error: micError, toggle, setError: setMicError, stop } =
    useSpeechDictation({
      value: observacoes,
      onChange: setObservacoes,
      preserveNewlines: true,
    })

  useEffect(() => {
    setMetodologiaOk(null)
    setEngajamento(null)
    setEstruturaOk(null)
    setObservacoes('')
    setError('')
    setMicError('')
    stop()
  }, [aula, setMicError, stop])

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
    if (metodologiaOk === null) {
      setError('A sugestão metodológica funcionou?')
      return
    }
    if (!engajamento) {
      setError('Como foi o engajamento dos alunos?')
      return
    }
    if (estruturaOk === null) {
      setError('A estrutura existente acomodou a sugestão?')
      return
    }
    stop()
    onSubmit?.({
      metodologia_ok: metodologiaOk,
      engajamento,
      estrutura_ok: estruturaOk,
      observacoes: observacoes.trim(),
    })
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center overflow-y-auto bg-bordo-deep/55 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="class-feedback-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) {
          stop()
          onCancel?.()
        }
      }}
    >
      <form
        onSubmit={handleSubmit}
        className="my-2 w-full max-w-lg rounded-2xl border border-brand-200 bg-white p-4 shadow-soft sm:my-4 sm:p-5"
        style={{ maxHeight: 'min(92vh, 920px)', overflowY: 'auto' }}
      >
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
          Feedback Loop
        </p>
        <h2 id="class-feedback-title" className="mt-1 font-display text-xl font-bold text-bordo-deep">
          Retroalimentação da aula
        </h2>
        <p className="mt-2 text-sm text-bordo-soft">
          Três cliques e, se quiser, ditado por voz. Ajuda a melhorar a próxima sugestão
          metodológica.
        </p>

        <div className="mt-4 space-y-5">
          <ToggleGroup
            label="A sugestão metodológica funcionou?"
            options={METODOLOGIA}
            value={metodologiaOk}
            onChange={setMetodologiaOk}
          />
          <ToggleGroup
            label="Os alunos responderam de forma adequada?"
            options={ENGAJAMENTO}
            value={engajamento}
            onChange={setEngajamento}
            multiLine
          />
          <ToggleGroup
            label="A estrutura existente acomodou a sugestão?"
            options={ESTRUTURA}
            value={estruturaOk}
            onChange={setEstruturaOk}
          />

          <div>
            <label
              htmlFor="class-feedback-obs"
              className="block text-sm font-bold text-bordo-deep"
            >
              Sugestões ou observações da aula
            </label>
            <div className="relative mt-2">
              <textarea
                id="class-feedback-obs"
                rows={4}
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                placeholder="Opcional — digite ou use o microfone"
                className={`field-input min-h-[110px] w-full resize-y ${
                  supported ? 'pr-14' : ''
                }`}
                disabled={busy}
              />
              {supported ? (
                <button
                  type="button"
                  onClick={() => {
                    setMicError('')
                    toggle()
                  }}
                  disabled={busy}
                  title={listening ? 'Parar ditado' : 'Ditar por microfone'}
                  aria-label={listening ? 'Parar ditado' : 'Ditar por microfone'}
                  aria-pressed={listening}
                  className={[
                    'absolute right-2 top-2 flex h-11 w-11 items-center justify-center rounded-xl transition',
                    listening
                      ? 'bg-red-600 text-white shadow-soft ring-2 ring-red-200'
                      : 'bg-brand-50 text-bordo hover:bg-brand-100',
                  ].join(' ')}
                >
                  {listening ? (
                    <span className="relative flex h-3.5 w-3.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white/80" />
                      <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-white" />
                    </span>
                  ) : (
                    <span aria-hidden className="text-lg leading-none">
                      🎤
                    </span>
                  )}
                </button>
              ) : (
                <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] font-semibold text-amber-900">
                  Ditado por voz indisponível neste navegador. Use Chrome ou Edge, ou digite as
                  observações normalmente.
                </p>
              )}
            </div>
            {listening ? (
              <p className="mt-1.5 text-[11px] font-semibold text-red-600">
                Ouvindo… continue falando. Toque no microfone vermelho para encerrar.
              </p>
            ) : null}
            {micError ? <p className="mt-1 text-[11px] text-bordo">{micError}</p> : null}
          </div>
        </div>

        {error ? (
          <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
            {error}
          </p>
        ) : null}

        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
          {typeof onSkip === 'function' ? (
            <button
              type="button"
              className="btn-ghost order-3 min-h-[48px] w-full sm:order-1 sm:w-auto"
              disabled={busy}
              onClick={() => {
                stop()
                onSkip()
              }}
            >
              Pular por agora
            </button>
          ) : null}
          <button
            type="button"
            className="btn-ghost order-2 min-h-[48px] w-full sm:w-auto"
            disabled={busy}
            onClick={() => {
              if (!busy) {
                stop()
                onCancel?.()
              }
            }}
          >
            Fechar
          </button>
          <button
            type="submit"
            className="btn-primary order-1 min-h-[48px] w-full sm:order-3 sm:w-auto"
            disabled={busy}
          >
            {busy ? 'Salvando…' : 'Enviar feedback'}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  )
}

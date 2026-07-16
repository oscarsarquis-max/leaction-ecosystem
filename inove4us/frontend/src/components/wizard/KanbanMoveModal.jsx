import { useEffect, useState } from 'react'
import DictationField from '../DictationField'

/**
 * Modal de observação obrigatória ao mover card no Kanban (padrão Chamelleon).
 * Só confirma a migração se a observação estiver preenchida.
 */
export default function KanbanMoveModal({ pending, onConfirm, onCancel }) {
  const [nota, setNota] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    setNota('')
    setError('')
  }, [pending])

  if (!pending) return null

  const { task, fromLabel, toLabel } = pending

  function handleSubmit(e) {
    e.preventDefault()
    const texto = nota.trim()
    if (!texto) {
      setError('Preencha a observação de implementação para mover o card.')
      return
    }
    onConfirm?.(texto)
  }

  return (
    <div
      className="fixed inset-0 z-[80] flex items-end justify-center bg-bordo-deep/45 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="kanban-move-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel?.()
      }}
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-5 shadow-soft animate-fade-in"
      >
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
          Movimentação no Kanban
        </p>
        <h2 id="kanban-move-title" className="mt-1 font-display text-xl font-bold text-bordo-deep">
          Observação de implementação
        </h2>
        <p className="mt-2 text-sm text-bordo-soft">
          <span className="font-semibold text-bordo">{task?.titulo}</span>
          <br />
          <span className="text-xs">
            {fromLabel} → <strong>{toLabel}</strong>
          </span>
        </p>

        <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-bordo">
          O que foi feito / o que muda nesta coluna?
        </label>
        <div className="mt-1.5">
          <DictationField
            as="textarea"
            value={nota}
            onChange={setNota}
            rows={4}
            placeholder="Digite ou dite a observação de implementação…"
            className="field-input min-h-[110px] resize-y"
            autoFocus
          />
        </div>
        {error ? <p className="mt-2 text-xs font-semibold text-brand-700">{error}</p> : null}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-ghost !px-4 !py-2 text-sm" onClick={onCancel}>
            Cancelar
          </button>
          <button type="submit" className="btn-primary !px-4 !py-2 text-sm">
            Confirmar movimentação
          </button>
        </div>
      </form>
    </div>
  )
}

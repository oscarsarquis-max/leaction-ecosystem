import { useEffect, useId, useRef, useState } from 'react'

export const PEI_PERFIS = [
  { id: 'TDAH', label: 'TDAH (Atenção e Hiperatividade)' },
  { id: 'TEA', label: 'TEA (Espectro Autista)' },
  { id: 'Dislexia', label: 'Dislexia' },
  { id: 'Deficiência Visual', label: 'Deficiência Visual' },
]

/**
 * Gatilho 🧩 no card pai — escolhe perfil e dispara adaptação PEI.
 */
export default function KanbanPeiMenu({ disabled, busy, onSelectPerfil }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const menuId = useId()

  useEffect(() => {
    if (!open) return undefined
    function onDoc(e) {
      if (!rootRef.current?.contains(e.target)) setOpen(false)
    }
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  useEffect(() => {
    if (busy) setOpen(false)
  }, [busy])

  return (
    <div ref={rootRef} className="relative shrink-0 print:hidden">
      <button
        type="button"
        disabled={disabled || busy}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        title="Adaptação inclusiva (PEI)"
        onClick={(e) => {
          e.stopPropagation()
          e.preventDefault()
          if (disabled || busy) return
          setOpen((v) => !v)
        }}
        className={[
          'inline-flex h-8 w-8 items-center justify-center rounded-lg border text-base shadow-sm transition',
          busy
            ? 'cursor-wait border-amber-400 bg-amber-100 text-amber-900'
            : 'border-amber-300 bg-white text-bordo hover:border-amber-500 hover:bg-amber-50',
          disabled ? 'cursor-not-allowed opacity-40' : '',
        ].join(' ')}
      >
        {busy ? (
          <span className="text-[10px] font-bold" aria-hidden>
            …
          </span>
        ) : (
          <span aria-hidden>🧩</span>
        )}
        <span className="sr-only">
          {busy ? 'Gerando adaptação PEI' : 'Adaptar card (PEI)'}
        </span>
      </button>

      {open ? (
        <div
          id={menuId}
          role="menu"
          className="absolute right-0 z-30 mt-1 w-64 overflow-hidden rounded-xl border border-brand-200 bg-white shadow-soft"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="border-b border-brand-100 px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-bordo-soft">
            Perfil de inclusão
          </p>
          <ul className="py-1">
            {PEI_PERFIS.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  role="menuitem"
                  className="w-full px-3 py-2.5 text-left text-xs font-semibold text-bordo hover:bg-amber-50"
                  onClick={() => {
                    setOpen(false)
                    onSelectPerfil?.(p.id)
                  }}
                >
                  {p.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

export function isPeiSubcard(task) {
  const parent = task?.parent_card_id
  return parent != null && String(parent).trim() !== ''
}

/**
 * Ordena cards da coluna: pais primeiro, filhos logo abaixo do pai.
 * Subcards órfãos (pai em outra coluna) ficam no fim, indentados.
 */
export function orderColumnCards(cardsInColumn) {
  const list = Array.isArray(cardsInColumn) ? cardsInColumn : []
  const byId = new Map(list.map((t) => [String(t.id), t]))
  const roots = list.filter((t) => !isPeiSubcard(t))
  const used = new Set()
  const ordered = []

  for (const parent of roots) {
    ordered.push({ task: parent, depth: 0 })
    used.add(String(parent.id))
    const kids = list.filter(
      (t) => isPeiSubcard(t) && String(t.parent_card_id) === String(parent.id),
    )
    for (const kid of kids) {
      ordered.push({ task: kid, depth: 1 })
      used.add(String(kid.id))
    }
  }

  for (const t of list) {
    if (used.has(String(t.id))) continue
    // órfão ou pai fora desta coluna
    const parentMissing = isPeiSubcard(t) && !byId.has(String(t.parent_card_id))
    ordered.push({ task: t, depth: isPeiSubcard(t) || parentMissing ? 1 : 0 })
  }

  return ordered
}

import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../../lib/api'

/** Alinha aee_canonico do School + Dislexia (perfil só do B2C). */
export const PEI_PERFIS = [
  { id: 'TEA', label: 'TEA (Espectro Autista)' },
  { id: 'TDAH', label: 'TDAH (Atenção e Hiperatividade)' },
  { id: 'Altas Habilidades', label: 'Altas Habilidades' },
  { id: 'Deficiência Intelectual', label: 'Deficiência Intelectual' },
  { id: 'Deficiência Visual', label: 'Deficiência Visual' },
  { id: 'Deficiência Auditiva', label: 'Deficiência Auditiva' },
  { id: 'Deficiência Física', label: 'Deficiência Física' },
  { id: 'Outras Dificuldades Severas', label: 'Outras Dificuldades Severas' },
  { id: 'Dislexia', label: 'Dislexia' },
]

const MENU_WIDTH = 288
const MENU_EST_HEIGHT = 380

function menuPosition(anchor) {
  const r = anchor.getBoundingClientRect()
  let left = r.right - MENU_WIDTH
  if (left < 8) left = 8
  if (left + MENU_WIDTH > window.innerWidth - 8) {
    left = Math.max(8, window.innerWidth - MENU_WIDTH - 8)
  }
  const spaceBelow = window.innerHeight - r.bottom
  const openUp = spaceBelow < MENU_EST_HEIGHT && r.top > spaceBelow
  const top = openUp ? Math.max(8, r.top - MENU_EST_HEIGHT - 4) : r.bottom + 4
  return { top, left }
}

/**
 * Gatilho 🧩 no card pai — escolhe perfil e dispara adaptação PEI.
 * O menu abre em portal (document.body) para não ficar atrás do card vizinho
 * (cards usam transform: rotate(), o que cria stacking context).
 * alunoNome opcional: best-effort para casar PEI individual da escola.
 */
export default function KanbanPeiMenu({ disabled, busy, onSelectPerfil }) {
  const [open, setOpen] = useState(false)
  const [alunoNome, setAlunoNome] = useState('')
  const [escolaHint, setEscolaHint] = useState('')
  const [coords, setCoords] = useState({ top: 0, left: 0 })
  const rootRef = useRef(null)
  const menuRef = useRef(null)
  const btnRef = useRef(null)
  const menuId = useId()

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return undefined
    const place = () => {
      if (btnRef.current) setCoords(menuPosition(btnRef.current))
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => {
      window.removeEventListener('resize', place)
      window.removeEventListener('scroll', place, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    function onDoc(e) {
      const t = e.target
      if (rootRef.current?.contains(t)) return
      if (menuRef.current?.contains(t)) return
      setOpen(false)
    }
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false)
    }
    // click (não mousedown): o item do menu precisa receber o clique
    // antes de um close que desmonte o portal.
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

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    ;(async () => {
      try {
        const data = await api.listPeiOverrides()
        if (cancelled) return
        const bases = (data?.base || [])
          .map((b) => b.condicao)
          .filter(Boolean)
        const nomes = (data?.individual || [])
          .map((i) => i.aluno_nome)
          .filter(Boolean)
        const parts = []
        if (bases.length) {
          parts.push(`Diretriz AEE da escola: ${bases.join(', ')}.`)
        }
        if (nomes.length) {
          parts.push(`PEI individual: ${nomes.slice(0, 4).join(', ')}${nomes.length > 4 ? '…' : ''}.`)
        }
        setEscolaHint(parts.join(' '))
      } catch {
        if (!cancelled) setEscolaHint('')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open])

  const menu =
    open && typeof document !== 'undefined'
      ? createPortal(
          <div
            ref={menuRef}
            id={menuId}
            role="menu"
            data-pei-menu="1"
            className="fixed z-[400] w-72 overflow-hidden rounded-xl border border-brand-200 bg-white shadow-soft"
            style={{ top: coords.top, left: coords.left }}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => e.stopPropagation()}
          >
            <p className="border-b border-brand-100 px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-bordo-soft">
              Perfil de inclusão
            </p>
            {escolaHint ? (
              <p className="border-b border-amber-100 bg-amber-50 px-3 py-2 text-[10px] leading-snug text-amber-950">
                <span className="font-semibold">Regra da escola. </span>
                {escolaHint}
              </p>
            ) : null}
            <label className="block border-b border-brand-50 px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-bordo-soft">
                Nome do aluno (opcional)
              </span>
              <input
                type="text"
                className="mt-1 w-full rounded-lg border border-brand-200 px-2 py-1.5 text-xs text-bordo outline-none focus:border-brand-500"
                value={alunoNome}
                onChange={(e) => setAlunoNome(e.target.value)}
                placeholder="Ex.: João Pedro — casa PEI da escola"
                autoComplete="off"
              />
            </label>
            <ul className="max-h-56 overflow-y-auto py-1">
              {PEI_PERFIS.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    role="menuitem"
                    className="w-full px-3 py-2.5 text-left text-xs font-semibold text-bordo hover:bg-amber-50"
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      setOpen(false)
                      onSelectPerfil?.(p.id, alunoNome.trim())
                    }}
                  >
                    {p.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>,
          document.body,
        )
      : null

  return (
    <div ref={rootRef} data-pei-menu="1" className="relative shrink-0 print:hidden">
      <button
        ref={btnRef}
        type="button"
        disabled={disabled || busy}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        title="Adaptação inclusiva (PEI)"
        onClick={(e) => {
          e.stopPropagation()
          e.preventDefault()
          if (disabled || busy) return
          setOpen((v) => !v)
        }}
        className={[
          'relative z-[5] inline-flex h-8 w-8 items-center justify-center rounded-lg border text-base shadow-sm transition',
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
          {busy ? 'Carregando adaptação PEI' : 'Adaptar card (PEI)'}
        </span>
      </button>
      {menu}
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

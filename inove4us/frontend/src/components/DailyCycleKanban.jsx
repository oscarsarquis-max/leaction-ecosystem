import { useEffect, useState } from 'react'
import KanbanMoveModal from './wizard/KanbanMoveModal'

const COLUNAS = [
  { id: 'para_fazer', label: 'Para Fazer', tone: 'border-brand-200 bg-brand-50/60' },
  { id: 'fazendo', label: 'Fazendo', tone: 'border-amber-200 bg-amber-50/70' },
  { id: 'pronto', label: 'Pronto', tone: 'border-emerald-200 bg-emerald-50/70' },
]

export const ESTACOES_CICLO = [
  {
    id: 'est_alinhamento',
    campo: 'acolhida',
    titulo: '1 · Acolhida',
    cor: '#FDE68A',
  },
  {
    id: 'est_entrega',
    campo: 'conteudo_essencial',
    titulo: '2 · Conteúdo',
    cor: '#BBF7D0',
  },
  {
    id: 'est_campo',
    campo: 'dinamica_texto',
    titulo: '3 · Dinâmica',
    cor: '#A5F3FC',
  },
  {
    id: 'est_retro',
    campo: 'fechamento_checkout',
    titulo: '4 · Fechamento',
    cor: '#DDD6FE',
  },
]

function colunaLabel(id) {
  return COLUNAS.find((c) => c.id === id)?.label || id
}

function previewOf(text, { max = 120 } = {}) {
  const t = String(text || '').trim()
  if (!t) return 'Ainda sem conteúdo no formulário'
  return t.length > max ? `${t.slice(0, max - 3)}…` : t
}

/**
 * Monta/mescla as 4 estações do ciclo com estado de colunas/histórico.
 */
export function buildCycleTasks(form, kanbanState) {
  const prevList = Array.isArray(kanbanState?.tarefas)
    ? kanbanState.tarefas
    : Array.isArray(kanbanState)
      ? kanbanState
      : []
  const byId = Object.fromEntries(prevList.map((t) => [t.id, t]))

  return ESTACOES_CICLO.map((est) => {
    const prev = byId[est.id] || {}
    const full = String(form?.[est.campo] || '').trim()
    const isDin = est.campo === 'dinamica_texto'
    const passos = isDin && Array.isArray(form?.dinamica_passos) ? form.dinamica_passos : []
    const nomeDin = isDin ? String(form?.dinamica_nome || '').trim() : ''
    const resumoDin = nomeDin
      ? `${nomeDin}${passos.length ? ` · ${passos.length} passos` : ''} (diretriz)`
      : previewOf(full, { max: 180 })
    return {
      id: est.id,
      titulo: est.titulo,
      campo: est.campo,
      cor: est.cor,
      coluna: prev.coluna || 'para_fazer',
      resumo: isDin ? resumoDin : previewOf(full, { max: 180 }),
      conteudo: full,
      passos: isDin ? passos : undefined,
      dinamica_nome: isDin ? nomeDin : undefined,
      historico: Array.isArray(prev.historico) ? prev.historico : [],
      ultima_observacao: prev.ultima_observacao || '',
    }
  })
}

export function cycleKanbanPayload(tasks) {
  return { tarefas: tasks }
}

/**
 * mesa do ciclo Dia a Dia — 4 estações como cards; migração exige modal.
 * focusMode: roteiro de voo (só cards em evidência).
 */
export default function DailyCycleKanban({
  tasks,
  onTasksChange,
  enabled = true,
  focusMode = false,
}) {
  const [draggingId, setDraggingId] = useState(null)
  const [dropTarget, setDropTarget] = useState(null)
  const [pendingMove, setPendingMove] = useState(null)

  useEffect(() => {
    if (!enabled) setPendingMove(null)
  }, [enabled])

  function requestMove(taskId, toColuna) {
    if (!enabled) return
    const task = tasks.find((t) => t.id === taskId)
    if (!task) return
    const fromColuna = task.coluna || 'para_fazer'
    if (fromColuna === toColuna) return
    setPendingMove({
      task,
      fromColuna,
      toColuna,
      fromLabel: colunaLabel(fromColuna),
      toLabel: colunaLabel(toColuna),
    })
  }

  function confirmMove(nota) {
    if (!pendingMove) return
    const { task, fromColuna, toColuna } = pendingMove
    const entrada = {
      de: fromColuna,
      para: toColuna,
      nota: nota.trim(),
      em: new Date().toISOString(),
    }
    const next = tasks.map((t) => {
      if (t.id !== task.id) return t
      const historico = Array.isArray(t.historico) ? [...t.historico, entrada] : [entrada]
      return { ...t, coluna: toColuna, historico, ultima_observacao: nota.trim() }
    })
    onTasksChange?.(next)
    setPendingMove(null)
  }

  if (focusMode) {
    const ordered = ESTACOES_CICLO.map((est) => tasks.find((t) => t.id === est.id)).filter(
      Boolean,
    )
    return (
      <section className="rounded-2xl border border-amber-300 bg-gradient-to-b from-amber-50/80 to-white p-4 shadow-soft sm:p-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-amber-800">
          Modo Aula · roteiro
        </p>
        <h2 className="mt-1 font-display text-2xl font-bold text-bordo-deep">
          Os 4 momentos
        </h2>
        <p className="mt-1 text-sm text-bordo-soft">
          Siga o roteiro. Pode fechar o notebook — a aula continua em execução até você
          encerrar.
        </p>
        <ol className="mt-5 grid gap-3 sm:grid-cols-2">
          {ordered.map((task, idx) => {
            const passos = Array.isArray(task.passos) ? task.passos : []
            const isDinamica = task.campo === 'dinamica_texto' && passos.length > 0
            return (
              <li
                key={task.id}
                className={`rounded-xl border border-black/5 p-4 shadow-sm ${
                  isDinamica ? 'sm:col-span-2' : ''
                }`}
                style={{ backgroundColor: task.cor || '#fff' }}
              >
                <p className="text-[10px] font-bold uppercase tracking-wide text-bordo-soft">
                  Momento {idx + 1}
                </p>
                <p className="mt-1 font-display text-lg font-bold text-bordo-deep">
                  {task.titulo}
                  {task.dinamica_nome ? (
                    <span className="ml-2 text-sm font-semibold text-bordo-soft">
                      · {task.dinamica_nome}
                    </span>
                  ) : null}
                </p>
                {isDinamica ? (
                  <ol className="mt-3 space-y-2">
                    {passos.map((p, i) => (
                      <li
                        key={`${p.ordem || i}-${p.titulo || i}`}
                        className="rounded-lg border border-black/5 bg-white/70 px-3 py-2"
                      >
                        <p className="text-sm font-bold text-bordo-deep">
                          {p.ordem || i + 1}. {p.titulo}
                          {p.duracao_minutos ? (
                            <span className="ml-2 text-[11px] font-semibold text-bordo-soft">
                              ~{p.duracao_minutos} min
                            </span>
                          ) : null}
                        </p>
                        {p.como_executar ? (
                          <p className="mt-1 text-[12px] leading-relaxed text-bordo">
                            {p.como_executar}
                          </p>
                        ) : null}
                        {p.dica_de_facilitacao ? (
                          <p className="mt-1 text-[11px] italic text-amber-900">
                            Facilitação: {p.dica_de_facilitacao}
                          </p>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-bordo">
                    {String(task.conteudo || task.resumo || '').trim() || '—'}
                  </p>
                )}
              </li>
            )
          })}
        </ol>
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-emerald-200 bg-emerald-50/30 p-4 shadow-soft sm:p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-800">
        Board do ciclo
      </p>
      <h2 className="mt-1 font-display text-xl font-bold text-bordo-deep">Mesa · 50 min</h2>
      <p className="mt-1 text-xs text-bordo-soft">
        Arraste Acolhida, Conteúdo, Dinâmica e Fechamento entre as colunas. Toda migração
        pede uma observação obrigatória.
      </p>
      {!enabled ? (
        <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-[11px] font-semibold text-amber-900">
          Preencha o tema e a data à esquerda para liberar o board.
        </p>
      ) : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {COLUNAS.map((col) => {
          const cards = tasks.filter((t) => (t.coluna || 'para_fazer') === col.id)
          const isTarget = dropTarget === col.id
          return (
            <div
              key={col.id}
              className={`min-h-[240px] rounded-xl border p-3 transition ${col.tone} ${
                isTarget ? 'ring-2 ring-emerald-500 ring-offset-2' : ''
              }`}
              onDragOver={(e) => {
                if (!enabled) return
                e.preventDefault()
                e.dataTransfer.dropEffect = 'move'
                if (dropTarget !== col.id) setDropTarget(col.id)
              }}
              onDragLeave={() => {
                if (dropTarget === col.id) setDropTarget(null)
              }}
              onDrop={(e) => {
                e.preventDefault()
                setDropTarget(null)
                const taskId = e.dataTransfer.getData('text/plain')
                setDraggingId(null)
                if (taskId) requestMove(taskId, col.id)
              }}
            >
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-bold text-bordo-deep">{col.label}</h3>
                <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-bold text-bordo-soft">
                  {cards.length}
                </span>
              </div>
              <ul className="space-y-2">
                {cards.map((task) => (
                  <li
                    key={task.id}
                    draggable={enabled}
                    onDragStart={(e) => {
                      if (!enabled) {
                        e.preventDefault()
                        return
                      }
                      e.dataTransfer.setData('text/plain', String(task.id))
                      e.dataTransfer.effectAllowed = 'move'
                      setDraggingId(task.id)
                    }}
                    onDragEnd={() => {
                      setDraggingId(null)
                      setDropTarget(null)
                    }}
                    className={`rounded-lg border border-black/5 p-3 text-sm shadow-sm ${
                      enabled
                        ? 'cursor-grab active:cursor-grabbing'
                        : 'cursor-not-allowed opacity-80'
                    } ${draggingId === task.id ? 'opacity-50' : ''}`}
                    style={{ backgroundColor: task.cor || '#fff' }}
                  >
                    <p className="font-bold text-bordo-deep">{task.titulo}</p>
                    <p className="mt-1 line-clamp-3 text-[11px] leading-relaxed text-bordo-soft">
                      {task.resumo}
                    </p>
                    {task.ultima_observacao ? (
                      <p className="mt-2 border-t border-black/5 pt-1.5 text-[10px] italic text-bordo">
                        Última nota: {task.ultima_observacao}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>

      <KanbanMoveModal
        pending={pendingMove}
        onConfirm={confirmMove}
        onCancel={() => setPendingMove(null)}
      />
    </section>
  )
}

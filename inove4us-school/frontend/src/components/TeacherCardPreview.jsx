/**
 * TeacherCardPreview — espelho visual do Card da Mesa (inove4us B2C).
 * Tokens bordo/brand do Inove (propositalmente), leitura-only no School.
 */

const COLUNAS = [
  { id: 'para_fazer', label: 'Para Fazer', tone: 'border-[#fecdd3] bg-[#fff1f2]/60' },
  { id: 'fazendo', label: 'Fazendo', tone: 'border-amber-200 bg-amber-50/50' },
  { id: 'pronto', label: 'Pronto', tone: 'border-emerald-200 bg-emerald-50/50' },
]

function asCards(mesa) {
  if (!mesa || typeof mesa !== 'object') return []
  const raw =
    mesa.cards ||
    mesa.kanban_cards ||
    mesa.etapas ||
    mesa.passos ||
    mesa.steps ||
    []
  if (Array.isArray(raw)) return raw
  if (raw && typeof raw === 'object' && Array.isArray(raw.tarefas)) return raw.tarefas
  return []
}

function colunaOf(card) {
  const c = String(card?.coluna || card?.status || 'para_fazer').toLowerCase()
  if (c.includes('pronto') || c === 'done' || c === 'concluido') return 'pronto'
  if (c.includes('fazendo') || c === 'doing' || c === 'em_andamento') return 'fazendo'
  return 'para_fazer'
}

function progresso(cards) {
  if (!cards.length) return { pct: 0, done: 0, total: 0, minDone: 0, minTotal: 0 }
  let weight = 0
  let minDone = 0
  let minTotal = 0
  for (const c of cards) {
    const col = colunaOf(c)
    const min = Number(c.duracao_minutos) > 0 ? Number(c.duracao_minutos) : 10
    minTotal += min
    if (col === 'pronto') {
      weight += 1
      minDone += min
    } else if (col === 'fazendo') {
      weight += 0.5
      minDone += min * 0.5
    }
  }
  const pct = Math.round((weight / cards.length) * 100)
  return {
    pct,
    done: cards.filter((c) => colunaOf(c) === 'pronto').length,
    total: cards.length,
    minDone: Math.round(minDone),
    minTotal: Math.round(minTotal),
  }
}

function MesaCard({ card }) {
  const pei = Boolean(card?.perfil_inclusao || card?.parent_card_id)
  const col = colunaOf(card)
  const titulo = card.titulo || card.titulo_do_card || card.nome || 'Card'
  const rot = (String(card.id || titulo).charCodeAt(1) % 3) - 1
  const obs = String(card.ultima_observacao || '').trim()
  const objetivo = String(card.objetivo || '').trim()
  const como = String(
    card.como_executar_detalhado ||
      card.mecanica_passo_a_passo ||
      card.descricao ||
      '',
  ).trim()

  return (
    <li
      className={[
        'rounded-lg border p-3 text-sm font-medium shadow-sm',
        pei
          ? 'ml-3 border-l-4 border-l-yellow-400 border-amber-200/80 bg-amber-50'
          : 'border-black/5',
        !pei && col === 'pronto' ? 'ring-1 ring-emerald-400/70' : '',
      ].join(' ')}
      style={
        pei
          ? { color: '#450a0a' }
          : {
              color: '#450a0a',
              backgroundColor: card.cor || '#FDE68A',
              transform: `rotate(${rot}deg)`,
            }
      }
    >
      {pei ? (
        <p className="mb-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-800">
          PEI · {card.perfil_inclusao || 'Adaptação'}
        </p>
      ) : null}
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold leading-snug">{titulo}</p>
        {Number(card.duracao_minutos) > 0 ? (
          <span className="shrink-0 rounded bg-white/70 px-1.5 py-0.5 text-[10px] font-bold text-[#7f1d1d]/80">
            {Math.round(Number(card.duracao_minutos))}′
          </span>
        ) : null}
      </div>
      {objetivo ? (
        <p className="mt-2 text-xs font-normal leading-relaxed text-[#7f1d1d]/90">
          <span className="font-bold">Objetivo:</span> {objetivo}
        </p>
      ) : null}
      {como ? (
        <p className="mt-1 text-xs font-normal leading-relaxed text-[#7f1d1d]/80 line-clamp-3">
          <span className="font-bold">Como fazer:</span> {como}
        </p>
      ) : null}
      {obs ? (
        <p className="mt-2 rounded bg-white/60 px-2 py-1 text-[11px] font-normal italic text-[#7f1d1d]">
          Última obs.: {obs}
        </p>
      ) : null}
    </li>
  )
}

/**
 * @param {{
 *   mesa?: Record<string, unknown> | null,
 *   meta?: Record<string, unknown>,
 *   avisos?: Array<{ id?: string, texto?: string, titulo?: string }>,
 *   className?: string,
 * }} props
 */
export default function TeacherCardPreview({
  mesa = null,
  meta = {},
  avisos = [],
  className = '',
}) {
  const data = mesa && typeof mesa === 'object' ? mesa : {}
  const cards = asCards(data)
  const prog = progresso(cards)
  const titulo =
    data.titulo || data.title || meta.conteudo_resumo || meta.metodologia_nome || 'Aula'
  const metodologia =
    data.metodologia_nome || data.metodologia || meta.metodologia_nome || '—'
  const versaoEscola =
    data.metodologia_versao_escola ||
    data.versao_metodologia ||
    meta.metodologia_versao ||
    null
  const aulaContexto = data.aula_contexto || meta.aula_contexto || ''
  const listaAvisos = Array.isArray(avisos) && avisos.length
    ? avisos
    : Array.isArray(data.avisos_fixados)
      ? data.avisos_fixados
      : []

  const byCol = Object.fromEntries(COLUNAS.map((c) => [c.id, []]))
  for (const card of cards) {
    byCol[colunaOf(card)].push(card)
  }

  return (
    <div
      className={[
        'overflow-hidden rounded-2xl border border-[#fecdd3] bg-white shadow-lg',
        className,
      ].join(' ')}
      style={{ fontFamily: '"DM Sans", "IBM Plex Sans", system-ui, sans-serif' }}
    >
      {/* Header bordo — espelho Mesa */}
      <header className="bg-gradient-to-b from-[#e11d48] to-[#7f1d1d] px-4 py-4 text-white sm:px-5">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/80">
          Espelho · Mesa do Professor
        </p>
        <h3
          className="mt-1 text-xl font-bold leading-tight"
          style={{ fontFamily: '"Source Serif 4", Georgia, serif' }}
        >
          {titulo}
        </h3>
        <p className="mt-1 text-sm text-white/90">
          Metodologia da Escola: <strong>{metodologia}</strong>
          {versaoEscola ? ` · v${versaoEscola}` : ''}
        </p>
        {aulaContexto ? (
          <p className="mt-0.5 text-xs text-white/75">{aulaContexto}</p>
        ) : null}
        {(meta.turma_nome || meta.professor_email) && (
          <p className="mt-2 text-xs text-white/80">
            {[meta.turma_nome, meta.professor_email || meta.professor_nome]
              .filter(Boolean)
              .join(' · ')}
          </p>
        )}
      </header>

      {/* Avisos fixados */}
      {listaAvisos.length ? (
        <div className="border-b border-[#fecdd3] bg-[#fff1f2] px-4 py-3 sm:px-5">
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#e11d48]">
            Avisos fixados
          </p>
          <ul className="mt-1.5 space-y-1.5">
            {listaAvisos.map((a, i) => (
              <li
                key={a.id || i}
                className="rounded-lg border border-[#fecdd3] bg-white px-3 py-2 text-sm text-[#7f1d1d]"
              >
                {a.titulo ? <span className="font-bold">{a.titulo}: </span> : null}
                {a.texto || a.descricao || a.mensagem || '—'}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="border-b border-dashed border-[#fecdd3] bg-[#fff1f2]/50 px-4 py-2.5 text-xs text-[#991b1b] sm:px-5">
          Nenhum aviso fixado nesta mesa no momento.
        </div>
      )}

      {/* Progresso */}
      <div className="flex flex-wrap items-center gap-3 border-b border-[#fecdd3] px-4 py-3 sm:px-5">
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#e11d48]">
              Progresso
            </p>
            <p className="text-sm font-bold text-[#450a0a]">{prog.pct}%</p>
          </div>
          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-[#fecdd3]/80">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#e11d48] to-[#7f1d1d] transition-all"
              style={{ width: `${prog.pct}%` }}
            />
          </div>
          <p className="mt-1 text-[11px] text-[#991b1b]">
            {prog.done}/{prog.total} cards em Pronto
            {prog.minTotal
              ? ` · ~${prog.minDone}/${prog.minTotal} min`
              : ''}
          </p>
        </div>
        <span className="rounded-full bg-[#fff1f2] px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[#7f1d1d]">
          Somente leitura
        </span>
      </div>

      {/* Kanban 3 colunas */}
      <div className="grid gap-3 p-3 sm:grid-cols-3 sm:p-4">
        {COLUNAS.map((col) => (
          <div
            key={col.id}
            className={`rounded-xl border p-2.5 ${col.tone}`}
          >
            <p className="mb-2 px-1 text-[10px] font-bold uppercase tracking-wide text-[#7f1d1d]">
              {col.label}
              <span className="ml-1 font-semibold text-[#991b1b]/70">
                ({byCol[col.id].length})
              </span>
            </p>
            {byCol[col.id].length ? (
              <ul className="space-y-2">
                {byCol[col.id].map((card, i) => (
                  <MesaCard key={card.id || `${col.id}-${i}`} card={card} />
                ))}
              </ul>
            ) : (
              <p className="px-1 py-4 text-center text-[11px] text-[#991b1b]/60">
                Vazio
              </p>
            )}
          </div>
        ))}
      </div>

      {!cards.length ? (
        <p className="border-t border-[#fecdd3] px-4 py-4 text-center text-sm text-[#991b1b] sm:px-5">
          Snapshot da mesa ainda sem cards sincronizados. O espelho completa após
          movimentações / fechamento no Inove.
        </p>
      ) : null}
    </div>
  )
}

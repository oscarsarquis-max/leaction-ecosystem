import { useMemo } from 'react'

const MESES_MIN = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
]

const MET_BAR = [
  'bg-sky-500',
  'bg-violet-500',
  'bg-teal-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-indigo-500',
  'bg-cyan-500',
  'bg-fuchsia-500',
  'bg-orange-500',
  'bg-emerald-500',
  'bg-blue-500',
  'bg-pink-500',
]

function pad2(n) {
  return String(n).padStart(2, '0')
}

export function rotuloRecorteLegivel(tipo, periodo) {
  const ini = periodo?.inicio
  const fim = periodo?.fim
  if (!ini || Number.isNaN(ini.getTime())) return '—'
  const mesIni = MESES_MIN[ini.getMonth()]
  if (tipo === 'diario') return `${pad2(ini.getDate())} de ${mesIni}`
  if (tipo === 'anual') return String(ini.getFullYear())
  if (tipo === 'mensal') {
    const nome = mesIni.charAt(0).toUpperCase() + mesIni.slice(1)
    return `${nome} de ${ini.getFullYear()}`
  }
  if (!fim || Number.isNaN(fim.getTime())) {
    return `${pad2(ini.getDate())} de ${mesIni}`
  }
  const mesFim = MESES_MIN[fim.getMonth()]
  if (ini.getMonth() === fim.getMonth() && ini.getFullYear() === fim.getFullYear()) {
    return `${pad2(ini.getDate())} a ${pad2(fim.getDate())} de ${mesIni}`
  }
  return `${pad2(ini.getDate())} de ${mesIni} a ${pad2(fim.getDate())} de ${mesFim}`
}

function isEventoItem(item) {
  return item?.item_kind === 'evento' || item?.tipo_aula === 'evento'
}

function deriveKpis(planos) {
  const list = (Array.isArray(planos) ? planos : []).filter((p) => !isEventoItem(p))
  let dia = 0
  let desafio = 0
  let pendente = 0
  let aprovado = 0
  let reprovado = 0
  const profs = new Set()
  for (const p of list) {
    if (p.tipo_aula === 'desafio') desafio += 1
    else dia += 1
    if (p.status === 'aprovado') aprovado += 1
    else if (p.status === 'reprovado') reprovado += 1
    else pendente += 1
    if (p.professor_vinculo_id) profs.add(p.professor_vinculo_id)
  }
  return {
    total: list.length,
    por_tipo_aula: { dia_a_dia: dia, desafio },
    por_status: { pendente, aprovado, reprovado },
    professores_ativos: profs.size,
  }
}

function colorMet(nome) {
  const s = String(nome || '')
  let h = 0
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return MET_BAR[h % MET_BAR.length]
}

function EmptyNote({ children }) {
  return (
    <p className="text-sm leading-relaxed text-slate-600">
      {children}
    </p>
  )
}

function BlockShell({ tone, kicker, title, hint, children }) {
  const tones = {
    sky: 'border-sky-200 bg-gradient-to-br from-sky-50 to-white',
    emerald: 'border-emerald-200 bg-gradient-to-br from-emerald-50 to-white',
    violet: 'border-violet-200 bg-gradient-to-br from-violet-50 to-white',
    slate: 'border-slate-200 bg-white',
  }
  const kickers = {
    sky: 'text-sky-700',
    emerald: 'text-emerald-800',
    violet: 'text-violet-800',
    slate: 'text-muted',
  }
  return (
    <section className={`rounded-2xl border p-4 shadow-panel ${tones[tone] || tones.slate}`}>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className={`text-[10px] font-bold uppercase tracking-[0.16em] ${kickers[tone] || kickers.slate}`}>
            {kicker}
          </p>
          <h2 className="mt-1 text-base font-semibold tracking-tight text-ink">{title}</h2>
        </div>
        {hint ? <p className="max-w-md text-xs text-muted">{hint}</p> : null}
      </div>
      {children}
    </section>
  )
}

function PulsoCard({ label, children, className = '', onClick }) {
  const clickable = typeof onClick === 'function'
  const Comp = clickable ? 'button' : 'article'
  return (
    <Comp
      type={clickable ? 'button' : undefined}
      onClick={onClick}
      className={[
        'rounded-xl border p-3 text-left shadow-sm',
        clickable
          ? 'cursor-pointer transition hover:brightness-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500'
          : '',
        className,
      ].join(' ')}
    >
      <p className="text-[10px] font-bold uppercase tracking-wide opacity-80">{label}</p>
      {children}
    </Comp>
  )
}

function MiniProportion({ dia, desafio }) {
  const total = dia + desafio
  if (!total) {
    return <EmptyNote>Nenhuma aula registrada neste recorte ainda.</EmptyNote>
  }
  const pctDia = Math.round((100 * dia) / total)
  return (
    <div>
      <div className="mt-2 flex h-3 overflow-hidden rounded-full bg-slate-200">
        <div
          className="bg-emerald-500"
          style={{ width: `${pctDia}%` }}
          title={`Dia a Dia: ${dia}`}
        />
        <div
          className="bg-amber-500"
          style={{ width: `${100 - pctDia}%` }}
          title={`Desafio: ${desafio}`}
        />
      </div>
      <p className="mt-2 text-sm font-semibold text-sky-950">
        {dia} Dia a Dia · {desafio} Desafio
      </p>
      <p className="text-[11px] text-sky-800/80">{pctDia}% no ciclo rápido</p>
    </div>
  )
}

function coberturaBarClass(pct) {
  if (pct >= 70) return 'bg-emerald-600'
  if (pct >= 40) return 'bg-emerald-500'
  if (pct >= 15) return 'bg-emerald-400'
  if (pct > 0) return 'bg-amber-400'
  return 'bg-slate-200'
}

export default function RadarHomeBlocks({
  instituicaoNome,
  unidadeNome,
  tipoPeriodo,
  periodo,
  planos,
  loading,
  consolidado,
  cobertura,
  inclusao,
  onPendentesClick,
  onNavigate,
}) {
  const kpis = useMemo(() => deriveKpis(planos), [planos])
  const metodologias = useMemo(() => {
    const map = new Map()
    for (const p of Array.isArray(planos) ? planos : []) {
      if (isEventoItem(p)) continue
      const nome = String(p.metodologia_nome || '').trim()
      if (!nome) continue
      map.set(nome, (map.get(nome) || 0) + 1)
    }
    return [...map.entries()]
      .map(([nome, aulas]) => ({ nome, aulas }))
      .sort((a, b) => b.aulas - a.aulas || a.nome.localeCompare(b.nome))
  }, [planos])

  const contexto = [unidadeNome || instituicaoNome || 'Instituição', rotuloRecorteLegivel(tipoPeriodo, periodo)]
    .filter(Boolean)
    .join(' · ')

  const chips = [
    {
      key: 'gestao',
      label: 'Gestão',
      value: consolidado
        ? `${consolidado.unidades ?? 0} un. · ${consolidado.turmas_ativas ?? 0} turmas`
        : '—',
      to: '/secretaria',
    },
    {
      key: 'docente',
      label: 'Docentes',
      value: consolidado ? `${consolidado.professores_ativos ?? 0} ativos` : '—',
      to: '/equipe',
    },
    {
      key: 'com',
      label: 'Agenda',
      value: consolidado ? `${consolidado.eventos_semana ?? 0} eventos` : '—',
      to: '/secretaria',
    },
    {
      key: 'editor',
      label: 'Editor',
      value: consolidado
        ? `${consolidado.metodologias_ativas ?? 0} met. · ${consolidado.planos_pei ?? 0} PEI`
        : '—',
      to: '/editor-pedagogico',
    },
  ]

  const emptyAulas = !loading && kpis.total === 0
  const pendentes = kpis.por_status.pendente
  const maxMet = Math.max(1, ...metodologias.map((m) => m.aulas))
  const cobItens = cobertura?.itens || []
  const inc = inclusao || {
    alunos_pei_ativos: 0,
    alunos_com_adaptacao: 0,
    aulas_com_adaptacao: 0,
    aulas_no_recorte: 0,
    percentual: 0,
  }

  return (
    <div className="space-y-4">
      <header className="rounded-2xl border border-slate-200 bg-gradient-to-r from-school-700 via-school-600 to-sky-800 px-5 py-5 text-white shadow-panel">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/70">
          Radar Pedagógico
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
          {contexto}
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-white/80">
          Pulso da escola neste recorte — o que foi dado, com qual método, o que a BNCC já
          cobriu e se a adaptação AEE chegou à sala.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {chips.map((c) => (
            <button
              key={c.key}
              type="button"
              onClick={() => onNavigate?.(c.to)}
              className="rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-left backdrop-blur-sm transition hover:bg-white/20"
            >
              <span className="block text-[10px] font-bold uppercase tracking-wide text-white/70">
                {c.label}
              </span>
              <span className="text-xs font-semibold">{c.value}</span>
            </button>
          ))}
        </div>
      </header>

      <BlockShell
        tone="sky"
        kicker="Pulso da semana"
        title="O que aconteceu neste recorte"
        hint="Os mesmos quatro números de sempre, agora com cor e estado vazio explícito."
      >
        {loading && !kpis.total ? (
          <p className="text-sm text-sky-800">Carregando o recorte…</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <PulsoCard className="border-sky-200 bg-sky-100/70 text-sky-950" label="Planos no recorte">
              {emptyAulas ? (
                <EmptyNote>Nenhuma aula registrada neste recorte ainda.</EmptyNote>
              ) : (
                <p className="mt-1 text-3xl font-semibold tabular-nums">{kpis.total}</p>
              )}
            </PulsoCard>
            <PulsoCard className="border-sky-200 bg-white text-sky-950" label="Dia a Dia vs Desafio">
              {emptyAulas ? (
                <EmptyNote>Sem aulas para comparar os dois ciclos.</EmptyNote>
              ) : (
                <MiniProportion
                  dia={kpis.por_tipo_aula.dia_a_dia}
                  desafio={kpis.por_tipo_aula.desafio}
                />
              )}
            </PulsoCard>
            <PulsoCard
              className={
                pendentes > 0
                  ? 'border-amber-400 bg-amber-100 text-amber-950'
                  : 'border-slate-200 bg-slate-50 text-slate-700'
              }
              label="Pendentes"
              onClick={onPendentesClick}
            >
              {emptyAulas ? (
                <EmptyNote>Nada pendente — ainda não há aulas neste recorte.</EmptyNote>
              ) : pendentes > 0 ? (
                <>
                  <p className="mt-1 text-3xl font-semibold tabular-nums">{pendentes}</p>
                  <p className="mt-1 text-xs font-semibold">
                    {kpis.por_status.aprovado} aprovados · {kpis.por_status.reprovado}{' '}
                    reprovados — clique para filtrar a Lista
                  </p>
                </>
              ) : (
                <>
                  <p className="mt-1 text-3xl font-semibold tabular-nums">0</p>
                  <p className="mt-1 text-xs">Nenhuma aula pendente neste recorte.</p>
                </>
              )}
            </PulsoCard>
            <PulsoCard className="border-sky-200 bg-sky-50 text-sky-950" label="Professores no recorte">
              {emptyAulas ? (
                <EmptyNote>Nenhum professor com aula neste recorte ainda.</EmptyNote>
              ) : (
                <>
                  <p className="mt-1 text-3xl font-semibold tabular-nums">
                    {kpis.professores_ativos}
                  </p>
                  <p className="mt-1 text-xs text-sky-800/80">Contagem agregada, sem nomes.</p>
                </>
              )}
            </PulsoCard>
          </div>
        )}
      </BlockShell>

      <BlockShell
        tone="slate"
        kicker="Adoção de metodologia"
        title="Quais métodos a escola usou"
        hint="Agregado da unidade — as 39 metodologias do catálogo, sem identificar professor."
      >
        {emptyAulas ? (
          <EmptyNote>Nenhuma aula registrada neste recorte ainda.</EmptyNote>
        ) : metodologias.length === 0 ? (
          <EmptyNote>
            As aulas deste recorte ainda não têm metodologia identificada no espelho.
          </EmptyNote>
        ) : (
          <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
            {metodologias.map((m) => (
              <li key={m.nome} className="flex items-center gap-3">
                <p className="w-40 shrink-0 truncate text-sm font-medium text-ink" title={m.nome}>
                  {m.nome}
                </p>
                <div className="h-3 min-w-0 flex-1 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full ${colorMet(m.nome)}`}
                    style={{ width: `${Math.max(6, Math.round((100 * m.aulas) / maxMet))}%` }}
                  />
                </div>
                <p className="w-16 shrink-0 text-right text-sm font-semibold tabular-nums text-ink">
                  {m.aulas} aula{m.aulas === 1 ? '' : 's'}
                </p>
              </li>
            ))}
          </ul>
        )}
      </BlockShell>

      <BlockShell
        tone="emerald"
        kicker="Cobertura curricular"
        title="Temas BNCC já dados em aula"
        hint="Cruza o catálogo aprovado com o tema escolhido nas aulas do recorte."
      >
        {emptyAulas ? (
          <EmptyNote>Nenhuma aula registrada neste recorte ainda.</EmptyNote>
        ) : cobItens.length === 0 ? (
          <EmptyNote>
            {cobertura?.aulas_com_tema_bncc
              ? 'Há temas nas aulas, mas ainda sem par disciplina × ano no catálogo BNCC aprovado.'
              : 'As aulas deste recorte ainda não têm tema BNCC selecionado.'}
          </EmptyNote>
        ) : (
          <ul className="space-y-3">
            {cobItens.map((item) => (
              <li key={`${item.disciplina_nome}-${item.curso_ano}`}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-sm font-semibold text-emerald-950">
                    {item.disciplina_nome} {item.curso_ano}
                  </p>
                  <p className="text-xs font-medium text-emerald-800">
                    {item.temas_cobertos} de {item.temas_catalogo} temas cobertos ·{' '}
                    {item.percentual}%
                  </p>
                </div>
                <div className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-emerald-100">
                  <div
                    className={`h-full rounded-full ${coberturaBarClass(item.percentual)}`}
                    style={{ width: `${Math.max(item.percentual, item.temas_cobertos ? 4 : 0)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </BlockShell>

      <BlockShell
        tone="violet"
        kicker="Inclusão em ação"
        title="PEI que chegou à aula"
        hint="Alunos com PEI ativo que tiveram a adaptação AEE aplicada neste recorte."
      >
        {emptyAulas ? (
          <EmptyNote>
            Nenhuma aula registrada neste recorte ainda.
            {inc.alunos_pei_ativos > 0
              ? ` Há ${inc.alunos_pei_ativos} aluno${
                  inc.alunos_pei_ativos === 1 ? '' : 's'
                } com PEI ativo — a adaptação aparece aqui quando for aplicada em aula.`
              : ''}
          </EmptyNote>
        ) : inc.alunos_pei_ativos === 0 ? (
          <EmptyNote>Nenhum aluno com PEI ativo nesta unidade ainda.</EmptyNote>
        ) : (
          <div
            className={
              inc.alunos_com_adaptacao > 0
                ? 'rounded-xl border border-violet-300 bg-violet-100/70 p-4'
                : 'rounded-xl border border-amber-300 bg-amber-50 p-4'
            }
          >
            <p className="text-2xl font-semibold tracking-tight text-violet-950 sm:text-3xl">
              {inc.alunos_com_adaptacao} de {inc.alunos_pei_ativos} alunos com PEI
            </p>
            <p className="mt-1 text-sm text-violet-900">
              tiveram adaptação aplicada nas aulas deste recorte.
            </p>
            <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-violet-200/80">
              <div
                className={
                  inc.percentual > 0 ? 'h-full rounded-full bg-violet-600' : 'h-full bg-transparent'
                }
                style={{ width: `${inc.percentual}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-violet-800/80">
              {inc.aulas_com_adaptacao} aula
              {inc.aulas_com_adaptacao === 1 ? '' : 's'} com card AEE aplicado · sem identificar
              aluno ou professor nesta tela.
            </p>
          </div>
        )}
      </BlockShell>
    </div>
  )
}

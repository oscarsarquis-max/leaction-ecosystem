import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

const FEATURE_KEY = 'desempenho_professores_91'

function pad2(n) {
  return n < 10 ? `0${n}` : String(n)
}

function toISODate(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function startOfDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

function addDays(d, n) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  x.setDate(x.getDate() + n)
  return x
}

function startOfWeek(d) {
  const x = startOfDay(d)
  const day = x.getDay()
  const diff = day === 0 ? -6 : 1 - day
  return addDays(x, diff)
}

function formatarDataBR(iso) {
  const p = String(iso || '').slice(0, 10).split('-')
  if (p.length !== 3) return iso || '—'
  return `${p[2]}/${p[1]}/${p[0]}`
}

function PERIODOS() {
  return [
    { id: 'diario', label: 'Dia' },
    { id: 'semanal', label: 'Semana' },
    { id: 'quinzenal', label: 'Quinzena' },
    { id: 'mensal', label: 'Mês' },
    { id: 'anual', label: 'Ano' },
  ]
}

function resolverPeriodo(tipo, anchor) {
  const a = startOfDay(anchor || new Date())
  const y = a.getFullYear()
  const m = a.getMonth()
  if (tipo === 'diario') {
    return { data_inicio: toISODate(a), data_fim: toISODate(a), inicio: a, fim: a }
  }
  if (tipo === 'semanal') {
    const inicio = startOfWeek(a)
    const fim = addDays(inicio, 6)
    return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
  }
  if (tipo === 'quinzenal') {
    if (a.getDate() <= 15) {
      const inicio = new Date(y, m, 1)
      const fim = new Date(y, m, 15)
      return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
    }
    const inicio = new Date(y, m, 16)
    const fim = new Date(y, m + 1, 0)
    return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
  }
  if (tipo === 'anual') {
    const inicio = new Date(y, 0, 1)
    const fim = new Date(y, 12, 0)
    return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
  }
  const inicio = new Date(y, m, 1)
  const fim = new Date(y, m + 1, 0)
  return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
}

function shiftAnchor(tipo, anchor, delta) {
  const a = startOfDay(anchor)
  if (tipo === 'diario') return addDays(a, delta)
  if (tipo === 'semanal') return addDays(a, delta * 7)
  if (tipo === 'quinzenal') return addDays(a, delta * 15)
  if (tipo === 'anual') return new Date(a.getFullYear() + delta, a.getMonth(), 1)
  return new Date(a.getFullYear(), a.getMonth() + delta, 1)
}

function rotuloPeriodo(tipo, periodo) {
  const ini = formatarDataBR(periodo.data_inicio)
  const fim = formatarDataBR(periodo.data_fim)
  if (tipo === 'diario') return ini
  if (tipo === 'anual') return String(periodo.inicio.getFullYear())
  return `${ini} — ${fim}`
}

function capitalizeToken(s) {
  const t = String(s || '').trim()
  if (!t) return ''
  return t.charAt(0).toUpperCase() + t.slice(1).toLowerCase()
}

function professorDisplayName(emailOrName, idx = 0) {
  const raw = String(emailOrName || '').trim()
  if (!raw) return `Prof. ${idx + 1}`
  if (!raw.includes('@')) {
    const parts = raw.replace(/^Prof\.?\s*/i, '').split(/\s+/).filter(Boolean)
    if (parts.length >= 2) {
      return `Prof. ${capitalizeToken(parts[0])} ${capitalizeToken(parts[parts.length - 1])}`
    }
    if (parts.length === 1) return `Prof. ${capitalizeToken(parts[0])}`
    return `Prof. ${idx + 1}`
  }
  const local = raw.split('@')[0] || ''
  const parts = local.split(/[._+-]+/).filter(Boolean)
  if (parts.length >= 2) {
    return `Prof. ${capitalizeToken(parts[0])} ${capitalizeToken(parts[parts.length - 1])}`
  }
  if (parts.length === 1) return `Prof. ${capitalizeToken(parts[0])}`
  return `Prof. ${idx + 1}`
}

function formatWhen(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR')
  } catch {
    return iso
  }
}

function peiTexto(pei) {
  const alunos = Number(pei?.alunos_pei_nas_turmas || 0)
  const aulas = Number(pei?.aulas_com_adaptacao || 0)
  if (!alunos) return 'Sem aluno com PEI nas turmas deste recorte'
  if (!aulas) {
    return `${alunos} aluno(s) com PEI nas turmas · nenhuma adaptação aplicada neste recorte`
  }
  return `${alunos} aluno(s) com PEI nas turmas · ${aulas} aula(s) com adaptação`
}

function adesaoTexto(adesao) {
  const c = Number(adesao?.canonica || 0)
  const p = Number(adesao?.personalizada || 0)
  const s = Number(adesao?.sem_carimbo || 0)
  return `Canônico ${c} · Personalizado ${p} · Sem carimbo ${s}`
}

export default function DesempenhoProfessores() {
  const [tipoPeriodo, setTipoPeriodo] = useState('semanal')
  const [anchor, setAnchor] = useState(() => startOfDay(new Date()))
  const periodo = useMemo(
    () => resolverPeriodo(tipoPeriodo, anchor),
    [tipoPeriodo, anchor],
  )

  const [unidades, setUnidades] = useState([])
  const [unidadeId, setUnidadeId] = useState('')
  const [professorId, setProfessorId] = useState('')
  const [metodologia, setMetodologia] = useState('')
  const [payload, setPayload] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [feedbackAberto, setFeedbackAberto] = useState(false)
  const [feedbackTexto, setFeedbackTexto] = useState('')
  const [feedbackMsg, setFeedbackMsg] = useState('')
  const [feedbackBusy, setFeedbackBusy] = useState(false)
  const [feedbacks, setFeedbacks] = useState([])

  const selectClass =
    'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100'

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/pedagogico/unidades', { credentials: 'include' })
        const body = await res.json().catch(() => [])
        if (!res.ok) throw new Error(body.error || 'Não foi possível carregar as unidades')
        if (!cancelled) setUnidades(Array.isArray(body) ? body : [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Erro ao carregar unidades')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const q = new URLSearchParams({
          data_inicio: periodo.data_inicio,
          data_fim: periodo.data_fim,
        })
        if (unidadeId) q.set('unidade_id', unidadeId)
        const res = await fetch(`/api/pedagogico/desempenho-professores?${q}`, {
          credentials: 'include',
        })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Não foi possível carregar o desempenho')
        if (!cancelled) setPayload(body)
      } catch (err) {
        if (!cancelled) {
          setPayload(null)
          setError(err.message || 'Erro ao carregar')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [unidadeId, periodo.data_inicio, periodo.data_fim])

  const loadFeedbacks = async () => {
    const res = await fetch(
      `/api/pedagogico/feedback-features?feature_key=${encodeURIComponent(FEATURE_KEY)}`,
      { credentials: 'include' },
    )
    const body = await res.json().catch(() => ({}))
    if (res.ok) setFeedbacks(Array.isArray(body.itens) ? body.itens : [])
  }

  useEffect(() => {
    loadFeedbacks().catch(() => {})
  }, [])

  const professores = payload?.professores || []
  const metodologiasOpts = useMemo(() => {
    const set = new Set()
    for (const row of professores) {
      for (const nome of row.metodologias || []) {
        if (nome) set.add(nome)
      }
    }
    return [...set].sort((a, b) => a.localeCompare(b, 'pt-BR'))
  }, [professores])

  const linhas = useMemo(() => {
    return professores.filter((r) => {
      if (professorId && r.professor_vinculo_id !== professorId) return false
      if (metodologia && !(r.metodologias || []).includes(metodologia)) return false
      return true
    })
  }, [professores, professorId, metodologia])

  const enviarFeedback = async () => {
    const texto = feedbackTexto.trim()
    if (!texto) return
    setFeedbackBusy(true)
    setFeedbackMsg('')
    try {
      const res = await fetch('/api/pedagogico/feedback-features', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feature_key: FEATURE_KEY, texto }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error || 'Não foi possível registrar')
      setFeedbackTexto('')
      setFeedbackMsg('Opinião registrada. Obrigado — isso fica visível para o Oscar.')
      await loadFeedbacks()
    } catch (err) {
      setFeedbackMsg(err.message || 'Falha ao enviar')
    } finally {
      setFeedbackBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-[90rem] space-y-5">
      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <span className="inline-flex rounded-full border border-amber-400 bg-white px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-amber-800">
              Experimental — em avaliação no piloto
            </span>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
              Desempenho do professor
            </h1>
            <p className="mt-1 max-w-3xl text-sm text-muted">
              Componentes lado a lado, no mesmo recorte da Mesa de Som. Sem nota única e sem
              ranking — de propósito, para o gestor do piloto opinar antes de qualquer síntese.
            </p>
          </div>
          <Link
            to="/"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
          >
            Voltar ao Radar
          </Link>
        </div>
      </div>

      <section className="rounded-xl border border-sky-200 bg-white p-4 shadow-panel">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-sky-800">
            Mesa de som · Filtros
          </p>
          <p className="text-xs font-semibold text-ink">
            {rotuloPeriodo(tipoPeriodo, periodo)}
          </p>
        </div>
        <div className="grid gap-3 lg:grid-cols-12 lg:items-end">
          <label className="block lg:col-span-2">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Unidade
            </span>
            <select
              value={unidadeId}
              onChange={(e) => setUnidadeId(e.target.value)}
              className={selectClass}
            >
              <option value="">Todas</option>
              {unidades.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome}
                </option>
              ))}
            </select>
          </label>
          <label className="block lg:col-span-2">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Professor
            </span>
            <select
              value={professorId}
              onChange={(e) => setProfessorId(e.target.value)}
              className={selectClass}
            >
              <option value="">Todos</option>
              {professores.map((p, idx) => (
                <option key={p.professor_vinculo_id} value={p.professor_vinculo_id}>
                  {professorDisplayName(p.professor_nome || p.professor_email, idx)}
                </option>
              ))}
            </select>
          </label>
          <label className="block lg:col-span-2">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Metodologia
            </span>
            <select
              value={metodologia}
              onChange={(e) => setMetodologia(e.target.value)}
              className={selectClass}
            >
              <option value="">Todas</option>
              {metodologiasOpts.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <div className="lg:col-span-4">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Período
            </span>
            <div className="flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-white p-1">
              {PERIODOS().map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setTipoPeriodo(p.id)}
                  className={[
                    'flex-1 rounded-md px-2 py-1.5 text-xs font-semibold transition sm:text-sm',
                    tipoPeriodo === p.id
                      ? 'bg-school-700 text-white'
                      : 'text-muted hover:bg-school-50 hover:text-ink',
                  ].join(' ')}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <label className="block lg:col-span-2">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Data base
            </span>
            <input
              type="date"
              value={toISODate(anchor)}
              onChange={(e) => {
                if (!e.target.value) return
                const [y, m, d] = e.target.value.split('-').map(Number)
                setAnchor(startOfDay(new Date(y, m - 1, d)))
              }}
              className={selectClass}
            />
          </label>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setAnchor((a) => shiftAnchor(tipoPeriodo, a, -1))}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-ink hover:bg-school-50"
          >
            ‹
          </button>
          <button
            type="button"
            onClick={() => setAnchor((a) => shiftAnchor(tipoPeriodo, a, 1))}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-ink hover:bg-school-50"
          >
            ›
          </button>
        </div>
      </section>

      {error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-ink">Por professor · ordem alfabética</h2>
          <p className="mt-0.5 text-xs text-muted">
            Lista lado a lado. Não há ranking nem nota consolidada nesta rodada.
          </p>
        </div>
        {loading ? (
          <p className="px-4 py-8 text-sm text-muted">Carregando…</p>
        ) : linhas.length === 0 ? (
          <p className="px-4 py-8 text-sm text-muted">
            Nenhuma aula neste recorte. No piloto da Escola Teste, tente data base 04/09/2026
            (semana 31/08–06/09).
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-2">Professor</th>
                  <th className="px-4 py-2">Aulas planejadas</th>
                  <th className="px-4 py-2">Metodologias</th>
                  <th className="px-4 py-2">Adesão ao padrão</th>
                  <th className="px-4 py-2">Curadoria</th>
                  <th className="px-4 py-2">PEI / AEE</th>
                </tr>
              </thead>
              <tbody>
                {linhas.map((row, idx) => (
                  <tr key={row.professor_vinculo_id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-semibold text-ink">
                      {professorDisplayName(row.professor_nome || row.professor_email, idx)}
                    </td>
                    <td className="px-4 py-3 text-ink">
                      {row.aulas_total} no recorte
                      <span className="mt-0.5 block text-xs text-muted">
                        Dia a Dia {row.aulas_dia_a_dia} · Desafio {row.aulas_desafio}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-ink">
                      {row.metodologias_distintas} distinta(s)
                      <span className="mt-0.5 block text-xs text-muted">
                        {(row.metodologias || []).join(', ') || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-ink">{adesaoTexto(row.adesao)}</td>
                    <td className="px-4 py-3 text-ink">
                      {row.curadoria_enviadas} sugestão(ões)
                    </td>
                    <td className="px-4 py-3 text-ink">{peiTexto(row.pei)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-panel">
        <button
          type="button"
          onClick={() => setFeedbackAberto((v) => !v)}
          className="text-sm font-semibold text-school-700 hover:underline"
        >
          O que você acha dessa visão?
        </button>
        {feedbackAberto ? (
          <div className="mt-3 space-y-2">
            <textarea
              value={feedbackTexto}
              onChange={(e) => setFeedbackTexto(e.target.value)}
              rows={4}
              placeholder="Escreva livremente: o que ajuda, o que falta, o que não deveria existir…"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-ink outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
            />
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={feedbackBusy || !feedbackTexto.trim()}
                onClick={() => enviarFeedback()}
                className="rounded-lg bg-school-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {feedbackBusy ? 'Enviando…' : 'Enviar opinião'}
              </button>
              {feedbackMsg ? (
                <span className="text-sm text-muted">{feedbackMsg}</span>
              ) : null}
            </div>
          </div>
        ) : null}

        {feedbacks.length ? (
          <div className="mt-4 border-t border-slate-100 pt-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-muted">
              Opiniões já registradas nesta instituição
            </p>
            <ul className="mt-2 space-y-2">
              {feedbacks.slice(0, 8).map((item) => (
                <li key={item.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-ink">
                  <p>{item.texto}</p>
                  <p className="mt-1 text-[11px] text-muted">
                    {item.gestor_nome || 'Gestor'} · {formatWhen(item.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    </div>
  )
}

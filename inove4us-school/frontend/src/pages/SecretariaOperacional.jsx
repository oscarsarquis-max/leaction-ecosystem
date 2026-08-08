import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../lib/auth'
import { tabClassNameCompact } from '../lib/tabs'
import MonthAgendaCalendar from '../components/MonthAgendaCalendar'

/**
 * Secretaria Acadêmica v2 — 6 abas:
 * Unidades · Estrutura · Alunos · Calendário · Mural · Planejamento Escolar
 */

const TABS = [
  { id: 'unidades', label: 'Unidades' },
  { id: 'estrutura', label: 'Estrutura Acadêmica' },
  { id: 'alunos', label: 'Alunos' },
  { id: 'calendario', label: 'Calendário' },
  { id: 'comunicacoes', label: 'Mural / Comunicações' },
  { id: 'planejamento', label: 'Planejamento Escolar' },
]

const PLAN_TIPOS = [
  { value: 'aula', label: 'Aula' },
  { value: 'evento', label: 'Evento' },
]

const PLAN_STATUS_LABEL = {
  rascunho: 'Rascunho',
  enviado: 'Enviado',
  erro: 'Erro',
}

const PLAN_STATUS_CLASS = {
  rascunho: 'bg-sky-50 text-sky-800',
  enviado: 'bg-emerald-50 text-emerald-800',
  erro: 'bg-red-50 text-red-700',
}

const TIPOS_PERIODO = [
  { value: 'anual', label: 'Anual' },
  { value: 'semestral', label: 'Semestral' },
  { value: 'trimestral', label: 'Trimestral' },
  { value: 'modular', label: 'Modular' },
]

const TURNOS = [
  { value: 'manha', label: 'Manhã' },
  { value: 'tarde', label: 'Tarde' },
  { value: 'integral', label: 'Integral' },
  { value: 'noite', label: 'Noite' },
]

const CAL_TIPOS = [
  { value: 'letivo', label: 'Dia letivo', tone: 'emerald' },
  { value: 'feriado', label: 'Feriado', tone: 'rose' },
  { value: 'avaliacao', label: 'Avaliação', tone: 'amber' },
  { value: 'evento', label: 'Evento', tone: 'sky' },
]

const COM_TIPOS = [
  { value: 'reuniao_pedagogica', label: 'Reunião pedagógica' },
  { value: 'evento_escolar', label: 'Evento escolar' },
]

const COM_PUBLICOS = [
  { value: 'professores', label: 'Professores' },
  { value: 'toda_instituicao', label: 'Toda a instituição' },
  { value: 'unidade', label: 'Unidade' },
]

const TURNO_LABEL = Object.fromEntries(TURNOS.map((t) => [t.value, t.label]))
const CAL_TIPO_LABEL = Object.fromEntries(CAL_TIPOS.map((t) => [t.value, t.label]))
const CAL_TIPO_TONE = Object.fromEntries(CAL_TIPOS.map((t) => [t.value, t.tone]))
const COM_TIPO_LABEL = Object.fromEntries(COM_TIPOS.map((t) => [t.value, t.label]))
const COM_PUBLICO_LABEL = Object.fromEntries(COM_PUBLICOS.map((t) => [t.value, t.label]))

function Modal({ title, open, onClose, children, wide }) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className={[
          'max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-xl',
          wide ? 'max-w-2xl' : 'max-w-lg',
        ].join(' ')}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-lg font-semibold text-ink">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-2.5 py-1 text-sm text-slate-600 hover:bg-slate-50"
          >
            Fechar
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
        {label}
      </span>
      {children}
    </label>
  )
}

const inputCls =
  'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100'
const btnPrimary =
  'rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60'
const btnGhost =
  'rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-ink hover:bg-slate-50 disabled:opacity-60'
const btnDanger =
  'rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 disabled:opacity-60'
const btnSmall =
  'rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-ink hover:bg-slate-50 disabled:opacity-60'

function InactiveBadge() {
  return (
    <span className="ml-2 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
      Inativo
    </span>
  )
}

function StatusBadge({ status }) {
  const map = {
    agendado: 'bg-sky-50 text-sky-800',
    publicado: 'bg-emerald-50 text-emerald-800',
    cancelado: 'bg-slate-100 text-slate-600',
  }
  const label = {
    agendado: 'Agendado',
    publicado: 'Publicado',
    cancelado: 'Cancelado',
  }
  return (
    <span
      className={[
        'inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
        map[status] || 'bg-slate-100 text-slate-600',
      ].join(' ')}
    >
      {label[status] || status || '—'}
    </span>
  )
}

function TipoBadge({ tipo }) {
  const isReuniao = tipo === 'reuniao_pedagogica'
  return (
    <span
      className={[
        'inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
        isReuniao ? 'bg-violet-50 text-violet-800' : 'bg-amber-50 text-amber-800',
      ].join(' ')}
    >
      {COM_TIPO_LABEL[tipo] || tipo || '—'}
    </span>
  )
}

async function apiJson(url, options = {}) {
  const res = await fetch(url, { credentials: 'include', ...options })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Falha na requisição')
  return data
}

function eachDateInclusive(startIso, endIso) {
  const start = String(startIso || '').slice(0, 10)
  const end = String(endIso || start).slice(0, 10)
  if (!start) return []
  const out = []
  const cur = new Date(`${start}T12:00:00`)
  const last = new Date(`${end}T12:00:00`)
  if (Number.isNaN(cur.getTime())) return []
  while (cur <= last) {
    const y = cur.getFullYear()
    const m = String(cur.getMonth() + 1).padStart(2, '0')
    const d = String(cur.getDate()).padStart(2, '0')
    out.push(`${y}-${m}-${d}`)
    cur.setDate(cur.getDate() + 1)
  }
  return out
}

const EMPTY = {
  unidade: { nome: '', endereco: '', codigo: '', cidade: '', uf: '' },
  periodo: {
    nome: '',
    data_inicio: '',
    data_fim: '',
    ano_letivo: new Date().getFullYear(),
    tipo_periodo: 'semestral',
    unidade_id: '',
  },
  curso: { nome: '' },
  disciplina: { nome: '', ementa_macro: '', carga_horaria: '', curso_id: '' },
  turma: {
    nome: '',
    serie_ano: '',
    turno: 'manha',
    unidade_id: '',
    curso_id: '',
    periodo_letivo_id: '',
  },
  aluno: { nome: '', matricula: '', turma_id: '', data_nascimento: '' },
  calendario: {
    titulo: '',
    tipo: 'letivo',
    data_inicio: '',
    data_fim: '',
    unidade_id: '',
  },
  aloc: { disciplina_id: '', professor_id: '' },
  com: {
    titulo: '',
    descricao: '',
    tipo: 'reuniao_pedagogica',
    publico_alvo: 'professores',
    data_hora_inicio: '',
    data_hora_fim: '',
    unidade_id: '',
  },
  plan: {
    turma_id: '',
    disciplina_id: '',
    titulo: '',
    tipo: 'aula',
    data: '',
    hora_inicio: '',
    hora_fim: '',
    observacoes: '',
    item_pai_id: '',
  },
}

export default function SecretariaOperacional() {
  const { user } = useAuth()
  const [tab, setTab] = useState('estrutura')
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  const [unidades, setUnidades] = useState([])
  const [periodos, setPeriodos] = useState([])
  const [cursos, setCursos] = useState([])
  const [disciplinas, setDisciplinas] = useState([])
  const [turmas, setTurmas] = useState([])
  const [alunos, setAlunos] = useState([])
  const [calendario, setCalendario] = useState([])
  const [alocacoes, setAlocacoes] = useState([])
  const [professores, setProfessores] = useState([])
  const [comunicacoes, setComunicacoes] = useState([])
  const [planejamento, setPlanejamento] = useState([])

  const [periodoSel, setPeriodoSel] = useState('')
  const [cursoSel, setCursoSel] = useState('')
  const [turmaSel, setTurmaSel] = useState('')
  const [filtroTurmaId, setFiltroTurmaId] = useState('')
  const [filtroPlanTurmaId, setFiltroPlanTurmaId] = useState('')
  const [planSelected, setPlanSelected] = useState([])
  const [planRelatorio, setPlanRelatorio] = useState(null)

  const [calYear, setCalYear] = useState(() => new Date().getFullYear())
  const [calMonth, setCalMonth] = useState(() => new Date().getMonth())
  const [calDay, setCalDay] = useState('')

  const [modal, setModal] = useState(null)
  const [editId, setEditId] = useState(null)
  const [context, setContext] = useState({})

  const [formUnidade, setFormUnidade] = useState(EMPTY.unidade)
  const [formPeriodo, setFormPeriodo] = useState(EMPTY.periodo)
  const [formCurso, setFormCurso] = useState(EMPTY.curso)
  const [formDisc, setFormDisc] = useState(EMPTY.disciplina)
  const [formTurma, setFormTurma] = useState(EMPTY.turma)
  const [formAluno, setFormAluno] = useState(EMPTY.aluno)
  const [formCal, setFormCal] = useState(EMPTY.calendario)
  const [formAloc, setFormAloc] = useState(EMPTY.aloc)
  const [formCom, setFormCom] = useState(EMPTY.com)
  const [formPlan, setFormPlan] = useState(EMPTY.plan)

  const escola = useMemo(
    () => user?.instituicao_nome || user?.nome || 'Instituição',
    [user],
  )

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [u, p, c, d, t, a, cal, aloc, pr, co, pl] = await Promise.all([
        fetch('/api/secretaria/unidades', { credentials: 'include' }),
        fetch('/api/secretaria/periodos', { credentials: 'include' }),
        fetch('/api/secretaria/cursos', { credentials: 'include' }),
        fetch('/api/secretaria/disciplinas', { credentials: 'include' }),
        fetch('/api/secretaria/turmas', { credentials: 'include' }),
        fetch('/api/secretaria/alunos', { credentials: 'include' }),
        fetch('/api/secretaria/calendario', { credentials: 'include' }),
        fetch('/api/secretaria/alocacoes', { credentials: 'include' }),
        fetch('/api/secretaria/professores', { credentials: 'include' }),
        fetch('/api/secretaria/comunicacoes', { credentials: 'include' }),
        fetch('/api/secretaria/planejamento', { credentials: 'include' }),
      ])
      const ju = await u.json().catch(() => ({}))
      const jp = await p.json().catch(() => ({}))
      const jc = await c.json().catch(() => ({}))
      const jd = await d.json().catch(() => ({}))
      const jt = await t.json().catch(() => ({}))
      const ja = await a.json().catch(() => ({}))
      const jcal = await cal.json().catch(() => ({}))
      const jaloc = await aloc.json().catch(() => ({}))
      const jpr = await pr.json().catch(() => ({}))
      const jco = await co.json().catch(() => ({}))
      const jpl = await pl.json().catch(() => ({}))

      if (!u.ok) throw new Error(ju.error || 'Falha ao carregar unidades')
      if (!p.ok) throw new Error(jp.error || 'Falha ao carregar períodos')
      if (!c.ok) throw new Error(jc.error || 'Falha ao carregar cursos')
      if (!d.ok) throw new Error(jd.error || 'Falha ao carregar disciplinas')
      if (!t.ok) throw new Error(jt.error || 'Falha ao carregar turmas')
      if (!a.ok) throw new Error(ja.error || 'Falha ao carregar alunos')
      if (!cal.ok) throw new Error(jcal.error || 'Falha ao carregar calendário')
      if (!aloc.ok) throw new Error(jaloc.error || 'Falha ao carregar alocações')
      if (!pr.ok) throw new Error(jpr.error || 'Falha ao carregar professores')
      if (!pl.ok) throw new Error(jpl.error || 'Falha ao carregar planejamento')

      setUnidades(ju.items || [])
      setPeriodos(jp.items || [])
      setCursos(jc.items || [])
      setDisciplinas(jd.items || [])
      setTurmas(jt.items || [])
      setAlunos(ja.items || [])
      setCalendario(jcal.items || [])
      setAlocacoes(jaloc.items || [])
      setProfessores(jpr.items || [])
      setComunicacoes(co.ok ? jco.items || [] : [])
      setPlanejamento(jpl.items || [])
    } catch (err) {
      setError(err.message || 'Erro ao carregar Secretaria Acadêmica')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  useEffect(() => {
    if (!periodoSel && periodos.length) {
      const ativo = periodos.find((p) => p.ativo) || periodos[0]
      setPeriodoSel(ativo.id)
    }
  }, [periodos, periodoSel])

  useEffect(() => {
    setCursoSel('')
    setTurmaSel('')
  }, [periodoSel])

  const alunosFiltrados = useMemo(() => {
    if (!filtroTurmaId) return alunos
    return alunos.filter((a) => a.turma_id === filtroTurmaId)
  }, [alunos, filtroTurmaId])

  const cursosDoPeriodo = useMemo(
    () => cursos.filter((c) => c.periodo_letivo_id === periodoSel),
    [cursos, periodoSel],
  )

  const turmasSemCurso = useMemo(
    () =>
      turmas.filter(
        (t) => t.periodo_letivo_id === periodoSel && !t.curso_id && t.ativa !== false,
      ),
    [turmas, periodoSel],
  )

  const discsSemCurso = useMemo(
    () => disciplinas.filter((d) => !d.curso_id && d.ativo !== false),
    [disciplinas],
  )

  const comunicacoesOrdenadas = useMemo(
    () =>
      [...comunicacoes].sort((a, b) =>
        String(b.data_hora_inicio || '').localeCompare(String(a.data_hora_inicio || '')),
      ),
    [comunicacoes],
  )

  const planejamentoFiltrado = useMemo(() => {
    const list = filtroPlanTurmaId
      ? planejamento.filter((p) => p.turma_id === filtroPlanTurmaId)
      : planejamento
    return [...list].sort((a, b) =>
      String(a.data || '').localeCompare(String(b.data || '')),
    )
  }, [planejamento, filtroPlanTurmaId])

  const discsAlocadasTurma = useMemo(() => {
    const tid = formPlan.turma_id
    if (!tid) return []
    const ids = new Set(
      alocacoes
        .filter((a) => a.turma_id === tid && a.ativo !== false)
        .map((a) => a.disciplina_id),
    )
    return disciplinas.filter((d) => ids.has(d.id))
  }, [formPlan.turma_id, alocacoes, disciplinas])

  const itensPaiOpcoes = useMemo(() => {
    const tid = formPlan.turma_id
    if (!tid) return []
    return planejamento.filter(
      (p) => p.turma_id === tid && (!editId || p.id !== editId),
    )
  }, [planejamento, formPlan.turma_id, editId])

  const dayMarkers = useMemo(() => {
    const map = {}
    calendario.forEach((ev) => {
      eachDateInclusive(ev.data_inicio, ev.data_fim || ev.data_inicio).forEach((iso) => {
        if (!map[iso]) map[iso] = []
        map[iso].push({
          id: ev.id,
          tone: CAL_TIPO_TONE[ev.tipo] || 'slate',
          title: ev.titulo,
        })
      })
    })
    return map
  }, [calendario])

  const eventosDoDia = useMemo(() => {
    if (!calDay) return []
    return calendario.filter((ev) =>
      eachDateInclusive(ev.data_inicio, ev.data_fim || ev.data_inicio).includes(calDay),
    )
  }, [calendario, calDay])

  function clearMessages() {
    setFeedback('')
    setError('')
  }

  function switchTab(id) {
    setTab(id)
    clearMessages()
  }

  function closeModal() {
    setModal(null)
    setEditId(null)
    setContext({})
  }

  async function runBusy(fn) {
    setBusy(true)
    setError('')
    try {
      await fn()
    } catch (err) {
      setError(err.message || 'Operação falhou')
    } finally {
      setBusy(false)
    }
  }

  function openPeriodo(item) {
    clearMessages()
    if (item) {
      setEditId(item.id)
      setFormPeriodo({
        nome: item.nome || '',
        data_inicio: item.data_inicio || '',
        data_fim: item.data_fim || '',
        ano_letivo: item.ano_letivo ?? new Date().getFullYear(),
        tipo_periodo: item.tipo_periodo || 'semestral',
        unidade_id: item.unidade_id || '',
      })
    } else {
      setEditId(null)
      setFormPeriodo(EMPTY.periodo)
    }
    setModal('periodo')
  }

  function openCurso(item) {
    clearMessages()
    if (item) {
      setEditId(item.id)
      setFormCurso({ nome: item.nome || '' })
    } else {
      setEditId(null)
      setFormCurso(EMPTY.curso)
    }
    setContext({ periodo_letivo_id: periodoSel })
    setModal('curso')
  }

  function openDisc({ item, cursoId }) {
    clearMessages()
    if (item) {
      setEditId(item.id)
      setFormDisc({
        nome: item.nome || '',
        ementa_macro: item.ementa_macro || '',
        carga_horaria: item.carga_horaria != null ? String(item.carga_horaria) : '',
        curso_id: item.curso_id || cursoId || '',
      })
    } else {
      setEditId(null)
      setFormDisc({
        ...EMPTY.disciplina,
        curso_id: cursoId || '',
      })
    }
    setContext({ curso_id: cursoId || '' })
    setModal('disciplina')
  }

  function openTurma({ item, cursoId }) {
    clearMessages()
    const periodo = periodos.find((p) => p.id === periodoSel)
    if (item) {
      setEditId(item.id)
      setFormTurma({
        nome: item.nome || '',
        serie_ano: item.serie_ano || '',
        turno: item.turno || 'manha',
        unidade_id: item.unidade_id || '',
        curso_id: item.curso_id || cursoId || '',
        periodo_letivo_id: item.periodo_letivo_id || periodoSel,
      })
    } else {
      setEditId(null)
      setFormTurma({
        ...EMPTY.turma,
        unidade_id: unidades[0]?.id || '',
        curso_id: cursoId || '',
        periodo_letivo_id: periodoSel,
        ano_sugerido: periodo?.ano_letivo || new Date().getFullYear(),
      })
    }
    setContext({ curso_id: cursoId || '', periodo_letivo_id: periodoSel })
    setModal('turma')
  }

  function openAloc(turma) {
    clearMessages()
    setEditId(null)
    setFormAloc(EMPTY.aloc)
    setContext({ turma })
    setModal('aloc')
  }

  function openCal(iso, item) {
    clearMessages()
    if (item) {
      setEditId(item.id)
      setFormCal({
        titulo: item.titulo || '',
        tipo: item.tipo || 'letivo',
        data_inicio: item.data_inicio || iso || '',
        data_fim: item.data_fim || '',
        unidade_id: item.unidade_id || '',
      })
    } else {
      setEditId(null)
      setFormCal({
        ...EMPTY.calendario,
        data_inicio: iso || '',
        data_fim: iso || '',
      })
    }
    setModal('calendario')
  }

  async function saveUnidade(e) {
    e.preventDefault()
    await runBusy(async () => {
      const body = {
        nome: formUnidade.nome,
        endereco: formUnidade.endereco || null,
        codigo: formUnidade.codigo || null,
        cidade: formUnidade.cidade || null,
        uf: formUnidade.uf || null,
      }
      if (editId) {
        await apiJson(`/api/secretaria/unidades/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Unidade atualizada.')
      } else {
        await apiJson('/api/secretaria/unidades', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Unidade criada.')
      }
      closeModal()
      await loadAll()
    })
  }

  async function savePeriodo(e) {
    e.preventDefault()
    await runBusy(async () => {
      const body = {
        nome: formPeriodo.nome,
        data_inicio: formPeriodo.data_inicio,
        data_fim: formPeriodo.data_fim,
        ano_letivo: Number(formPeriodo.ano_letivo),
        tipo_periodo: formPeriodo.tipo_periodo,
        unidade_id: formPeriodo.unidade_id || null,
      }
      if (editId) {
        await apiJson(`/api/secretaria/periodos/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Período atualizado.')
      } else {
        const res = await apiJson('/api/secretaria/periodos', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Período criado.')
        if (res.item?.id) setPeriodoSel(res.item.id)
      }
      closeModal()
      await loadAll()
    })
  }

  async function toggleAtivo(kind, item, field = 'ativo') {
    const next = !item[field]
    const urls = {
      unidade: `/api/secretaria/unidades/${item.id}`,
      periodo: `/api/secretaria/periodos/${item.id}`,
      curso: `/api/secretaria/cursos/${item.id}`,
      disciplina: `/api/secretaria/disciplinas/${item.id}`,
      turma: `/api/secretaria/turmas/${item.id}`,
      aluno: `/api/secretaria/alunos/${item.id}`,
    }
    const bodyKey = kind === 'turma' ? 'ativa' : 'ativo'
    await runBusy(async () => {
      await apiJson(urls[kind], {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [bodyKey]: next }),
      })
      setFeedback(next ? 'Reativado.' : 'Desativado.')
      await loadAll()
    })
  }

  async function saveCurso(e) {
    e.preventDefault()
    await runBusy(async () => {
      const body = {
        nome: formCurso.nome,
        periodo_letivo_id: context.periodo_letivo_id || periodoSel,
      }
      if (editId) {
        await apiJson(`/api/secretaria/cursos/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nome: formCurso.nome }),
        })
        setFeedback('Curso atualizado.')
      } else {
        const res = await apiJson('/api/secretaria/cursos', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Curso criado.')
        if (res.item?.id) setCursoSel(res.item.id)
      }
      closeModal()
      await loadAll()
    })
  }

  async function saveDisc(e) {
    e.preventDefault()
    await runBusy(async () => {
      const body = {
        nome: formDisc.nome,
        ementa_macro: formDisc.ementa_macro || null,
        carga_horaria: formDisc.carga_horaria ? Number(formDisc.carga_horaria) : null,
        curso_id: formDisc.curso_id || null,
      }
      if (editId) {
        await apiJson(`/api/secretaria/disciplinas/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Disciplina atualizada.')
      } else {
        await apiJson('/api/secretaria/disciplinas', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Disciplina criada.')
      }
      closeModal()
      await loadAll()
    })
  }

  async function saveTurma(e) {
    e.preventDefault()
    await runBusy(async () => {
      const periodo = periodos.find(
        (p) => p.id === (formTurma.periodo_letivo_id || periodoSel),
      )
      const body = {
        nome: formTurma.nome,
        serie_ano: formTurma.serie_ano,
        turno: formTurma.turno,
        unidade_id: formTurma.unidade_id,
        periodo_letivo_id: formTurma.periodo_letivo_id || periodoSel,
        curso_id: formTurma.curso_id || null,
        ano_letivo: periodo?.ano_letivo || new Date().getFullYear(),
      }
      if (editId) {
        await apiJson(`/api/secretaria/turmas/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Turma atualizada.')
      } else {
        const res = await apiJson('/api/secretaria/turmas', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Turma criada.')
        if (res.item?.id) setTurmaSel(res.item.id)
      }
      closeModal()
      await loadAll()
    })
  }

  async function saveAluno(e) {
    e.preventDefault()
    await runBusy(async () => {
      const body = {
        nome: formAluno.nome,
        matricula: formAluno.matricula,
        turma_id: formAluno.turma_id || null,
        data_nascimento: formAluno.data_nascimento || null,
      }
      if (editId) {
        await apiJson(`/api/secretaria/alunos/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Aluno atualizado.')
      } else {
        await apiJson('/api/secretaria/alunos', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Aluno criado.')
      }
      closeModal()
      await loadAll()
    })
  }

  async function saveCal(e) {
    e.preventDefault()
    await runBusy(async () => {
      const body = {
        titulo: formCal.titulo,
        tipo: formCal.tipo,
        data_inicio: formCal.data_inicio,
        data_fim: formCal.data_fim || null,
        unidade_id: formCal.unidade_id || null,
      }
      if (editId) {
        await apiJson(`/api/secretaria/calendario/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Evento atualizado.')
      } else {
        await apiJson('/api/secretaria/calendario', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Evento criado.')
      }
      closeModal()
      await loadAll()
    })
  }

  async function deleteCal(item) {
    if (!window.confirm(`Excluir o evento "${item.titulo}"?`)) return
    await runBusy(async () => {
      await apiJson(`/api/secretaria/calendario/${item.id}`, { method: 'DELETE' })
      setFeedback('Evento excluído.')
      closeModal()
      await loadAll()
    })
  }

  async function saveAloc(e) {
    e.preventDefault()
    const turma = context.turma
    if (!turma) return
    await runBusy(async () => {
      await apiJson('/api/secretaria/alocacoes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          unidade_id: turma.unidade_id,
          periodo_id: turma.periodo_letivo_id,
          disciplina_id: formAloc.disciplina_id,
          professor_id: formAloc.professor_id,
          turma_id: turma.id,
        }),
      })
      setFeedback('Professor alocado à turma.')
      closeModal()
      await loadAll()
    })
  }

  async function saveCom(e) {
    e.preventDefault()
    await runBusy(async () => {
      await apiJson('/api/secretaria/comunicacoes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titulo: formCom.titulo,
          descricao: formCom.descricao || null,
          tipo: formCom.tipo,
          publico_alvo: formCom.publico_alvo,
          data_hora_inicio: formCom.data_hora_inicio,
          data_hora_fim: formCom.data_hora_fim || null,
          unidade_id: formCom.unidade_id || null,
          status: 'publicado',
        }),
      })
      setFeedback('Comunicado publicado.')
      closeModal()
      await loadAll()
    })
  }

  async function cancelarComunicacao(item) {
    if (!window.confirm(`Cancelar o comunicado "${item.titulo}"?`)) return
    await runBusy(async () => {
      await apiJson(`/api/secretaria/comunicacoes/${item.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'cancelado' }),
      })
      setFeedback('Comunicado cancelado.')
      await loadAll()
    })
  }

  function openPlan(item) {
    clearMessages()
    setPlanRelatorio(null)
    if (item) {
      if (item.status_push !== 'rascunho') {
        setError('Itens já enviados não podem ser editados.')
        return
      }
      setEditId(item.id)
      setFormPlan({
        turma_id: item.turma_id || '',
        disciplina_id: item.disciplina_id || '',
        titulo: item.titulo || '',
        tipo: item.tipo || 'aula',
        data: item.data || '',
        hora_inicio: item.hora_inicio || '',
        hora_fim: item.hora_fim || '',
        observacoes: item.observacoes || '',
        item_pai_id: item.item_pai_id || '',
      })
    } else {
      setEditId(null)
      setFormPlan({
        ...EMPTY.plan,
        turma_id: filtroPlanTurmaId || '',
      })
    }
    setModal('planejamento')
  }

  async function savePlan(e) {
    e.preventDefault()
    await runBusy(async () => {
      const body = {
        turma_id: formPlan.turma_id,
        disciplina_id: formPlan.disciplina_id,
        titulo: formPlan.titulo,
        tipo: formPlan.tipo,
        data: formPlan.data,
        hora_inicio: formPlan.hora_inicio || null,
        hora_fim: formPlan.hora_fim || null,
        observacoes: formPlan.observacoes || null,
        item_pai_id: formPlan.item_pai_id || null,
      }
      if (editId) {
        await apiJson(`/api/secretaria/planejamento/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Item de planejamento atualizado.')
      } else {
        await apiJson('/api/secretaria/planejamento', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        setFeedback('Item de planejamento criado.')
      }
      closeModal()
      await loadAll()
    })
  }

  async function deletePlan(item) {
    if (item.status_push !== 'rascunho') return
    if (!window.confirm(`Excluir o rascunho "${item.titulo}"?`)) return
    await runBusy(async () => {
      await apiJson(`/api/secretaria/planejamento/${item.id}`, { method: 'DELETE' })
      setFeedback('Rascunho excluído.')
      setPlanSelected((ids) => ids.filter((id) => id !== item.id))
      await loadAll()
    })
  }

  function togglePlanSelect(id) {
    setPlanSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  function togglePlanSelectAll() {
    const elegiveis = planejamentoFiltrado
      .filter((p) => p.status_push === 'rascunho' || p.status_push === 'erro')
      .map((p) => p.id)
    const allOn = elegiveis.length > 0 && elegiveis.every((id) => planSelected.includes(id))
    setPlanSelected(allOn ? [] : elegiveis)
  }

  async function enviarPlanejamento() {
    if (planSelected.length === 0) {
      setError('Selecione ao menos um item em rascunho (ou com erro) para enviar.')
      return
    }
    if (!window.confirm(`Enviar ${planSelected.length} item(ns) pro Inove?`)) return
    await runBusy(async () => {
      const res = await apiJson('/api/secretaria/planejamento/enviar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: planSelected }),
      })
      setPlanRelatorio(res)
      setPlanSelected([])
      setFeedback(
        `Envio concluído: ${res.enviados || 0} sucesso, ${res.erros || 0} erro(s).`,
      )
      await loadAll()
    })
  }

  function discsForCurso(cursoId) {
    return disciplinas.filter((d) => d.curso_id === cursoId)
  }

  function turmasForCurso(cursoId) {
    return turmas.filter((t) => t.curso_id === cursoId)
  }

  function alocacoesForTurma(turmaId) {
    return alocacoes.filter((a) => a.turma_id === turmaId && a.ativo !== false)
  }

  function discsForAloc(turma) {
    if (!turma) return []
    if (turma.curso_id) return discsForCurso(turma.curso_id)
    return [
      ...discsSemCurso,
      ...disciplinas.filter((d) => {
        const curso = cursos.find((c) => c.id === d.curso_id)
        return curso?.periodo_letivo_id === turma.periodo_letivo_id
      }),
    ]
  }

  function renderTurmaBlock(turma, { showCursoHint } = {}) {
    const expanded = turmaSel === turma.id
    const alocs = alocacoesForTurma(turma.id)
    return (
      <div
        key={turma.id}
        className={[
          'rounded-xl border bg-white',
          expanded ? 'border-violet-300 shadow-sm' : 'border-slate-200',
          turma.ativa === false ? 'opacity-60' : '',
        ].join(' ')}
      >
        <button
          type="button"
          className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left"
          onClick={() => setTurmaSel(expanded ? '' : turma.id)}
        >
          <div>
            <p className="text-sm font-semibold text-ink">
              {turma.nome}
              {turma.ativa === false ? <InactiveBadge /> : null}
            </p>
            <p className="text-xs text-muted">
              {turma.serie_ano} · {TURNO_LABEL[turma.turno] || turma.turno} ·{' '}
              {turma.unidade_nome || '—'}
              {showCursoHint && !turma.curso_id ? ' · Sem curso' : ''}
            </p>
          </div>
          <span className="text-xs font-bold text-muted">{expanded ? '▾' : '▸'}</span>
        </button>
        {expanded ? (
          <div className="border-t border-slate-100 px-3 py-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-xs font-bold uppercase tracking-wide text-muted">
                Alocação docente
              </p>
              <div className="flex flex-wrap gap-2">
                <button type="button" className={btnSmall} onClick={() => openTurma({ item: turma, cursoId: turma.curso_id })}>
                  Editar turma
                </button>
                <button
                  type="button"
                  className={btnSmall}
                  onClick={() => toggleAtivo('turma', turma, 'ativa')}
                >
                  {turma.ativa === false ? 'Reativar' : 'Desativar'}
                </button>
                <button type="button" className={btnSmall} onClick={() => openAloc(turma)}>
                  + Alocar professor
                </button>
              </div>
            </div>
            {alocs.length === 0 ? (
              <p className="text-xs text-muted">Nenhum professor alocado nesta turma.</p>
            ) : (
              <ul className="space-y-1.5">
                {alocs.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-center justify-between rounded-lg bg-slate-50 px-2.5 py-2 text-xs"
                  >
                    <span className="font-medium text-ink">
                      {a.professor_email || a.professor_nome || 'Professor'}
                    </span>
                    <span className="text-muted">{a.disciplina_nome || '—'}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </div>
    )
  }

  function renderCursoPanel(curso) {
    const expanded = cursoSel === curso.id
    const tList = turmasForCurso(curso.id)
    const dList = discsForCurso(curso.id)
    return (
      <div
        key={curso.id}
        className={[
          'rounded-2xl border bg-white shadow-panel',
          expanded ? 'border-violet-300' : 'border-slate-200',
          curso.ativo === false ? 'opacity-70' : '',
        ].join(' ')}
      >
        <button
          type="button"
          className="flex w-full items-start justify-between gap-3 p-4 text-left"
          onClick={() => setCursoSel(expanded ? '' : curso.id)}
        >
          <div>
            <p className="text-base font-semibold text-ink">
              {curso.nome}
              {curso.ativo === false ? <InactiveBadge /> : null}
            </p>
            <p className="mt-1 text-xs text-muted">
              {curso.turmas_count ?? tList.length} turmas ·{' '}
              {curso.disciplinas_count ?? dList.length} disciplinas
            </p>
          </div>
          <span className="text-sm font-bold text-muted">{expanded ? '▾' : '▸'}</span>
        </button>
        {expanded ? (
          <div className="space-y-4 border-t border-slate-100 p-4">
            <div className="flex flex-wrap gap-2">
              <button type="button" className={btnSmall} onClick={() => openCurso(curso)}>
                Editar curso
              </button>
              <button type="button" className={btnSmall} onClick={() => toggleAtivo('curso', curso)}>
                {curso.ativo === false ? 'Reativar' : 'Desativar'}
              </button>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <section>
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wide text-muted">Turmas</h4>
                  <button
                    type="button"
                    className={btnSmall}
                    onClick={() => openTurma({ cursoId: curso.id })}
                  >
                    + Nova turma
                  </button>
                </div>
                <div className="space-y-2">
                  {tList.length === 0 ? (
                    <p className="text-xs text-muted">Nenhuma turma neste curso.</p>
                  ) : (
                    tList.map((t) => renderTurmaBlock(t))
                  )}
                </div>
              </section>
              <section>
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wide text-muted">
                    Disciplinas
                  </h4>
                  <button
                    type="button"
                    className={btnSmall}
                    onClick={() => openDisc({ cursoId: curso.id })}
                  >
                    + Nova disciplina
                  </button>
                </div>
                <div className="overflow-hidden rounded-xl border border-slate-200">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-50 text-xs uppercase text-muted">
                      <tr>
                        <th className="px-3 py-2">Nome</th>
                        <th className="px-3 py-2">Ementa</th>
                        <th className="px-3 py-2 text-right">Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dList.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="px-3 py-4 text-xs text-muted">
                            Nenhuma disciplina neste curso.
                          </td>
                        </tr>
                      ) : (
                        dList.map((d) => (
                          <tr key={d.id} className="border-t border-slate-100">
                            <td className="px-3 py-2 font-medium text-ink">
                              {d.nome}
                              {d.ativo === false ? <InactiveBadge /> : null}
                            </td>
                            <td className="max-w-[220px] truncate px-3 py-2 text-xs text-muted">
                              {d.ementa_macro || '—'}
                            </td>
                            <td className="whitespace-nowrap px-3 py-2 text-right">
                              <button
                                type="button"
                                className={btnSmall}
                                onClick={() => openDisc({ item: d, cursoId: curso.id })}
                              >
                                Editar
                              </button>{' '}
                              <button
                                type="button"
                                className={btnSmall}
                                onClick={() => toggleAtivo('disciplina', d)}
                              >
                                {d.ativo === false ? 'Reativar' : 'Desativar'}
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
          Secretaria Acadêmica
        </p>
        <h1 className="mt-1 text-2xl font-bold text-ink">{escola}</h1>
        <p className="mt-1 text-sm text-muted">
          Estrutura acadêmica, alunos, calendário letivo e mural institucional.
        </p>
      </header>

      <nav className="mb-5 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tabClassNameCompact(tab === t.id)}
            onClick={() => switchTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {feedback ? (
        <p className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {feedback}
        </p>
      ) : null}
      {error ? (
        <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      {loading ? <p className="text-sm text-muted">Carregando…</p> : null}

      {/* —— Unidades —— */}
      {!loading && tab === 'unidades' ? (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-ink">Unidades</h2>
            <button
              type="button"
              className={btnPrimary}
              onClick={() => {
                clearMessages()
                setEditId(null)
                setFormUnidade(EMPTY.unidade)
                setModal('unidade')
              }}
            >
              + Nova unidade
            </button>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">Cidade</th>
                  <th className="px-4 py-3">UF</th>
                  <th className="px-4 py-3 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {unidades.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-muted">
                      Nenhuma unidade cadastrada.
                    </td>
                  </tr>
                ) : (
                  unidades.map((u) => (
                    <tr key={u.id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium">
                        {u.nome}
                        {u.ativo === false ? <InactiveBadge /> : null}
                      </td>
                      <td className="px-4 py-3 text-muted">{u.cidade || '—'}</td>
                      <td className="px-4 py-3 text-muted">{u.uf || '—'}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          className={btnGhost}
                          onClick={() => {
                            clearMessages()
                            setEditId(u.id)
                            setFormUnidade({
                              nome: u.nome || '',
                              endereco: u.endereco || '',
                              codigo: u.codigo || '',
                              cidade: u.cidade || '',
                              uf: u.uf || '',
                            })
                            setModal('unidade')
                          }}
                        >
                          Editar
                        </button>{' '}
                        <button
                          type="button"
                          className={btnGhost}
                          onClick={() => toggleAtivo('unidade', u)}
                        >
                          {u.ativo === false ? 'Reativar' : 'Desativar'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {/* —— Estrutura Acadêmica —— */}
      {!loading && tab === 'estrutura' ? (
        <section className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            {periodos.map((p) => {
              const sel = p.id === periodoSel
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setPeriodoSel(p.id)}
                  onDoubleClick={() => openPeriodo(p)}
                  className={[
                    'rounded-full px-3.5 py-1.5 text-sm font-semibold transition',
                    sel
                      ? 'bg-violet-600 text-white shadow-sm'
                      : 'bg-slate-100 text-ink hover:bg-slate-200',
                    p.ativo === false ? 'opacity-60' : '',
                  ].join(' ')}
                  title="Clique para selecionar · duplo clique para editar"
                >
                  {p.nome}
                </button>
              )
            })}
            <button type="button" className={btnGhost} onClick={() => openPeriodo(null)}>
              + Novo período
            </button>
            {periodoSel ? (
              <button
                type="button"
                className={btnSmall}
                onClick={() => {
                  const p = periodos.find((x) => x.id === periodoSel)
                  if (p) openPeriodo(p)
                }}
              >
                Editar período
              </button>
            ) : null}
          </div>

          {!periodoSel ? (
            <p className="text-sm text-muted">Crie ou selecione um período letivo para continuar.</p>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-ink">Cursos do período</h2>
                <button type="button" className={btnPrimary} onClick={() => openCurso(null)}>
                  + Novo curso
                </button>
              </div>
              <div className="space-y-3">
                {cursosDoPeriodo.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-muted">
                    Nenhum curso neste período. Crie um curso ou use a seção Sem curso abaixo.
                  </p>
                ) : (
                  cursosDoPeriodo.map((c) => renderCursoPanel(c))
                )}
              </div>

              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="text-base font-semibold text-ink">Sem curso</h3>
                    <p className="text-xs text-muted">
                      Turmas e disciplinas flat deste período (escola sem hierarquia de curso).
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className={btnGhost}
                      onClick={() => openTurma({ cursoId: '' })}
                    >
                      + Nova turma
                    </button>
                    <button
                      type="button"
                      className={btnGhost}
                      onClick={() => openDisc({ cursoId: '' })}
                    >
                      + Nova disciplina
                    </button>
                  </div>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-muted">Turmas</p>
                    {turmasSemCurso.length === 0 ? (
                      <p className="text-xs text-muted">Nenhuma turma sem curso.</p>
                    ) : (
                      turmasSemCurso.map((t) => renderTurmaBlock(t, { showCursoHint: true }))
                    )}
                  </div>
                  <div>
                    <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">
                      Disciplinas
                    </p>
                    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                      <table className="min-w-full text-left text-sm">
                        <thead className="bg-slate-50 text-xs uppercase text-muted">
                          <tr>
                            <th className="px-3 py-2">Nome</th>
                            <th className="px-3 py-2 text-right">Ações</th>
                          </tr>
                        </thead>
                        <tbody>
                          {discsSemCurso.length === 0 ? (
                            <tr>
                              <td colSpan={2} className="px-3 py-4 text-xs text-muted">
                                Nenhuma disciplina sem curso.
                              </td>
                            </tr>
                          ) : (
                            discsSemCurso.map((d) => (
                              <tr key={d.id} className="border-t border-slate-100">
                                <td className="px-3 py-2 font-medium">
                                  {d.nome}
                                  {d.ativo === false ? <InactiveBadge /> : null}
                                </td>
                                <td className="px-3 py-2 text-right">
                                  <button
                                    type="button"
                                    className={btnSmall}
                                    onClick={() => openDisc({ item: d, cursoId: '' })}
                                  >
                                    Editar
                                  </button>{' '}
                                  <button
                                    type="button"
                                    className={btnSmall}
                                    onClick={() => toggleAtivo('disciplina', d)}
                                  >
                                    {d.ativo === false ? 'Reativar' : 'Desativar'}
                                  </button>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </section>
      ) : null}

      {/* —— Alunos —— */}
      {!loading && tab === 'alunos' ? (
        <section>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-ink">Alunos</h2>
            <div className="flex flex-wrap items-center gap-2">
              <select
                className={inputCls + ' w-auto min-w-[200px]'}
                value={filtroTurmaId}
                onChange={(e) => setFiltroTurmaId(e.target.value)}
              >
                <option value="">Todas as turmas</option>
                {turmas.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nome}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className={btnPrimary}
                onClick={() => {
                  clearMessages()
                  setEditId(null)
                  setFormAluno({
                    ...EMPTY.aluno,
                    turma_id: filtroTurmaId || '',
                  })
                  setModal('aluno')
                }}
              >
                + Novo aluno
              </button>
            </div>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Nome</th>
                  <th className="px-4 py-3">Matrícula</th>
                  <th className="px-4 py-3">Turma</th>
                  <th className="px-4 py-3 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {alunosFiltrados.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-muted">
                      Nenhum aluno encontrado.
                    </td>
                  </tr>
                ) : (
                  alunosFiltrados.map((a) => (
                    <tr key={a.id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium">
                        {a.nome}
                        {a.ativo === false ? <InactiveBadge /> : null}
                      </td>
                      <td className="px-4 py-3 text-muted">{a.matricula}</td>
                      <td className="px-4 py-3 text-muted">{a.turma_nome || 'Sem turma'}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          className={btnGhost}
                          onClick={() => {
                            clearMessages()
                            setEditId(a.id)
                            setFormAluno({
                              nome: a.nome || '',
                              matricula: a.matricula || '',
                              turma_id: a.turma_id || '',
                              data_nascimento: a.data_nascimento || '',
                            })
                            setModal('aluno')
                          }}
                        >
                          Editar
                        </button>{' '}
                        <button
                          type="button"
                          className={btnGhost}
                          onClick={() => toggleAtivo('aluno', a)}
                        >
                          {a.ativo === false ? 'Reativar' : 'Desativar'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {/* —— Calendário —— */}
      {!loading && tab === 'calendario' ? (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-ink">Calendário letivo</h2>
            <button
              type="button"
              className={btnPrimary}
              onClick={() => openCal(calDay || new Date().toISOString().slice(0, 10))}
            >
              + Novo evento
            </button>
          </div>
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
            <MonthAgendaCalendar
              viewYear={calYear}
              viewMonth={calMonth}
              onShiftMonth={(delta) => {
                const d = new Date(calYear, calMonth + delta, 1)
                setCalYear(d.getFullYear())
                setCalMonth(d.getMonth())
              }}
              dayMarkers={dayMarkers}
              legend={CAL_TIPOS.map((t) => ({ tone: t.tone, label: t.label }))}
              selectedDate={calDay || undefined}
              onSelectDate={setCalDay}
              dayPanelTitle="Eventos do dia"
              dayEmptyText="Nenhum evento neste dia."
              emptyActionLabel="+ Evento neste dia"
              onEmptyDayAction={(iso) => openCal(iso)}
              dayItems={eventosDoDia}
              renderDayItem={(ev) => (
                <button
                  type="button"
                  onClick={() => openCal(ev.data_inicio, ev)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-left transition hover:ring-2 hover:ring-school-500/30"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-bold text-ink">{ev.titulo}</p>
                    <span className="text-[10px] font-bold uppercase text-muted">
                      {CAL_TIPO_LABEL[ev.tipo] || ev.tipo}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-muted">
                    {ev.data_inicio}
                    {ev.data_fim && ev.data_fim !== ev.data_inicio
                      ? ` até ${ev.data_fim}`
                      : ''}
                    {ev.unidade_nome ? ` · ${ev.unidade_nome}` : ''}
                  </p>
                </button>
              )}
            />
          </div>
        </section>
      ) : null}

      {/* —— Planejamento Escolar —— */}
      {!loading && tab === 'planejamento' ? (
        <section>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-ink">Planejamento Escolar</h2>
              <p className="text-xs text-muted">
                Esqueletos de aula/evento enviados à agenda do professor no Inove.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                className={`${inputCls} w-auto min-w-[200px]`}
                value={filtroPlanTurmaId}
                onChange={(e) => {
                  setFiltroPlanTurmaId(e.target.value)
                  setPlanSelected([])
                }}
              >
                <option value="">Todas as turmas</option>
                {turmas.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nome}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className={btnGhost}
                disabled={busy || planSelected.length === 0}
                onClick={enviarPlanejamento}
              >
                Enviar selecionados pro Inove
              </button>
              <button type="button" className={btnPrimary} onClick={() => openPlan(null)}>
                + Novo item
              </button>
            </div>
          </div>

          {planRelatorio ? (
            <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="font-semibold text-ink">Relatório do último envio</p>
                <button
                  type="button"
                  className={btnSmall}
                  onClick={() => setPlanRelatorio(null)}
                >
                  Fechar
                </button>
              </div>
              <p className="text-muted">
                {planRelatorio.enviados || 0} enviado(s) · {planRelatorio.erros || 0} erro(s)
              </p>
              <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto text-xs">
                {(planRelatorio.resultados || []).map((r) => (
                  <li key={r.id} className="flex justify-between gap-2">
                    <span className="truncate font-mono text-muted">{r.id.slice(0, 8)}…</span>
                    <span
                      className={
                        r.status_push === 'enviado' ? 'text-emerald-700' : 'text-red-700'
                      }
                    >
                      {PLAN_STATUS_LABEL[r.status_push] || r.status_push}
                      {r.resposta?.error ? ` — ${r.resposta.error}` : ''}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-muted">
                <tr>
                  <th className="px-3 py-3">
                    <input
                      type="checkbox"
                      aria-label="Selecionar todos elegíveis"
                      onChange={togglePlanSelectAll}
                      checked={
                        planejamentoFiltrado.filter(
                          (p) => p.status_push === 'rascunho' || p.status_push === 'erro',
                        ).length > 0 &&
                        planejamentoFiltrado
                          .filter(
                            (p) => p.status_push === 'rascunho' || p.status_push === 'erro',
                          )
                          .every((p) => planSelected.includes(p.id))
                      }
                    />
                  </th>
                  <th className="px-3 py-3">Data</th>
                  <th className="px-3 py-3">Título</th>
                  <th className="px-3 py-3">Tipo</th>
                  <th className="px-3 py-3">Disciplina</th>
                  <th className="px-3 py-3">Professor</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {planejamentoFiltrado.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-6 text-muted">
                      Nenhum item de planejamento.
                    </td>
                  </tr>
                ) : (
                  planejamentoFiltrado.map((item) => {
                    const enviado = item.status_push === 'enviado'
                    const elegivel =
                      item.status_push === 'rascunho' || item.status_push === 'erro'
                    return (
                      <tr
                        key={item.id}
                        className={[
                          'border-t border-slate-100',
                          enviado ? 'bg-slate-50/80 text-muted' : '',
                        ].join(' ')}
                      >
                        <td className="px-3 py-3">
                          <input
                            type="checkbox"
                            disabled={!elegivel}
                            checked={planSelected.includes(item.id)}
                            onChange={() => togglePlanSelect(item.id)}
                          />
                        </td>
                        <td className="px-3 py-3 whitespace-nowrap">{item.data || '—'}</td>
                        <td className="px-3 py-3 font-medium text-ink">
                          {item.titulo}
                          {item.item_pai_id ? (
                            <span className="ml-1 text-[10px] font-normal text-muted">
                              (sequência)
                            </span>
                          ) : null}
                        </td>
                        <td className="px-3 py-3 capitalize">{item.tipo}</td>
                        <td className="px-3 py-3">{item.disciplina_nome || '—'}</td>
                        <td className="px-3 py-3 text-xs">
                          {item.professor_email ||
                            (item.professor_b2c_id != null
                              ? `id ${item.professor_b2c_id}`
                              : '—')}
                        </td>
                        <td className="px-3 py-3">
                          <span
                            className={[
                              'inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                              PLAN_STATUS_CLASS[item.status_push] || 'bg-slate-100',
                            ].join(' ')}
                          >
                            {PLAN_STATUS_LABEL[item.status_push] || item.status_push}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-right">
                          {item.status_push === 'rascunho' ? (
                            <>
                              <button
                                type="button"
                                className={btnSmall}
                                onClick={() => openPlan(item)}
                              >
                                Editar
                              </button>{' '}
                              <button
                                type="button"
                                className={btnSmall}
                                onClick={() => deletePlan(item)}
                              >
                                Excluir
                              </button>
                            </>
                          ) : item.status_push === 'erro' ? (
                            <button
                              type="button"
                              className={btnSmall}
                              title={item.resposta_b2c_json?.error || 'Erro no envio'}
                              onClick={() =>
                                setPlanRelatorio({
                                  enviados: 0,
                                  erros: 1,
                                  resultados: [
                                    {
                                      id: item.id,
                                      status_push: 'erro',
                                      resposta: item.resposta_b2c_json,
                                    },
                                  ],
                                })
                              }
                            >
                              Ver erro
                            </button>
                          ) : (
                            <span className="text-xs text-muted">Registro</span>
                          )}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {/* —— Mural —— */}
      {!loading && tab === 'comunicacoes' ? (
        <section>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-ink">Mural / Comunicações</h2>
              <p className="text-xs text-muted">Quadro de comunicados — mais recentes primeiro.</p>
            </div>
            <button
              type="button"
              className={btnPrimary}
              onClick={() => {
                clearMessages()
                setFormCom(EMPTY.com)
                setModal('comunicacao')
              }}
            >
              + Publicar comunicado
            </button>
          </div>
          {comunicacoesOrdenadas.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-muted">
              Nenhum comunicado no mural.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {comunicacoesOrdenadas.map((item) => (
                <article
                  key={item.id}
                  className="flex flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-panel"
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <TipoBadge tipo={item.tipo} />
                    <StatusBadge status={item.status} />
                  </div>
                  <h3 className="text-base font-semibold text-ink">{item.titulo}</h3>
                  {item.descricao ? (
                    <p className="mt-1 line-clamp-3 text-sm text-muted">{item.descricao}</p>
                  ) : null}
                  <p className="mt-3 text-xs text-muted">
                    {item.data_hora_inicio
                      ? new Date(item.data_hora_inicio).toLocaleString('pt-BR')
                      : '—'}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    Público: {COM_PUBLICO_LABEL[item.publico_alvo] || item.publico_alvo || '—'}
                    {item.unidade_nome ? ` · ${item.unidade_nome}` : ''}
                  </p>
                  {item.status === 'publicado' || item.status === 'agendado' ? (
                    <button
                      type="button"
                      className={`${btnDanger} mt-4 self-start`}
                      disabled={busy}
                      onClick={() => cancelarComunicacao(item)}
                    >
                      Cancelar
                    </button>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {/* Modais */}
      <Modal title={editId ? 'Editar unidade' : 'Nova unidade'} open={modal === 'unidade'} onClose={closeModal}>
        <form onSubmit={saveUnidade} className="space-y-3">
          <Field label="Nome">
            <input className={inputCls} required value={formUnidade.nome} onChange={(e) => setFormUnidade((f) => ({ ...f, nome: e.target.value }))} />
          </Field>
          <Field label="Endereço">
            <input className={inputCls} value={formUnidade.endereco} onChange={(e) => setFormUnidade((f) => ({ ...f, endereco: e.target.value }))} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Cidade">
              <input className={inputCls} value={formUnidade.cidade} onChange={(e) => setFormUnidade((f) => ({ ...f, cidade: e.target.value }))} />
            </Field>
            <Field label="UF">
              <input className={inputCls} maxLength={2} value={formUnidade.uf} onChange={(e) => setFormUnidade((f) => ({ ...f, uf: e.target.value.toUpperCase() }))} />
            </Field>
          </div>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Salvar'}</button>
        </form>
      </Modal>

      <Modal title={editId ? 'Editar período' : 'Novo período letivo'} open={modal === 'periodo'} onClose={closeModal}>
        <form onSubmit={savePeriodo} className="space-y-3">
          <Field label="Nome">
            <input className={inputCls} required value={formPeriodo.nome} onChange={(e) => setFormPeriodo((f) => ({ ...f, nome: e.target.value }))} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Data início">
              <input type="date" className={inputCls} required value={formPeriodo.data_inicio} onChange={(e) => setFormPeriodo((f) => ({ ...f, data_inicio: e.target.value }))} />
            </Field>
            <Field label="Data fim">
              <input type="date" className={inputCls} required value={formPeriodo.data_fim} onChange={(e) => setFormPeriodo((f) => ({ ...f, data_fim: e.target.value }))} />
            </Field>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Ano letivo">
              <input type="number" className={inputCls} required value={formPeriodo.ano_letivo} onChange={(e) => setFormPeriodo((f) => ({ ...f, ano_letivo: e.target.value }))} />
            </Field>
            <Field label="Tipo">
              <select className={inputCls} value={formPeriodo.tipo_periodo} onChange={(e) => setFormPeriodo((f) => ({ ...f, tipo_periodo: e.target.value }))}>
                {TIPOS_PERIODO.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </Field>
          </div>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Salvar'}</button>
        </form>
      </Modal>

      <Modal title={editId ? 'Editar curso' : 'Novo curso'} open={modal === 'curso'} onClose={closeModal}>
        <form onSubmit={saveCurso} className="space-y-3">
          <Field label="Nome">
            <input className={inputCls} required value={formCurso.nome} onChange={(e) => setFormCurso((f) => ({ ...f, nome: e.target.value }))} />
          </Field>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Salvar'}</button>
        </form>
      </Modal>

      <Modal title={editId ? 'Editar disciplina' : 'Nova disciplina'} open={modal === 'disciplina'} onClose={closeModal}>
        <form onSubmit={saveDisc} className="space-y-3">
          <Field label="Nome">
            <input className={inputCls} required value={formDisc.nome} onChange={(e) => setFormDisc((f) => ({ ...f, nome: e.target.value }))} />
          </Field>
          <Field label="Curso">
            <select className={inputCls} value={formDisc.curso_id} onChange={(e) => setFormDisc((f) => ({ ...f, curso_id: e.target.value }))}>
              <option value="">Nenhum</option>
              {cursos
                .filter((c) => !periodoSel || c.periodo_letivo_id === periodoSel)
                .map((c) => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
            </select>
          </Field>
          <Field label="Ementa">
            <textarea className={inputCls} rows={3} value={formDisc.ementa_macro} onChange={(e) => setFormDisc((f) => ({ ...f, ementa_macro: e.target.value }))} />
          </Field>
          <Field label="Carga horária">
            <input type="number" className={inputCls} value={formDisc.carga_horaria} onChange={(e) => setFormDisc((f) => ({ ...f, carga_horaria: e.target.value }))} />
          </Field>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Salvar'}</button>
        </form>
      </Modal>

      <Modal title={editId ? 'Editar turma' : 'Nova turma'} open={modal === 'turma'} onClose={closeModal}>
        <form onSubmit={saveTurma} className="space-y-3">
          <Field label="Nome">
            <input className={inputCls} required value={formTurma.nome} onChange={(e) => setFormTurma((f) => ({ ...f, nome: e.target.value }))} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Série / ano">
              <input className={inputCls} required value={formTurma.serie_ano} onChange={(e) => setFormTurma((f) => ({ ...f, serie_ano: e.target.value }))} />
            </Field>
            <Field label="Turno">
              <select className={inputCls} value={formTurma.turno} onChange={(e) => setFormTurma((f) => ({ ...f, turno: e.target.value }))}>
                {TURNOS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Unidade">
            <select className={inputCls} required value={formTurma.unidade_id} onChange={(e) => setFormTurma((f) => ({ ...f, unidade_id: e.target.value }))}>
              <option value="">Selecione</option>
              {unidades.map((u) => (
                <option key={u.id} value={u.id}>{u.nome}</option>
              ))}
            </select>
          </Field>
          <Field label="Curso">
            <select className={inputCls} value={formTurma.curso_id} onChange={(e) => setFormTurma((f) => ({ ...f, curso_id: e.target.value }))}>
              <option value="">Nenhum (sem curso)</option>
              {cursosDoPeriodo.map((c) => (
                <option key={c.id} value={c.id}>{c.nome}</option>
              ))}
            </select>
          </Field>
          <p className="text-xs text-muted">
            Ano letivo derivado do período selecionado
            {periodos.find((p) => p.id === (formTurma.periodo_letivo_id || periodoSel))
              ? `: ${periodos.find((p) => p.id === (formTurma.periodo_letivo_id || periodoSel)).ano_letivo}`
              : ''}
            .
          </p>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Salvar'}</button>
        </form>
      </Modal>

      <Modal title={editId ? 'Editar aluno' : 'Novo aluno'} open={modal === 'aluno'} onClose={closeModal}>
        <form onSubmit={saveAluno} className="space-y-3">
          <Field label="Nome">
            <input className={inputCls} required value={formAluno.nome} onChange={(e) => setFormAluno((f) => ({ ...f, nome: e.target.value }))} />
          </Field>
          <Field label="Matrícula">
            <input className={inputCls} required value={formAluno.matricula} onChange={(e) => setFormAluno((f) => ({ ...f, matricula: e.target.value }))} />
          </Field>
          <Field label="Turma">
            <select className={inputCls} value={formAluno.turma_id} onChange={(e) => setFormAluno((f) => ({ ...f, turma_id: e.target.value }))}>
              <option value="">Sem turma</option>
              {turmas.map((t) => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </select>
          </Field>
          <Field label="Data de nascimento">
            <input type="date" className={inputCls} value={formAluno.data_nascimento} onChange={(e) => setFormAluno((f) => ({ ...f, data_nascimento: e.target.value }))} />
          </Field>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Salvar'}</button>
        </form>
      </Modal>

      <Modal
        title={editId ? 'Editar evento' : 'Novo evento'}
        open={modal === 'calendario'}
        onClose={closeModal}
      >
        <form onSubmit={saveCal} className="space-y-3">
          <Field label="Título">
            <input className={inputCls} required value={formCal.titulo} onChange={(e) => setFormCal((f) => ({ ...f, titulo: e.target.value }))} />
          </Field>
          <Field label="Tipo">
            <select className={inputCls} value={formCal.tipo} onChange={(e) => setFormCal((f) => ({ ...f, tipo: e.target.value }))}>
              {CAL_TIPOS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Início">
              <input type="date" className={inputCls} required value={formCal.data_inicio} onChange={(e) => setFormCal((f) => ({ ...f, data_inicio: e.target.value }))} />
            </Field>
            <Field label="Fim">
              <input type="date" className={inputCls} value={formCal.data_fim} onChange={(e) => setFormCal((f) => ({ ...f, data_fim: e.target.value }))} />
            </Field>
          </div>
          <Field label="Unidade (opcional)">
            <select className={inputCls} value={formCal.unidade_id} onChange={(e) => setFormCal((f) => ({ ...f, unidade_id: e.target.value }))}>
              <option value="">Toda a instituição</option>
              {unidades.map((u) => (
                <option key={u.id} value={u.id}>{u.nome}</option>
              ))}
            </select>
          </Field>
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Salvar'}</button>
            {editId ? (
              <button
                type="button"
                className={btnDanger}
                disabled={busy}
                onClick={() => {
                  const ev = calendario.find((c) => c.id === editId)
                  if (ev) deleteCal(ev)
                }}
              >
                Excluir
              </button>
            ) : null}
          </div>
        </form>
      </Modal>

      <Modal title="Alocar professor" open={modal === 'aloc'} onClose={closeModal}>
        <form onSubmit={saveAloc} className="space-y-3">
          <p className="text-sm text-muted">
            Turma: <strong className="text-ink">{context.turma?.nome}</strong>
          </p>
          <Field label="Disciplina">
            <select className={inputCls} required value={formAloc.disciplina_id} onChange={(e) => setFormAloc((f) => ({ ...f, disciplina_id: e.target.value }))}>
              <option value="">Selecione</option>
              {discsForAloc(context.turma).map((d) => (
                <option key={d.id} value={d.id}>{d.nome}</option>
              ))}
            </select>
          </Field>
          <Field label="Professor">
            <select className={inputCls} required value={formAloc.professor_id} onChange={(e) => setFormAloc((f) => ({ ...f, professor_id: e.target.value }))}>
              <option value="">Selecione</option>
              {professores.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label || p.email || p.email_convite || p.id}
                </option>
              ))}
            </select>
          </Field>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Alocar'}</button>
        </form>
      </Modal>

      <Modal title="Publicar comunicado" open={modal === 'comunicacao'} onClose={closeModal} wide>
        <form onSubmit={saveCom} className="space-y-3">
          <Field label="Título">
            <input className={inputCls} required value={formCom.titulo} onChange={(e) => setFormCom((f) => ({ ...f, titulo: e.target.value }))} />
          </Field>
          <Field label="Descrição">
            <textarea className={inputCls} rows={3} value={formCom.descricao} onChange={(e) => setFormCom((f) => ({ ...f, descricao: e.target.value }))} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Tipo">
              <select className={inputCls} value={formCom.tipo} onChange={(e) => setFormCom((f) => ({ ...f, tipo: e.target.value }))}>
                {COM_TIPOS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </Field>
            <Field label="Público">
              <select className={inputCls} value={formCom.publico_alvo} onChange={(e) => setFormCom((f) => ({ ...f, publico_alvo: e.target.value }))}>
                {COM_PUBLICOS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </Field>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Início">
              <input type="datetime-local" className={inputCls} required value={formCom.data_hora_inicio} onChange={(e) => setFormCom((f) => ({ ...f, data_hora_inicio: e.target.value }))} />
            </Field>
            <Field label="Fim">
              <input type="datetime-local" className={inputCls} value={formCom.data_hora_fim} onChange={(e) => setFormCom((f) => ({ ...f, data_hora_fim: e.target.value }))} />
            </Field>
          </div>
          <Field label="Unidade (opcional)">
            <select className={inputCls} value={formCom.unidade_id} onChange={(e) => setFormCom((f) => ({ ...f, unidade_id: e.target.value }))}>
              <option value="">Toda a instituição</option>
              {unidades.map((u) => (
                <option key={u.id} value={u.id}>{u.nome}</option>
              ))}
            </select>
          </Field>
          <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Publicando…' : 'Publicar'}</button>
        </form>
      </Modal>

      <Modal
        title={editId ? 'Editar planejamento' : 'Novo item de planejamento'}
        open={modal === 'planejamento'}
        onClose={closeModal}
        wide
      >
        <form onSubmit={savePlan} className="space-y-3">
          <Field label="Turma">
            <select
              className={inputCls}
              required
              value={formPlan.turma_id}
              onChange={(e) =>
                setFormPlan((f) => ({
                  ...f,
                  turma_id: e.target.value,
                  disciplina_id: '',
                  item_pai_id: '',
                }))
              }
            >
              <option value="">Selecione</option>
              {turmas.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nome}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Disciplina (com alocação nesta turma)">
            <select
              className={inputCls}
              required
              value={formPlan.disciplina_id}
              onChange={(e) =>
                setFormPlan((f) => ({ ...f, disciplina_id: e.target.value }))
              }
            >
              <option value="">Selecione</option>
              {discsAlocadasTurma.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome}
                </option>
              ))}
            </select>
            {formPlan.turma_id && discsAlocadasTurma.length === 0 ? (
              <p className="mt-1 text-xs text-amber-700">
                Nenhuma disciplina com professor alocado nesta turma. Vá em Estrutura
                Acadêmica e aloque um professor.
              </p>
            ) : null}
          </Field>
          <Field label="Título">
            <input
              className={inputCls}
              required
              value={formPlan.titulo}
              onChange={(e) => setFormPlan((f) => ({ ...f, titulo: e.target.value }))}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Tipo">
              <select
                className={inputCls}
                value={formPlan.tipo}
                onChange={(e) => setFormPlan((f) => ({ ...f, tipo: e.target.value }))}
              >
                {PLAN_TIPOS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Data">
              <input
                type="date"
                className={inputCls}
                required
                value={formPlan.data}
                onChange={(e) => setFormPlan((f) => ({ ...f, data: e.target.value }))}
              />
            </Field>
            <Field label="Vincular a (opcional)">
              <select
                className={inputCls}
                value={formPlan.item_pai_id}
                onChange={(e) =>
                  setFormPlan((f) => ({ ...f, item_pai_id: e.target.value }))
                }
              >
                <option value="">Nenhum</option>
                {itensPaiOpcoes.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.data} — {p.titulo}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Hora início">
              <input
                type="time"
                className={inputCls}
                value={formPlan.hora_inicio}
                onChange={(e) =>
                  setFormPlan((f) => ({ ...f, hora_inicio: e.target.value }))
                }
              />
            </Field>
            <Field label="Hora fim">
              <input
                type="time"
                className={inputCls}
                value={formPlan.hora_fim}
                onChange={(e) => setFormPlan((f) => ({ ...f, hora_fim: e.target.value }))}
              />
            </Field>
          </div>
          <Field label="Observações">
            <textarea
              className={inputCls}
              rows={2}
              value={formPlan.observacoes}
              onChange={(e) =>
                setFormPlan((f) => ({ ...f, observacoes: e.target.value }))
              }
            />
          </Field>
          <button type="submit" disabled={busy} className={btnPrimary}>
            {busy ? 'Salvando…' : 'Salvar'}
          </button>
        </form>
      </Modal>
    </div>
  )
}

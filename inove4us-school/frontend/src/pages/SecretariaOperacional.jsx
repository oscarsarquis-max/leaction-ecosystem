import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../lib/auth'
import MonthAgendaCalendar from '../components/MonthAgendaCalendar'
import ProfessorChip from '../components/ProfessorChip'

/**
 * Secretaria Acadêmica — Unidades · Estrutura · Alunos · Situação por período ·
 * Calendário · Mural · Planejamento Escolar
 */

const TABS = [
  { id: 'unidades', label: 'Unidades' },
  { id: 'estrutura', label: 'Estrutura Acadêmica' },
  { id: 'alunos', label: 'Alunos' },
  { id: 'situacao', label: 'Situação por período' },
  { id: 'calendario', label: 'Calendário' },
  { id: 'comunicacoes', label: 'Mural / Comunicações' },
  { id: 'planejamento', label: 'Planejamento Escolar' },
]

/** Identidade de cor por aba — borda superior do painel + fundo da barra de contexto. */
const TAB_THEME = {
  unidades: {
    tabActive: 'bg-slate-600 text-white',
    panel: 'border-t-4 border-t-slate-500',
    context: 'border-b border-slate-200 bg-slate-50',
    label: 'text-slate-700',
  },
  estrutura: {
    tabActive: 'bg-sky-600 text-white',
    panel: 'border-t-4 border-t-sky-500',
    context: 'border-b border-sky-200 bg-sky-50',
    label: 'text-sky-800',
  },
  alunos: {
    tabActive: 'bg-teal-600 text-white',
    panel: 'border-t-4 border-t-teal-500',
    context: 'border-b border-teal-200 bg-teal-50',
    label: 'text-teal-800',
  },
  situacao: {
    tabActive: 'bg-amber-600 text-white',
    panel: 'border-t-4 border-t-amber-500',
    context: 'border-b border-amber-200 bg-amber-50',
    label: 'text-amber-900',
  },
  calendario: {
    tabActive: 'bg-orange-500 text-white',
    panel: 'border-t-4 border-t-orange-400',
    context: 'border-b border-orange-200 bg-orange-50',
    label: 'text-orange-800',
  },
  comunicacoes: {
    tabActive: 'bg-rose-500 text-white',
    panel: 'border-t-4 border-t-rose-400',
    context: 'border-b border-rose-200 bg-rose-50',
    label: 'text-rose-800',
  },
  planejamento: {
    tabActive: 'bg-violet-600 text-white',
    panel: 'border-t-4 border-t-violet-500',
    context: 'border-b border-violet-200 bg-violet-50',
    label: 'text-violet-800',
  },
}

const PERIODO_STATUS_LABEL = {
  planejamento: 'Planejamento',
  em_andamento: 'Em andamento',
  encerrado: 'Encerrado',
}

const PERIODO_STATUS_CLASS = {
  planejamento: 'bg-slate-100 text-slate-700',
  em_andamento: 'bg-emerald-50 text-emerald-800',
  encerrado: 'bg-amber-50 text-amber-900',
}

const SITUACAO_AVISO_UI =
  'Situação atual por período. Os números refletem o cadastro de hoje. Alunos e professores que mudaram de turma ou período aparecem apenas onde estão agora. Não há snapshot de fechamento de período neste painel.'

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
  { value: 'turma', label: 'Turma' },
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

const COUNT_BADGE_TONE = {
  turma: 'bg-teal-50 text-teal-800 ring-teal-200',
  disciplina: 'bg-rose-50 text-rose-800 ring-rose-200',
  professor: 'bg-amber-50 text-amber-900 ring-amber-200',
  aluno: 'bg-slate-100 text-slate-700 ring-slate-200',
}

function CountBadge({ tone, children }) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold ring-1 ring-inset',
        COUNT_BADGE_TONE[tone] || COUNT_BADGE_TONE.aluno,
      ].join(' ')}
    >
      {children}
    </span>
  )
}

function IconAlocacao() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
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

function toDatetimeLocal(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function ReplicadoBadge({ item }) {
  if (item.status === 'agendado') return null
  const ok = Boolean(item.replicado_b2c)
  if (item.status === 'cancelado') {
    return (
      <span
        className={[
          'inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
          ok ? 'bg-slate-100 text-slate-600' : 'bg-amber-50 text-amber-900',
        ].join(' ')}
      >
        {ok ? 'Cancelamento no mural' : 'Cancelamento não replicado'}
      </span>
    )
  }
  return (
    <span
      className={[
        'inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
        ok ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-900',
      ].join(' ')}
    >
      {ok ? 'No mural dos professores' : 'Não replicado no mural'}
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

/** Planejamento Escolar no Calendário (mesma data; não mistura com o CRUD letivo). */
function planToCalItem(p) {
  const iso = String(p?.data || '').slice(0, 10)
  const evento = p?.tipo === 'evento'
  return {
    id: `plan-${p.id}`,
    titulo: p.titulo,
    tipo: evento ? 'evento' : 'letivo',
    tipo_label: evento ? 'Evento' : 'Aula',
    data_inicio: iso,
    data_fim: iso,
    unidade_nome: [p.turma_nome, p.disciplina_nome].filter(Boolean).join(' · '),
    source: 'planejamento',
    hora_inicio: p.hora_inicio,
    hora_fim: p.hora_fim,
  }
}

const EQUIPE_PAPEL_LABEL = {
  gestor_principal: 'Gestor principal',
  gestor_academico: 'Gestor acadêmico',
  coordenador: 'Coordenador',
}

const EMPTY = {
  unidade: { nome: '', endereco: '', codigo: '', cidade: '', uf: '' },
  unidadeFicha: {
    logradouro: '',
    numero: '',
    bairro: '',
    cep: '',
    telefone: '',
    email_institucional: '',
    cidade: '',
    uf: '',
  },
  equipe: {
    modo: 'gestor',
    papel: 'coordenador',
    gestor_id: '',
    nome: '',
    email: '',
    telefone: '',
    area_coordenacao: '',
  },
  periodo: {
    nome: '',
    data_inicio: '',
    data_fim: '',
    ano_letivo: new Date().getFullYear(),
    tipo_periodo: 'semestral',
    unidade_id: '',
  },
  curso: { nome: '' },
  disciplina: {
    nome: '',
    ementa_macro: '',
    carga_horaria: '',
    modo: 'nova',
    disciplina_id: '',
  },
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
    turma_id: '',
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
  const [discSel, setDiscSel] = useState('')
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
  const [fichaId, setFichaId] = useState(null)
  const [ficha, setFicha] = useState(null)
  const [fichaLoading, setFichaLoading] = useState(false)
  const [formFicha, setFormFicha] = useState(EMPTY.unidadeFicha)
  const [formEquipe, setFormEquipe] = useState(EMPTY.equipe)
  const [gestoresOpts, setGestoresOpts] = useState([])
  const [formPeriodo, setFormPeriodo] = useState(EMPTY.periodo)
  const [formCurso, setFormCurso] = useState(EMPTY.curso)
  const [formDisc, setFormDisc] = useState(EMPTY.disciplina)
  const [formTurma, setFormTurma] = useState(EMPTY.turma)
  const [formAluno, setFormAluno] = useState(EMPTY.aluno)
  const [importStep, setImportStep] = useState('upload')
  const [importFile, setImportFile] = useState(null)
  const [importPreview, setImportPreview] = useState(null)
  const [importPermitirMudancaTurma, setImportPermitirMudancaTurma] = useState(false)
  const [situacaoItems, setSituacaoItems] = useState([])
  const [situacaoLoading, setSituacaoLoading] = useState(false)
  const [situacaoUnidadeId, setSituacaoUnidadeId] = useState('')
  const [situacaoCursoId, setSituacaoCursoId] = useState('')
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

  const loadSituacao = useCallback(async () => {
    setSituacaoLoading(true)
    setError('')
    try {
      const qs = new URLSearchParams()
      if (situacaoUnidadeId) qs.set('unidade_id', situacaoUnidadeId)
      if (situacaoCursoId) qs.set('curso_id', situacaoCursoId)
      const url = `/api/secretaria/situacao-por-periodo${qs.toString() ? `?${qs}` : ''}`
      const data = await apiJson(url)
      setSituacaoItems(data.items || [])
    } catch (err) {
      setError(err.message || 'Falha ao carregar situação por período')
      setSituacaoItems([])
    } finally {
      setSituacaoLoading(false)
    }
  }, [situacaoUnidadeId, situacaoCursoId])

  useEffect(() => {
    if (tab === 'situacao') loadSituacao()
  }, [tab, loadSituacao])

  useEffect(() => {
    if (!periodoSel && periodos.length) {
      const ativo = periodos.find((p) => p.ativo) || periodos[0]
      setPeriodoSel(ativo.id)
    }
  }, [periodos, periodoSel])

  useEffect(() => {
    setTurmaSel('')
    setDiscSel('')
    setCursoSel((prev) => {
      if (!prev) return ''
      const stillHere = cursos.some(
        (c) => c.id === prev && c.periodo_letivo_id === periodoSel,
      )
      return stillHere ? prev : ''
    })
    // Só reage a troca de período (navegação da ficha preserva cursoSel do mesmo período).
    // eslint-disable-next-line react-hooks/exhaustive-deps -- cursos lidos do closure atual
  }, [periodoSel])

  const alunosFiltrados = useMemo(() => {
    if (!filtroTurmaId) return alunos
    return alunos.filter((a) => a.turma_id === filtroTurmaId)
  }, [alunos, filtroTurmaId])

  const cursosDoPeriodo = useMemo(
    () => cursos.filter((c) => c.periodo_letivo_id === periodoSel),
    [cursos, periodoSel],
  )

  const estruturaNodes = useMemo(() => {
    if (!periodoSel) return []
    return cursosDoPeriodo
  }, [periodoSel, cursosDoPeriodo])

  const countsByTurma = useMemo(() => {
    const map = {}
    for (const t of turmas) {
      map[t.id] = { alunos: 0, professores: new Set() }
    }
    for (const a of alunos) {
      if (a.ativo === false || !a.turma_id) continue
      if (!map[a.turma_id]) map[a.turma_id] = { alunos: 0, professores: new Set() }
      map[a.turma_id].alunos += 1
    }
    for (const al of alocacoes) {
      if (al.ativo === false || !al.turma_id) continue
      if (!map[al.turma_id]) map[al.turma_id] = { alunos: 0, professores: new Set() }
      if (al.professor_id) map[al.turma_id].professores.add(al.professor_id)
    }
    const out = {}
    for (const [tid, v] of Object.entries(map)) {
      out[tid] = { alunos: v.alunos, professores: v.professores.size }
    }
    return out
  }, [turmas, alunos, alocacoes])

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
    planejamento.forEach((p) => {
      const item = planToCalItem(p)
      if (!item.data_inicio) return
      if (!map[item.data_inicio]) map[item.data_inicio] = []
      map[item.data_inicio].push({
        id: item.id,
        tone: CAL_TIPO_TONE[item.tipo] || 'slate',
        title: item.titulo,
      })
    })
    return map
  }, [calendario, planejamento])

  const eventosDoDia = useMemo(() => {
    if (!calDay) return []
    const doCalendario = calendario.filter((ev) =>
      eachDateInclusive(ev.data_inicio, ev.data_fim || ev.data_inicio).includes(calDay),
    )
    const doPlanejamento = planejamento
      .filter((p) => String(p.data || '').slice(0, 10) === calDay)
      .map(planToCalItem)
    return [...doCalendario, ...doPlanejamento]
  }, [calendario, planejamento, calDay])

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
    setImportStep('upload')
    setImportFile(null)
    setImportPreview(null)
    setImportPermitirMudancaTurma(false)
  }

  function downloadModeloCsv() {
    const content = 'nome,matricula,data_nascimento\n'
    const blob = new Blob(['\uFEFF' + content], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'modelo_alunos.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  function openImportAlunos() {
    clearMessages()
    if (!filtroTurmaId) {
      setError('Selecione uma turma no filtro antes de importar.')
      return
    }
    setImportStep('upload')
    setImportFile(null)
    setImportPreview(null)
    setImportPermitirMudancaTurma(false)
    setModal('importAlunos')
  }

  async function runImportPreview() {
    if (!filtroTurmaId || !importFile) {
      setError('Selecione o arquivo CSV e uma turma.')
      return
    }
    await runBusy(async () => {
      const fd = new FormData()
      fd.append('file', importFile)
      fd.append('turma_id', filtroTurmaId)
      const res = await fetch('/api/secretaria/alunos/importar/preview', {
        method: 'POST',
        credentials: 'include',
        body: fd,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Falha no preview da importação')
      setImportPreview(data)
      setImportPermitirMudancaTurma(false)
      setImportStep('preview')
    })
  }

  async function runImportConfirm() {
    if (!filtroTurmaId || !importPreview?.linhas) return
    const linhasOk = importPreview.linhas
      .filter((L) => L.status === 'ok')
      .map((L) => ({
        linha: L.linha,
        nome: L.nome,
        matricula: L.matricula,
        data_nascimento: L.data_nascimento || null,
        permitir_mudanca_turma: importPermitirMudancaTurma,
      }))
    if (!linhasOk.length) {
      setError('Nenhuma linha válida para importar.')
      return
    }
    await runBusy(async () => {
      const data = await apiJson('/api/secretaria/alunos/importar/confirmar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          turma_id: filtroTurmaId,
          linhas: linhasOk,
          permitir_mudanca_turma: importPermitirMudancaTurma,
        }),
      })
      const partes = [
        `${data.criados || 0} criado(s)`,
        `${data.atualizados || 0} atualizado(s)`,
      ]
      if (data.mudancas_turma) {
        partes.push(`${data.mudancas_turma} mudança(s) de turma`)
      }
      let msg = `Importação concluída: ${partes.join(', ')}.`
      const pulados = data.nao_aplicados || (data.pulados || []).length
      if (pulados) {
        msg += ` ${pulados} linha(s) não aplicada(s) (mudança de turma sem autorização).`
      }
      setFeedback(msg)
      closeModal()
      await loadAll()
    })
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
        modo: 'nova',
        disciplina_id: '',
      })
    } else {
      setEditId(null)
      setFormDisc({ ...EMPTY.disciplina, modo: 'nova' })
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
      if (fichaId) await loadFicha(fichaId)
    })
  }

  async function loadFicha(id) {
    if (!id) return
    setFichaLoading(true)
    setError('')
    try {
      const data = await apiJson(`/api/secretaria/unidades/${id}`)
      const item = data.item || null
      setFicha(item)
      setFichaId(id)
      if (item) {
        setFormFicha({
          logradouro: item.logradouro || '',
          numero: item.numero || '',
          bairro: item.bairro || '',
          cep: item.cep || '',
          telefone: item.telefone || '',
          email_institucional: item.email_institucional || '',
          cidade: item.cidade || '',
          uf: item.uf || '',
        })
      }
    } catch (err) {
      setError(err.message || 'Falha ao abrir ficha da unidade')
      setFicha(null)
    } finally {
      setFichaLoading(false)
    }
  }

  function closeFicha() {
    setFichaId(null)
    setFicha(null)
    setFormFicha(EMPTY.unidadeFicha)
  }

  async function saveFichaInstitucional(e) {
    e.preventDefault()
    if (!fichaId) return
    await runBusy(async () => {
      await apiJson(`/api/secretaria/unidades/${fichaId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          logradouro: formFicha.logradouro || null,
          numero: formFicha.numero || null,
          bairro: formFicha.bairro || null,
          cep: formFicha.cep || null,
          telefone: formFicha.telefone || null,
          email_institucional: formFicha.email_institucional || null,
          cidade: formFicha.cidade || null,
          uf: formFicha.uf || null,
        }),
      })
      setFeedback('Dados institucionais atualizados.')
      await loadAll()
      await loadFicha(fichaId)
    })
  }

  async function openEquipeModal(papel = 'coordenador') {
    clearMessages()
    setFormEquipe({ ...EMPTY.equipe, papel })
    try {
      const data = await apiJson('/api/secretaria/gestores')
      setGestoresOpts(data.items || [])
    } catch {
      setGestoresOpts([])
    }
    setModal('equipe')
  }

  async function saveEquipe(e) {
    e.preventDefault()
    if (!fichaId) return
    await runBusy(async () => {
      const body = {
        papel: formEquipe.papel,
        area_coordenacao:
          formEquipe.papel === 'coordenador'
            ? formEquipe.area_coordenacao || null
            : null,
      }
      if (formEquipe.modo === 'gestor') {
        if (!formEquipe.gestor_id) throw new Error('Selecione um gestor')
        body.gestor_id = formEquipe.gestor_id
      } else {
        if (!formEquipe.nome.trim()) throw new Error('Nome é obrigatório')
        body.nome = formEquipe.nome
        body.email = formEquipe.email || null
        body.telefone = formEquipe.telefone || null
      }
      await apiJson(`/api/secretaria/unidades/${fichaId}/equipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      setFeedback('Membro adicionado à equipe gestora.')
      closeModal()
      await loadFicha(fichaId)
    })
  }

  async function softRemoveEquipe(membro) {
    if (!fichaId || !membro?.id) return
    if (!window.confirm(`Remover ${membro.nome || 'este membro'} da equipe?`)) return
    await runBusy(async () => {
      await apiJson(`/api/secretaria/unidades/${fichaId}/equipe/${membro.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ativo: false }),
      })
      setFeedback('Membro removido da equipe.')
      await loadFicha(fichaId)
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
      const cursoId = context.curso_id
      if (editId) {
        await apiJson(`/api/secretaria/disciplinas/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nome: formDisc.nome,
            ementa_macro: formDisc.ementa_macro || null,
            carga_horaria: formDisc.carga_horaria ? Number(formDisc.carga_horaria) : null,
          }),
        })
        setFeedback('Disciplina atualizada em todos os cursos associados.')
      } else if (formDisc.modo === 'existente') {
        if (!cursoId || !formDisc.disciplina_id) {
          throw new Error('Selecione a disciplina para associar a este curso.')
        }
        await apiJson(`/api/secretaria/cursos/${cursoId}/disciplinas`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ disciplina_id: formDisc.disciplina_id }),
        })
        setFeedback('Disciplina associada ao catálogo do curso.')
      } else {
        const path = cursoId
          ? `/api/secretaria/cursos/${cursoId}/disciplinas`
          : '/api/secretaria/disciplinas'
        await apiJson(path, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nome: formDisc.nome,
            ementa_macro: formDisc.ementa_macro || null,
            carga_horaria: formDisc.carga_horaria ? Number(formDisc.carga_horaria) : null,
          }),
        })
        setFeedback(
          cursoId
            ? 'Disciplina criada e associada a este curso.'
            : 'Disciplina criada no catálogo institucional.',
        )
      }
      closeModal()
      await loadAll()
    })
  }

  async function dissociateDisc(cursoId, disc) {
    if (!cursoId || !disc?.id) return
    if (!window.confirm(`Remover "${disc.nome}" do catálogo deste curso? A disciplina continua no catálogo da instituição.`)) {
      return
    }
    await runBusy(async () => {
      await apiJson(`/api/secretaria/cursos/${cursoId}/disciplinas/${disc.id}`, {
        method: 'DELETE',
      })
      setFeedback('Disciplina desassociada deste curso.')
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
        curso_id: formTurma.curso_id,
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

  function openCom(item) {
    clearMessages()
    if (item) {
      setEditId(item.id)
      setFormCom({
        titulo: item.titulo || '',
        descricao: item.descricao || '',
        tipo: item.tipo || 'reuniao_pedagogica',
        publico_alvo: item.publico_alvo || 'professores',
        data_hora_inicio: toDatetimeLocal(item.data_hora_inicio),
        data_hora_fim: toDatetimeLocal(item.data_hora_fim),
        unidade_id: item.unidade_id || '',
        turma_id: item.turma_id || '',
      })
    } else {
      setEditId(null)
      const scopedUnidade = user?.unidade_id || ''
      setFormCom({
        ...EMPTY.com,
        publico_alvo: scopedUnidade ? 'unidade' : 'professores',
        unidade_id: scopedUnidade,
      })
    }
    setModal('comunicacao')
  }

  async function saveCom(e) {
    e.preventDefault()
    await runBusy(async () => {
      const body = {
        titulo: formCom.titulo,
        descricao: formCom.descricao || null,
        tipo: formCom.tipo,
        publico_alvo: formCom.publico_alvo,
        data_hora_inicio: formCom.data_hora_inicio,
        data_hora_fim: formCom.data_hora_fim || null,
        unidade_id: formCom.publico_alvo === 'unidade' ? formCom.unidade_id || null : null,
        turma_id: formCom.publico_alvo === 'turma' ? formCom.turma_id || null : null,
        status: 'publicado',
      }
      const data = editId
        ? await apiJson(`/api/secretaria/comunicacoes/${editId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          })
        : await apiJson('/api/secretaria/comunicacoes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          })
      setFeedback(data.message || 'Comunicado salvo.')
      closeModal()
      await loadAll()
    })
  }

  async function cancelarComunicacao(item) {
    if (!window.confirm(`Cancelar o comunicado "${item.titulo}"?`)) return
    await runBusy(async () => {
      const data = await apiJson(`/api/secretaria/comunicacoes/${item.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'cancelado' }),
      })
      setFeedback(data.message || 'Comunicado cancelado.')
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

  function discInCurso(d, cursoId) {
    if (!d || !cursoId) return false
    if (Array.isArray(d.curso_ids) && d.curso_ids.includes(cursoId)) return true
    if (Array.isArray(d.cursos) && d.cursos.some((c) => c.id === cursoId)) return true
    return false
  }

  function discsForCurso(cursoId) {
    return disciplinas.filter((d) => discInCurso(d, cursoId))
  }

  function turmasForCurso(cursoId) {
    return turmas.filter((t) => t.curso_id === cursoId)
  }

  function alocacoesForTurma(turmaId) {
    return alocacoes.filter((a) => a.turma_id === turmaId && a.ativo !== false)
  }

  function alocacoesForDisc(disciplinaId) {
    return alocacoes.filter((a) => a.disciplina_id === disciplinaId && a.ativo !== false)
  }

  function turmasForNode(node) {
    if (!node) return []
    return turmasForCurso(node.id)
  }

  function discsForNode(node) {
    if (!node) return []
    return discsForCurso(node.id)
  }

  function countsForNode(node) {
    const tList = turmasForNode(node)
    const dList = discsForNode(node)
    const turmaIds = new Set(tList.map((t) => t.id))
    let alunosN = 0
    for (const tid of turmaIds) {
      alunosN += countsByTurma[tid]?.alunos ?? 0
    }
    const profs = new Set()
    for (const al of alocacoes) {
      if (al.ativo === false || !al.turma_id || !al.professor_id) continue
      if (!turmaIds.has(al.turma_id)) continue
      profs.add(al.professor_id)
    }
    return {
      turmas: tList.length,
      disciplinas: dList.length,
      professores: profs.size,
      alunos: alunosN,
    }
  }

  function discsForAloc(turma) {
    if (!turma?.curso_id) return []
    return discsForCurso(turma.curso_id)
  }

  function openCursoNaEstrutura(cursoFicha) {
    clearMessages()
    if (cursoFicha?.periodo_id) setPeriodoSel(cursoFicha.periodo_id)
    setCursoSel(cursoFicha.id)
    setTurmaSel('')
    setDiscSel('')
    switchTab('estrutura')
  }

  function renderDiscRow(disc, { cursoIdForEdit } = {}) {
    const expanded = discSel === disc.id
    const alocs = alocacoesForDisc(disc.id)
    const editCursoId = cursoIdForEdit || ''
    const extraCursos = (disc.cursos || []).filter((c) => c.id && c.id !== editCursoId)
    return (
      <div
        key={disc.id}
        className={[
          'border-t border-rose-100 first:border-t-0',
          disc.ativo === false ? 'opacity-60' : '',
        ].join(' ')}
      >
        <div className="flex items-stretch gap-1">
          <button
            type="button"
            className="flex min-w-0 flex-1 items-center justify-between gap-2 px-3 py-2.5 text-left hover:bg-rose-50/50"
            onClick={() => setDiscSel(expanded ? '' : disc.id)}
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink">
                {disc.nome}
                {disc.ativo === false ? <InactiveBadge /> : null}
              </p>
              {disc.ementa_macro ? (
                <p className="truncate text-xs text-muted">{disc.ementa_macro}</p>
              ) : null}
              {extraCursos.length ? (
                <p className="mt-0.5 truncate text-[10px] text-rose-700">
                  Também em: {extraCursos.map((c) => c.nome).join(', ')}
                </p>
              ) : null}
            </div>
            <span className="shrink-0 text-xs font-bold text-rose-400">
              {expanded ? '▾' : '▸'}
            </span>
          </button>
          <div className="flex shrink-0 items-center gap-1 px-2" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className={btnSmall}
              onClick={(e) => {
                e.stopPropagation()
                openDisc({ item: disc, cursoId: editCursoId })
              }}
            >
              Editar
            </button>
            <button
              type="button"
              className={btnSmall}
              onClick={(e) => {
                e.stopPropagation()
                toggleAtivo('disciplina', disc)
              }}
            >
              {disc.ativo === false ? 'Reativar' : 'Desativar'}
            </button>
            {editCursoId ? (
              <button
                type="button"
                className={btnSmall}
                onClick={(e) => {
                  e.stopPropagation()
                  dissociateDisc(editCursoId, disc)
                }}
              >
                Remover do curso
              </button>
            ) : null}
          </div>
        </div>
        {expanded ? (
          <div className="border-t border-rose-100 bg-rose-50/40 px-3 py-2.5">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-rose-800">
              Ministrada em
            </p>
            {alocs.length === 0 ? (
              <p className="text-xs text-muted">Ainda não alocada em nenhuma turma.</p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {alocs.map((a) => (
                  <li key={a.id}>
                    <ProfessorChip
                      nome={a.professor_nome}
                      email={a.professor_email}
                      badge={
                        a.turma_nome ||
                        turmas.find((t) => t.id === a.turma_id)?.nome ||
                        (a.turma_id ? 'Turma' : 'Sem turma')
                      }
                      badgeTone="turma"
                    />
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </div>
    )
  }

  function renderTurmaBlock(turma, { showCursoHint } = {}) {
    const expanded = turmaSel === turma.id
    const alocs = alocacoesForTurma(turma.id)
    const nAlunos = countsByTurma[turma.id]?.alunos ?? 0
    return (
      <div
        key={turma.id}
        className={[
          'rounded-xl border border-l-4 bg-white',
          expanded ? 'border-teal-300 border-l-teal-500 shadow-sm' : 'border-slate-200 border-l-teal-500',
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
              {' · '}
              {nAlunos} aluno{nAlunos === 1 ? '' : 's'}
            </p>
          </div>
          <span className="text-xs font-bold text-teal-500">{expanded ? '▾' : '▸'}</span>
        </button>
        {expanded ? (
          <div className="border-t border-teal-100 px-3 py-3">
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
              <div className="mb-2.5 flex items-center gap-2 text-amber-950">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-200">
                  <IconAlocacao />
                </span>
                <h5 className="text-sm font-bold">Alocação docente</h5>
              </div>
              {alocs.length === 0 ? (
                <p className="text-xs text-amber-900/80">Nenhum professor alocado nesta turma.</p>
              ) : (
                <ul className="flex flex-wrap gap-1.5">
                  {alocs.map((a) => (
                    <li key={a.id}>
                      <ProfessorChip
                        nome={a.professor_nome}
                        email={a.professor_email}
                        badge={a.disciplina_nome || '—'}
                        badgeTone="disciplina"
                      />
                    </li>
                  ))}
                </ul>
              )}
              <button
                type="button"
                className="mt-3 rounded-lg bg-amber-600 px-3 py-2 text-xs font-bold text-white hover:bg-amber-700 disabled:opacity-60"
                onClick={() => openAloc(turma)}
              >
                + Alocar professor
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <button
                type="button"
                className={btnSmall}
                onClick={() => openTurma({ item: turma, cursoId: turma.curso_id })}
              >
                Editar turma
              </button>
              <button
                type="button"
                className={btnSmall}
                onClick={() => {
                  setFiltroTurmaId(turma.id)
                  switchTab('alunos')
                }}
              >
                Ver alunos
              </button>
              <button
                type="button"
                className={btnSmall}
                onClick={() => toggleAtivo('turma', turma, 'ativa')}
              >
                {turma.ativa === false ? 'Reativar' : 'Desativar'}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  function renderEstruturaNode(node) {
    const expanded = cursoSel === node.id
    const tList = turmasForNode(node)
    const dList = discsForNode(node)
    const counts = countsForNode(node)
    const cursoIdForCreate = node.id
    return (
      <div
        key={node.id}
        className={[
          'rounded-2xl border border-l-4 bg-white shadow-panel',
          expanded ? 'border-sky-300 border-l-sky-500' : 'border-slate-200 border-l-sky-500',
          node.ativo === false ? 'opacity-70' : '',
        ].join(' ')}
      >
        <button
          type="button"
          className="flex w-full items-start justify-between gap-3 p-4 text-left"
          onClick={() => setCursoSel(expanded ? '' : node.id)}
        >
          <div className="min-w-0">
            <p className="text-base font-semibold text-ink">
              {node.nome}
              {node.ativo === false ? <InactiveBadge /> : null}
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <CountBadge tone="turma">
                {counts.turmas} turma{counts.turmas === 1 ? '' : 's'}
              </CountBadge>
              <CountBadge tone="disciplina">
                {counts.disciplinas} disciplina{counts.disciplinas === 1 ? '' : 's'}
              </CountBadge>
              <CountBadge tone="professor">
                {counts.professores} professor{counts.professores === 1 ? '' : 'es'}
              </CountBadge>
              <CountBadge tone="aluno">
                {counts.alunos} aluno{counts.alunos === 1 ? '' : 's'}
              </CountBadge>
            </div>
          </div>
          <span className="text-sm font-bold text-sky-500">{expanded ? '▾' : '▸'}</span>
        </button>
        {expanded ? (
          <div className="space-y-4 border-t border-sky-100 p-4">
            <div className="flex flex-wrap gap-2">
                <button type="button" className={btnSmall} onClick={() => openCurso(node)}>
                  Editar curso
                </button>
                <button type="button" className={btnSmall} onClick={() => toggleAtivo('curso', node)}>
                  {node.ativo === false ? 'Reativar' : 'Desativar'}
                </button>
              </div>
            <div className="relative ml-1 border-l-2 border-sky-200 pl-5">
              <div className="grid gap-4 lg:grid-cols-2">
                <section>
                  <div className="mb-2 flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wide text-teal-700">
                      Turmas
                    </h4>
                    <button
                      type="button"
                      className={btnSmall}
                      onClick={() => openTurma({ cursoId: cursoIdForCreate })}
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
                    <h4 className="text-xs font-bold uppercase tracking-wide text-rose-700">
                      Disciplinas
                    </h4>
                    <button
                      type="button"
                      className={btnSmall}
                      onClick={() => openDisc({ cursoId: cursoIdForCreate })}
                    >
                      + Associar disciplina
                    </button>
                  </div>
                  <div className="overflow-hidden rounded-xl border border-l-4 border-slate-200 border-l-rose-400 bg-white">
                    {dList.length === 0 ? (
                      <p className="px-3 py-4 text-xs text-muted">
                        Nenhuma disciplina neste curso.
                      </p>
                    ) : (
                      dList.map((d) =>
                        renderDiscRow(d, {
                          cursoIdForEdit: node.id,
                        }),
                      )
                    )}
                  </div>
                </section>
              </div>
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

      <nav className="mb-0 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={[
              'rounded-t-lg px-3 py-2 text-sm font-semibold transition',
              tab === t.id
                ? TAB_THEME[t.id].tabActive
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200',
            ].join(' ')}
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

      {!loading ? (
        <div
          className={[
            'overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel',
            TAB_THEME[tab].panel,
          ].join(' ')}
        >
          <div className={['px-4 py-3', TAB_THEME[tab].context].join(' ')}>
            {tab === 'estrutura' ? (
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
                          ? 'bg-sky-600 text-white shadow-sm'
                          : 'bg-white text-ink hover:bg-sky-100',
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
            ) : (
              <p
                className={[
                  'text-xs font-bold uppercase tracking-[0.18em]',
                  TAB_THEME[tab].label,
                ].join(' ')}
              >
                {TABS.find((t) => t.id === tab)?.label}
              </p>
            )}
          </div>
          <div className="p-4 sm:p-5">

      {/* —— Unidades —— */}
      {tab === 'unidades' ? (
        <section className="space-y-5">
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
                    <tr
                      key={u.id}
                      className={[
                        'border-t border-slate-100 cursor-pointer hover:bg-slate-50/80',
                        fichaId === u.id ? 'bg-violet-50/60' : '',
                      ].join(' ')}
                      onClick={() => {
                        clearMessages()
                        loadFicha(u.id)
                      }}
                    >
                      <td className="px-4 py-3 font-medium">
                        {u.nome}
                        {u.ativo === false ? <InactiveBadge /> : null}
                      </td>
                      <td className="px-4 py-3 text-muted">{u.cidade || '—'}</td>
                      <td className="px-4 py-3 text-muted">{u.uf || '—'}</td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
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

          {fichaId ? (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-panel space-y-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">Ficha da unidade</p>
                  <h3 className="text-xl font-semibold text-ink">
                    {ficha?.nome || '…'}
                    {ficha?.ativo === false ? <InactiveBadge /> : null}
                  </h3>
                  {ficha?.codigo ? (
                    <p className="text-sm text-muted">Código: {ficha.codigo}</p>
                  ) : null}
                </div>
                <button type="button" className={btnGhost} onClick={closeFicha}>
                  Fechar ficha
                </button>
              </div>

              {fichaLoading ? (
                <p className="text-sm text-muted">Carregando ficha…</p>
              ) : ficha ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    {[
                      ['Cursos', ficha.resumo?.cursos],
                      ['Turmas', ficha.resumo?.turmas],
                      ['Disciplinas', ficha.resumo?.disciplinas],
                      ['Alunos', ficha.resumo?.alunos],
                      ['Professores alocados', ficha.resumo?.professores_alocados],
                    ].map(([label, n]) => (
                      <span
                        key={label}
                        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-ink"
                      >
                        <span className="text-muted font-medium">{label}</span>
                        {n ?? 0}
                      </span>
                    ))}
                  </div>

                  <form onSubmit={saveFichaInstitucional} className="space-y-3 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-semibold text-ink">Dados institucionais</h4>
                    {!formFicha.logradouro && !formFicha.numero && !formFicha.bairro && ficha.endereco ? (
                      <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
                        Endereço (legado): {ficha.endereco}
                      </p>
                    ) : null}
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Field label="Logradouro">
                        <input
                          className={inputCls}
                          value={formFicha.logradouro}
                          onChange={(e) => setFormFicha((f) => ({ ...f, logradouro: e.target.value }))}
                        />
                      </Field>
                      <Field label="Número">
                        <input
                          className={inputCls}
                          value={formFicha.numero}
                          onChange={(e) => setFormFicha((f) => ({ ...f, numero: e.target.value }))}
                        />
                      </Field>
                      <Field label="Bairro">
                        <input
                          className={inputCls}
                          value={formFicha.bairro}
                          onChange={(e) => setFormFicha((f) => ({ ...f, bairro: e.target.value }))}
                        />
                      </Field>
                      <Field label="CEP">
                        <input
                          className={inputCls}
                          value={formFicha.cep}
                          onChange={(e) => setFormFicha((f) => ({ ...f, cep: e.target.value }))}
                        />
                      </Field>
                      <Field label="Telefone">
                        <input
                          className={inputCls}
                          value={formFicha.telefone}
                          onChange={(e) => setFormFicha((f) => ({ ...f, telefone: e.target.value }))}
                        />
                      </Field>
                      <Field label="E-mail institucional">
                        <input
                          type="email"
                          className={inputCls}
                          value={formFicha.email_institucional}
                          onChange={(e) =>
                            setFormFicha((f) => ({ ...f, email_institucional: e.target.value }))
                          }
                        />
                      </Field>
                      <Field label="Cidade">
                        <input
                          className={inputCls}
                          value={formFicha.cidade}
                          onChange={(e) => setFormFicha((f) => ({ ...f, cidade: e.target.value }))}
                        />
                      </Field>
                      <Field label="UF">
                        <input
                          className={inputCls}
                          maxLength={2}
                          value={formFicha.uf}
                          onChange={(e) =>
                            setFormFicha((f) => ({ ...f, uf: e.target.value.toUpperCase() }))
                          }
                        />
                      </Field>
                    </div>
                    <button type="submit" disabled={busy} className={btnPrimary}>
                      {busy ? 'Salvando…' : 'Salvar dados institucionais'}
                    </button>
                  </form>

                  <div className="space-y-3 border-t border-slate-100 pt-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h4 className="text-sm font-semibold text-ink">Equipe gestora</h4>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className={btnSmall}
                          onClick={() => openEquipeModal('gestor_principal')}
                        >
                          + Gestor principal
                        </button>
                        <button
                          type="button"
                          className={btnSmall}
                          onClick={() => openEquipeModal('gestor_academico')}
                        >
                          + Gestor acadêmico
                        </button>
                        <button
                          type="button"
                          className={btnSmall}
                          onClick={() => openEquipeModal('coordenador')}
                        >
                          + Coordenador
                        </button>
                      </div>
                    </div>
                    {['gestor_principal', 'gestor_academico', 'coordenador'].map((papel) => {
                      const membros = (ficha.equipe_gestora || []).filter((m) => m.papel === papel)
                      return (
                        <div key={papel} className="rounded-lg border border-slate-100 bg-slate-50/50 p-3">
                          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
                            {EQUIPE_PAPEL_LABEL[papel]}
                          </p>
                          {membros.length === 0 ? (
                            <p className="text-sm text-muted">Nenhum cadastrado.</p>
                          ) : (
                            <ul className="space-y-2">
                              {membros.map((m) => (
                                <li
                                  key={m.id}
                                  className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2"
                                >
                                  <div className="min-w-0">
                                    <p className="font-medium text-ink">
                                      {m.nome || '—'}
                                      {m.tem_login ? (
                                        <span className="ml-2 text-[10px] font-bold uppercase text-violet-700">
                                          login
                                        </span>
                                      ) : (
                                        <span className="ml-2 text-[10px] font-bold uppercase text-slate-500">
                                          avulso
                                        </span>
                                      )}
                                    </p>
                                    <p className="text-xs text-muted">
                                      {[m.email, m.telefone].filter(Boolean).join(' · ') || 'Sem contato'}
                                    </p>
                                    {m.area_coordenacao ? (
                                      <p className="text-xs text-muted">Área: {m.area_coordenacao}</p>
                                    ) : null}
                                  </div>
                                  <button
                                    type="button"
                                    className={btnDanger}
                                    onClick={() => softRemoveEquipe(m)}
                                  >
                                    Remover
                                  </button>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )
                    })}
                  </div>

                  <div className="space-y-2 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-semibold text-ink">Cursos oferecidos</h4>
                    {(ficha.cursos || []).length === 0 ? (
                      <p className="text-sm text-muted">
                        Nenhum curso com período vinculado a esta unidade.
                      </p>
                    ) : (
                      <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                        {(ficha.cursos || []).map((c) => (
                          <li key={c.id}>
                            <button
                              type="button"
                              className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-sm hover:bg-slate-50"
                              onClick={() => openCursoNaEstrutura(c)}
                            >
                              <span>
                                <span className="font-medium text-ink">{c.nome}</span>
                                <span className="ml-2 text-xs text-muted">
                                  {c.periodo_rotulo || 'Período'}
                                </span>
                              </span>
                              <span className="shrink-0 text-xs text-muted">
                                {c.n_turmas} turma(s) · {c.n_disciplinas} disc.
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted">Não foi possível carregar a ficha.</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted">Clique em uma unidade da tabela para abrir a ficha.</p>
          )}
        </section>
      ) : null}

      {/* —— Estrutura Acadêmica —— */}
      {tab === 'estrutura' ? (
        <section className="space-y-5">
          {!periodoSel ? (
            <p className="text-sm text-muted">Crie ou selecione um período letivo para continuar.</p>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-ink">Estrutura do período</h2>
                <button type="button" className={btnPrimary} onClick={() => openCurso(null)}>
                  + Novo curso
                </button>
              </div>
              {cursosDoPeriodo.length === 0 ? (
                <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-muted">
                  Nenhum curso neste período — crie um curso para cadastrar turmas.
                </p>
              ) : null}
              <div className="space-y-3">
                {estruturaNodes.map((node) => renderEstruturaNode(node))}
              </div>
            </>
          )}
        </section>
      ) : null}

      {/* —— Alunos —— */}
      {tab === 'alunos' ? (
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
                className={btnGhost}
                disabled={!filtroTurmaId}
                title={
                  filtroTurmaId
                    ? 'Importar CSV para a turma selecionada'
                    : 'Selecione uma turma no filtro para importar'
                }
                onClick={openImportAlunos}
              >
                Importar alunos
              </button>
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

      {/* —— Situação por período —— */}
      {tab === 'situacao' ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-ink">Situação por período</h2>
              <p className="text-sm text-muted">
                Corte do estado atual por período letivo — não é um histórico de matrículas.
              </p>
            </div>
            <div className="flex flex-wrap items-end gap-2">
              {unidades.length > 1 ? (
                <label className="block text-sm">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                    Unidade
                  </span>
                  <select
                    className={inputCls + ' w-auto min-w-[180px]'}
                    value={situacaoUnidadeId}
                    onChange={(e) => setSituacaoUnidadeId(e.target.value)}
                  >
                    <option value="">Todas</option>
                    {unidades.map((u) => (
                      <option key={u.id} value={u.id}>{u.nome}</option>
                    ))}
                  </select>
                </label>
              ) : null}
              <label className="block text-sm">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                  Curso
                </span>
                <select
                  className={inputCls + ' w-auto min-w-[200px]'}
                  value={situacaoCursoId}
                  onChange={(e) => setSituacaoCursoId(e.target.value)}
                >
                  <option value="">Todos</option>
                  {cursos.map((c) => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-950">
            {SITUACAO_AVISO_UI}
          </div>

          {situacaoLoading ? (
            <p className="text-sm text-muted">Carregando situação…</p>
          ) : situacaoItems.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-muted">
              Nenhum período letivo cadastrado.
            </p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-muted">
                  <tr>
                    <th className="px-4 py-3">Período</th>
                    <th className="px-4 py-3">Ano</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Datas</th>
                    <th className="px-4 py-3">Unidade</th>
                    <th className="px-4 py-3 text-right">Turmas</th>
                    <th
                      className="px-4 py-3 text-right"
                      title="Contagem pelo vínculo atual do aluno à turma do período"
                    >
                      Alunos
                    </th>
                    <th
                      className="px-4 py-3 text-right"
                      title="Professores com alocação ativa neste período (estado atual)"
                    >
                      Professores
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {situacaoItems.map((row) => (
                    <tr key={row.periodo_id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium text-ink">
                        {row.rotulo}
                        {row.em_curso ? (
                          <span className="ml-2 text-[10px] font-bold uppercase text-violet-700">
                            vigente
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-muted">{row.ano_letivo}</td>
                      <td className="px-4 py-3">
                        <span
                          className={[
                            'inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
                            PERIODO_STATUS_CLASS[row.status] || 'bg-slate-100 text-slate-600',
                          ].join(' ')}
                        >
                          {PERIODO_STATUS_LABEL[row.status] || row.status || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted whitespace-nowrap">
                        {(row.data_inicio || '—').slice(0, 10)}
                        {' – '}
                        {(row.data_fim || '—').slice(0, 10)}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {row.unidade_nome || 'Institucional'}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold">{row.n_turmas}</td>
                      <td className="px-4 py-3 text-right font-semibold">{row.n_alunos}</td>
                      <td className="px-4 py-3 text-right font-semibold">{row.n_professores}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      {/* —— Calendário —— */}
      {tab === 'calendario' ? (
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
              renderDayItem={(ev) => {
                const fromPlan = ev.source === 'planejamento'
                return (
                <button
                  type="button"
                  onClick={() => {
                    if (fromPlan) return
                    openCal(ev.data_inicio, ev)
                  }}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-left transition hover:ring-2 hover:ring-school-500/30"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-bold text-ink">{ev.titulo}</p>
                    <span className="text-[10px] font-bold uppercase text-muted">
                      {fromPlan
                        ? ev.tipo_label || 'Planejamento'
                        : CAL_TIPO_LABEL[ev.tipo] || ev.tipo}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-muted">
                    {fromPlan ? 'Planejamento escolar' : ev.data_inicio}
                    {ev.data_fim && ev.data_fim !== ev.data_inicio
                      ? ` até ${ev.data_fim}`
                      : ''}
                    {ev.unidade_nome ? ` · ${ev.unidade_nome}` : ''}
                  </p>
                </button>
                )
              }}
            />
          </div>
        </section>
      ) : null}

      {/* —— Planejamento Escolar —— */}
      {tab === 'planejamento' ? (
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
      {tab === 'comunicacoes' ? (
        <section>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-ink">Mural / Comunicações</h2>
              <p className="text-xs text-muted">Quadro de comunicados — mais recentes primeiro.</p>
            </div>
            <button
              type="button"
              className={btnPrimary}
              onClick={() => openCom(null)}
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
                    <ReplicadoBadge item={item} />
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
                    {item.turma_nome ? ` · ${item.turma_nome}` : ''}
                  </p>
                  {item.status === 'publicado' || item.status === 'agendado' ? (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      <button
                        type="button"
                        className={btnSmall}
                        disabled={busy}
                        onClick={() => openCom(item)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className={btnDanger}
                        disabled={busy}
                        onClick={() => cancelarComunicacao(item)}
                      >
                        Cancelar
                      </button>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

          </div>
        </div>
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

      <Modal
        title={`Adicionar — ${EQUIPE_PAPEL_LABEL[formEquipe.papel] || 'Equipe'}`}
        open={modal === 'equipe'}
        onClose={closeModal}
      >
        <form onSubmit={saveEquipe} className="space-y-3">
          <Field label="Papel">
            <select
              className={inputCls}
              value={formEquipe.papel}
              onChange={(e) => setFormEquipe((f) => ({ ...f, papel: e.target.value }))}
            >
              {Object.entries(EQUIPE_PAPEL_LABEL).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </Field>
          <div className="flex gap-2 text-sm">
            <button
              type="button"
              className={formEquipe.modo === 'gestor' ? btnPrimary : btnGhost}
              onClick={() => setFormEquipe((f) => ({ ...f, modo: 'gestor' }))}
            >
              Gestor existente
            </button>
            <button
              type="button"
              className={formEquipe.modo === 'avulso' ? btnPrimary : btnGhost}
              onClick={() => setFormEquipe((f) => ({ ...f, modo: 'avulso' }))}
            >
              Contato avulso
            </button>
          </div>
          {formEquipe.modo === 'gestor' ? (
            <Field label="Gestor">
              <select
                className={inputCls}
                required
                value={formEquipe.gestor_id}
                onChange={(e) => setFormEquipe((f) => ({ ...f, gestor_id: e.target.value }))}
              >
                <option value="">Selecione…</option>
                {gestoresOpts.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.nome} ({g.email})
                  </option>
                ))}
              </select>
            </Field>
          ) : (
            <>
              <Field label="Nome">
                <input
                  className={inputCls}
                  required
                  value={formEquipe.nome}
                  onChange={(e) => setFormEquipe((f) => ({ ...f, nome: e.target.value }))}
                />
              </Field>
              <Field label="E-mail">
                <input
                  type="email"
                  className={inputCls}
                  value={formEquipe.email}
                  onChange={(e) => setFormEquipe((f) => ({ ...f, email: e.target.value }))}
                />
              </Field>
              <Field label="Telefone">
                <input
                  className={inputCls}
                  value={formEquipe.telefone}
                  onChange={(e) => setFormEquipe((f) => ({ ...f, telefone: e.target.value }))}
                />
              </Field>
            </>
          )}
          {formEquipe.papel === 'coordenador' ? (
            <Field label="Área de coordenação (opcional)">
              <input
                className={inputCls}
                value={formEquipe.area_coordenacao}
                onChange={(e) =>
                  setFormEquipe((f) => ({ ...f, area_coordenacao: e.target.value }))
                }
              />
            </Field>
          ) : null}
          <button type="submit" disabled={busy} className={btnPrimary}>
            {busy ? 'Salvando…' : 'Adicionar'}
          </button>
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

      <Modal
        title={
          editId
            ? 'Editar disciplina'
            : context.curso_id
              ? 'Associar disciplina ao curso'
              : 'Nova disciplina'
        }
        open={modal === 'disciplina'}
        onClose={closeModal}
      >
        <form onSubmit={saveDisc} className="space-y-3">
          {!editId && context.curso_id ? (
            <div className="flex gap-2">
              <button
                type="button"
                className={formDisc.modo === 'nova' ? btnPrimary : btnGhost}
                onClick={() => setFormDisc((f) => ({ ...f, modo: 'nova', disciplina_id: '' }))}
              >
                Criar nova
              </button>
              <button
                type="button"
                className={formDisc.modo === 'existente' ? btnPrimary : btnGhost}
                onClick={() => setFormDisc((f) => ({ ...f, modo: 'existente' }))}
              >
                Associar existente
              </button>
            </div>
          ) : null}
          {!editId && formDisc.modo === 'existente' && context.curso_id ? (
            <Field label="Disciplina do catálogo">
              <select
                className={inputCls}
                required
                value={formDisc.disciplina_id}
                onChange={(e) => setFormDisc((f) => ({ ...f, disciplina_id: e.target.value }))}
              >
                <option value="">Selecione</option>
                {disciplinas
                  .filter((d) => d.ativo !== false && !discInCurso(d, context.curso_id))
                  .map((d) => (
                    <option key={d.id} value={d.id}>{d.nome}</option>
                  ))}
              </select>
            </Field>
          ) : (
            <>
              <Field label="Nome">
                <input className={inputCls} required={formDisc.modo !== 'existente'} value={formDisc.nome} onChange={(e) => setFormDisc((f) => ({ ...f, nome: e.target.value }))} />
              </Field>
              <Field label="Ementa">
                <textarea className={inputCls} rows={3} value={formDisc.ementa_macro} onChange={(e) => setFormDisc((f) => ({ ...f, ementa_macro: e.target.value }))} />
              </Field>
              <Field label="Carga horária">
                <input type="number" className={inputCls} value={formDisc.carga_horaria} onChange={(e) => setFormDisc((f) => ({ ...f, carga_horaria: e.target.value }))} />
              </Field>
            </>
          )}
          <button type="submit" disabled={busy} className={btnPrimary}>
            {busy ? 'Salvando…' : editId ? 'Salvar' : formDisc.modo === 'existente' ? 'Associar' : 'Salvar'}
          </button>
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
            <select className={inputCls} required value={formTurma.curso_id} onChange={(e) => setFormTurma((f) => ({ ...f, curso_id: e.target.value }))}>
              <option value="">Selecione o curso</option>
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
        title="Importar alunos"
        open={modal === 'importAlunos'}
        onClose={closeModal}
        wide
      >
        <p className="mb-3 text-sm text-muted">
          Turma destino:{' '}
          <span className="font-semibold text-ink">
            {turmas.find((t) => t.id === filtroTurmaId)?.nome || '—'}
          </span>
          . Alunos novos e atualizações na mesma turma entram nesta turma.
          Matrículas de outra turma só mudam se você autorizar explicitamente.
        </p>
        {importStep === 'upload' ? (
          <div className="space-y-3">
            <Field label="Arquivo CSV">
              <input
                type="file"
                accept=".csv,text/csv"
                className="block w-full text-sm"
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              />
            </Field>
            <button
              type="button"
              className="text-sm font-semibold text-violet-700 hover:underline"
              onClick={downloadModeloCsv}
            >
              Baixar modelo CSV
            </button>
            <div className="flex flex-wrap gap-2 pt-1">
              <button
                type="button"
                className={btnPrimary}
                disabled={busy || !importFile}
                onClick={runImportPreview}
              >
                {busy ? 'Analisando…' : 'Analisar arquivo'}
              </button>
              <button type="button" className={btnGhost} onClick={closeModal}>
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {[
                ['Total', importPreview?.resumo?.total],
                ['Ok', importPreview?.resumo?.ok],
                ['Erros', importPreview?.resumo?.erro],
                ['Novos', importPreview?.resumo?.novos],
                ['Atualizações', importPreview?.resumo?.atualizacoes],
                ['Mudança de turma', importPreview?.resumo?.mudancas_turma],
              ].map(([label, n]) => (
                <span
                  key={label}
                  className={
                    label === 'Mudança de turma'
                      ? 'inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900'
                      : 'inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-ink'
                  }
                >
                  <span className="font-medium text-muted">{label}</span>
                  {n ?? 0}
                </span>
              ))}
            </div>
            {(importPreview?.resumo?.mudancas_turma || 0) > 0 && (
              <label className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={importPermitirMudancaTurma}
                  onChange={(e) => setImportPermitirMudancaTurma(e.target.checked)}
                />
                <span>
                  Autorizar mudança de turma para{' '}
                  <strong>{importPreview.resumo.mudancas_turma}</strong> aluno(s).
                  Sem esta autorização, essas linhas não serão aplicadas.
                </span>
              </label>
            )}
            <div className="max-h-72 overflow-auto rounded-xl border border-slate-200">
              <table className="min-w-full text-left text-xs">
                <thead className="sticky top-0 bg-slate-50 text-[10px] uppercase text-muted">
                  <tr>
                    <th className="px-2 py-2">Linha</th>
                    <th className="px-2 py-2">Nome</th>
                    <th className="px-2 py-2">Matrícula</th>
                    <th className="px-2 py-2">Nascimento</th>
                    <th className="px-2 py-2">Status</th>
                    <th className="px-2 py-2">Ação</th>
                    <th className="px-2 py-2">Turma</th>
                    <th className="px-2 py-2">Erro</th>
                  </tr>
                </thead>
                <tbody>
                  {(importPreview?.linhas || []).map((L) => (
                    <tr
                      key={`${L.linha}-${L.matricula || ''}`}
                      className={
                        L.acao === 'mudar_turma'
                          ? 'border-t border-amber-100 bg-amber-50/70'
                          : 'border-t border-slate-100'
                      }
                    >
                      <td className="px-2 py-1.5 text-muted">{L.linha}</td>
                      <td className="px-2 py-1.5 font-medium text-ink">{L.nome || '—'}</td>
                      <td className="px-2 py-1.5">{L.matricula || '—'}</td>
                      <td className="px-2 py-1.5 text-muted">{L.data_nascimento || '—'}</td>
                      <td className="px-2 py-1.5">
                        <span
                          className={
                            L.status === 'ok'
                              ? 'font-semibold text-emerald-700'
                              : 'font-semibold text-red-700'
                          }
                        >
                          {L.status === 'ok' ? 'Ok' : L.status === 'erro' ? 'Erro' : L.status}
                        </span>
                      </td>
                      <td className="px-2 py-1.5 text-muted">
                        {L.acao === 'criar'
                          ? 'Novo'
                          : L.acao === 'atualizar'
                            ? 'Atualizar'
                            : L.acao === 'mudar_turma'
                              ? 'Mudança de turma'
                              : '—'}
                      </td>
                      <td className="px-2 py-1.5 text-muted">
                        {L.acao === 'mudar_turma'
                          ? `${L.turma_atual_nome || 'sem turma'} → ${L.turma_nova_nome || 'esta turma'}`
                          : L.acao === 'atualizar'
                            ? (L.turma_atual_nome || L.turma_nova_nome || '—')
                            : (L.turma_nova_nome || '—')}
                      </td>
                      <td className="px-2 py-1.5 text-red-700">{L.erro || ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className={btnPrimary}
                disabled={busy || !(importPreview?.resumo?.ok > 0)}
                onClick={runImportConfirm}
              >
                {busy ? 'Importando…' : 'Confirmar importação'}
              </button>
              <button
                type="button"
                className={btnGhost}
                disabled={busy}
                onClick={() => {
                  setImportStep('upload')
                  setImportPreview(null)
                  setImportPermitirMudancaTurma(false)
                }}
              >
                Voltar
              </button>
              <button type="button" className={btnGhost} disabled={busy} onClick={closeModal}>
                Cancelar
              </button>
            </div>
          </div>
        )}
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
          {discsForAloc(context.turma).length === 0 ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Este curso ainda não tem disciplinas no catálogo. Associe disciplinas ao curso
              antes de alocar um professor.
            </p>
          ) : (
            <>
              <Field label="Disciplina do catálogo do curso">
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
                  {professores.map((p) => {
                    const hab = Array.isArray(p.habilitacao_disciplina_ids)
                      ? p.habilitacao_disciplina_ids
                      : []
                    const habilitado = formAloc.disciplina_id && hab.includes(formAloc.disciplina_id)
                    return (
                      <option key={p.id} value={p.id}>
                        {p.label || p.email || p.email_convite || p.id}
                        {habilitado ? ' · habilitado' : ''}
                      </option>
                    )
                  })}
                </select>
              </Field>
              <p className="text-xs text-muted">
                “Habilitado” é só informativo — qualquer professor da equipe pode ser alocado.
              </p>
              <button type="submit" disabled={busy} className={btnPrimary}>{busy ? 'Salvando…' : 'Alocar'}</button>
            </>
          )}
        </form>
      </Modal>

      <Modal
        title={editId ? 'Editar comunicado' : 'Publicar comunicado'}
        open={modal === 'comunicacao'}
        onClose={closeModal}
        wide
      >
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
              <select
                className={inputCls}
                value={formCom.publico_alvo}
                onChange={(e) =>
                  setFormCom((f) => ({
                    ...f,
                    publico_alvo: e.target.value,
                    unidade_id: e.target.value === 'unidade' ? f.unidade_id || user?.unidade_id || '' : '',
                    turma_id: e.target.value === 'turma' ? f.turma_id : '',
                  }))
                }
              >
                {(user?.unidade_id
                  ? COM_PUBLICOS.filter((t) => t.value === 'unidade' || t.value === 'turma')
                  : COM_PUBLICOS
                ).map((t) => (
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
          {formCom.publico_alvo === 'unidade' ? (
            <Field label="Unidade">
              <select
                className={inputCls}
                required
                value={formCom.unidade_id}
                onChange={(e) => setFormCom((f) => ({ ...f, unidade_id: e.target.value }))}
              >
                <option value="">Selecione</option>
                {unidades.map((u) => (
                  <option key={u.id} value={u.id}>{u.nome}</option>
                ))}
              </select>
            </Field>
          ) : null}
          {formCom.publico_alvo === 'turma' ? (
            <Field label="Turma">
              <select
                className={inputCls}
                required
                value={formCom.turma_id}
                onChange={(e) => setFormCom((f) => ({ ...f, turma_id: e.target.value }))}
              >
                <option value="">Selecione</option>
                {turmas
                  .filter((t) => !user?.unidade_id || t.unidade_id === user.unidade_id)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nome}
                      {t.unidade_nome ? ` · ${t.unidade_nome}` : ''}
                    </option>
                  ))}
              </select>
            </Field>
          ) : null}
          <button type="submit" disabled={busy} className={btnPrimary}>
            {busy ? 'Salvando…' : editId ? 'Salvar e enviar ao mural' : 'Publicar'}
          </button>
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

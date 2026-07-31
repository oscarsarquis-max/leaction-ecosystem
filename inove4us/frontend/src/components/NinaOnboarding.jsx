import { useEffect, useId, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { NINA_AVATAR_SRC } from '../lib/ninaAvatar'
import {
  criarCurso,
  criarDisciplina,
  criarInstituicao,
  criarPeriodo,
  isSchemaPendingError,
  listarInstituicoes,
  marcarPeriodoEmCurso,
} from '../services/instituicoesService'

function storageKey(userId) {
  return `i4_has_completed_onboarding_${userId || 'anon'}`
}

function readDone(userId) {
  try {
    return localStorage.getItem(storageKey(userId)) === '1'
  } catch {
    return false
  }
}

function writeDone(userId) {
  try {
    localStorage.setItem(storageKey(userId), '1')
  } catch {
    /* ignore quota / private mode */
  }
}

function defaultPeriodoPayload() {
  const year = new Date().getFullYear()
  return {
    rotulo: `Ano Letivo ${year}`,
    ano_letivo: year,
    tipo_periodo: 'anual',
    etapa: '',
    data_inicio: `${year}-02-01`,
    data_fim: `${year}-12-15`,
    carga_horaria_total_horas: '',
    duracao_padrao_aula_min: 50,
    dias_semana_letivos: ['seg', 'ter', 'qua', 'qui', 'sex'],
    status: 'em_andamento',
    em_curso: true,
  }
}

const STEPS = [
  {
    key: 'instituicao',
    title: 'Onde você dá aula?',
    text: 'Olá, Professor(a)! Sou a Nina. Para eu organizar sua mesa de trabalho, onde você dá aula hoje?',
    label: 'Instituição',
    placeholder: 'Ex.: Escola Municipal Dom Pedro II',
    field: 'instituicao',
  },
  {
    key: 'curso',
    title: 'Curso ou programa',
    text: 'Legal! E nessa instituição, qual é o curso ou programa?',
    label: 'Curso / Contexto',
    placeholder: 'Ex.: 1º ano do Ensino Médio',
    field: 'curso',
  },
  {
    key: 'disciplina',
    title: 'Sua disciplina',
    text: 'Para fechar, qual disciplina você ensina lá?',
    label: 'Disciplina',
    placeholder: 'Ex.: Física · Termodinâmica',
    field: 'disciplina',
  },
]

/**
 * Onboarding guiado da Nina — primeiro acesso do professor.
 * Não fecha por clique fora; só ao concluir os 3 passos.
 */
export default function NinaOnboarding() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const titleId = useId()
  const userId = user?.id_clie

  const [open, setOpen] = useState(false)
  const [checking, setChecking] = useState(true)
  const [step, setStep] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    instituicao: '',
    curso: '',
    disciplina: '',
  })

  useEffect(() => {
    if (!userId) {
      setOpen(false)
      setChecking(false)
      return undefined
    }

    let cancelled = false
    ;(async () => {
      setChecking(true)

      // ?reset_onboarding=1 limpa o flag local (útil em homologação).
      try {
        const sp = new URLSearchParams(window.location.search)
        if (sp.get('reset_onboarding') === '1') {
          localStorage.removeItem(storageKey(userId))
        }
      } catch {
        /* ignore */
      }

      // Se já tem instituição ativa, não força o tour de novo.
      try {
        const data = await listarInstituicoes()
        const list = Array.isArray(data?.instituicoes) ? data.instituicoes : []
        if (list.length > 0) {
          writeDone(userId)
          if (!cancelled) {
            setOpen(false)
            setChecking(false)
          }
          return
        }
      } catch {
        /* schema pendente ou rede — ainda assim oferecemos o onboarding */
      }

      // Sem instituição: reabre o onboarding mesmo com flag antiga no localStorage.
      try {
        localStorage.removeItem(storageKey(userId))
      } catch {
        /* ignore */
      }

      if (!cancelled) {
        setOpen(true)
        setChecking(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [userId])

  const current = STEPS[step]
  const value = form[current.field]
  const canAdvance = value.trim().length >= 2

  const progress = useMemo(
    () => ((step + 1) / STEPS.length) * 100,
    [step],
  )

  function setField(field, next) {
    setForm((prev) => ({ ...prev, [field]: next }))
    setError('')
  }

  function handleBack() {
    if (step === 0 || busy) return
    setStep((s) => Math.max(0, s - 1))
    setError('')
  }

  async function handleNext() {
    if (!canAdvance || busy) return
    if (step < STEPS.length - 1) {
      setStep((s) => s + 1)
      return
    }
    await finish()
  }

  async function finish() {
    setBusy(true)
    setError('')
    try {
      const instRes = await criarInstituicao({
        nome: form.instituicao.trim(),
        tipo_instituicao: 'escola',
        segmento: '',
        rede: 'nao_informado',
        cidade: '',
        uf: '',
        pais: 'BR',
        observacoes: 'Criado no onboarding da Nina',
      })
      const instituicaoId = instRes?.instituicao?.id
      if (!instituicaoId) throw new Error('Não foi possível criar a instituição.')

      const perRes = await criarPeriodo(instituicaoId, defaultPeriodoPayload())
      const periodoId = perRes?.periodo?.id || perRes?.id
      if (!periodoId) throw new Error('Não foi possível criar o período letivo.')

      try {
        await marcarPeriodoEmCurso(periodoId)
      } catch {
        /* não bloqueia o onboarding */
      }

      const curRes = await criarCurso(periodoId, {
        nome: form.curso.trim(),
        nivel: null,
        turma_turno: '',
        carga_horaria_total_horas: null,
        observacoes: '',
      })
      const cursoId = curRes?.curso?.id || curRes?.id
      if (!cursoId) throw new Error('Não foi possível criar o curso.')

      await criarDisciplina(cursoId, {
        nome: form.disciplina.trim(),
        codigo: '',
        carga_horaria_horas: null,
        ementa: '',
      })

      writeDone(userId)
      setOpen(false)
      navigate('/mesa-do-inovador', { replace: true })
    } catch (err) {
      if (isSchemaPendingError(err)) {
        setError(
          'O cadastro escolar ainda está sendo preparado. Você pode continuar pela Mesa e voltar em Instituições.',
        )
        writeDone(userId)
        setOpen(false)
        navigate('/mesa-do-inovador', { replace: true })
      } else {
        setError(err?.message || 'Não foi possível salvar. Tente de novo.')
      }
    } finally {
      setBusy(false)
    }
  }

  if (checking || !open || !userId) return null

  const isLast = step === STEPS.length - 1

  return (
    <div
      className="fixed inset-0 z-[80] flex items-end justify-center bg-bordo-deep/45 p-4 backdrop-blur-[2px] sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <div
        className="relative w-full max-w-md overflow-hidden rounded-3xl border border-brand-100 bg-white shadow-2xl shadow-bordo/20"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="h-1.5 bg-brand-100">
          <div
            className="h-full bg-gradient-to-r from-brand-500 to-bordo transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="px-6 pb-6 pt-7 sm:px-8">
          <div className="flex flex-col items-center text-center">
            <div className="relative mb-4">
              <div className="absolute -inset-2 rounded-full bg-gradient-to-br from-brand-200/80 to-bordo/10 blur-md" />
              {/* object-contain + fundo: o JPEG é retrato; cover cortava o topo da cabeça */}
              <div className="relative h-32 w-32 overflow-hidden rounded-full bg-[#4a3428] p-1.5 ring-4 ring-white shadow-lg sm:h-36 sm:w-36">
                <img
                  src={NINA_AVATAR_SRC}
                  alt="Nina, assistente da inove4us"
                  className="h-full w-full rounded-full object-contain object-top"
                />
              </div>
            </div>
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-brand-600">
              Passo {step + 1} de {STEPS.length}
            </p>
            <h2
              id={titleId}
              className="mt-1 font-display text-2xl font-bold text-bordo-deep"
            >
              {current.title}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
              {current.text}
            </p>
          </div>

          <label className="mt-6 block text-left">
            <span className="field-label">{current.label}</span>
            <input
              className="field-input mt-1 min-h-12"
              value={value}
              onChange={(e) => setField(current.field, e.target.value.slice(0, 160))}
              placeholder={current.placeholder}
              autoFocus
              disabled={busy}
              maxLength={160}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  void handleNext()
                }
              }}
            />
          </label>

          {error ? (
            <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-950">
              {error}
            </p>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              className="btn-ghost min-h-11 !px-4 text-sm disabled:opacity-40"
              onClick={handleBack}
              disabled={step === 0 || busy}
            >
              Voltar
            </button>
            <button
              type="button"
              className="btn-primary min-h-11 flex-1 sm:flex-none sm:min-w-[200px]"
              onClick={() => void handleNext()}
              disabled={!canAdvance || busy}
            >
              {busy ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Organizando…
                </>
              ) : isLast ? (
                'Pronto! Ir para minha Mesa.'
              ) : (
                'Continuar'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useId, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { NINA_AVATAR_SRC } from '../lib/ninaAvatar'
import {
  clearNinaOnboardingLocal,
  consumeNinaOnboardingReplay,
  writeNinaOnboardingDone,
} from '../lib/ninaOnboarding'
import {
  criarCurso,
  criarDisciplina,
  criarInstituicao,
  criarPeriodo,
  isSchemaPendingError,
  marcarPeriodoEmCurso,
} from '../services/instituicoesService'

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

/** Passos do cadastro escolar (só se o professor optar por cadastrar agora). */
const SCHOOL_STEPS = [
  {
    key: 'instituicao',
    title: 'Onde você dá aula?',
    text: 'Beleza. Qual é o nome da instituição? Depois você pode cadastrar outras em Instituições — e o vínculo com escola nas aulas e desafios continua opcional.',
    label: 'Instituição',
    placeholder: 'Ex.: Escola Municipal Dom Pedro II',
    field: 'instituicao',
  },
  {
    key: 'curso',
    title: 'Curso ou programa',
    text: 'Nessa instituição, qual é o curso ou programa?',
    label: 'Curso / Contexto',
    placeholder: 'Ex.: 1º ano do Ensino Médio',
    field: 'curso',
  },
  {
    key: 'disciplina',
    title: 'Sua disciplina',
    text: 'Para fechar este primeiro cadastro, qual disciplina você ensina lá?',
    label: 'Disciplina',
    placeholder: 'Ex.: Física · Termodinâmica',
    field: 'disciplina',
  },
]

/**
 * Onboarding guiado da Nina — primeiro acesso do professor.
 * Escopo do produto → convite (opcional) a cadastrar escola → Mesa.
 * Não fecha por clique fora; conclui ao pular ou ao salvar o cadastro.
 */
export default function NinaOnboarding() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const titleId = useId()
  const userId = user?.id_clie
  const serverDone = Boolean(user?.nina_onboarding_done)

  const [open, setOpen] = useState(false)
  const [checking, setChecking] = useState(true)
  /** welcome | ask_escola | school (índice em SCHOOL_STEPS) */
  const [phase, setPhase] = useState('welcome')
  const [schoolStep, setSchoolStep] = useState(0)
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

      // ?reset_onboarding=1 ou pedido pós-login — limpa DB + reabre.
      const forceReplay = consumeNinaOnboardingReplay(userId)
      if (forceReplay) {
        try {
          const data = await api.resetNinaOnboarding()
          if (!cancelled && data?.user) {
            setUser((prev) =>
              prev
                ? { ...prev, ...data.user, nina_onboarding_done: false }
                : { ...data.user, nina_onboarding_done: false },
            )
          } else if (!cancelled) {
            setUser((prev) =>
              prev ? { ...prev, nina_onboarding_done: false } : prev,
            )
          }
        } catch {
          if (!cancelled) {
            setUser((prev) =>
              prev ? { ...prev, nina_onboarding_done: false } : prev,
            )
          }
        }
        if (!cancelled) {
          clearNinaOnboardingLocal(userId)
          setPhase('welcome')
          setSchoolStep(0)
          setOpen(true)
          setChecking(false)
        }
        return
      }

      // Fonte da verdade: servidor (auth/me).
      if (serverDone) {
        writeNinaOnboardingDone(userId)
        if (!cancelled) {
          setOpen(false)
          setChecking(false)
        }
        return
      }

      if (!cancelled) {
        setPhase('welcome')
        setSchoolStep(0)
        setOpen(true)
        setChecking(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [userId, serverDone, setUser])

  const schoolCurrent = SCHOOL_STEPS[schoolStep]
  const schoolValue = schoolCurrent ? form[schoolCurrent.field] : ''
  const canAdvanceSchool = schoolValue.trim().length >= 2

  const progress = useMemo(() => {
    if (phase === 'welcome') return 20
    if (phase === 'ask_escola') return 40
    return 40 + ((schoolStep + 1) / SCHOOL_STEPS.length) * 60
  }, [phase, schoolStep])

  const stepLabel = useMemo(() => {
    if (phase === 'welcome') return 'Boas-vindas'
    if (phase === 'ask_escola') return 'Primeiro passo'
    return `Cadastro ${schoolStep + 1} de ${SCHOOL_STEPS.length}`
  }, [phase, schoolStep])

  function setField(field, next) {
    setForm((prev) => ({ ...prev, [field]: next }))
    setError('')
  }

  async function completeAndGo() {
    setBusy(true)
    setError('')
    try {
      const data = await api.completeNinaOnboarding()
      writeNinaOnboardingDone(userId)
      if (data?.user) {
        setUser((prev) =>
          prev
            ? { ...prev, ...data.user, nina_onboarding_done: true }
            : { ...data.user, nina_onboarding_done: true },
        )
      } else {
        setUser((prev) =>
          prev ? { ...prev, nina_onboarding_done: true } : prev,
        )
      }
      setOpen(false)
      navigate('/mesa-do-inovador', { replace: true })
    } catch (err) {
      setError(
        err?.message ||
          'Não foi possível concluir o onboarding. Tente de novo.',
      )
    } finally {
      setBusy(false)
    }
  }

  function handleSkipSchool() {
    if (busy) return
    void completeAndGo()
  }

  function handleBack() {
    if (busy) return
    setError('')
    if (phase === 'ask_escola') {
      setPhase('welcome')
      return
    }
    if (phase === 'school') {
      if (schoolStep === 0) {
        setPhase('ask_escola')
        return
      }
      setSchoolStep((s) => Math.max(0, s - 1))
    }
  }

  async function handleSchoolNext() {
    if (!canAdvanceSchool || busy) return
    if (schoolStep < SCHOOL_STEPS.length - 1) {
      setSchoolStep((s) => s + 1)
      return
    }
    await finishWithSchool()
  }

  async function finishWithSchool() {
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

      await completeAndGo()
    } catch (err) {
      if (isSchemaPendingError(err)) {
        setError(
          'O cadastro escolar ainda está sendo preparado. Você pode continuar pela Mesa e voltar em Instituições.',
        )
        await completeAndGo()
      } else {
        setError(err?.message || 'Não foi possível salvar. Tente de novo.')
      }
    } finally {
      setBusy(false)
    }
  }

  if (checking || !open || !userId) return null

  const isLastSchool = phase === 'school' && schoolStep === SCHOOL_STEPS.length - 1

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
              {stepLabel}
            </p>

            {phase === 'welcome' ? (
              <>
                <h2
                  id={titleId}
                  className="mt-1 font-display text-2xl font-bold text-bordo-deep"
                >
                  Olá! Eu sou a Nina
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
                  Estou aqui para te acompanhar no dia a dia pedagógico. O escopo
                  principal do inove4us é:
                </p>
                <ul className="mt-4 w-full space-y-2.5 text-left text-sm text-bordo-deep">
                  <li className="rounded-2xl bg-brand-50/80 px-3.5 py-2.5 leading-snug">
                    <span className="font-semibold text-bordo">Cadastro</span>
                    <span className="text-bordo-soft">
                      {' '}
                      — instituição, períodos, cursos e disciplinas, quando fizer sentido.
                    </span>
                  </li>
                  <li className="rounded-2xl bg-brand-50/80 px-3.5 py-2.5 leading-snug">
                    <span className="font-semibold text-bordo">Planejamento</span>
                    <span className="text-bordo-soft">
                      {' '}
                      — organizar o que vem pela frente na sua mesa.
                    </span>
                  </li>
                  <li className="rounded-2xl bg-brand-50/80 px-3.5 py-2.5 leading-snug">
                    <span className="font-semibold text-bordo">Dia a dia</span>
                    <span className="text-bordo-soft">
                      {' '}
                      — registrar o trabalho pedagógico das aulas.
                    </span>
                  </li>
                  <li className="rounded-2xl bg-brand-50/80 px-3.5 py-2.5 leading-snug">
                    <span className="font-semibold text-bordo">Desafio</span>
                    <span className="text-bordo-soft">
                      {' '}
                      — planejar e acompanhar desafios de aprendizagem.
                    </span>
                  </li>
                </ul>
              </>
            ) : null}

            {phase === 'ask_escola' ? (
              <>
                <h2
                  id={titleId}
                  className="mt-1 font-display text-2xl font-bold text-bordo-deep"
                >
                  Quer começar pela escola?
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
                  Cadastrar uma instituição agora ajuda a organizar o contexto —
                  e você pode repetir esse passo depois, em Instituições, quando
                  quiser. Isso{' '}
                  <strong className="font-semibold text-bordo-deep">
                    não obriga
                  </strong>{' '}
                  vincular cada aula ou desafio a essa escola: o vínculo continua
                  opcional.
                </p>
                <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
                  Prefere explorar a Mesa primeiro? Sem problema — pulamos o
                  cadastro por agora.
                </p>
              </>
            ) : null}

            {phase === 'school' && schoolCurrent ? (
              <>
                <h2
                  id={titleId}
                  className="mt-1 font-display text-2xl font-bold text-bordo-deep"
                >
                  {schoolCurrent.title}
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
                  {schoolCurrent.text}
                </p>
              </>
            ) : null}
          </div>

          {phase === 'school' && schoolCurrent ? (
            <label className="mt-6 block text-left">
              <span className="field-label">{schoolCurrent.label}</span>
              <input
                className="field-input mt-1 min-h-12"
                value={schoolValue}
                onChange={(e) =>
                  setField(schoolCurrent.field, e.target.value.slice(0, 160))
                }
                placeholder={schoolCurrent.placeholder}
                autoFocus
                disabled={busy}
                maxLength={160}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void handleSchoolNext()
                  }
                }}
              />
            </label>
          ) : null}

          {error ? (
            <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-950">
              {error}
            </p>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            {phase === 'welcome' ? (
              <button
                type="button"
                className="btn-primary min-h-11 w-full"
                onClick={() => setPhase('ask_escola')}
              >
                Continuar
              </button>
            ) : null}

            {phase === 'ask_escola' ? (
              <>
                <button
                  type="button"
                  className="btn-ghost min-h-11 !px-4 text-sm"
                  onClick={handleBack}
                  disabled={busy}
                >
                  Voltar
                </button>
                <div className="flex w-full flex-col gap-2 sm:ml-auto sm:w-auto sm:min-w-[220px]">
                  <button
                    type="button"
                    className="btn-primary min-h-11 w-full"
                    onClick={() => {
                      setSchoolStep(0)
                      setPhase('school')
                      setError('')
                    }}
                    disabled={busy}
                  >
                    Cadastrar instituição agora
                  </button>
                  <button
                    type="button"
                    className="btn-ghost min-h-11 w-full text-sm"
                    onClick={handleSkipSchool}
                    disabled={busy}
                  >
                    Agora não — ir para a Mesa
                  </button>
                </div>
              </>
            ) : null}

            {phase === 'school' ? (
              <>
                <button
                  type="button"
                  className="btn-ghost min-h-11 !px-4 text-sm disabled:opacity-40"
                  onClick={handleBack}
                  disabled={busy}
                >
                  Voltar
                </button>
                <div className="flex flex-1 flex-col gap-2 sm:flex-none sm:min-w-[200px]">
                  <button
                    type="button"
                    className="btn-primary min-h-11 w-full"
                    onClick={() => void handleSchoolNext()}
                    disabled={!canAdvanceSchool || busy}
                  >
                    {busy ? (
                      <>
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                        Organizando…
                      </>
                    ) : isLastSchool ? (
                      'Pronto! Ir para minha Mesa.'
                    ) : (
                      'Continuar'
                    )}
                  </button>
                  {schoolStep === 0 ? (
                    <button
                      type="button"
                      className="btn-ghost min-h-10 w-full text-sm"
                      onClick={handleSkipSchool}
                      disabled={busy}
                    >
                      Prefiro pular o cadastro
                    </button>
                  ) : null}
                </div>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

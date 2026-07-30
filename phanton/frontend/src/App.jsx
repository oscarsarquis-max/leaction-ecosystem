import { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Circle,
  Loader2,
  Lock,
  Play,
  ShieldCheck,
  Sparkles,
  Workflow,
} from 'lucide-react'
import CopyableBlock from './components/CopyableBlock'
import FixedTextField from './components/FixedTextField'
import PhaseCard from './components/PhaseCard'
import PipelineGraph from './components/dag/PipelineGraph'
import PipelineStatusBar from './components/PipelineStatusBar'
import RequirementsDraftPanel from './components/RequirementsDraftPanel'
import AcceptedProjectsPanel from './components/AcceptedProjectsPanel'
import RunHistory from './components/RunHistory'
import LinearExportButton from './components/LinearExportButton'
import {
  PROMPT_COMPOSITION_HINTS,
  analyzePromptSufficiency,
  extractInitialPromptFromSpec,
} from './lib/promptSufficiency'
import { findLinearExportCandidate } from './lib/taskBreakdown'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8010'

/** Spec mínimo ao começar do zero — sem fases de exemplo. */
const BLANK_SPEC = `{
  "description": "",
  "version": "1.0",
  "warnings": [],
  "phases": {}
}`

function phasesFromSpecText(specText) {
  try {
    const spec = JSON.parse(specText)
    const phases = spec?.phases
    if (!phases || typeof phases !== 'object') return []
    return Object.entries(phases)
      .map(([phase_id, cfg]) => ({
        phase_id,
        name: cfg?.name || phase_id,
        status: 'PENDING',
        order: Number(cfg?.order) || 999,
      }))
      .sort((a, b) => a.order - b.order)
  } catch {
    return []
  }
}

function warningsFromSpecText(specText) {
  try {
    const spec = JSON.parse(specText)
    const warnings = spec?.warnings
    if (!Array.isArray(warnings)) return []
    return warnings.filter(
      (w) => w && typeof w === 'object' && (w.descricao || w.campo),
    )
  } catch {
    return []
  }
}

function App() {
  const [naturalPrompt, setNaturalPrompt] = useState('')
  const [specText, setSpecText] = useState(BLANK_SPEC)
  const [runId, setRunId] = useState(null)
  const [runStatus, setRunStatus] = useState(null)
  const [phases, setPhases] = useState([])
  const [starting, setStarting] = useState(false)
  const [generatingSpec, setGeneratingSpec] = useState(false)
  const [draftingRequirements, setDraftingRequirements] = useState(false)
  const [requirementsDraft, setRequirementsDraft] = useState(null)
  const [requirementsReady, setRequirementsReady] = useState(false)
  const [approvingToken, setApprovingToken] = useState(null)
  const [deliveringModulo, setDeliveringModulo] = useState(null)
  const [autoApprove, setAutoApprove] = useState(false)
  const [reopeningPhaseId, setReopeningPhaseId] = useState(null)
  const [error, setError] = useState(null)
  const [historyItems, setHistoryItems] = useState([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [statusBarBump, setStatusBarBump] = useState(0)
  const [canAccept, setCanAccept] = useState(false)
  const [immutable, setImmutable] = useState(false)
  const [projectMeta, setProjectMeta] = useState(null)
  const [accepting, setAccepting] = useState(false)
  const [pendingSubstituteRunId, setPendingSubstituteRunId] = useState(null)
  const [acceptedPanelKey, setAcceptedPanelKey] = useState(0)
  const [phasesView, setPhasesView] = useState('graph') // 'graph' | 'list'

  const sufficiency = useMemo(
    () => analyzePromptSufficiency(naturalPrompt),
    [naturalPrompt],
  )

  const parsedSpec = useMemo(() => {
    try {
      const spec = JSON.parse(specText)
      return spec && typeof spec === 'object' ? spec : null
    } catch {
      return null
    }
  }, [specText])

  const contextWarnings = useMemo(
    () => warningsFromSpecText(specText),
    [specText],
  )

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const { data } = await axios.get(`${API_BASE}/api/pipeline`, {
        params: { limit: 40 },
      })
      setHistoryItems(data.items || [])
      setHistoryTotal(data.total || 0)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Falha ao carregar histórico')
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  const fetchStatus = useCallback(async (id, { syncSpec = false } = {}) => {
    const { data } = await axios.get(`${API_BASE}/api/pipeline/${id}`)
    setRunStatus(data.status)
    if (data.phases?.length) {
      setPhases(data.phases)
    }
    if (data.spec && typeof data.spec === 'object') {
      setAutoApprove(Boolean(data.spec.auto_approve))
      if (data.spec.structured_requirements) {
        setRequirementsDraft(data.spec.structured_requirements)
        setRequirementsReady(
          data.spec.structured_requirements.perfil_sugerido === 'software_saas',
        )
      }
      if (syncSpec) {
        setSpecText(JSON.stringify(data.spec, null, 2))
      }
    }
    setCanAccept(Boolean(data.can_accept))
    setImmutable(Boolean(data.immutable))
    setProjectMeta({
      project_key: data.project_key,
      project_name: data.project_name,
      version: data.version,
      acceptance_status: data.acceptance_status,
    })
    return data
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  useEffect(() => {
    if (runId) return
    setPhases(phasesFromSpecText(specText))
  }, [specText, runId])

  useEffect(() => {
    if (!runId) return undefined

    let cancelled = false
    let timer = null

    const tick = async () => {
      try {
        if (!cancelled) {
          const data = await fetchStatus(runId)
          setError(null)
          const upper = String(data?.status || '').toUpperCase()
          // Poll rápido enquanto executa; mais lento em gate humano / fim.
          const nextMs =
            upper === 'RUNNING' ? 800 : upper === 'AWAITING_APPROVAL' ? 2000 : 5000
          if (!cancelled) {
            timer = window.setTimeout(tick, nextMs)
          }
          return
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message || 'Falha ao buscar status')
          timer = window.setTimeout(tick, 2000)
        }
      }
    }

    tick()

    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [runId, fetchStatus])

  // Atualiza histórico quando o run termina ou muda de status relevante
  useEffect(() => {
    if (!runStatus) return
    const upper = String(runStatus).toUpperCase()
    if (upper === 'COMPLETED' || upper === 'RUNNING' || upper === 'AWAITING_APPROVAL') {
      fetchHistory()
    }
  }, [runStatus, fetchHistory])

  const runGenerateSpec = async (prompt, structuredRequirements = null) => {
    setGeneratingSpec(true)
    try {
      const body = { prompt }
      if (structuredRequirements) {
        body.structured_requirements = structuredRequirements
      }
      const { data } = await axios.post(
        `${API_BASE}/api/pipeline/generate-spec`,
        body,
      )
      const spec = data?.spec ?? data
      const nextText = JSON.stringify(spec, null, 2)
      setSpecText(nextText)
      setPhases(phasesFromSpecText(nextText))
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || 'Falha ao transformar em Pipeline Spec',
      )
    } finally {
      setGeneratingSpec(false)
    }
  }

  const handleDraftOrGenerate = async () => {
    setError(null)
    const prompt = naturalPrompt.trim()
    const check = analyzePromptSufficiency(prompt)
    if (!check.ok) {
      setError(
        'Pedido ainda insuficiente. Complete os critérios abaixo da caixa de descrição antes de gerar o Spec.',
      )
      return
    }

    // Já revisou o rascunho software → confirma e gera Spec
    if (requirementsReady && requirementsDraft?.perfil_sugerido === 'software_saas') {
      await runGenerateSpec(prompt, requirementsDraft)
      return
    }

    setDraftingRequirements(true)
    try {
      const { data } = await axios.post(
        `${API_BASE}/api/pipeline/draft-requirements`,
        { prompt },
      )
      const structured = data?.structured_requirements
      const skipPanel = Boolean(data?.skip_panel) || structured?.perfil_sugerido === 'artefato'

      if (skipPanel || !structured) {
        setRequirementsDraft(null)
        setRequirementsReady(false)
        await runGenerateSpec(prompt, null)
        return
      }

      setRequirementsDraft(structured)
      setRequirementsReady(true)
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || 'Falha ao rascunhar requisitos',
      )
    } finally {
      setDraftingRequirements(false)
    }
  }

  const handleStart = async () => {
    setError(null)

    let spec
    try {
      spec = JSON.parse(specText)
    } catch {
      setError('JSON da Pipeline Spec inválido.')
      return
    }

    const prompt = naturalPrompt.trim()
    if (prompt) {
      spec = {
        ...spec,
        description: prompt.slice(0, 800),
        user_prompt: prompt,
      }
    }
    if (requirementsDraft?.perfil_sugerido === 'software_saas') {
      spec = { ...spec, structured_requirements: requirementsDraft }
    }
    spec = { ...spec, auto_approve: Boolean(autoApprove) }
    setSpecText(JSON.stringify(spec, null, 2))

    if (!spec.phases || !Object.keys(spec.phases).length) {
      setError('Spec sem fases. Gere o Pipeline Spec a partir da descrição antes de iniciar.')
      return
    }

    setStarting(true)
    const draftPhases = phasesFromSpecText(JSON.stringify(spec))
    // Feedback imediato na barra: 1ª fase já como Executando.
    if (draftPhases.length) {
      draftPhases[0] = { ...draftPhases[0], status: 'RUNNING' }
    }
    setPhases(draftPhases)
    setRunStatus('RUNNING')

    try {
      const body = { spec }
      if (pendingSubstituteRunId) {
        body.existing_run_id = pendingSubstituteRunId
      }
      const { data } = await axios.post(`${API_BASE}/api/pipeline/start`, body)
      // runId cedo → poll começa enquanto a 1ª fase ainda roda no backend
      setRunId(data.run_id)
      setPendingSubstituteRunId(null)
      setRunStatus(data.status || 'RUNNING')
      if (data.phase_id) {
        setPhases((prev) =>
          prev.map((p) =>
            p.phase_id === data.phase_id
              ? { ...p, status: 'RUNNING' }
              : p.status === 'RUNNING' && p.phase_id !== data.phase_id
                ? { ...p, status: 'PENDING' }
                : p,
          ),
        )
      }
      await fetchStatus(data.run_id)
      await fetchHistory()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Falha ao iniciar pipeline')
      setRunStatus(null)
    } finally {
      setStarting(false)
    }
  }

  const handleAutoApproveToggle = async (checked) => {
    setAutoApprove(checked)
    try {
      const nextSpec = JSON.parse(specText)
      nextSpec.auto_approve = Boolean(checked)
      setSpecText(JSON.stringify(nextSpec, null, 2))
    } catch {
      /* Spec JSON inválido — checkbox ainda vale no próximo start */
    }
    if (!runId) return
    try {
      await axios.patch(`${API_BASE}/api/pipeline/${runId}/auto-approve`, {
        auto_approve: Boolean(checked),
      })
      await fetchStatus(runId, { syncSpec: true })
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || 'Falha ao atualizar auto-aprovação',
      )
    }
  }

  const handleReopen = async (phaseId) => {
    if (!runId || !phaseId) return
    setError(null)
    setReopeningPhaseId(phaseId)
    try {
      await axios.post(`${API_BASE}/api/pipeline/${runId}/phases/${phaseId}/reopen`)
      await fetchStatus(runId)
      await fetchHistory()
      setStatusBarBump((n) => n + 1)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Falha ao reabrir fase')
    } finally {
      setReopeningPhaseId(null)
    }
  }

  const handleApprove = async (taskToken, modifiedArtifact) => {
    setError(null)
    setApprovingToken(taskToken)

    // Otimista: fase atual aprovada; próxima pendente vira Executando na barra.
    setPhases((prev) => {
      const idx = prev.findIndex((p) => p.task_token === taskToken)
      if (idx < 0) return prev
      return prev.map((p, i) => {
        if (i === idx) return { ...p, status: 'APPROVED', task_token: null }
        if (i === idx + 1 && (p.status === 'PENDING' || !p.status)) {
          return { ...p, status: 'RUNNING' }
        }
        return p
      })
    })
    setRunStatus('RUNNING')

    try {
      const body = { approver: 'operator' }
      if (modifiedArtifact != null && typeof modifiedArtifact === 'object') {
        body.modified_artifact = modifiedArtifact
      }
      await axios.post(`${API_BASE}/api/pipeline/approve/${taskToken}`, body)
      if (runId) await fetchStatus(runId)
      await fetchHistory()
      setStatusBarBump((n) => n + 1)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Falha ao aprovar fase')
    } finally {
      setApprovingToken(null)
    }
  }

  const handleDeliverModule = async (phaseId, modulo) => {
    if (!runId || !phaseId || !modulo) return
    setError(null)
    setDeliveringModulo(modulo)
    try {
      await axios.post(
        `${API_BASE}/api/pipeline/${runId}/phases/${phaseId}/modules/deliver`,
        { modulo },
      )
      await fetchStatus(runId)
      setStatusBarBump((n) => n + 1)
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || 'Falha ao marcar módulo entregue',
      )
    } finally {
      setDeliveringModulo(null)
    }
  }

  const handleSelectHistory = async (selectedRunId) => {
    setError(null)
    setPendingSubstituteRunId(null)
    try {
      setRunId(selectedRunId)
      const data = await fetchStatus(selectedRunId, { syncSpec: true })
      const spec = data?.spec && typeof data.spec === 'object' ? data.spec : null
      if (spec) {
        const initial = extractInitialPromptFromSpec(spec)
        if (initial) setNaturalPrompt(initial)
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Falha ao recuperar pipeline')
    }
  }

  const handleNewCreation = () => {
    setError(null)
    setNaturalPrompt('')
    setSpecText(BLANK_SPEC)
    setRunId(null)
    setRunStatus(null)
    setPhases([])
    setApprovingToken(null)
    setStarting(false)
    setGeneratingSpec(false)
    setDraftingRequirements(false)
    setRequirementsDraft(null)
    setRequirementsReady(false)
    setCanAccept(false)
    setImmutable(false)
    setProjectMeta(null)
    setPendingSubstituteRunId(null)
    setStatusBarBump((n) => n + 1)
  }

  const handleAcceptProject = async () => {
    if (!runId) return
    setError(null)
    setAccepting(true)
    try {
      await axios.post(`${API_BASE}/api/pipeline/${runId}/accept`, {})
      await fetchStatus(runId, { syncSpec: true })
      await fetchHistory()
      setAcceptedPanelKey((n) => n + 1)
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || 'Falha ao aceitar o projeto',
      )
    } finally {
      setAccepting(false)
    }
  }

  const handleSubstituteCreated = (data) => {
    if (!data?.spec) return
    setError(null)
    setPendingSubstituteRunId(data.run_id)
    setRunId(null)
    setRunStatus('pending')
    setPhases(phasesFromSpecText(JSON.stringify(data.spec, null, 2)))
    setSpecText(JSON.stringify(data.spec, null, 2))
    setNaturalPrompt(
      typeof data.spec.user_prompt === 'string' ? data.spec.user_prompt : '',
    )
    setCanAccept(false)
    setImmutable(false)
    setProjectMeta({
      project_key: data.project_key,
      project_name: data.project_name,
      version: data.version,
      acceptance_status: 'open',
    })
    setStatusBarBump((n) => n + 1)
    fetchHistory()
  }

  const planPhases = useMemo(() => {
    if (phases?.length) return phases
    return phasesFromSpecText(specText)
  }, [phases, specText])

  const linearExportCandidate = useMemo(
    () => (runId ? findLinearExportCandidate(planPhases) : null),
    [runId, planPhases],
  )

  return (
    <div className="min-h-screen font-body text-slate-900">
      <header className="border-b border-slate-200/80 bg-white/75 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-950 text-emerald-400">
              <Workflow className="h-6 w-6" />
            </div>
            <div className="text-left">
              <p className="font-display text-2xl font-semibold tracking-tight text-slate-950">
                Phanton
              </p>
              <p className="text-sm text-slate-500">Orquestração de Pipeline Multi-Modelo</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {projectMeta?.version ? (
              <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700">
                {projectMeta.project_name || 'Projeto'}
                <span className="mx-1 text-slate-300">·</span>
                v{projectMeta.version}
              </span>
            ) : null}
            {immutable ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800">
                <Lock className="h-3.5 w-3.5" />
                Aceito · imutável
              </span>
            ) : null}
            <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700">
              <Activity className="h-3.5 w-3.5 text-emerald-500" />
              {runId ? (
                <span>
                  Run <span className="font-mono">{String(runId).slice(0, 8)}</span>
                  {runStatus ? ` · ${runStatus}` : ''}
                </span>
              ) : pendingSubstituteRunId ? (
                <span>
                  Substituto{' '}
                  <span className="font-mono">
                    {String(pendingSubstituteRunId).slice(0, 8)}
                  </span>{' '}
                  · revise e inicie
                </span>
              ) : (
                <span>Nenhum run ativo</span>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8">
        {/* Painel de Controle — horizontal */}
        <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur">
          <div className="text-left">
            <h2 className="font-display text-lg font-semibold text-slate-950">
              Painel de Controle
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              1) Descreva à esquerda · 2) Transforme no botão do meio · 3) Revise o
              JSON · 4) Inicie o pipeline.
            </p>
          </div>

          <div className="mt-4 flex flex-col items-stretch gap-3 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:items-stretch lg:gap-2">
            <div className="flex flex-col rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <label className="block text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                1 · O que você deseja construir? (Linguagem Natural)
              </label>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                Inclua no texto:{' '}
                {PROMPT_COMPOSITION_HINTS.map((hint, i) => (
                  <span key={hint}>
                    {i > 0 ? ' · ' : ''}
                    <span className="font-medium text-slate-600">{hint}</span>
                  </span>
                ))}
                .
              </p>
              <FixedTextField
                className="mt-2"
                value={naturalPrompt}
                readOnly={false}
                onChange={(e) => {
                  setNaturalPrompt(e.target.value)
                  setRequirementsDraft(null)
                  setRequirementsReady(false)
                }}
                aria-label="Descrição em linguagem natural"
              />

              {requirementsReady &&
              requirementsDraft?.perfil_sugerido === 'software_saas' ? (
                <RequirementsDraftPanel
                  value={requirementsDraft}
                  onChange={setRequirementsDraft}
                />
              ) : null}

              <div
                className={`mt-3 rounded-lg border px-3 py-2.5 text-left ${
                  !naturalPrompt.trim()
                    ? 'border-slate-200 bg-white/80'
                    : sufficiency.ok
                      ? 'border-emerald-200 bg-emerald-50/80'
                      : 'border-amber-200 bg-amber-50/80'
                }`}
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                    Suficiência do pedido
                  </p>
                  <span className="text-[11px] font-medium text-slate-500">
                    {sufficiency.passed}/{sufficiency.total}
                    {sufficiency.ok ? ' · pronto' : naturalPrompt.trim() ? ' · incompleto' : ''}
                  </span>
                </div>
                <ul className="space-y-1.5">
                  {sufficiency.checks.map((item) => (
                    <li key={item.id} className="flex items-start gap-2 text-xs text-slate-700">
                      {item.pass ? (
                        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                      ) : naturalPrompt.trim() ? (
                        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                      ) : (
                        <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-300" />
                      )}
                      <span>
                        <span className={item.pass ? 'font-medium text-slate-800' : ''}>
                          {item.label}
                        </span>
                        {!item.pass ? (
                          <span className="mt-0.5 block text-[11px] text-slate-500">
                            {item.hint}
                          </span>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
                {!sufficiency.ok && naturalPrompt.trim() ? (
                  <p className="mt-2 text-[11px] text-amber-800">
                    Faltam itens essenciais (objetivo e formato da entrega). Complete-os
                    para liberar o Spec.
                  </p>
                ) : null}
              </div>
            </div>

            <div className="flex items-center justify-center lg:px-1">
              <button
                type="button"
                onClick={handleDraftOrGenerate}
                disabled={generatingSpec || draftingRequirements || !sufficiency.ok}
                title={
                  !sufficiency.ok
                    ? 'Complete a suficiência do pedido antes de continuar'
                    : requirementsReady &&
                        requirementsDraft?.perfil_sugerido === 'software_saas'
                      ? 'Gera o Spec com os requisitos revisados'
                      : 'Analisa o pedido (rascunho 29148) e segue para o Spec'
                }
                className="inline-flex w-auto items-center justify-center gap-1.5 rounded-lg bg-emerald-900 px-3 py-2 font-display text-xs font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-70 lg:w-[8.5rem] lg:flex-col lg:gap-1 lg:px-2.5 lg:py-3 lg:text-center lg:leading-snug"
              >
                {draftingRequirements || generatingSpec ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                    <span>
                      {draftingRequirements ? 'Analisando…' : 'Gerando…'}
                    </span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5 shrink-0" />
                    <span>
                      {requirementsReady &&
                      requirementsDraft?.perfil_sugerido === 'software_saas'
                        ? 'Confirmar e gerar Spec'
                        : 'Analisar pedido'}
                    </span>
                  </>
                )}
              </button>
            </div>

            <div className="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <label className="block shrink-0 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                2 · Pipeline Spec (revise antes de iniciar)
              </label>
              {contextWarnings.length > 0 ? (
                <div
                  className="mt-2 rounded-xl border border-amber-400 bg-amber-50 px-3 py-3 text-left shadow-[0_0_0_1px_rgba(245,158,11,0.25)]"
                  role="status"
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
                    <div className="min-w-0 flex-1">
                      <p className="font-display text-sm font-semibold text-amber-950">
                        Lacunas de contexto no pedido ({contextWarnings.length})
                      </p>
                      <p className="mt-0.5 text-xs text-amber-900/80">
                        A geração não foi bloqueada — revise o pedido ou aceite o risco
                        antes de iniciar o pipeline.
                      </p>
                      <ul className="mt-2 space-y-2">
                        {contextWarnings.map((w, idx) => (
                          <li
                            key={`${w.campo || 'w'}-${idx}`}
                            className="rounded-lg border border-amber-200 bg-white/70 px-2.5 py-2 text-xs text-amber-950"
                          >
                            <span className="font-semibold">
                              {w.campo || 'aviso'}
                              {w.descricao ? ': ' : ''}
                            </span>
                            {w.descricao || ''}
                            {w.impacto ? (
                              <span className="mt-1 block text-[11px] text-amber-800/90">
                                Impacto: {w.impacto}
                              </span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ) : null}
              <CopyableBlock
                className="mt-2 flex min-h-0 flex-1 flex-col"
                label="Copiar JSON"
                buttonClassName="border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400 hover:bg-slate-700 hover:text-white"
                text={specText}
              >
                <FixedTextField
                  className="!h-full min-h-[12rem] flex-1"
                  value={specText}
                  readOnly={false}
                  onChange={(e) => setSpecText(e.target.value)}
                  aria-label="Pipeline Spec JSON"
                />
              </CopyableBlock>
            </div>
          </div>
          <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-left">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 rounded border-slate-300 text-emerald-700 focus:ring-emerald-600"
              checked={autoApprove}
              onChange={(e) => handleAutoApproveToggle(e.target.checked)}
            />
            <span>
              <span className="block font-display text-sm font-semibold text-slate-900">
                Aprovação automática quando a qualidade for alta
              </span>
              <span className="mt-0.5 block text-xs text-slate-500">
                Default desligado. Com o switch ligado, fases com nota ≥ 80 avançam sozinhas
                (exceto security_guidelines, que continua pedindo revisão humana).
              </span>
            </span>
          </label>

          <button
            type="button"
            onClick={handleStart}
            disabled={starting || generatingSpec || immutable}
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-700 via-emerald-600 to-lime-500 px-4 py-3.5 font-display text-sm font-semibold text-white shadow-[0_8px_24px_rgba(16,185,129,0.35)] transition hover:from-emerald-800 hover:via-emerald-700 hover:to-lime-600 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {starting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Iniciando…
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                {pendingSubstituteRunId
                  ? 'Iniciar pipeline substituto'
                  : 'Iniciar Pipeline'}
              </>
            )}
          </button>

          {linearExportCandidate ? (
            <div className="mt-4 rounded-xl border border-[#5E6AD2]/40 bg-[#5E6AD2]/8 px-4 py-4 text-left">
              <p className="font-display text-sm font-semibold text-slate-950">
                Integração Linear disponível
              </p>
              <p className="mt-1 text-xs leading-relaxed text-slate-600">
                O Task Breakdown foi aprovado
                {linearExportCandidate.epics?.length
                  ? ` (${linearExportCandidate.epics.length} épicos)`
                  : ''}
                . Mesmo sem pedir Linear no texto inicial, você pode exportar
                Epics/Issues agora.
              </p>
              <LinearExportButton
                className="mt-3"
                runId={runId}
                apiBase={API_BASE}
                epicCount={linearExportCandidate.epics.length}
                compact
              />
            </div>
          ) : null}

          {canAccept ? (
            <div className="mt-4 rounded-xl border border-emerald-300 bg-emerald-50/90 px-4 py-4 text-left">
              <p className="font-display text-sm font-semibold text-emerald-950">
                Pipeline completo — revise antes de aceitar
              </p>
              <p className="mt-1 text-xs text-emerald-900/80">
                Ao aceitar, esta versão ({projectMeta?.version || '1.0'}) fica imutável.
                Depois disso, retorno e evolução criam um pipeline substituto com nova
                versão.
              </p>
              <button
                type="button"
                onClick={handleAcceptProject}
                disabled={accepting}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-800 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
              >
                {accepting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ShieldCheck className="h-3.5 w-3.5" />
                )}
                Aceitar projeto
              </button>
            </div>
          ) : null}

          {error && (
            <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-left text-sm text-red-700">
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </p>
          )}
        </section>

        <PipelineStatusBar
          phases={planPhases}
          runId={runId}
          runStatus={runStatus}
          bumpKey={statusBarBump}
        />

        <RunHistory
          items={historyItems}
          total={historyTotal}
          loading={historyLoading}
          activeRunId={runId}
          onSelect={handleSelectHistory}
          onRefresh={fetchHistory}
          onNewCreation={handleNewCreation}
        />

        <AcceptedProjectsPanel
          key={acceptedPanelKey}
          apiBase={API_BASE}
          onError={setError}
          onSubstituteCreated={handleSubstituteCreated}
        />

        {/* Plano Geral */}
        <section className="rounded-2xl border border-slate-200 bg-white/85 p-6 shadow-sm backdrop-blur">
          <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="text-left">
              <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Plano Geral
              </p>
              <h2 className="font-display mt-1 text-2xl font-semibold text-slate-950">
                Fases do Pipeline
              </h2>
              <p className="mt-1 max-w-2xl text-sm text-slate-500">
                Topologia DAG (paralelismo e dependências) ou lista detalhada com
                artefatos e aprovação.
                {immutable ? ' Esta versão foi aceita e está imutável.' : ''}
              </p>
            </div>
            <div
              className="inline-flex shrink-0 rounded-xl border border-slate-200 bg-slate-50 p-1"
              role="tablist"
              aria-label="Visualização das fases"
            >
              <button
                type="button"
                role="tab"
                aria-selected={phasesView === 'graph'}
                onClick={() => setPhasesView('graph')}
                className={`rounded-lg px-3.5 py-2 font-display text-xs font-semibold transition ${
                  phasesView === 'graph'
                    ? 'bg-white text-slate-950 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Grafo DAG
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={phasesView === 'list'}
                onClick={() => setPhasesView('list')}
                className={`rounded-lg px-3.5 py-2 font-display text-xs font-semibold transition ${
                  phasesView === 'list'
                    ? 'bg-white text-slate-950 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Detalhes
              </button>
            </div>
          </div>

          {phasesView === 'graph' ? (
            <PipelineGraph
              spec={parsedSpec}
              phases={planPhases}
              onApprove={immutable ? undefined : handleApprove}
              approvingToken={approvingToken}
              immutable={immutable}
              runId={runId}
              apiBase={API_BASE}
            />
          ) : (
            <div className="max-w-3xl">
              {planPhases.map((phase, index) => (
                <PhaseCard
                  key={`${runId || pendingSubstituteRunId || 'draft'}-${phase.phase_id}`}
                  phaseId={phase.phase_id}
                  name={phase.name}
                  status={phase.status}
                  artifactData={phase.artifact_data}
                  taskToken={immutable ? null : phase.task_token}
                  approver={phase.approver}
                  isLast={index === planPhases.length - 1}
                  approving={approvingToken === phase.task_token}
                  onApprove={immutable ? undefined : handleApprove}
                  canDeliverModules={Boolean(runId) && !immutable}
                  deliveringModulo={deliveringModulo}
                  onDeliverModule={(modulo) => handleDeliverModule(phase.phase_id, modulo)}
                  autoApproveEnabled={autoApprove}
                  reopening={reopeningPhaseId === phase.phase_id}
                  onReopen={immutable ? undefined : handleReopen}
                  runId={runId}
                  apiBase={API_BASE}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App

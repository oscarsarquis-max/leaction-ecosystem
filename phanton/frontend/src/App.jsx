import { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Activity, Loader2, Play, Sparkles, Workflow } from 'lucide-react'
import CopyableBlock from './components/CopyableBlock'
import FixedTextField from './components/FixedTextField'
import PhaseCard from './components/PhaseCard'
import PipelineStatusBar from './components/PipelineStatusBar'
import RunHistory from './components/RunHistory'

const API_BASE = 'http://localhost:8000'

const DEFAULT_SPEC = `{
  "description": "Exemplo: metodologia + pesquisas + síntese + entrega final (artefato pedido pelo usuário)",
  "version": "1.0",
  "phases": {
    "metodologia": {
      "name": "Alinhamento metodológico",
      "type": "methodology",
      "order": 1,
      "descricao": "Definir princípios e abordagem do projeto"
    },
    "pesquisa_casos": {
      "name": "Pesquisa de casos reais",
      "type": "research",
      "order": 2,
      "descricao": "Buscar casos reais e referências de domínio"
    },
    "pesquisa_stack": {
      "name": "Pesquisa de stack técnica",
      "type": "research",
      "order": 3,
      "descricao": "Buscar práticas e bibliotecas recomendadas para a implementação"
    },
    "sintese": {
      "name": "Síntese integrada",
      "type": "synthesize",
      "order": 4,
      "depends_on": ["metodologia", "pesquisa_casos", "pesquisa_stack"],
      "descricao": "Agrupar metodologia e as duas pesquisas num plano coerente"
    },
    "entrega_final": {
      "name": "Entrega final",
      "type": "prompt",
      "order": 5,
      "depends_on": ["sintese"],
      "descricao": "Produzir o artefato final pedido pelo usuário (apresentação, documento ou protótipo), usando a síntese como fonte da verdade. Não gerar prompt intermediário."
    }
  }
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

function App() {
  const [naturalPrompt, setNaturalPrompt] = useState('')
  const [specText, setSpecText] = useState(DEFAULT_SPEC)
  const [runId, setRunId] = useState(null)
  const [runStatus, setRunStatus] = useState(null)
  const [phases, setPhases] = useState(() => phasesFromSpecText(DEFAULT_SPEC))
  const [starting, setStarting] = useState(false)
  const [generatingSpec, setGeneratingSpec] = useState(false)
  const [approvingToken, setApprovingToken] = useState(null)
  const [error, setError] = useState(null)
  const [historyItems, setHistoryItems] = useState([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [statusBarBump, setStatusBarBump] = useState(0)

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
    if (syncSpec && data.spec) {
      setSpecText(JSON.stringify(data.spec, null, 2))
    }
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

    const tick = async () => {
      try {
        if (!cancelled) {
          await fetchStatus(runId)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message || 'Falha ao buscar status')
        }
      }
    }

    tick()
    const timer = setInterval(tick, 3000)

    return () => {
      cancelled = true
      clearInterval(timer)
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

  const handleGenerateSpec = async () => {
    setError(null)
    const prompt = naturalPrompt.trim()
    if (prompt.length < 8) {
      setError('Descreva o que deseja construir com um pouco mais de detalhe.')
      return
    }

    setGeneratingSpec(true)
    try {
      const { data } = await axios.post(`${API_BASE}/api/pipeline/generate-spec`, {
        prompt,
      })
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

  const handleStart = async () => {
    setError(null)

    let spec
    try {
      spec = JSON.parse(specText)
    } catch {
      setError('JSON da Pipeline Spec inválido.')
      return
    }

    setStarting(true)
    setPhases(phasesFromSpecText(specText))
    setRunStatus('RUNNING')

    try {
      const { data } = await axios.post(`${API_BASE}/api/pipeline/start`, { spec })
      setRunId(data.run_id)
      setRunStatus(data.status)
      await fetchStatus(data.run_id)
      await fetchHistory()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Falha ao iniciar pipeline')
      setRunStatus(null)
    } finally {
      setStarting(false)
    }
  }

  const handleApprove = async (taskToken, modifiedArtifact) => {
    setError(null)
    setApprovingToken(taskToken)

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

  const handleSelectHistory = async (selectedRunId) => {
    setError(null)
    try {
      setRunId(selectedRunId)
      await fetchStatus(selectedRunId, { syncSpec: true })
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Falha ao recuperar pipeline')
    }
  }

  const planPhases = useMemo(() => {
    if (phases?.length) return phases
    return phasesFromSpecText(specText)
  }, [phases, specText])

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

          <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700">
            <Activity className="h-3.5 w-3.5 text-emerald-500" />
            {runId ? (
              <span>
                Run <span className="font-mono">{String(runId).slice(0, 8)}</span>
                {runStatus ? ` · ${runStatus}` : ''}
              </span>
            ) : (
              <span>Nenhum run ativo</span>
            )}
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
              Descreva em linguagem natural, revise o JSON gerado e inicie o pipeline.
            </p>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <label className="block text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                O que você deseja construir? (Linguagem Natural)
              </label>
              <FixedTextField
                className="mt-2"
                value={naturalPrompt}
                readOnly={false}
                onChange={(e) => setNaturalPrompt(e.target.value)}
                aria-label="Descrição em linguagem natural"
              />
              <button
                type="button"
                onClick={handleGenerateSpec}
                disabled={generatingSpec}
                className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-900 px-4 py-3 font-display text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {generatingSpec ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Gerando Spec…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Transformar em Pipeline Spec
                  </>
                )}
              </button>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <label className="block text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                Pipeline Spec (revise antes de iniciar)
              </label>
              <CopyableBlock
                className="mt-2"
                label="Copiar JSON"
                buttonClassName="border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400 hover:bg-slate-700 hover:text-white"
                text={specText}
              >
                <FixedTextField
                  value={specText}
                  readOnly={false}
                  onChange={(e) => setSpecText(e.target.value)}
                  aria-label="Pipeline Spec JSON"
                />
              </CopyableBlock>
            </div>
          </div>

          <button
            type="button"
            onClick={handleStart}
            disabled={starting || generatingSpec}
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
                Iniciar Pipeline
              </>
            )}
          </button>

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
        />

        {/* Plano Geral */}
        <section className="rounded-2xl border border-slate-200 bg-white/85 p-6 shadow-sm backdrop-blur">
          <div className="mb-6 text-left">
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
              Plano Geral
            </p>
            <h2 className="font-display mt-1 text-2xl font-semibold text-slate-950">
              Fases do Pipeline
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">
              Resultados de cada fase são persistidos no banco. Selecione um item do
              histórico para recuperar artefatos anteriores, ou acompanhe o run ativo.
            </p>
          </div>

          <div className="max-w-3xl">
            {planPhases.map((phase, index) => (
              <PhaseCard
                key={`${runId || 'draft'}-${phase.phase_id}`}
                phaseId={phase.phase_id}
                name={phase.name}
                status={phase.status}
                artifactData={phase.artifact_data}
                taskToken={phase.task_token}
                isLast={index === planPhases.length - 1}
                approving={approvingToken === phase.task_token}
                onApprove={handleApprove}
              />
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
